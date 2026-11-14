"""Build corporate lineage from SEC EDGAR: renames, mergers, bankruptcies, exits.

Input is the SEC ``submissions.zip`` bulk archive (see edgar_bulk_export.py).
It holds, for every EDGAR entity, its SIC code, former names, and complete
filing history with 8-K item numbers. Everything below comes from that file.

The repository's one rule applies: no value here is invented. Each event
carries a ``basis`` of ``observed`` or ``derived``, and every derived event
names the rule that produced it.

Observed events (read directly off a filing record)
---------------------------------------------------
- ``renamed``            a ``formerNames`` entry: the old name and its dates.
- ``bankruptcy_filed``   an 8-K reporting Item 1.03 (Bankruptcy or
                         Receivership). Item numbers exist on EDGAR from
                         August 2004, so earlier bankruptcies do not appear.
- ``deregistered``       a Form 15 (15-12B, 15-12G, 15-15D): the issuer ended
                         its SEC reporting obligation.
- ``delisted``           a Form 25 or 25-NSE naming the issuer.
- ``form10_registered``  a Form 10-12B or 10-12G: registration of a class of
                         securities without a public offering. Spin-offs
                         register this way, and so do some direct listings.
- ``combination_filing`` the entity appears on a business-combination filing
                         (Form 425, merger proxy, tender offer) together with
                         another entity. EDGAR lists one accession under every
                         party, so the pair is observed, not inferred.

Derived events (computed by a stated rule)
------------------------------------------
- ``merged_into``  Two entities share a business-combination filing. One of
  them (the absorbed entity) files a Form 15 or Form 25 within 730 days after
  their last shared filing, files no periodic report more than 120 days after
  that termination, and the other (the survivor) files a periodic report
  after it. When both or neither entity meets the test, no direction is
  assigned and only the observed ``combination_filing`` remains.
- ``spun_off_from`` A Form 10-12B/10-12G accession lists a second operating
  entity; that entity is recorded as the parent.
- ``ceased_reporting`` An entity that once filed periodic reports and has
  filed none in the 18 months before the as-of date. Its reason is the latest
  terminal event above, or ``undisclosed`` when there is none.

Output (``tools/data_fabric/out/edgar_lineage/``)
-------------------------------------------------
- ``entities.csv.gz``  one row per entity that ever filed a periodic report.
- ``events.csv.gz``    every event above, with accession, date, and basis.
- ``industry_series.json`` per SIC major group and year: reporting
  companies, entrants, and exits by reason.
- ``summary.json``     counts, rules, and the input archive's SHA-256.

Usage:
    python tools/data_fabric/edgar_corporate_events.py --submissions .sec-export/bulk/submissions.zip
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import multiprocessing as mp
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools" / "data_fabric" / "out" / "edgar_lineage"

PERIODIC = ("10-K", "10-Q", "20-F", "40-F", "10-KSB", "10-QSB", "10-K405", "10-KT", "10-QT", "10-KSB40")
DEREGISTER = ("15-12B", "15-12G", "15-15D", "15-12B/A", "15-12G/A", "15-15D/A")
DELIST = ("25", "25-NSE")
FORM10 = ("10-12B", "10-12G")
COMBINATION = (
    "425", "DEFM14A", "PREM14A", "DEFM14C", "PREM14C", "DEFA14M",
    "SC TO-T", "SC TO-T/A", "SC 14D9", "SC 14D9/A", "SC14D1F", "SC 14D1",
)
# A shared accession with more parties than this is a fund-family or
# co-registrant filing, not a two-sided combination.
MAX_PARTIES = 3
ABSORB_WINDOW_DAYS = 730
TRAILING_PERIODIC_DAYS = 120
DARK_AFTER_DAYS = 548  # 18 months

RULES = {
    "merged_into": (
        "Entities A and B share a business-combination accession "
        f"({', '.join(COMBINATION)}). A files Form 15 or Form 25 within "
        f"{ABSORB_WINDOW_DAYS} days after their last shared filing, files no periodic "
        f"report more than {TRAILING_PERIODIC_DAYS} days after that termination, and B "
        "files a periodic report after it. Direction is left unassigned when both or "
        "neither entity passes. When A passes against several counterparties, the one "
        "with the latest shared filing is the survivor; a tie leaves A unassigned."
    ),
    "spun_off_from": "A Form 10-12B/10-12G accession lists a second entity that files periodic reports; that entity is the parent.",
    "ceased_reporting": (
        f"No periodic report in the {DARK_AFTER_DAYS} days before the as-of date, after at "
        "least one. Reason = latest terminal event (merged_into, bankruptcy_filed, "
        "deregistered, delisted), else undisclosed."
    ),
}

# SIC divisions, from the SIC Manual (1987) major-group ranges.
SIC_DIVISIONS = [
    (1, 9, "A", "Agriculture, Forestry, and Fishing"),
    (10, 14, "B", "Mining"),
    (15, 17, "C", "Construction"),
    (20, 39, "D", "Manufacturing"),
    (40, 49, "E", "Transportation, Communications, Electric, Gas, and Sanitary Services"),
    (50, 51, "F", "Wholesale Trade"),
    (52, 59, "G", "Retail Trade"),
    (60, 67, "H", "Finance, Insurance, and Real Estate"),
    (70, 89, "I", "Services"),
    (91, 99, "J", "Public Administration"),
]


def sic_division(sic: str) -> tuple[str, str]:
    if not sic or not sic.isdigit():
        return "", "Unclassified"
    group = int(sic[:2]) if len(sic) == 4 else int(sic) // 100
    for low, high, code, name in SIC_DIVISIONS:
        if low <= group <= high:
            return code, name
    return "", "Unclassified"


def _iter_filings(block: dict) -> Iterable[tuple[str, str, str, str]]:
    forms = block.get("form", [])
    dates = block.get("filingDate", [])
    accs = block.get("accessionNumber", [])
    items = block.get("items", [""] * len(forms))
    for i in range(len(forms)):
        yield accs[i], forms[i], dates[i], items[i] if i < len(items) else ""


def _scan(args: tuple[str, list[str]]) -> list[dict[str, Any]]:
    """Worker: read one slice of the archive, keep entities with periodic reports
    plus the accessions every entity shares on combination and Form 10 filings."""
    path, names = args
    out: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as zf:
        for name in names:
            doc = json.loads(zf.read(name))
            filings = doc.get("filings", {})
            blocks = [filings.get("recent", {})]
            for extra in filings.get("files", []):
                try:
                    blocks.append(json.loads(zf.read(extra["name"])))
                except KeyError:
                    continue
            periodic: list[str] = []
            events: list[tuple[str, str, str, str]] = []
            shared: list[tuple[str, str, str]] = []
            first = last = ""
            for block in blocks:
                for acc, form, filed, items in _iter_filings(block):
                    if not filed:
                        continue
                    first = filed if not first or filed < first else first
                    last = filed if filed > last else last
                    if form in PERIODIC:
                        periodic.append(filed)
                    elif form == "8-K" and items and "1.03" in items.split(","):
                        events.append(("bankruptcy_filed", filed, acc, form))
                    elif form in DEREGISTER:
                        events.append(("deregistered", filed, acc, form))
                    elif form in DELIST:
                        events.append(("delisted", filed, acc, form))
                    elif form in FORM10:
                        events.append(("form10_registered", filed, acc, form))
                    if form in COMBINATION or form in FORM10:
                        shared.append((acc, form, filed))
            cik = str(doc.get("cik", "")).zfill(10)
            record: dict[str, Any] = {"cik": cik, "shared": shared, "has_periodic": bool(periodic)}
            if periodic or events:
                record.update(
                    {
                        "name": doc.get("name", ""),
                        "sic": doc.get("sic", "") or "",
                        "sic_description": doc.get("sicDescription", "") or "",
                        "entity_type": doc.get("entityType", "") or "",
                        "tickers": doc.get("tickers", []) or [],
                        "exchanges": [e for e in (doc.get("exchanges", []) or []) if e],
                        "state_of_incorporation": doc.get("stateOfIncorporation", "") or "",
                        "former_names": doc.get("formerNames", []) or [],
                        "first_filed": first,
                        "last_filed": last,
                        "first_periodic": min(periodic) if periodic else "",
                        "last_periodic": max(periodic) if periodic else "",
                        "periodic_years": sorted({d[:4] for d in periodic}),
                        "events": events,
                    }
                )
            if periodic or shared:
                out.append(record)
    return out


def scan(path: Path, workers: int) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json") and "-submissions-" not in n]
    chunk = 2000
    jobs = [(str(path), names[i : i + chunk]) for i in range(0, len(names), chunk)]
    records: list[dict[str, Any]] = []
    with mp.Pool(workers) as pool:
        for n, part in enumerate(pool.imap_unordered(_scan, jobs), 1):
            records.extend(part)
            if n % 50 == 0:
                print(f"  scanned {n * chunk:,} of {len(names):,} entities")
    return records


def _d(value: str) -> date:
    return date.fromisoformat(value[:10])


def derive(records: list[dict[str, Any]], as_of: date) -> tuple[dict[str, dict], list[dict]]:
    entities = {r["cik"]: r for r in records if r.get("has_periodic")}
    events: list[dict[str, Any]] = []

    def add(cik: str, kind: str, when: str, basis: str, **extra: Any) -> None:
        events.append({"cik": cik, "event": kind, "date": when[:10], "basis": basis, **extra})

    for cik, ent in entities.items():
        for former in ent["former_names"]:
            add(cik, "renamed", former.get("to") or "", "observed",
                detail=f"formerly {former.get('name', '')} ({(former.get('from') or '')[:10]} to {(former.get('to') or '')[:10]})")
        for kind, when, acc, form in ent["events"]:
            add(cik, kind, when, "observed", accession=acc, form=form)

    # Accessions shared by more than one entity: observed pairings.
    by_acc: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for r in records:
        for acc, form, filed in r["shared"]:
            by_acc[acc].append((r["cik"], form, filed))

    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    spin_parent: dict[str, tuple[str, str, str]] = {}
    for acc, parties in by_acc.items():
        ciks = sorted({p[0] for p in parties})
        if len(ciks) < 2 or len(ciks) > MAX_PARTIES:
            continue
        form, filed = parties[0][1], parties[0][2]
        if form in FORM10:
            registrants = [c for c in ciks if c in entities]
            # Parent = the co-listed entity that reported before this filing.
            for child in registrants:
                for parent in registrants:
                    if parent != child and entities[parent]["first_periodic"] and entities[parent]["first_periodic"] < filed \
                            and (not entities[child]["first_periodic"] or entities[child]["first_periodic"] >= filed):
                        spin_parent.setdefault(child, (parent, filed, acc))
            continue
        for i, a in enumerate(ciks):
            for b in ciks[i + 1 :]:
                if a not in entities or b not in entities:
                    continue
                pair = pairs.setdefault((a, b), {"first": filed, "last": filed, "forms": set(), "accession": acc})
                pair["first"] = min(pair["first"], filed)
                if filed >= pair["last"]:
                    pair["last"], pair["accession"] = filed, acc
                pair["forms"].add(form)

    candidates: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for (a, b), pair in pairs.items():
        forms = ";".join(sorted(pair["forms"]))
        add(a, "combination_filing", pair["last"], "observed", counterparty=b, accession=pair["accession"], form=forms)
        add(b, "combination_filing", pair["last"], "observed", counterparty=a, accession=pair["accession"], form=forms)

        def absorbed(x: str, y: str) -> str | None:
            last = _d(pair["last"])
            terms = sorted(
                when for kind, when, _, _ in entities[x]["events"]
                if kind in ("deregistered", "delisted") and _d(pair["first"]) <= _d(when) <= last + timedelta(days=ABSORB_WINDOW_DAYS)
            )
            if not terms:
                return None
            term = terms[0]
            x_last = entities[x]["last_periodic"]
            if x_last and _d(x_last) > _d(term) + timedelta(days=TRAILING_PERIODIC_DAYS):
                return None
            y_last = entities[y]["last_periodic"]
            if not y_last or y_last <= term:
                return None
            return term

        a_term, b_term = absorbed(a, b), absorbed(b, a)
        if a_term and not b_term:
            candidates[a].append((pair["last"], b, a_term, pair["accession"]))
        elif b_term and not a_term:
            candidates[b].append((pair["last"], a, b_term, pair["accession"]))

    for target, options in candidates.items():
        options.sort(reverse=True)
        if len(options) > 1 and options[0][0] == options[1][0]:
            continue  # two survivors on the same latest date: no direction
        _, survivor, term, acc = options[0]
        add(target, "merged_into", term, "derived", counterparty=survivor, accession=acc, rule="merged_into")

    for child, (parent, filed, acc) in spin_parent.items():
        add(child, "spun_off_from", filed, "derived", counterparty=parent, accession=acc, rule="spun_off_from")

    # Ceased reporting, with the latest terminal event as its reason.
    by_cik: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        by_cik[ev["cik"]].append(ev)
    cutoff = as_of - timedelta(days=DARK_AFTER_DAYS)
    for cik, ent in entities.items():
        last = ent["last_periodic"]
        if not last or _d(last) > cutoff:
            ent["status"] = "reporting"
            continue
        terminal = [e for e in by_cik[cik] if e["event"] in ("merged_into", "bankruptcy_filed", "deregistered", "delisted")]
        precedence = {"merged_into": 0, "bankruptcy_filed": 1, "deregistered": 2, "delisted": 3}
        near = [e for e in terminal if _d(e["date"]) >= _d(last) - timedelta(days=730)]
        reason = min(near, key=lambda e: (precedence[e["event"]], e["date"]))["event"] if near else "undisclosed"
        ent["status"] = f"ceased:{reason}"
        add(cik, "ceased_reporting", last, "derived", reason=reason, rule="ceased_reporting")
    return entities, events


def industry_series(entities: dict[str, dict], as_of: date) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    for ent in entities.values():
        sic = ent["sic"]
        group = sic[:2] if len(sic) == 4 else "00"
        g = groups.setdefault(group, {"sic_major_group": group, "division": sic_division(sic)[1], "years": defaultdict(Counter), "sic_codes": Counter()})
        if sic:
            g["sic_codes"][f"{sic} {ent['sic_description']}"] += 1
        for year in ent["periodic_years"]:
            g["years"][year]["reporting"] += 1
        if ent["first_periodic"]:
            g["years"][ent["first_periodic"][:4]]["entered"] += 1
        status = ent.get("status", "reporting")
        if status.startswith("ceased:"):
            g["years"][ent["last_periodic"][:4]][f"exit_{status.split(':')[1]}"] += 1
    return {
        key: {
            "sic_major_group": g["sic_major_group"],
            "division": g["division"],
            "sic_codes": dict(g["sic_codes"].most_common()),
            "years": {y: dict(c) for y, c in sorted(g["years"].items())},
        }
        for key, g in sorted(groups.items())
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(entities: dict[str, dict], events: list[dict], source: Path, as_of: date, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    ent_cols = ["cik", "name", "sic", "sic_description", "division", "entity_type", "tickers", "exchanges",
                "state_of_incorporation", "first_filed", "first_periodic", "last_periodic", "last_filed", "status"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ent_cols, lineterminator="\n")
    w.writeheader()
    for cik in sorted(entities):
        e = entities[cik]
        w.writerow({**{k: e.get(k, "") for k in ent_cols}, "division": sic_division(e["sic"])[1],
                    "tickers": ";".join(e["tickers"]), "exchanges": ";".join(e["exchanges"])})
    # mtime=0 keeps the archive byte-identical across runs with identical content.
    (out / "entities.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))

    ev_cols = ["cik", "event", "date", "basis", "counterparty", "accession", "form", "reason", "rule", "detail"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ev_cols, lineterminator="\n")
    w.writeheader()
    for ev in sorted(events, key=lambda e: (e["cik"], e["date"], e["event"], e.get("counterparty", ""), e.get("accession", ""))):
        w.writerow({k: ev.get(k, "") for k in ev_cols})
    (out / "events.csv.gz").write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))

    (out / "industry_series.json").write_text(json.dumps(industry_series(entities, as_of), indent=1) + "\n", encoding="utf-8")

    counts = Counter(e["event"] for e in events)
    status = Counter(e.get("status", "") for e in entities.values())
    summary = {
        "schema_version": "1.0",
        "generated_by": "tools/data_fabric/edgar_corporate_events.py",
        "as_of": as_of.isoformat(),
        "source": {
            "name": "SEC EDGAR submissions bulk archive",
            "url": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
        },
        "universe": "every EDGAR entity that has filed at least one periodic report (10-K, 10-Q, 20-F, 40-F and their small-business and transition variants)",
        "entity_count": len(entities),
        "status_counts": dict(status.most_common()),
        "event_counts": dict(counts.most_common()),
        "basis_counts": dict(Counter(e["basis"] for e in events)),
        "rules": RULES,
        "coverage_limits": [
            "EDGAR electronic filing began in 1993 and became mandatory for all domestic filers in May 1996; earlier history is absent.",
            "8-K item numbers start in August 2004, so bankruptcy_filed misses earlier filings and any bankruptcy not reported on an 8-K.",
            "merged_into needs a shared EDGAR accession. Acquisitions of private companies, and deals filed without one (for example a cash merger where only the target files a proxy), leave the target's exit undisclosed.",
            "SIC codes are SEC's current assignment for each entity, not the code it held in each historical year.",
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--submissions", type=Path, default=ROOT / ".sec-export" / "bulk" / "submissions.zip")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count()))
    args = parser.parse_args()
    records = scan(args.submissions, args.workers)
    entities, events = derive(records, args.as_of)
    summary = write(entities, events, args.submissions, args.as_of, args.out)
    print(json.dumps({k: summary[k] for k in ("entity_count", "status_counts", "event_counts", "basis_counts")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
