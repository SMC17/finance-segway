"""Pack the EDGAR lineage dataset into one compact JSON for the lineage page.

Reads ``tools/data_fabric/out/edgar_lineage/`` (written by
edgar_corporate_events.py) and writes the ``data.json`` the interactive
lineage page loads. It adds no values: every field is copied or re-keyed
from the lineage dataset, and the page labels each event observed or derived
exactly as the dataset does.

Usage:
    python tools/data_fabric/edgar_lineage_page_data.py --out path/to/data.json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINEAGE = ROOT / "tools" / "data_fabric" / "out" / "edgar_lineage"
STATUS_CODE = {
    "reporting": "R", "ceased:merged_into": "M", "ceased:bankruptcy_filed": "B",
    "ceased:deregistered": "D", "ceased:delisted": "L", "ceased:undisclosed": "U",
}


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def build(src: Path) -> dict:
    summary = json.loads((src / "summary.json").read_text(encoding="utf-8"))
    ents, sic_names, group_sics = [], {}, defaultdict(Counter)
    divisions = {}
    for r in _rows(src / "entities.csv.gz"):
        sic = int(r["sic"]) if r["sic"].isdigit() else 0
        if sic:
            sic_names[sic] = r["sic_description"]
        group = f"{sic:04d}"[:2] if sic else "00"
        group_sics[group][r["sic_description"] or "Unassigned"] += 1
        divisions[group] = r["division"]
        ents.append([
            int(r["cik"]), r["name"], sic,
            int(r["first_periodic"][:4]) if r["first_periodic"] else None,
            r["last_periodic"], STATUS_CODE[r["status"]], r["tickers"].replace(";", " "),
        ])

    merged, bankrupt, renamed, combos = [], [], [], {}
    for r in _rows(src / "events.csv.gz"):
        kind, cik = r["event"], int(r["cik"])
        if kind == "merged_into":
            merged.append([cik, int(r["counterparty"]), r["date"], r["accession"]])
        elif kind == "bankruptcy_filed":
            bankrupt.append([cik, r["date"], r["accession"]])
        elif kind == "renamed":
            # detail reads "formerly NAME (FROM to TO)"
            body = r["detail"].removeprefix("formerly ")
            name, _, span = body.rpartition(" (")
            start, _, end = span.rstrip(")").partition(" to ")
            renamed.append([cik, name, start, end])
        elif kind == "combination_filing":
            other = int(r["counterparty"])
            key = (min(cik, other), max(cik, other))
            combos.setdefault(key, [key[0], key[1], r["date"], r["form"], r["accession"]])

    groups = {}
    for g, counts in group_sics.items():
        largest = counts.most_common(1)[0][0]
        groups[g] = {
            "division": divisions[g],
            "name": f"{len(counts)} SIC codes, largest {largest}" if len(counts) > 1 else largest,
        }
    return {
        "as_of": summary["as_of"],
        "source_sha256": summary["source"]["sha256"],
        "rules": summary["rules"],
        "limits": summary["coverage_limits"],
        "sic": {str(k): v for k, v in sorted(sic_names.items())},
        "groups": groups,
        "ents": ents,
        "merged": merged,
        "bankrupt": bankrupt,
        "renamed": renamed,
        "combos": list(combos.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--src", type=Path, default=LINEAGE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = build(args.src)
    args.out.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB, {len(data['ents']):,} companies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
