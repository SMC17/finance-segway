"""Release-grade real-estate workbook with lease, debt, REIT, and risk controls."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools.builders.legacy_release_adapter import build_release
    from tools.builders.template_helpers import (
        BLACK,
        BLUE,
        BOLD,
        BORDER,
        CUR,
        GRAY_FILL,
        ITALIC_GRAY,
        MULT,
        NUM,
        PCT,
        PCT2,
        TITLE,
        YELLOW_FILL,
        set_col_widths,
        style_header_row,
    )
except ModuleNotFoundError:
    from legacy_release_adapter import build_release
    from template_helpers import (
        BLACK,
        BLUE,
        BOLD,
        BORDER,
        CUR,
        GRAY_FILL,
        ITALIC_GRAY,
        MULT,
        NUM,
        PCT,
        PCT2,
        TITLE,
        YELLOW_FILL,
        set_col_widths,
        style_header_row,
    )


def _overall(check_range: str) -> str:
    return f'=IF(COUNTIF({check_range},"FAIL")+COUNTIF({check_range},"BREACH")>0,"BREACH",IF(COUNTIF({check_range},"REVIEW")>0,"REVIEW","PASS"))'


def enrich(workbook) -> None:
    for name in ("Lease Roll", "Debt Schedule", "Decision & Checks"):
        if name in workbook.sheetnames:
            del workbook[name]

    proforma = workbook["Property Pro Forma"]
    proforma["B6"] = "Vacancy & credit loss"
    proforma["B10"] = "Operating expenses (taxes, insurance, management, R&M)"
    proforma["B12"] = "Recurring capex reserve"
    proforma["B13"] = "Debt service (P&I)"
    proforma["C7"] = "=C5-C6"
    proforma["C9"] = "=C7+C8"
    proforma["C11"] = "=C9-C10"
    proforma["C14"] = "=C11-C12-C13"

    reit = workbook["REIT FFO-AFFO"]
    reit["B6"] = "Gains on property sales"
    reit["B9"] = "Recurring capex / leasing costs"
    reit["B10"] = "Straight-line rent adjustment"
    reit["C7"] = "=C4+C5-C6"
    reit["C11"] = "=C7-C9-C10"
    reit["D11"] = "AFFO is non-GAAP and must disclose its definition and reconciliation; this implementation deducts recurring capex and straight-line rent."
    reit["D11"].font = ITALIC_GRAY

    hold = workbook["5-Year Hold & IRR"]
    lease_position = workbook.sheetnames.index("Property Pro Forma") + 1
    lease = workbook.create_sheet("Lease Roll", lease_position)
    set_col_widths(lease, [4, 12, 18, 15, 17, 16, 16, 16, 18, 16, 14])
    lease["B2"] = "Lease Expiration, Renewal, Downtime, and Occupancy Roll"
    lease["B2"].font = TITLE
    headers = ["Year", "Beginning annual rent", "Expiring rent %", "Renewal probability", "Renewal spread", "Downtime months", "Lost rent", "Renewed rent", "Ending annual rent", "Economic occupancy"]
    for column, value in enumerate(headers, start=2):
        lease.cell(4, column, value)
    style_header_row(lease, 4, len(headers), start_col=2)
    assumptions = [
        (0.18, 0.75, 0.03, 3.0),
        (0.20, 0.72, 0.03, 3.0),
        (0.22, 0.70, 0.025, 4.0),
        (0.18, 0.68, 0.02, 4.0),
        (0.25, 0.65, 0.02, 5.0),
    ]
    for index, (expiry, renewal, spread, downtime) in enumerate(assumptions, start=0):
        row = 5 + index
        lease.cell(row, 2, index + 1)
        lease.cell(row, 3, "='Property Pro Forma'!C5" if row == 5 else f"=J{row-1}")
        lease.cell(row, 3).number_format = CUR
        for column, value, number_format in (
            (4, expiry, PCT),
            (5, renewal, PCT),
            (6, spread, PCT),
            (7, downtime, "0.0"),
        ):
            cell = lease.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        lease.cell(row, 8, f"=C{row}*D{row}*(1-E{row})*G{row}/12")
        lease.cell(row, 9, f"=C{row}*D{row}*E{row}*(1+F{row})")
        lease.cell(row, 10, f"=C{row}*(1-D{row})+I{row}")
        lease.cell(row, 11, f"=IFERROR(1-H{row}/C{row},0)")
        for column in (8, 9, 10):
            lease.cell(row, column).number_format = CUR
            lease.cell(row, column).border = BORDER
        lease.cell(row, 11).number_format = PCT
        lease.cell(row, 11).border = BORDER
    lease["B12"] = "This roll deliberately separates contractual expiration, renewal probability, spread, and downtime; new-leasing assumptions must be added explicitly rather than hidden in rent growth."
    lease["B12"].font = ITALIC_GRAY
    lease.freeze_panes = "B5"
    lease.sheet_view.showGridLines = False

    debt_position = workbook.sheetnames.index("Cap Rate & Valuation") + 1
    debt = workbook.create_sheet("Debt Schedule", debt_position)
    set_col_widths(debt, [4, 12, 18, 16, 16, 16, 18, 16, 16, 16])
    debt["B2"] = "Property Debt Amortization and Coverage"
    debt["B2"].font = TITLE
    debt["B3"] = "Interest rate"
    debt["C3"] = 0.06
    debt["C3"].font = BLUE
    debt["C3"].fill = YELLOW_FILL
    debt["C3"].number_format = PCT
    debt["C3"].border = BORDER
    debt["B4"] = "Amortization term (years)"
    debt["C4"] = 25
    debt["C4"].font = BLUE
    debt["C4"].fill = YELLOW_FILL
    debt["C4"].number_format = NUM
    debt["C4"].border = BORDER
    debt["B5"] = "Minimum DSCR"
    debt["C5"] = 1.25
    debt["C5"].font = BLUE
    debt["C5"].fill = YELLOW_FILL
    debt["C5"].number_format = MULT
    debt["C5"].border = BORDER
    for column, value in enumerate(["Year", "Beginning debt", "Interest", "Principal", "Debt service", "Ending debt", "NOI", "DSCR", "Headroom"], start=2):
        debt.cell(7, column, value)
    style_header_row(debt, 7, 9, start_col=2)
    for year in range(1, 6):
        row = 7 + year
        debt.cell(row, 2, year)
        debt.cell(row, 3, "='Cap Rate & Valuation'!C10" if year == 1 else f"=G{row-1}")
        debt.cell(row, 4, f"=C{row}*$C$3")
        debt.cell(row, 6, f"=MIN(C{row},MAX(0,-PMT($C$3,$C$4,'Cap Rate & Valuation'!$C$10)-D{row}))")
        debt.cell(row, 5, f"=D{row}+F{row}")
        debt.cell(row, 7, f"=MAX(0,C{row}-F{row})")
        debt.cell(row, 8, f"='5-Year Hold & IRR'!{chr(66+year)}13")
        debt.cell(row, 9, f"=IFERROR(H{row}/E{row},0)")
        debt.cell(row, 10, f"=I{row}-$C$5")
        for column in range(3, 9):
            debt.cell(row, column).number_format = CUR
            debt.cell(row, column).border = BORDER
        debt.cell(row, 9).number_format = MULT
        debt.cell(row, 10).number_format = MULT
        debt.cell(row, 9).border = BORDER
        debt.cell(row, 10).border = BORDER
    debt.freeze_panes = "B8"
    debt.sheet_view.showGridLines = False

    proforma["C13"] = "='Debt Schedule'!E8"
    for offset, source_row in enumerate(range(8, 13), start=3):
        hold.cell(14, offset, f"='Debt Schedule'!E{source_row}")
        hold.cell(14, offset).number_format = CUR
        hold.cell(16, offset, f"=IFERROR({chr(64+offset)}13/{chr(64+offset)}14,0)")
        hold.cell(16, offset).number_format = MULT
    hold["C22"] = "=-'Debt Schedule'!G12"

    checks_position = workbook.sheetnames.index("REIT FFO-AFFO") + 1
    checks = workbook.create_sheet("Decision & Checks", checks_position)
    set_col_widths(checks, [4, 38, 18, 18, 48])
    checks["B2"] = "Real Estate / REIT Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(["Check / decision", "Metric", "Status", "Interpretation / action"], start=2):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "NOI identity residual", "='Property Pro Forma'!C11-('Property Pro Forma'!C5-'Property Pro Forma'!C6+'Property Pro Forma'!C8-'Property Pro Forma'!C10)", '=IF(ABS(C5)<0.01,"PASS","FAIL")', "NOI must reconcile from gross rent through vacancy, other income, and operating expenses."),
        (6, "FFO bridge residual", "='REIT FFO-AFFO'!C7-('REIT FFO-AFFO'!C4+'REIT FFO-AFFO'!C5-'REIT FFO-AFFO'!C6)", '=IF(ABS(C6)<0.01,"PASS","FAIL")', "FFO must reconcile from GAAP net income under the disclosed Nareit-style definition."),
        (7, "AFFO bridge residual", "='REIT FFO-AFFO'!C11-('REIT FFO-AFFO'!C7-'REIT FFO-AFFO'!C9-'REIT FFO-AFFO'!C10)", '=IF(ABS(C7)<0.01,"PASS","FAIL")', "AFFO is non-GAAP; recurring capex and straight-line rent adjustments must be explicit."),
        (8, "Minimum five-year DSCR", "=MIN('Debt Schedule'!I8:I12)", '=IF(C8>=\'Debt Schedule\'!C5,"PASS",IF(C8>=1,"REVIEW","BREACH"))', "Escalate covenant pressure and refinance dependency."),
        (9, "Loan-to-value", "=IFERROR('Cap Rate & Valuation'!C10/'Cap Rate & Valuation'!C8,0)", '=IF(C9<=0.75,"PASS",IF(C9<=0.85,"REVIEW","BREACH"))', "High leverage magnifies cap-rate and NOI shocks."),
        (10, "Minimum economic occupancy", "=MIN('Lease Roll'!K5:K9)", '=IF(C10>=0.90,"PASS",IF(C10>=0.80,"REVIEW","BREACH"))', "Review tenant rollover, downtime, leasing costs, and concentration."),
        (11, "Year-one levered cash flow", "='Property Pro Forma'!C14", '=IF(C11>=0,"PASS","BREACH")', "Negative cash flow requires funded reserves or a restructuring plan."),
        (12, "Exit cap spread vs going-in", "='5-Year Hold & IRR'!C6-'Cap Rate & Valuation'!C9", '=IF(C12>=0,"PASS","REVIEW")', "Cap-rate compression should never be an unchallenged base-case return driver."),
    ]
    for row, label, formula, status, action in rows:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).border = BORDER
        checks.cell(row, 4, status)
        checks.cell(row, 4).border = BORDER
        checks.cell(row, 5, action)
    checks["B14"] = "Overall model status"
    checks["B14"].font = BOLD
    checks["C14"] = _overall("D5:D12")
    checks["C14"].font = BOLD
    checks["C14"].border = BORDER
    checks["B16"] = "Primary decision outputs"
    checks["B16"].font = BOLD
    checks["B16"].fill = GRAY_FILL
    outputs = [
        (17, "NOI", "='Property Pro Forma'!C11", CUR),
        (18, "Going-in cap rate", "='Cap Rate & Valuation'!C9", PCT),
        (19, "Levered IRR", "='5-Year Hold & IRR'!C27", PCT),
        (20, "Equity MOIC", "='5-Year Hold & IRR'!C28", MULT),
        (21, "FFO", "='REIT FFO-AFFO'!C7", CUR),
        (22, "AFFO", "='REIT FFO-AFFO'!C11", CUR),
        (23, "Ending debt", "='Debt Schedule'!G12", CUR),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_real_estate_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("REAL_ESTATE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
