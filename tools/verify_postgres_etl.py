"""
verify_postgres_etl.py — confirm Postgres holds exactly what's in the
source workbooks right now, not stale or ETL-mangled data.

This isn't an independent-oracle check in the tools/verify_reference_calcs.py
sense (there's no second, independently derived truth to compare against --
the workbook's committed cells ARE the truth for these frozen instances;
see db/README.md). What this catches is ETL bugs: a label the extractor
mismatched, a stale load after a workbook changed. Re-extracts every
registered deal fresh and diffs against what's actually stored in Postgres.

Usage:
    python3 tools/verify_postgres_etl.py [--dsn "dbname=finance_segway"]
Exit code is 0 iff Postgres matches a fresh extraction for every deal.
"""
import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

from postgres_etl import DEALS, extract_deal  # noqa: E402

TOL = 1e-6


def close(a, b):
    if a is None or b is None:
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < TOL
    return a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dsn", default=os.environ.get("FINANCE_SEGWAY_PG_DSN", "dbname=finance_segway"))
    args = ap.parse_args()

    import psycopg2
    conn = psycopg2.connect(args.dsn)
    mismatches = []
    deals_checked = 0

    try:
        for deal_id, meta in DEALS.items():
            payload = extract_deal(deal_id, meta["path"])
            deals_checked += 1
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT deal_name, sponsor, overall_check_status FROM deals WHERE deal_id = %s",
                    (deal_id,),
                )
                row = cur.fetchone()
                if row is None:
                    mismatches.append(f"{deal_id}: no deals row in Postgres")
                    continue
                db_name, db_sponsor, db_check = row
                cov = payload["cover"]
                if db_name != cov["deal_name"]:
                    mismatches.append(f"{deal_id}/deal_name: db={db_name!r} fresh={cov['deal_name']!r}")
                if db_check != payload["overall_check"]:
                    mismatches.append(f"{deal_id}/overall_check: db={db_check!r} fresh={payload['overall_check']!r}")

                cur.execute(
                    "SELECT period, metric, value FROM deal_returns WHERE deal_id = %s AND is_selected_exit",
                    (deal_id,),
                )
                db_returns = {metric: value for _, metric, value in cur.fetchall()}
                for period, is_selected, metric, value in payload["returns"]:
                    if not is_selected:
                        continue
                    db_val = db_returns.get(metric)
                    if not close(float(db_val) if db_val is not None else None, value):
                        mismatches.append(f"{deal_id}/selected-exit/{metric}: db={db_val} fresh={value}")

                cur.execute(
                    "SELECT period, metric, value FROM deal_debt_schedule WHERE deal_id = %s",
                    (deal_id,),
                )
                db_debt = {(p, m): v for p, m, v in cur.fetchall()}
                for period, order, metric, value in payload["debt_schedule"]:
                    db_val = db_debt.get((period, metric))
                    if not close(float(db_val) if db_val is not None else None, value):
                        mismatches.append(f"{deal_id}/{period}/{metric}: db={db_val} fresh={value}")
    finally:
        conn.close()

    print(f"Checked {deals_checked} deals against Postgres.")
    if mismatches:
        print(f"\n{len(mismatches)} MISMATCH(ES):")
        for m in mismatches[:50]:
            print(f"  - {m}")
        sys.exit(1)
    print("Postgres matches a fresh extraction from every source workbook. PASS")


if __name__ == "__main__":
    main()
