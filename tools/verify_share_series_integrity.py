"""Check whether share-count series in the recorded corpus are comparable across years.

WHAT THIS FOUND, AND WHY IT MATTERS
-----------------------------------
The corpus keeps one observation per fiscal period and resolves collisions by
"longest duration, then latest filed wins", so a restated figure supersedes the
original. That is the right rule for a single period: the most recent
restatement is the issuer's best answer for that year.

It is the wrong rule for a SERIES. Because each period-end takes its value from
whichever filing most recently restated it, and different periods were last
restated in different filings, adjacent observations can sit on different
bases. Tesla is the clearest case:

    WeightedAverageNumberOfSharesOutstandingBasic
      FY2017    166,000,000   filed 2020-02-13   pre-split
      FY2018    853,000,000   filed 2021-02-08   post 5:1
      FY2019    887,000,000   filed 2022-02-07   post 5:1
      FY2020  2,798,000,000   filed 2023-01-31   post 5:1 and post 3:1

Read as a series that is a 414% jump in 2018 and a 215% jump in 2020. Neither
happened. Tesla split its stock, and the series is measuring in three different
units. Anything per-share computed across those years -- earnings per share,
dilution, market capitalisation, a share-count growth rate -- is wrong, and
wrong in a way that looks like a finding rather than an artefact.

THREE DISTINCT DEFECTS, THREE SEVERITIES
----------------------------------------
split_basis (warning)
    Consecutive observations differ by close to a whole-number multiple and
    come from different filings. Each value is correct as filed; the series is
    not comparable. A model must source a per-share series from ONE filing.

unit_scale (failure)
    One observation is three or more orders of magnitude from its neighbours,
    e.g. Autodesk at 228,900,000 then 227 then 225,900,000 -- one filing
    reported shares in millions and the harvest kept the bare number. Unlike a
    split, there is no reading of the series under which this is right.

unclassified (warning)
    Outside the plausible band but matching no clean multiple. Usually a split
    combined with real issuance, or a partially restated period. Reported so a
    human decides rather than a threshold.

Usage:
    python tools/verify_share_series_integrity.py
    python tools/verify_share_series_integrity.py --report shares.json
    python tools/verify_share_series_integrity.py --ticker TSLA
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tools" / "data_fabric" / "out"

SHARE_CONCEPTS = {
    "CommonStockSharesOutstanding",
    "CommonStockSharesIssued",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
}

# A share count moving less than this is ordinary issuance or buyback, not a
# change of basis. Chosen wide: a real 70% single-year increase happens (a large
# secondary, an all-stock acquisition), and flagging those would bury the signal.
PLAUSIBLE_LOW, PLAUSIBLE_HIGH = 0.55, 1.8

# Whole-number multiples that stock splits actually use.
SPLIT_MULTIPLES = (2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30)
SPLIT_TOLERANCE = 0.06

# Three orders of magnitude cannot be a split.
UNIT_SCALE_FLOOR = 500


def classify(ratio: float) -> str:
    magnitude = max(ratio, 1 / ratio)
    if any(abs(magnitude - m) < SPLIT_TOLERANCE * m for m in SPLIT_MULTIPLES):
        return "split_basis"
    if magnitude >= UNIT_SCALE_FLOOR:
        return "unit_scale"
    return "unclassified"


KNOWN_DEFECTS = ROOT / "standards" / "conformance" / "known_data_defects.json"


def key_of(finding: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        finding["ticker"],
        finding["concept"],
        finding["from_period"],
        finding["to_period"],
    )


def load_known_defects() -> set[tuple[str, str, str, str]]:
    """Unit-scale defects already accepted as known, keyed by the pair they span.

    Keyed on the period pair rather than on the values, so a known entry keeps
    matching if a later harvest changes the numbers while leaving the defect in
    place -- and stops matching once the defect is actually fixed, which the
    check then reports as a stale entry to delete.
    """
    if not KNOWN_DEFECTS.exists():
        return set()
    payload = json.loads(KNOWN_DEFECTS.read_text(encoding="utf-8"))
    accepted = (payload.get("share_series_unit_scale") or {}).get("accepted") or []
    return {
        (e["ticker"], e["concept"], e["from_period"], e["to_period"]) for e in accepted
    }


def series_files(ticker: str | None = None) -> list[Path]:
    pattern = f"{ticker.upper()}_facts_annual_series.json" if ticker else "*_facts_annual_series.json"
    return sorted(OUT_DIR.glob(pattern))


def run(ticker: str | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    tallies: Counter[str] = Counter()
    tickers_scanned = 0
    series_scanned = 0

    for path in series_files(ticker):
        symbol = path.name.split("_facts_")[0]
        payload = json.loads(path.read_text(encoding="utf-8"))
        tickers_scanned += 1
        for series in payload["concepts"]:
            if series["concept"] not in SHARE_CONCEPTS:
                continue
            series_scanned += 1
            observations = sorted(
                (o for o in series["observations"] if o.get("value")),
                key=lambda o: o["end"],
            )
            for earlier, later in zip(observations, observations[1:]):
                if not earlier["value"] or not later["value"]:
                    continue
                if earlier["filed"] == later["filed"]:
                    # Both from one filing, so both on one basis. Any movement
                    # here is the issuer's own reported change.
                    continue
                ratio = later["value"] / earlier["value"]
                if PLAUSIBLE_LOW < ratio < PLAUSIBLE_HIGH:
                    continue
                kind = classify(ratio)
                tallies[kind] += 1
                findings.append({
                    "kind": kind,
                    "ticker": symbol,
                    "concept": series["concept"],
                    "from_period": earlier["end"],
                    "to_period": later["end"],
                    "from_value": earlier["value"],
                    "to_value": later["value"],
                    "ratio": round(ratio, 6),
                    "from_filed": earlier["filed"],
                    "to_filed": later["filed"],
                })

    # A unit-scale defect already recorded as known stays reported but does not
    # fail the build. That keeps the check fail-closed on anything NEW while
    # not blocking every run on 28 defects that cannot be fixed without
    # re-harvesting from a host this environment cannot reach.
    known = load_known_defects()
    unit_scale = [f for f in findings if f["kind"] == "unit_scale"]
    failures = [f for f in unit_scale if key_of(f) not in known]
    known_hits = [f for f in unit_scale if key_of(f) in known]
    warnings = [f for f in findings if f["kind"] != "unit_scale"]
    affected = sorted({f["ticker"] for f in findings})
    stale_known = sorted(known - {key_of(f) for f in unit_scale})

    for entry in stale_known:
        warnings.append({
            "kind": "stale_known_defect",
            "ticker": entry[0],
            "concept": entry[1],
            "from_period": entry[2],
            "to_period": entry[3],
            "from_value": 0,
            "to_value": 0,
            "ratio": 0.0,
            "from_filed": "",
            "to_filed": "",
        })

    return {
        "status": "PASS" if not failures else "FAIL",
        "tickers_scanned": tickers_scanned,
        "share_series_scanned": series_scanned,
        "by_kind": dict(tallies),
        "known_unit_scale_defects": len(known_hits),
        "new_unit_scale_defects": len(failures),
        "stale_known_defect_entries": [list(e) for e in stale_known],
        "tickers_with_any_finding": len(affected),
        "tickers_affected": affected,
        "findings": findings,
        "failures": [
            f"{f['ticker']} {f['concept']} {f['from_period']} -> {f['to_period']}: "
            f"{f['from_value']:,} -> {f['to_value']:,} (x{f['ratio']:.3g}); filings "
            f"{f['from_filed']} and {f['to_filed']} report in different units"
            for f in failures
        ],
        "warnings": [
            f"{f['ticker']} {f['concept']} {f['from_period']} -> {f['to_period']}: "
            f"{f['from_value']:,} -> {f['to_value']:,} (x{f['ratio']:.3g}) [{f['kind']}]; "
            f"filed {f['from_filed']} vs {f['to_filed']} -- not comparable as a series"
            for f in warnings
        ],
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "guidance": (
            "A per-share series must be sourced from a single filing, so every period "
            "is on that filing's split basis. Taking each period from whichever filing "
            "restated it last mixes bases and produces growth rates that are pure "
            "artefact."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--ticker", default=None)
    args = parser.parse_args()
    report = run(args.ticker)
    # The console gets a summary that stays valid JSON; the structured
    # per-pair findings go only to --report, where a consumer can key on them.
    printable = {k: v for k, v in report.items() if k != "findings"}
    printable["tickers_affected"] = report["tickers_affected"][:25]
    printable["warnings"] = report["warnings"][:15]
    printable["warnings_shown"] = min(15, report["warning_count"])
    print(json.dumps(printable, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
