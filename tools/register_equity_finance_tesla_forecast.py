"""Build the out-of-sample revenue forecast for the Equity Finance Tesla case.

WHAT IS FORECAST, AND WHY THIS METRIC
-------------------------------------
Tesla's total revenue for fiscal year 2026. The fiscal year ends 2026-12-31
and is reported in the FY2026 Form 10-K, which Tesla has filed in late
January for each of the last five years. Nothing in this repository knows the
answer yet, so the forecast is genuinely out of sample.

Revenue, specifically, and not a per-share figure. The recorded corpus keeps
one observation per fiscal period and resolves collisions by latest-filed,
so adjacent share-count observations can sit on different stock-split bases
-- Tesla's are the clearest instance in the corpus, and
verify_share_series_integrity.py reports them. Any per-share metric scored
against that series would measure the split, not the forecast. Revenue has
no split basis.

HOW THE POINT IS COMPUTED
-------------------------
Two quarters of fiscal 2026 are already reported: Q1 ending 2026-03-31 and
Q2 ending 2026-06-30. Their sum is an observed figure, not an estimate. Only
the second half has to be projected, and it is projected by the one thing the
disclosed record actually says about Tesla's second halves: how much larger
they are than the first half of the same year.

    forecast = H1_2026_observed * (1 + mean(H2/H1 over FY2021..FY2025))

The interval is the same arithmetic at the weakest and the strongest
seasonality in that five-year window. It is an envelope of observed
seasonality, not a confidence interval -- no distribution is claimed, and
this repository does not record elicited intervals as if they were
calibrated.

WHY THE WINDOW IS FIVE YEARS
----------------------------
FY2021 is the earliest year for which the recorded quarterly snapshot holds
all four quarters. FY2020 and earlier are excluded for a second reason as
well: Tesla's second half of 2020 was 62% larger than its first half, a
ramp that has not recurred, and including it would widen the envelope with a
period the company no longer resembles.

PROVENANCE
----------
Quarterly values come from the recorded Alpha Vantage snapshot, whose four
quarters sum to the annual figure to the dollar in every complete fiscal year
FY2021 through FY2025, and whose FY2025 annual figure matches the SEC EDGAR
observation exactly. The baseline is frozen from the EDGAR snapshot.

VINTAGE
-------
The linked case is dated 2020-02-14 and its own forward grid deliberately
excludes everything published after that date. This forecast is a separately
dated projection and does not touch the case's grid. It shares only the case
identifier, which is what ties forecasting skill back to a model.

Usage:
    python tools/register_equity_finance_tesla_forecast.py          # print
    python tools/register_equity_finance_tesla_forecast.py --write  # draft file
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from forecast_registration import draft_registration  # noqa: E402

QUARTERLY = ROOT / "tools" / "data_fabric" / "out" / "TSLA_alphavantage_income_statement_quarterly.json"
EDGAR = ROOT / "tools" / "data_fabric" / "out" / "TSLA_facts_annual_series.json"
FORECAST_DIR = ROOT / "standards" / "forecasts"

FORECAST_ID = "equity-tesla-fy2026-revenue"
CASE_ID = "equity-public-tesla-2020-offering"
MODEL_ID = "12"
METRIC = "fy2026_total_revenue_usd_mm"

SEASONALITY_YEARS = (2021, 2022, 2023, 2024, 2025)
TARGET_YEAR = 2026
# The two baseline history periods below FY2025 come from the same filing as
# FY2025 itself, so the three are on one basis.
HISTORY_PERIODS = ("2023-12-31", "2024-12-31", "2025-12-31")


def quarterly_revenue_mm() -> dict[str, float]:
    payload = json.loads(QUARTERLY.read_text(encoding="utf-8"))
    return {
        fact["end"]: fact["value"] / 1e6
        for fact in payload["facts"]
        if fact["av_field"] == "totalRevenue"
    }


def halves(revenue: dict[str, float]) -> dict[int, dict[str, float]]:
    by_year: dict[int, dict[int, float]] = defaultdict(dict)
    for end, value in revenue.items():
        year, month, _ = end.split("-")
        by_year[int(year)][int(month)] = value
    out = {}
    for year, months in sorted(by_year.items()):
        out[year] = {
            "h1": sum(months[m] for m in (3, 6) if m in months),
            "h2": sum(months[m] for m in (9, 12) if m in months),
            "quarters": len(months),
        }
    return out


def edgar_history_mm() -> list[tuple[str, float]]:
    payload = json.loads(EDGAR.read_text(encoding="utf-8"))
    series = next(s for s in payload["concepts"] if s["concept"] == "Revenues")
    observed = {o["end"]: o for o in series["observations"] if o.get("value")}
    filings = {observed[p]["filed"] for p in HISTORY_PERIODS}
    if len(filings) != 1:
        raise SystemExit(
            "baseline history spans more than one filing "
            f"({sorted(filings)}); a mixed-basis history makes the naive line "
            "an artefact. Pick periods that share a filing."
        )
    return [(p, observed[p]["value"] / 1e6) for p in HISTORY_PERIODS]


def build() -> dict[str, Any]:
    revenue = quarterly_revenue_mm()
    half_years = halves(revenue)

    target = half_years[TARGET_YEAR]
    if target["quarters"] != 2 or target["h2"] != 0.0:
        raise SystemExit(
            f"FY{TARGET_YEAR} has {target['quarters']} recorded quarters; this script "
            "assumes exactly the first two are reported. If the third has landed, "
            "project one quarter rather than a half year."
        )
    h1_observed = target["h1"]

    ratios = {}
    for year in SEASONALITY_YEARS:
        entry = half_years[year]
        if entry["quarters"] != 4:
            raise SystemExit(f"FY{year} has {entry['quarters']} recorded quarters, not 4")
        ratios[year] = entry["h2"] / entry["h1"]

    values = sorted(ratios.values())
    mean_ratio = sum(values) / len(values)
    point = round(h1_observed * (1 + mean_ratio), 1)
    interval = [
        round(h1_observed * (1 + values[0]), 1),
        round(h1_observed * (1 + values[-1]), 1),
    ]

    history = edgar_history_mm()
    history_source = (
        "us-gaap:Revenues from Tesla's SEC XBRL company facts (CIK 0001318605), "
        "recorded at tools/data_fabric/out/TSLA_facts_annual_series.json; the "
        "fiscal years ending 2023-12-31, 2024-12-31 and 2025-12-31 were all filed "
        "2026-01-29, so the three sit on one basis"
    )

    ratio_text = ", ".join(f"FY{y} {ratios[y]:.4f}" for y in SEASONALITY_YEARS)
    record = draft_registration(
        forecast_id=FORECAST_ID,
        case_id=CASE_ID,
        model_id=MODEL_ID,
        metric=METRIC,
        point=point,
        interval=interval,
        history=history,
        history_source=history_source,
        resolve_by="2027-03-31",
        resolution_source_expected=(
            "Tesla, Inc. FY2026 Form 10-K (us-gaap:Revenues for the fiscal year "
            "ending 2026-12-31, USD mm). Tesla filed its FY2021 through FY2025 "
            "10-Ks between 2024-01-29 and 2026-01-29, so the figure should be "
            "public well before the resolve_by date; 2027-03-31 allows for the "
            "60-day large-accelerated-filer deadline plus slack. "
            "METHOD: forecast = observed H1 FY2026 revenue of "
            f"{h1_observed:,.1f} USD mm (Q1 ending 2026-03-31 plus Q2 ending "
            "2026-06-30, from tools/data_fabric/out/"
            "TSLA_alphavantage_income_statement_quarterly.json) multiplied by "
            f"1 + {mean_ratio:.6f}, the mean of the observed second-half-to-"
            f"first-half revenue ratios for FY2021 through FY2025 ({ratio_text}). "
            "The interval applies the weakest and strongest of those five ratios "
            "and is an envelope of observed seasonality, not a calibrated "
            "confidence interval. "
            "VERIFICATION OF THE QUARTERLY SOURCE: the four recorded quarters sum "
            "to the vendor's own annual revenue to the dollar in every one of "
            "FY2021 through FY2025, and the FY2025 annual figure of 94,827 USD mm "
            "matches the SEC EDGAR observation exactly. "
            "NOTE ON VINTAGE: the linked case is dated 2020-02-14 and its forward "
            "grid excludes post-as-of data; this is a separately dated projection "
            "anchored on reported fiscal 2026 quarters, and it does not feed the "
            "case workbook. "
            "WHY REVENUE AND NOT A PER-SHARE METRIC: Tesla's recorded share-count "
            "series mixes stock-split bases, as verify_share_series_integrity.py "
            "reports, so a per-share forecast would be scored against an artefact."
        ),
    )
    record["_diagnostics"] = {
        "h1_2026_observed_usd_mm": round(h1_observed, 1),
        "seasonality_ratios": {f"FY{y}": round(r, 6) for y, r in ratios.items()},
        "mean_ratio": round(mean_ratio, 6),
        "implied_growth_vs_fy2025": round(point / history[-1][1] - 1, 6),
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true",
                        help="write the draft to standards/forecasts/ for --register to stamp")
    args = parser.parse_args()
    record = build()
    diagnostics = record.pop("_diagnostics")
    print(json.dumps({"diagnostics": diagnostics, "record": record}, indent=2))
    if args.write:
        path = FORECAST_DIR / f"{FORECAST_ID}.json"
        if path.exists():
            raise SystemExit(f"{path} already exists; registrations are immutable")
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path}")
        print("Now run: python tools/forecast_registration.py --register " + str(path.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
