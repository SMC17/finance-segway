"""
postgres_etl.py — extract verified LBO/PE deal outputs into Postgres.

v2: rebuilt after the institutional-rebuild workbook restructuring made
v1's hardcoded cell references (03_Private_Equity/deals/*.xlsx, fixed row
numbers on a "Returns"/"Debt Schedule" pair) point at files and sheets that
no longer exist anywhere in the repo. This version reads by ROW LABEL and
COLUMN HEADER instead of fixed coordinates, so a future template
restructuring changes what gets extracted, not whether extraction breaks.

This is a query/reporting layer, not a second calculation engine: every
number loaded here is read directly from a workbook that is already
committed, dated, and recalculated. Real-public instances (Home Depot,
Macy's, ...) are frozen evidence -- this script does NOT recalculate or
mutate them; it only reads openpyxl data_only values as committed.

Usage:
    python3 tools/postgres_etl.py                 # load all registered deals
    python3 tools/postgres_etl.py --dsn "dbname=finance_segway"
    python3 tools/postgres_etl.py --dry-run        # print extracted rows, skip DB writes

Requires: psycopg2 (pip install psycopg2-binary), a reachable Postgres
database with db/schema.sql already applied.
"""
import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import openpyxl  # noqa: E402

# Deal registry: workbook path (repo-relative) -> classification. Pilot
# scope is Private Equity / LBO (03_Private_Equity/instances/) -- both the
# real-public instances and the still-present synthetic benchmarks (their
# retirement is tracked separately; this ETL treats them as a distinct,
# clearly-labeled classification rather than assuming either will always
# be present). Add a new deal by adding one line here.
DEALS = {
    "home_depot_2023": {
        "path": "03_Private_Equity/instances/public_home_depot_2023.xlsx",
        "classification": "real_public",
    },
    "macys_2020_adversarial": {
        "path": "03_Private_Equity/instances/public_macys_2020_adversarial.xlsx",
        "classification": "real_public",
    },
    "benchmark_reference_buyout": {
        "path": "03_Private_Equity/instances/benchmark_reference_buyout.xlsx",
        "classification": "synthetic_benchmark",
    },
    "benchmark_adversarial_contraction": {
        "path": "03_Private_Equity/instances/benchmark_adversarial_contraction.xlsx",
        "classification": "synthetic_benchmark",
    },
}


def read_labeled_table(ws, header_row, label_col=2, first_data_col=3, last_data_col=None):
    """Generic label x column-header table reader: returns
    {row_label: {column_header: value}}. Reads by scanning the actual
    header row and row labels present in the sheet -- no fixed row/column
    assumptions beyond "there's a header row and a label column"."""
    last_data_col = last_data_col or ws.max_column
    headers = {}
    for c in range(first_data_col, last_data_col + 1):
        h = ws.cell(row=header_row, column=c).value
        if h:
            headers[c] = h
    table = {}
    for r in range(header_row + 1, ws.max_row + 1):
        label = ws.cell(row=r, column=label_col).value
        if not label:
            continue
        table[label] = {headers[c]: ws.cell(row=r, column=c).value for c in headers}
    return table


def period_order(period_label):
    if period_label == "Close":
        return 0
    if isinstance(period_label, str) and period_label.startswith("Year "):
        try:
            return int(period_label.split(" ")[1])
        except (IndexError, ValueError):
            return 99
    return 99  # e.g. "Selected exit" sorts last


def extract_cover(wb):
    cov = wb["Cover"]
    return {
        "deal_name": cov["C4"].value,
        "sponsor": cov["C5"].value,
        "entry_date": str(cov["C6"].value) if cov["C6"].value is not None else None,
        "active_scenario": cov["C9"].value,
    }


def extract_overall_check(wb):
    ws = wb["Checks"]
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == "Overall":
            return ws.cell(row=r, column=3).value
    return None


def extract_assumptions(wb):
    ws = wb["Assumptions"]
    table = read_labeled_table(ws, header_row=4, label_col=2, first_data_col=3, last_data_col=6)
    rows = []
    for label, cols in table.items():
        rows.append({
            "assumption": label,
            "base": cols.get("Base"),
            "downside": cols.get("Downside"),
            "active": cols.get("Active"),
            "units": cols.get("Units / note"),
        })
    return rows


def extract_sources_uses(wb):
    ws = wb["Sources & Uses"]
    rows = []
    header_row = None
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == "Uses" and ws.cell(row=r, column=5).value == "Sources":
            header_row = r
            break
    if header_row is None:
        return rows
    r = header_row + 1
    while r <= ws.max_row:
        label = ws.cell(row=r, column=2).value
        amount = ws.cell(row=r, column=3).value
        if label and isinstance(amount, (int, float)) and not str(label).lower().startswith("total"):
            rows.append(("Uses", label, amount))
        label = ws.cell(row=r, column=5).value
        amount = ws.cell(row=r, column=6).value
        if label and isinstance(amount, (int, float)) and not str(label).lower().startswith(("total", "sources less")):
            rows.append(("Sources", label, amount))
        r += 1
    return rows


def extract_debt_schedule(wb):
    ws = wb["Debt Schedule"]
    table = read_labeled_table(ws, header_row=4, label_col=2, first_data_col=3)
    rows = []
    for metric, cols in table.items():
        for period, value in cols.items():
            if isinstance(value, (int, float)):
                rows.append((period, period_order(period), metric, value))
    return rows


def extract_returns(wb):
    ws = wb["Returns Waterfall"]
    table = read_labeled_table(ws, header_row=4, label_col=2, first_data_col=3)
    rows = []
    for metric, cols in table.items():
        for period, value in cols.items():
            if isinstance(value, (int, float)):
                rows.append((period, period == "Selected exit", metric, value))
    return rows


def extract_deal(deal_id, path):
    abs_path = os.path.join(REPO_ROOT, path)
    wb = openpyxl.load_workbook(abs_path, data_only=True)
    return {
        "deal_id": deal_id,
        "path": path,
        "cover": extract_cover(wb),
        "overall_check": extract_overall_check(wb),
        "assumptions": extract_assumptions(wb),
        "sources_uses": extract_sources_uses(wb),
        "debt_schedule": extract_debt_schedule(wb),
        "returns": extract_returns(wb),
    }


def load_deal(cur, deal_id, classification, payload):
    cov = payload["cover"]
    cur.execute(
        """
        INSERT INTO deals (deal_id, deal_name, classification, sponsor, entry_date,
                            active_scenario, overall_check_status, workbook_path, last_synced_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (deal_id) DO UPDATE SET
            deal_name = EXCLUDED.deal_name, classification = EXCLUDED.classification,
            sponsor = EXCLUDED.sponsor, entry_date = EXCLUDED.entry_date,
            active_scenario = EXCLUDED.active_scenario,
            overall_check_status = EXCLUDED.overall_check_status,
            workbook_path = EXCLUDED.workbook_path, last_synced_at = now()
        """,
        (deal_id, cov["deal_name"], classification, cov["sponsor"], cov["entry_date"],
         cov["active_scenario"], payload["overall_check"], payload["path"]),
    )

    cur.execute("DELETE FROM deal_assumptions WHERE deal_id = %s", (deal_id,))
    for row in payload["assumptions"]:
        cur.execute(
            """INSERT INTO deal_assumptions (deal_id, assumption, base, downside, active, units)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (deal_id, row["assumption"], row["base"], row["downside"], row["active"], row["units"]),
        )

    cur.execute("DELETE FROM deal_sources_uses WHERE deal_id = %s", (deal_id,))
    for side, label, amount in payload["sources_uses"]:
        cur.execute(
            "INSERT INTO deal_sources_uses (deal_id, side, line_item, amount) VALUES (%s, %s, %s, %s)",
            (deal_id, side, label, amount),
        )

    cur.execute("DELETE FROM deal_debt_schedule WHERE deal_id = %s", (deal_id,))
    for period, order, metric, value in payload["debt_schedule"]:
        cur.execute(
            """INSERT INTO deal_debt_schedule (deal_id, period, period_order, metric, value)
               VALUES (%s, %s, %s, %s, %s)""",
            (deal_id, period, order, metric, value),
        )

    cur.execute("DELETE FROM deal_returns WHERE deal_id = %s", (deal_id,))
    for period, is_selected, metric, value in payload["returns"]:
        cur.execute(
            """INSERT INTO deal_returns (deal_id, period, is_selected_exit, metric, value)
               VALUES (%s, %s, %s, %s, %s)""",
            (deal_id, period, is_selected, metric, value),
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dsn", default=os.environ.get("FINANCE_SEGWAY_PG_DSN", "dbname=finance_segway"))
    ap.add_argument("--dry-run", action="store_true", help="extract and print, skip DB writes")
    args = ap.parse_args()

    conn = None
    if not args.dry_run:
        import psycopg2
        conn = psycopg2.connect(args.dsn)

    try:
        for deal_id, meta in DEALS.items():
            print(f"Extracting {deal_id} ({meta['path']}) ...", file=sys.stderr)
            payload = extract_deal(deal_id, meta["path"])
            if args.dry_run:
                returns_by_metric = {}
                for period, is_selected, metric, value in payload["returns"]:
                    if is_selected:
                        returns_by_metric[metric] = value
                print(f"  {meta['classification']}: sponsor MOIC="
                      f"{returns_by_metric.get('Sponsor MOIC')}, "
                      f"sponsor IRR={returns_by_metric.get('Sponsor IRR')}, "
                      f"overall check={payload['overall_check']}")
                continue
            with conn.cursor() as cur:
                load_deal(cur, deal_id, meta["classification"], payload)
            conn.commit()
            print(f"  loaded {deal_id} into Postgres", file=sys.stderr)
    finally:
        if conn is not None:
            conn.close()

    print("Done." if not args.dry_run else "Dry run complete (no DB writes).", file=sys.stderr)


if __name__ == "__main__":
    main()
