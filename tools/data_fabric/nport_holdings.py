"""Second source for universe holdings: the fund's own N-PORT filing.

The universe taxonomy's constituent list currently rests on one vendor
snapshot (the issuer profile via Alpha Vantage). Registered funds also file
their complete portfolios with the SEC on Form NPORT-P - the regulator's
copy of the same facts. This tool freezes that second source and
cross-checks the taxonomy against it, so the constituent list is verified
by two independent channels instead of trusted from one.

Caveats stated up front: NPORT-P reports quarter-end portfolios with a lag
(the latest public filing covers a period months behind a live profile), so
constituents and weights legitimately differ across sources; the cross-check
reports match RATES and largest weight gaps with the period difference named,
never exact equality. N-PORT identifies holdings by name/CUSIP/LEI, not
ticker, so matching to the taxonomy is by normalized issuer name against
both the profile description and the SEC-registered name.

    python tools/data_fabric/nport_holdings.py --cik 1067839 --tag QQQ
    python tools/data_fabric/nport_holdings.py --tag QQQ --cross-check
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"
TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"

UA = "FinanceSegway/1.0 (research; seancollins2027@u.northwestern.edu)"

STOPWORDS = {
    "INC", "CORP", "CO", "LTD", "PLC", "SA", "NV", "SE", "TRUST", "COMPANY",
    "CORPORATION", "INCORPORATED", "HOLDINGS", "HOLDING", "GROUP", "CLASS",
    "A", "B", "C", "THE", "NEW", "COM", "ADR", "ORD", "SHS", "SERIES", "1",
}


def normalize_name(name: str) -> str:
    """Issuer-name key: uppercase, alphanumeric tokens, suffixes dropped."""
    tokens = re.split(r"[^A-Z0-9]+", (name or "").upper())
    kept = [t for t in tokens if len(t) > 1 and t not in STOPWORDS]
    return " ".join(kept[:3])


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return session


def fetch_latest_nport(cik: str, session: requests.Session | None = None) -> dict:
    sess = session or _session()
    cik_padded = str(cik).zfill(10)
    subs = sess.get(
        f"https://data.sec.gov/submissions/CIK{cik_padded}.json", timeout=60
    )
    subs.raise_for_status()
    recent = subs.json()["filings"]["recent"]
    entity = subs.json()["name"]
    for form, accession, filed in zip(
        recent["form"], recent["accessionNumber"], recent["filingDate"]
    ):
        if form.startswith("NPORT-P"):
            break
    else:
        raise SystemExit(f"CIK {cik}: no NPORT-P filing found")
    acc = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
    index = sess.get(f"{base}/index.json", timeout=60)
    index.raise_for_status()
    xml_name = next(
        item["name"] for item in index.json()["directory"]["item"]
        if item["name"].endswith(".xml")
    )
    raw = sess.get(f"{base}/{xml_name}", timeout=120)
    raw.raise_for_status()
    return {
        "entity": entity,
        "accession": accession,
        "filed": filed,
        "url": f"{base}/{xml_name}",
        "xml": raw.content,
    }


def parse_holdings(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    match = re.match(r"\{(.+)\}", root.tag)
    ns = {"n": match.group(1)} if match else {}
    period = root.findtext(".//n:genInfo/n:repPdDate", None, ns)
    holdings = []
    for item in root.findall(".//n:invstOrSec", ns):
        pct = item.findtext("n:pctVal", None, ns)
        holdings.append(
            {
                "name": item.findtext("n:name", None, ns),
                "pct": float(pct) if pct else 0.0,
                "cusip": item.findtext("n:cusip", None, ns),
                "lei": item.findtext("n:lei", None, ns),
            }
        )
    holdings.sort(key=lambda h: -h["pct"])
    return {"report_period": period, "holdings": holdings}


def write_snapshot(tag: str, meta: dict, parsed: dict) -> Path:
    path = OUT_DIR / f"{tag.upper()}_sec_nport_holdings.json"
    payload = {
        "source": "SEC Form NPORT-P (fund-filed complete portfolio)",
        "entity": meta["entity"],
        "accession": meta["accession"],
        "filing_date": meta["filed"],
        "url": meta["url"],
        "report_period": parsed["report_period"],
        "note": (
            "The regulator's copy of the portfolio, identified by "
            "name/CUSIP/LEI (no tickers). Reported as of the period end - "
            "months behind a live issuer profile by construction."
        ),
        "holdings": parsed["holdings"],
    }
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return path


def cross_check(tag: str) -> dict:
    """Taxonomy constituents vs the frozen N-PORT snapshot, by issuer name."""
    snapshot = json.loads(
        (OUT_DIR / f"{tag.upper()}_sec_nport_holdings.json").read_text(
            encoding="utf-8"
        )
    )
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    nport_by_key: dict[str, dict] = {}
    for holding in snapshot["holdings"]:
        key = normalize_name(holding["name"])
        if key:
            entry = nport_by_key.setdefault(key, {"pct": 0.0, "names": []})
            entry["pct"] += holding["pct"]
            entry["names"].append(holding["name"])

    matched, unmatched, weight_gaps = [], [], []
    taxonomy_keys = set()
    for company in taxonomy["companies"]:
        if not company.get("modelable"):
            continue
        keys = {
            normalize_name(company.get("name") or ""),
            normalize_name(company.get("name_sec") or ""),
        } - {""}
        taxonomy_keys.update(keys)
        hit = next((k for k in keys if k in nport_by_key), None)
        if hit is None:
            unmatched.append(company["symbol"])
            continue
        nport_pct = nport_by_key[hit]["pct"] / 100.0
        taxonomy_weight = sum(
            m["weight"] for c in taxonomy["companies"]
            if c.get("cik") == company.get("cik") and c.get("modelable")
            for m in c["memberships"]
        )
        matched.append(company["symbol"])
        gap = abs(nport_pct - taxonomy_weight)
        if gap > 0.01:
            weight_gaps.append(
                {
                    "symbol": company["symbol"],
                    "taxonomy_weight": round(taxonomy_weight, 4),
                    "nport_pct": round(nport_pct, 4),
                    "gap": round(gap, 4),
                }
            )
    nport_only = sorted(
        entry["names"][0]
        for key, entry in nport_by_key.items()
        if key not in taxonomy_keys and entry["pct"] > 0.1
    )
    matched_unique = sorted(set(matched))
    return {
        "universe": tag.upper(),
        "taxonomy_as_of": taxonomy.get("as_of"),
        "nport_period": snapshot["report_period"],
        "period_note": (
            "sources are snapshots of different dates; adds/drops and weight "
            "moves between them are expected, discrepancies below are "
            "candidates for review, not automatic errors"
        ),
        "taxonomy_matched": len(matched_unique),
        "taxonomy_unmatched": sorted(set(unmatched)),
        "nport_only_over_10bps": nport_only,
        "weight_gaps_over_1pct": sorted(
            weight_gaps, key=lambda g: -g["gap"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cik", help="fund CIK (e.g. 1067839 for QQQ trust)")
    parser.add_argument("--tag", required=True, help="snapshot tag, e.g. QQQ")
    parser.add_argument("--cross-check", action="store_true",
                        help="compare the frozen snapshot to the taxonomy")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.cross_check:
        report = cross_check(args.tag)
        print(json.dumps(report, indent=2))
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + "\n",
                                   encoding="utf-8")
        return 0
    if not args.cik:
        parser.error("--cik is required to fetch (or use --cross-check)")
    meta = fetch_latest_nport(args.cik)
    parsed = parse_holdings(meta.pop("xml"))
    path = write_snapshot(args.tag, meta, parsed)
    print(f"Wrote {path} ({len(parsed['holdings'])} holdings, "
          f"period {parsed['report_period']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
