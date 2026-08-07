"""Resolve a due FRED-sourced registration with the realized value, verifiably.

The registry's fast windows (UST-10Y month ends) resolve against FRED. This
helper fetches the named series, finds the last business-day observation of
the registration's target month, PRINTS the evidence (date, value, series
URL), and - only with --commit - runs the registry's own --resolve. Without
--commit it is read-only: the operator sees exactly what would be recorded
and the resolve command to run, so resolution stays a deliberate act with
its evidence on the table, never a silent side effect.

    python tools/resolve_from_fred.py --forecast-id rates-ust10y-eom-2026-09
    python tools/resolve_from_fred.py --forecast-id rates-ust10y-eom-2026-09 --commit
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECAST_DIR = ROOT / "standards" / "forecasts"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}"


def month_of(forecast_id: str) -> str:
    match = re.search(r"(\d{4})-(\d{2})$", forecast_id)
    if not match:
        raise SystemExit(
            f"{forecast_id}: cannot infer target month from the id "
            "(expected a -YYYY-MM suffix)"
        )
    return match.group(0)


def last_business_day_value(series: str, month: str) -> tuple[str, float]:
    url = FRED_CSV.format(series=series, start=f"{month}-01")
    # FRED's edge rejects Python HTTP stacks at the TLS layer (curl passes,
    # requests hangs regardless of User-Agent), so fetch via curl - the same
    # posture as the benchmark's fetch_data.sh, and curl ships everywhere
    # this repo's CI runs.
    fetched = subprocess.run(
        ["curl", "-sS", "-m", "60", url],
        capture_output=True, text=True, check=True,
    )
    rows = [
        (date, value)
        for date, value in csv.reader(io.StringIO(fetched.stdout))
        if date.startswith(month) and value not in (".", "", "VALUE")
    ]
    if not rows:
        raise SystemExit(f"FRED {series}: no observations for {month} yet - "
                         "the window may not have closed")
    date, value = rows[-1]
    return date, float(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast-id", required=True)
    parser.add_argument("--series", default="DGS10")
    parser.add_argument("--commit", action="store_true",
                        help="actually run --resolve; default is read-only")
    args = parser.parse_args()

    record_path = FORECAST_DIR / f"{args.forecast_id}.json"
    if not record_path.exists():
        raise SystemExit(f"no registration at {record_path}")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("resolution") is not None:
        raise SystemExit(f"{args.forecast_id}: already resolved; resolutions are final")

    month = month_of(args.forecast_id)
    date, pct = last_business_day_value(args.series, month)
    realized = round(pct / 100.0, 4)
    source = f"FRED {args.series}, {date} (last business day of {month})"
    print(json.dumps({
        "forecast_id": args.forecast_id,
        "registered_point": record["point"],
        "baseline": record["baseline"]["value"],
        "realized": realized,
        "realized_pct": pct,
        "observation_date": date,
        "source": source,
    }, indent=2))
    command = [
        sys.executable, "tools/forecast_registration.py",
        "--resolve", args.forecast_id,
        "--realized", str(realized), "--source", source,
    ]
    if not args.commit:
        print("\nread-only: to record this resolution, re-run with --commit\n"
              + " ".join(command[1:]))
        return 0
    result = subprocess.run(command, cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
