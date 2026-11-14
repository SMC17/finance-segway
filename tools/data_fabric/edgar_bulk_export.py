"""Export the SEC EDGAR filing record in bulk, with a SHA-256 manifest.

What "all of EDGAR" means here, and what it does not
----------------------------------------------------
EDGAR holds every electronic filing since 1993: tens of millions of
documents and tens of terabytes. No git repository holds that, and a copy
of it is worth nothing that SEC's own archive does not already provide.
This tool exports the three public bulk products that together describe
every filing and every XBRL fact:

  1. ``full-index/<year>/QTR<n>/master.gz`` for every quarter from 1993 Q1:
     one row per filing per associated entity (CIK, entity name, form type,
     date filed, archive path). Together these list every filing on EDGAR.
  2. ``daily-index/bulkdata/submissions.zip``: one JSON per entity with its
     SIC code, tickers, state of incorporation, former names, and filing
     history including 8-K item numbers.
  3. ``daily-index/xbrl/companyfacts.zip``: every XBRL financial fact every
     filer has reported, as the companyfacts API serves it.

The raw files go to ``--out`` (default ``.sec-export/``, which git ignores).
The manifest goes to ``tools/data_fabric/out/edgar_export/manifest.json``
and records, for every file, its URL, byte size, SHA-256 digest, and the
server's Last-Modified header. Anyone can re-run the export and check that
they received the same bytes.

Quarterly files that already exist locally and match the server's size are
not downloaded again, except the current quarter, which SEC rewrites daily.

SEC fair access: at most 10 requests per second, with a User-Agent that
names the requester. Set ``SEC_USER_AGENT="Name contact@example.org"``.

Usage:
    python tools/data_fabric/edgar_bulk_export.py                 # everything
    python tools/data_fabric/edgar_bulk_export.py --skip-bulk     # indexes only
    python tools/data_fabric/edgar_bulk_export.py --since 2024    # recent quarters
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools" / "data_fabric" / "out" / "edgar_export" / "manifest.json"
BASE = "https://www.sec.gov/Archives/edgar"
BULK = {
    "submissions": f"{BASE}/daily-index/bulkdata/submissions.zip",
    "companyfacts": f"{BASE}/daily-index/xbrl/companyfacts.zip",
}
FIRST_YEAR = 1993
MIN_INTERVAL_S = 0.15  # stays under SEC's 10 requests/second ceiling


def user_agent() -> str:
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise SystemExit(
            "SEC_USER_AGENT is not set. SEC fair-access rules require a "
            'User-Agent naming the requester, e.g. "Name contact@example.org".'
        )
    return ua


class Fetcher:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"})
        self._last = 0.0

    def _wait(self) -> None:
        delay = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def head(self, url: str) -> requests.Response:
        self._wait()
        return self.session.head(url, timeout=60, allow_redirects=True)

    def download(self, url: str, dest: Path, attempts: int = 4) -> dict[str, Any]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        for attempt in range(1, attempts + 1):
            self._wait()
            try:
                with self.session.get(url, stream=True, timeout=120) as resp:
                    if resp.status_code == 404:
                        return {"url": url, "status": 404}
                    resp.raise_for_status()
                    digest = hashlib.sha256()
                    size = 0
                    with tmp.open("wb") as fh:
                        for chunk in resp.raw.stream(1 << 20, decode_content=False):
                            fh.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                    expected = resp.headers.get("Content-Length")
                    if expected is not None and int(expected) != size:
                        raise IOError(f"short read: {size} of {expected} bytes")
                    tmp.replace(dest)
                    return {
                        "url": url,
                        "status": 200,
                        "bytes": size,
                        "sha256": digest.hexdigest(),
                        "last_modified": resp.headers.get("Last-Modified"),
                    }
            except (requests.RequestException, IOError) as exc:
                if attempt == attempts:
                    raise
                print(f"  retry {attempt} for {url}: {exc}", file=sys.stderr)
                time.sleep(2 ** attempt)
        raise AssertionError("unreachable")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quarters(since: int, today: date) -> Iterator[tuple[int, int]]:
    current = (today.year, (today.month - 1) // 3 + 1)
    for year in range(since, today.year + 1):
        for qtr in range(1, 5):
            if (year, qtr) > current:
                return
            yield year, qtr


def export(out: Path, since: int, skip_bulk: bool, today: date, bulk: list[str] | None = None) -> dict[str, Any]:
    fetcher = Fetcher()
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    known = {item["path"]: item for item in previous.get("files", [])}
    current = (today.year, (today.month - 1) // 3 + 1)
    # Quarters before --since keep their prior manifest rows, so a partial
    # run updates the manifest instead of truncating it.
    files: list[dict[str, Any]] = [
        item for item in previous.get("files", [])
        if item.get("kind") == "quarterly_master_index" and int(item["path"].split("/")[1]) < since
    ]

    for year, qtr in quarters(since, today):
        rel = f"full-index/{year}/QTR{qtr}/master.gz"
        dest = out / rel
        url = f"{BASE}/{rel}"
        prior = known.get(rel)
        if dest.exists() and prior and (year, qtr) != current and dest.stat().st_size == prior.get("bytes"):
            files.append(prior)
            continue
        record = fetcher.download(url, dest)
        if record["status"] != 200:
            print(f"  {rel}: HTTP {record['status']}", file=sys.stderr)
            continue
        record["path"] = rel
        record["kind"] = "quarterly_master_index"
        files.append(record)
        print(f"  {rel}: {record['bytes']:,} bytes")

    wanted = [] if skip_bulk else (bulk or list(BULK))
    for name, url in BULK.items():
        if name not in wanted:
            files.extend(item for item in previous.get("files", []) if item.get("kind") == f"bulk_{name}")
            continue
        rel = f"bulk/{name}.zip"
        dest = out / rel
        head = fetcher.head(url)
        remote_size = int(head.headers.get("Content-Length", -1))
        if dest.exists() and dest.stat().st_size == remote_size:
            record = {
                "url": url,
                "status": 200,
                "bytes": remote_size,
                "sha256": sha256_file(dest),
                "last_modified": head.headers.get("Last-Modified"),
            }
        else:
            record = fetcher.download(url, dest)
        record["path"] = rel
        record["kind"] = f"bulk_{name}"
        files.append(record)
        print(f"  {rel}: {record['bytes']:,} bytes")

    manifest = {
        "schema_version": "1.0",
        "generated_by": "tools/data_fabric/edgar_bulk_export.py",
        "exported_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "SEC EDGAR public archive (https://www.sec.gov/Archives/edgar)",
        "license_or_restriction": "Public SEC data; SEC website terms and fair-access policy apply",
        "scope": (
            "Quarterly master indexes from 1993 Q1 list every EDGAR filing; the "
            "submissions and companyfacts bulk archives carry entity metadata, filing "
            "histories, and every reported XBRL fact. Filing documents themselves are "
            "not copied: each index row carries the archive path to fetch one."
        ),
        "raw_location": "not committed; re-run this tool to reproduce, then compare sha256",
        "quarter_count": sum(1 for f in files if f["kind"] == "quarterly_master_index"),
        "files": sorted(files, key=lambda f: f["path"]),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", type=Path, default=ROOT / ".sec-export")
    parser.add_argument("--since", type=int, default=FIRST_YEAR)
    parser.add_argument("--skip-bulk", action="store_true", help="indexes only; keep bulk rows from the prior manifest")
    parser.add_argument("--bulk", nargs="+", choices=sorted(BULK), help="bulk archives to fetch (default: all)")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    manifest = export(args.out.resolve(), args.since, args.skip_bulk, args.as_of, args.bulk)
    total = sum(f.get("bytes", 0) for f in manifest["files"])
    print(f"Exported {len(manifest['files'])} files, {total / 1e9:.2f} GB -> {args.out}")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
