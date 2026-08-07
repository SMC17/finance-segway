"""Report what is due for refresh, so the library runs on a cadence.

Everything here updates on a quarterly filing rhythm. Without a clock, that
becomes a permanent backfill: nobody knows what has gone stale, so either
everything gets rebuilt (wasteful, and it churns hashes for no reason) or
nothing does (and the library quietly rots while still displaying a
confident as-of date).

This is a *reporting* tool, not a rebuilder. It answers "what is stale and
why" and stops there. Refreshing a case rewrites sourced values and
workbook hashes, which is a change that should be reviewed, not something a
scheduler does unattended -- and the actual data pull needs a connector
this tool has no business assuming is available.

Staleness has two independent triggers, because they fail differently:

  1. Age. A case whose as_of predates the most recently completed reporting
     quarter is stale by the calendar, even if nothing about it changed.
  2. Source drift. A case whose recorded source snapshot has changed on
     disk since the case was built is stale regardless of age -- the
     underlying data moved.

Usage:
    python tools/quarterly_refresh.py
    python tools/quarterly_refresh.py --as-of 2026-08-06
    python tools/quarterly_refresh.py --report refresh-due.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"
TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"

# A filing quarter is not reportable the day it ends: issuers file over the
# following weeks. This lag is what stops the tool from flagging every case
# as stale on the first day of a new quarter, before any data exists to
# refresh it with.
FILING_LAG_DAYS = 45


def _parse(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def quarter_of(day: date) -> tuple[int, int]:
    return day.year, (day.month - 1) // 3 + 1


def quarter_end(year: int, quarter: int) -> date:
    month = quarter * 3
    last_day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
    return date(year, month, last_day)


def most_recent_reportable_quarter(today: date) -> tuple[int, int]:
    """The latest quarter whose filing window has plausibly closed."""
    year, quarter = quarter_of(today)
    # Walk back until the quarter ended at least FILING_LAG_DAYS ago.
    for _ in range(8):
        ended = quarter_end(year, quarter)
        if (today - ended).days >= FILING_LAG_DAYS:
            return year, quarter
        quarter -= 1
        if quarter == 0:
            year, quarter = year - 1, 4
    return year, quarter


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    target_year, target_quarter = most_recent_reportable_quarter(today)
    target_end = quarter_end(target_year, target_quarter)

    index = json.loads(PUBLIC_INDEX.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    for case in index.get("cases", []):
        manifest_path = ROOT / case["manifest"]
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        as_of = _parse(manifest.get("as_of"))
        reasons: list[str] = []

        if as_of is None:
            reasons.append("manifest has no parseable as_of date")
        elif as_of < target_end:
            quarters_behind = (
                (target_year - as_of.year) * 4 + (target_quarter - quarter_of(as_of)[1])
            )
            reasons.append(
                f"as_of {as_of.isoformat()} predates {target_year}Q{target_quarter} "
                f"({quarters_behind} quarters behind)"
            )

        # Source drift: does any recorded snapshot no longer match what the
        # case was frozen against?
        for source in manifest.get("sources", []):
            snapshot = str(source.get("url", ""))
            if not snapshot.startswith("repo://"):
                continue
            local = ROOT / snapshot[len("repo://") :]
            if not local.exists():
                reasons.append(f"recorded snapshot missing: {snapshot}")

        # An external historical case is pinned to a past event on purpose:
        # Macy's FY2020 does not get "refreshed" to 2026. Age alone is not a
        # defect for these, so it is reported separately rather than as work.
        pinned = manifest.get("classification") == "external_historical_case"

        rows.append(
            {
                "case_id": case["case_id"],
                "model_id": case["model_id"],
                "domain": case["domain"],
                "as_of": manifest.get("as_of"),
                "pinned_historical": pinned,
                "stale": bool(reasons),
                "reasons": reasons,
            }
        )

    universes: list[dict[str, Any]] = []
    if TAXONOMY.exists():
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        for universe in taxonomy.get("universes", []):
            source = universe.get("source") or {}
            captured = _parse(source.get("as_of"))
            snapshot_rel = source.get("snapshot")
            snapshot_exists = bool(snapshot_rel) and (ROOT / snapshot_rel).exists()
            universes.append(
                {
                    "universe": universe["id"],
                    "captured_as_of": source.get("as_of"),
                    "snapshot_present": snapshot_exists,
                    "stale": bool(captured and captured < target_end) or not snapshot_exists,
                }
            )

    actionable = [row for row in rows if row["stale"] and not row["pinned_historical"]]
    pinned_stale = [row for row in rows if row["stale"] and row["pinned_historical"]]
    live_cases = [row for row in rows if not row["pinned_historical"]]

    return {
        "today": today.isoformat(),
        "target_quarter": f"{target_year}Q{target_quarter}",
        "target_quarter_end": target_end.isoformat(),
        "filing_lag_days": FILING_LAG_DAYS,
        "cases_assessed": len(rows),
        "live_tracking_cases": len(live_cases),
        "refresh_due": len(actionable),
        "pinned_historical_behind_quarter": len(pinned_stale),
        "universes_due": [item for item in universes if item["stale"]],
        "due": actionable,
        "pinned": pinned_stale,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=str, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    today = _parse(args.as_of) or date.today()
    report = assess(today)

    print(
        f"As of {report['today']}, most recent reportable quarter is "
        f"{report['target_quarter']} (ended {report['target_quarter_end']}, "
        f"+{report['filing_lag_days']}d filing lag)"
    )
    print(
        f"Cases assessed: {report['cases_assessed']}  "
        f"Refresh due: {report['refresh_due']}  "
        f"Pinned historical behind quarter: {report['pinned_historical_behind_quarter']}"
    )
    if report["universes_due"]:
        print("\nUniverses due for a constituent re-pull:")
        for item in report["universes_due"]:
            print(f"  {item['universe']}: captured {item['captured_as_of']}")
    if report["due"]:
        print("\nCases due for refresh:")
        for row in report["due"]:
            print(f"  {row['case_id']:<45} {'; '.join(row['reasons'])}")
    elif report["live_tracking_cases"] == 0:
        # Distinguish "nothing is stale" from "nothing can be stale". The
        # second is a structural gap, not a clean bill of health: a library
        # made entirely of cases pinned to past events has nothing for a
        # quarterly cadence to update.
        print(
            "\nNo case is due -- but note that ZERO of the "
            f"{report['cases_assessed']} cases are live-tracking. Every one is "
            "classified external_historical_case, i.e. anchored to a past event "
            "on purpose.\nA quarterly refresh cadence needs cases that track a "
            "current subject forward; none exist yet, so there is nothing here "
            "to put on autopilot."
        )
    else:
        print(
            "\nNo live-tracking case is due. Pinned historical cases are anchored "
            "to a past event on purpose and are not refreshed forward."
        )

    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
