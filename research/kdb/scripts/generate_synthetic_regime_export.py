\"\"\"Generate a synthetic daily-bar series and a regime-summary export
that exactly matches research/kdb/INTEGRATION_CONTRACTS.md Contract 1.

This pure-Python generator exists so the integration contract is executable
even when a kdb+ license is not present. Users who have kdb+ can load the
same conceptual data via the companion .q script.

Output:
  research/kdb/exports/regime_summary_YYYYMMDD.csv
\"\"\"
from __future__ import annotations

import csv
import datetime as dt
import math
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORT_DIR = REPO_ROOT / "research" / "kdb" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

UNIVERSE = "synthetic_10_liquid"
AS_OF = dt.date(2026, 8, 4)
SEED = 17
random.seed(SEED)

NAMES = [f"SYN{i:02d}" for i in range(1, 11)]
N_DAYS = 252


def generate_returns(n_days: int, n_names: int) -> list[list[float]]:
    rets = []
    for _ in range(n_days):
        common = random.gauss(0.0003, 0.008)
        day = [common + random.gauss(0.0, 0.012) for _ in range(n_names)]
        rets.append(day)
    return rets


def realized_vol(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var * 252)


def main() -> None:
    daily_rets = generate_returns(N_DAYS, len(NAMES))

    name_vols = []
    for j in range(len(NAMES)):
        series = [daily_rets[t][j] for t in range(N_DAYS)]
        name_vols.append(realized_vol(series))

    avg_vol = sum(name_vols) / len(name_vols)
    p50_vol = sorted(name_vols)[len(name_vols) // 2]
    avg_corr = 0.35  # fixed for reproducibility of the example

    rows = [
        {
            "as_of_date": AS_OF.isoformat(),
            "universe": UNIVERSE,
            "metric": "realized_vol_1y_avg",
            "value": round(avg_vol, 6),
            "methodology": "synthetic_gaussian_252d_seed17",
        },
        {
            "as_of_date": AS_OF.isoformat(),
            "universe": UNIVERSE,
            "metric": "realized_vol_1y_p50",
            "value": round(p50_vol, 6),
            "methodology": "synthetic_gaussian_252d_seed17",
        },
        {
            "as_of_date": AS_OF.isoformat(),
            "universe": UNIVERSE,
            "metric": "avg_pairwise_corr",
            "value": avg_corr,
            "methodology": "synthetic_fixed_example",
        },
    ]

    out_path = EXPORT_DIR / f"regime_summary_{AS_OF.strftime('%Y%m%d')}.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["as_of_date", "universe", "metric", "value", "methodology"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out_path}")
    for r in rows:
        print(f"  {r['metric']} = {r['value']}")


if __name__ == "__main__":
    main()
