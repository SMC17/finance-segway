\"\"\"Fetch a real 10-name US mega-cap universe and materialise Stage-0 artifacts.

Outputs (under research/ram/data/ and research/kdb/exports/):
  - universe_real_10.json   metadata, vols, methodology
  - cov_real_10.json        annualised covariance matrix (list of lists)
  - rets_real_10.json       daily log returns (optional, for research)
  - regime_summary_YYYYMMDD.csv   Contract-1 export for the kdb rail

The pure-Python Stage-0 risk engine is deliberately left free of NumPy;
NumPy is used only for data preparation here.
\"\"\"
from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
EXPORT_DIR = REPO_ROOT / "research" / "kdb" / "exports"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "BRK-B", "JPM", "XOM", "JNJ",
]


def fetch_daily_adjclose(symbol: str, years: float = 1.1) -> list[tuple[str, float]]:
    period2 = int(time.time())
    period1 = period2 - int(years * 365.25 * 24 * 3600)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Finance-Segway research)"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    indicators = result["indicators"]
    if "adjclose" in indicators:
        closes = indicators["adjclose"][0]["adjclose"]
    else:
        closes = indicators["quote"][0]["close"]
    out = []
    for ts, px in zip(timestamps, closes):
        if px is None or px <= 0:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        out.append((dt, float(px)))
    return out


def main() -> None:
    print("Fetching real daily adjusted closes for", TICKERS)
    series: dict[str, list[tuple[str, float]]] = {}
    for t in TICKERS:
        series[t] = fetch_daily_adjclose(t)
        print(f"  {t}: {len(series[t])} points, last={series[t][-1]}")
        time.sleep(0.35)

    common = None
    for pts in series.values():
        dates = {d for d, _ in pts}
        common = dates if common is None else common & dates
    common_dates = sorted(common)
    print(f"Common trading days: {len(common_dates)}")

    price = {t: dict(series[t]) for t in TICKERS}
    px_mat = np.array([[price[t][d] for t in TICKERS] for d in common_dates], dtype=float)
    log_px = np.log(px_mat)
    rets = np.diff(log_px, axis=0)

    cov = np.cov(rets, rowvar=False) * 252.0
    vols = np.sqrt(np.diag(cov))
    corr = np.corrcoef(rets, rowvar=False)
    avg_corr = float((corr.sum() - np.trace(corr)) / (corr.size - len(TICKERS)))

    print("\nRealized annualized vols:")
    for t, v in zip(TICKERS, vols):
        print(f"  {t}: {v:.4f}")
    print(f"Avg pairwise corr: {avg_corr:.4f}")

    as_of = common_dates[-1]
    meta = {
        "as_of": as_of,
        "tickers": TICKERS,
        "n_days": int(rets.shape[0]),
        "vols": [float(v) for v in vols],
        "avg_pairwise_corr": avg_corr,
        "source": "Yahoo Finance chart API (adjusted close)",
        "methodology": "log returns, sample cov * 252",
    }
    (DATA_DIR / "universe_real_10.json").write_text(json.dumps(meta, indent=2))
    (DATA_DIR / "cov_real_10.json").write_text(json.dumps(cov.tolist()))
    (DATA_DIR / "rets_real_10.json").write_text(
        json.dumps({"dates": common_dates[1:], "tickers": TICKERS, "returns": rets.tolist()})
    )

    regime_rows = [
        {
            "as_of_date": as_of,
            "universe": "us_mega10_liquid",
            "metric": "realized_vol_1y_avg",
            "value": round(float(vols.mean()), 6),
            "methodology": "yahoo_adjclose_logret_samplecov252",
        },
        {
            "as_of_date": as_of,
            "universe": "us_mega10_liquid",
            "metric": "realized_vol_1y_p50",
            "value": round(float(np.median(vols)), 6),
            "methodology": "yahoo_adjclose_logret_samplecov252",
        },
        {
            "as_of_date": as_of,
            "universe": "us_mega10_liquid",
            "metric": "avg_pairwise_corr",
            "value": round(avg_corr, 6),
            "methodology": "yahoo_adjclose_logret_samplecorr",
        },
    ]
    regime_path = EXPORT_DIR / f"regime_summary_{as_of.replace('-', '')}.csv"
    with regime_path.open("w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["as_of_date", "universe", "metric", "value", "methodology"]
        )
        w.writeheader()
        w.writerows(regime_rows)

    print(f"\nWrote {DATA_DIR / 'universe_real_10.json'}")
    print(f"Wrote {DATA_DIR / 'cov_real_10.json'}")
    print(f"Wrote {regime_path}")
    print("Done.")


if __name__ == "__main__":
    main()
