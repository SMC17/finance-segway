"""Fetch and receipt a real public ten-asset market-data research snapshot.

The command requires an explicit ``--as-of`` date and has no generated-data
fallback. It uses only the Python standard library for data preparation.
Outputs remain research-only until licensing and human review permit commit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
EXPORT_DIR = ROOT / "research/kdb/exports"
UNIVERSE_ID = "us_mega10_liquid"
TICKERS = ("AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B", "JPM", "XOM", "JNJ")
SOURCE_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
METHODOLOGY = "adjusted-close log returns; pairwise-complete common dates; sample covariance annualized by 252"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def epoch(day: date) -> int:
    return int(datetime.combine(day, time(), tzinfo=timezone.utc).timestamp())


def source_url(symbol: str, start: date, end: date) -> str:
    query = urllib.parse.urlencode(
        {
            "period1": epoch(start),
            "period2": epoch(end + timedelta(days=1)),
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
    return f"{SOURCE_BASE}/{urllib.parse.quote(symbol)}?{query}"


def fetch_prices(symbol: str, start: date, end: date, timeout: int) -> tuple[dict[str, float], str]:
    url = source_url(symbol, start, end)
    request = urllib.request.Request(url, headers={"User-Agent": "Finance-Segway/real-data-research"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    chart = payload.get("chart", {})
    if chart.get("error") or not chart.get("result"):
        raise ValueError(f"{symbol}: source returned no result: {chart.get('error')}")
    result = chart["result"][0]
    timestamps = result.get("timestamp", [])
    indicators = result.get("indicators", {})
    adjusted = indicators.get("adjclose", [{}])[0].get("adjclose")
    closes = adjusted or indicators.get("quote", [{}])[0].get("close", [])
    prices: dict[str, float] = {}
    for timestamp, price in zip(timestamps, closes):
        if price is None or float(price) <= 0:
            continue
        day = datetime.fromtimestamp(timestamp, timezone.utc).date()
        if start <= day <= end:
            prices[day.isoformat()] = float(price)
    if len(prices) < 252:
        raise ValueError(f"{symbol}: expected at least 252 observations, got {len(prices)}")
    return prices, url


def sample_covariance(columns: list[list[float]]) -> list[list[float]]:
    observations = len(columns[0])
    if observations < 2 or any(len(column) != observations for column in columns):
        raise ValueError("return columns must have a common nontrivial length")
    means = [math.fsum(column) / observations for column in columns]
    return [
        [
            math.fsum(
                (left_value - means[left]) * (right_value - means[right])
                for left_value, right_value in zip(columns[left], columns[right])
            )
            / (observations - 1)
            * 252.0
            for right in range(len(columns))
        ]
        for left in range(len(columns))
    ]


def prepare_snapshot(series: dict[str, dict[str, float]], as_of: date) -> tuple[dict[str, Any], list[list[float]]]:
    common_dates = sorted(set.intersection(*(set(values) for values in series.values())))
    if len(common_dates) < 253:
        raise ValueError(f"expected at least 253 common prices, got {len(common_dates)}")
    returns: list[list[float]] = []
    for ticker in TICKERS:
        prices = [series[ticker][day] for day in common_dates]
        returns.append([math.log(prices[index] / prices[index - 1]) for index in range(1, len(prices))])
    covariance = sample_covariance(returns)
    volatilities = [math.sqrt(max(covariance[index][index], 0.0)) for index in range(len(TICKERS))]
    correlations = [
        covariance[left][right] / (volatilities[left] * volatilities[right])
        for left in range(len(TICKERS))
        for right in range(left)
        if volatilities[left] and volatilities[right]
    ]
    snapshot = {
        "schema_version": "1.0",
        "classification": "external_historical_market_observation",
        "universe_id": UNIVERSE_ID,
        "as_of": as_of.isoformat(),
        "tickers": list(TICKERS),
        "dates": common_dates,
        "adjusted_close": {ticker: [series[ticker][day] for day in common_dates] for ticker in TICKERS},
        "methodology": METHODOLOGY,
    }
    metadata = {
        "as_of": as_of.isoformat(),
        "tickers": list(TICKERS),
        "n_prices": len(common_dates),
        "n_returns": len(common_dates) - 1,
        "volatilities": volatilities,
        "avg_pairwise_correlation": math.fsum(correlations) / len(correlations),
        "methodology": METHODOLOGY,
    }
    return {"raw": snapshot, "metadata": metadata}, covariance


def write_release(snapshot: dict[str, Any], covariance: list[list[float]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    as_of = snapshot["metadata"]["as_of"]
    raw_path = DATA_DIR / f"raw_prices_{as_of}.json"
    meta_path = DATA_DIR / f"universe_{as_of}.json"
    covariance_path = DATA_DIR / f"covariance_{as_of}.json"
    atomic_write(raw_path, canonical_bytes(snapshot["raw"]))
    atomic_write(meta_path, canonical_bytes(snapshot["metadata"]))
    atomic_write(covariance_path, canonical_bytes(covariance))

    csv_path = EXPORT_DIR / f"regime_summary_{as_of.replace('-', '')}.csv"
    fields = ["as_of_date", "universe", "metric", "value", "methodology", "source_url", "source_as_of", "source_checksum", "license_note"]
    raw_hash = sha256_file(raw_path)
    source_root = SOURCE_BASE + "/"
    values = snapshot["metadata"]
    rows = [
        ("realized_vol_1y_avg", math.fsum(values["volatilities"]) / len(TICKERS)),
        ("realized_vol_1y_p50", sorted(values["volatilities"])[len(TICKERS) // 2]),
        ("avg_pairwise_corr", values["avg_pairwise_correlation"]),
    ]
    temporary_csv = csv_path.with_suffix(".csv.tmp")
    with temporary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for metric, value in rows:
            writer.writerow(
                {
                    "as_of_date": as_of,
                    "universe": UNIVERSE_ID,
                    "metric": metric,
                    "value": f"{value:.12g}",
                    "methodology": METHODOLOGY,
                    "source_url": source_root,
                    "source_as_of": as_of,
                    "source_checksum": raw_hash,
                    "license_note": "Review Yahoo Finance terms before redistribution",
                }
            )
    os.replace(temporary_csv, csv_path)

    receipt = {
        "schema_version": "1.0",
        "classification": "external_historical_market_observation",
        "evidence_status": "research_only_unreviewed",
        "counts_toward_maturity": False,
        "as_of": as_of,
        "methodology": METHODOLOGY,
        "sources": sources,
        "artifacts": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (raw_path, meta_path, covariance_path, csv_path)
        },
    }
    receipt_path = DATA_DIR / f"receipt_{as_of}.json"
    atomic_write(receipt_path, canonical_bytes(receipt))
    return {"receipt": str(receipt_path.relative_to(ROOT)), **receipt}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--lookback-days", type=int, default=420)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    start = args.as_of - timedelta(days=args.lookback_days)
    series: dict[str, dict[str, float]] = {}
    sources: list[dict[str, Any]] = []
    for ticker in TICKERS:
        prices, url = fetch_prices(ticker, start, args.as_of, args.timeout)
        series[ticker] = prices
        sources.append(
            {
                "ticker": ticker,
                "url": url,
                "start": start.isoformat(),
                "end": args.as_of.isoformat(),
                "observations": len(prices),
            }
        )
    snapshot, covariance = prepare_snapshot(series, args.as_of)
    print(json.dumps(write_release(snapshot, covariance, sources), indent=2))


if __name__ == "__main__":
    main()
