"""Verify that Postgres exactly matches the registered public workbooks."""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from typing import Any

from postgres_etl import DEALS, REAL_PUBLIC, extract_deal, validate_registry


TOLERANCE = 1e-6


def close(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left == right
    numeric = (int, float, Decimal)
    if isinstance(left, numeric) and isinstance(right, numeric):
        return abs(float(left) - float(right)) <= TOLERANCE
    return left == right


def verify_connection(connection) -> list[str]:
    validate_registry()
    mismatches: list[str] = []

    with connection.cursor() as cursor:
        cursor.execute("SELECT deal_id FROM deals ORDER BY deal_id")
        actual_ids = {row[0] for row in cursor.fetchall()}
    expected_ids = set(DEALS)
    if actual_ids != expected_ids:
        mismatches.append(
            f"deal registry: db={sorted(actual_ids)} expected={sorted(expected_ids)}"
        )

    for deal_id, meta in DEALS.items():
        payload = extract_deal(deal_id, meta["path"])
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT deal_name, classification, sponsor,
                          overall_check_status, workbook_path
                   FROM deals WHERE deal_id = %s""",
                (deal_id,),
            )
            row = cursor.fetchone()
            if row is None:
                mismatches.append(f"{deal_id}: no deals row")
                continue
            name, classification, sponsor, check_status, path = row
            cover = payload["cover"]
            expected_header = (
                cover["deal_name"],
                REAL_PUBLIC,
                cover["sponsor"],
                payload["overall_check"],
                payload["path"],
            )
            if row != expected_header:
                mismatches.append(
                    f"{deal_id}/header: db={row!r} expected={expected_header!r}"
                )

            cursor.execute(
                """SELECT period, metric, value FROM deal_returns
                   WHERE deal_id = %s AND is_selected_exit""",
                (deal_id,),
            )
            database_returns = {
                (period, metric): value for period, metric, value in cursor.fetchall()
            }
            expected_returns = {
                (period, metric): value
                for period, selected, metric, value in payload["returns"]
                if selected
            }
            if set(database_returns) != set(expected_returns):
                mismatches.append(f"{deal_id}/selected returns: key set differs")
            for key, expected in expected_returns.items():
                if not close(database_returns.get(key), expected):
                    mismatches.append(
                        f"{deal_id}/returns/{key}: "
                        f"db={database_returns.get(key)!r} expected={expected!r}"
                    )

            cursor.execute(
                """SELECT period, metric, value FROM deal_debt_schedule
                   WHERE deal_id = %s""",
                (deal_id,),
            )
            database_debt = {
                (period, metric): value for period, metric, value in cursor.fetchall()
            }
            expected_debt = {
                (period, metric): value
                for period, _order, metric, value in payload["debt_schedule"]
            }
            if set(database_debt) != set(expected_debt):
                mismatches.append(f"{deal_id}/debt schedule: key set differs")
            for key, expected in expected_debt.items():
                if not close(database_debt.get(key), expected):
                    mismatches.append(
                        f"{deal_id}/debt/{key}: "
                        f"db={database_debt.get(key)!r} expected={expected!r}"
                    )

    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn",
        default=os.environ.get("FINANCE_SEGWAY_PG_DSN", "dbname=finance_segway"),
    )
    args = parser.parse_args()

    import psycopg2

    with psycopg2.connect(args.dsn) as connection:
        mismatches = verify_connection(connection)
    print(f"Checked {len(DEALS)} real-public deals against Postgres.")
    if mismatches:
        for mismatch in mismatches[:50]:
            print(f"  - {mismatch}")
        raise SystemExit(1)
    print("Postgres matches every registered source workbook. PASS")


if __name__ == "__main__":
    main()
