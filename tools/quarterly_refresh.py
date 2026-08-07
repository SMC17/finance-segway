"""The quarterly autopilot: one command runs the whole refresh cycle.

Sean's cadence: "all this only ever gets updated once a quarter, so once
it's all set up we will backfill then be on autopilot." This driver IS that
command. It re-runs, in order, every data-layer step the repo already has -
no new policy, no new data semantics, just the sequence an operator would
type by hand:

  1. Facts refresh     edgar_company_facts --all-sectors (full re-fetch:
                       refresh means overwrite, resume is --skip-existing)
  2. Exhibits refresh  edgar_earnings_exhibits --all-sectors --skip-existing
                       (new quarters add filings; frozen ones never change)
  3. Second source     nport_holdings fetch + cross-check per universe
  4. Classification    sec_sic_classifications (constituents may have
                       churned) + build_universe_taxonomy + validate
  5. Inventory         universe_coverage_report --report
  6. The clock         forecast_registration --check and --due

Steps run via subprocess against this repo's own CLIs, so the driver can
never drift from what the tools actually do. Any step failing stops the
run with the step named - a half-refreshed depot must not look finished.

    python tools/quarterly_refresh.py --dry-run     # print the plan
    python tools/quarterly_refresh.py               # run it (network side)
    python tools/quarterly_refresh.py --skip facts exhibits   # partial
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNIVERSE_FUNDS = {"QQQ": "1067839"}

EXTRA_CONCEPTS = [
    "ResearchAndDevelopmentExpense", "SellingAndMarketingExpense",
    "GeneralAndAdministrativeExpense", "ShareBasedCompensation",
    "CostOfRevenue", "ContractWithCustomerLiabilityCurrent",
    "ContractWithCustomerLiability", "RevenueRemainingPerformanceObligation",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "InventoryNet", "AccountsReceivableNetCurrent",
]


def plan() -> list[tuple[str, list[str]]]:
    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        ("facts", [py, "tools/data_fabric/edgar_company_facts.py",
                   "--all-sectors", "--prefer-annual", "--annual-series",
                   "--extra-concepts", *EXTRA_CONCEPTS]),
        ("exhibits", [py, "tools/data_fabric/edgar_earnings_exhibits.py",
                      "--all-sectors", "--skip-existing"]),
    ]
    for tag, cik in UNIVERSE_FUNDS.items():
        steps.append((f"nport-{tag}", [py, "tools/data_fabric/nport_holdings.py",
                                        "--cik", cik, "--tag", tag]))
        steps.append((f"nport-{tag}-check",
                      [py, "tools/data_fabric/nport_holdings.py", "--tag", tag,
                       "--cross-check", "--report",
                       f"tools/data_fabric/out/{tag}_nport_cross_check.json"]))
    steps += [
        ("classification", [py, "tools/data_fabric/sec_sic_classifications.py"]),
        ("taxonomy", [py, "tools/build_universe_taxonomy.py"]),
        ("taxonomy-validate", [py, "tools/validate_universe_taxonomy.py"]),
        ("coverage", [py, "tools/universe_coverage_report.py", "--gaps-only",
                      "--report", "standards/universe/coverage_report.json"]),
        ("registry-check", [py, "tools/forecast_registration.py", "--check"]),
        ("registry-due", [py, "tools/forecast_registration.py", "--due"]),
    ]
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan without executing")
    parser.add_argument("--skip", nargs="*", default=[],
                        help="step names to skip (see --dry-run for names)")
    args = parser.parse_args()
    steps = [(name, cmd) for name, cmd in plan() if name not in args.skip]
    if args.dry_run:
        for name, cmd in steps:
            print(f"{name}: {' '.join(cmd[1:])}")
        return 0
    env_path = f"{ROOT}:{ROOT / 'tools'}"
    for name, cmd in steps:
        print(f"== {name} ==", flush=True)
        result = subprocess.run(
            cmd, cwd=ROOT,
            env={**__import__('os').environ, "PYTHONPATH": env_path},
        )
        if result.returncode != 0:
            print(f"REFRESH STOPPED at step '{name}' (exit {result.returncode}) - "
                  "a half-refreshed depot must not look finished")
            return result.returncode
    print("refresh complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
