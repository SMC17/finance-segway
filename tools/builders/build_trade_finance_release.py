"""Release-grade trade-finance workbook with credit, facility, and document controls."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools.builders.legacy_release_adapter import build_release
    from tools.builders.template_helpers import (
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
    for name in ("Credit & Facility", "Documentary Controls", "Decision & Checks"):
        if name in workbook.sheetnames:
            del workbook[name]

    cost = workbook["LC & Factoring Cost"]
    cost["C21"] = '=IFERROR(C19/C20*365/C17,"-")'
    cost["D21"] = "Effective cost uses the fee divided by net proceeds and annualizes by the collection period."
    cost["D21"].font = ITALIC_GRAY

    position = workbook.sheetnames.index("Working Capital Cycle") + 1
    credit = workbook.create_sheet("Credit & Facility", position)
    set_col_widths(credit, [4, 40, 18, 18, 18, 44])
    credit["B2"] = "Counterparty Credit, Country Risk, and Facility Utilization"
    credit["B2"].font = TITLE
    credit["B3"] = "Active scenario"
    credit["C3"] = "Base"
    credit["C3"].font = BLUE
    credit["C3"].fill = YELLOW_FILL
    credit["C3"].border = BORDER
    for column, value in enumerate(["Metric", "Base", "Downside", "Active", "Owner / interpretation"], start=2):
        credit.cell(4, column, value)
    style_header_row(credit, 4, 5, start_col=2)
    inputs = [
        ("Facility limit", 100.0, 100.0, CUR, "approved committed amount"),
        ("Drawn amount", 60.0, 120.0, CUR, "current and stress utilization"),
        ("Exposure at default", 60.0, 120.0, CUR, "drawn plus applicable contingent exposure"),
        ("Probability of default", 0.02, 0.20, PCT, "point-in-time or approved stress PD"),
        ("Loss given default", 0.40, 0.70, PCT, "net of collateral and recoveries"),
        ("Gross transaction margin", 8.0, 10.0, CUR, "before credit and country risk"),
        ("Country / transfer-risk cost", 0.5, 5.0, CUR, "approved economic charge"),
        ("Maximum utilization", 0.90, 0.90, PCT, "warning threshold"),
        ("Maximum cash-conversion days", 120.0, 120.0, "0.0", "working-capital warning threshold"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        credit.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = credit.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        credit.cell(row, 5, f'=IF($C$3="Downside",D{row},C{row})')
        credit.cell(row, 5).number_format = number_format
        credit.cell(row, 5).border = BORDER
        credit.cell(row, 6, note)
    credit["B16"] = "Derived outputs"
    credit["B16"].font = BOLD
    credit["B16"].fill = GRAY_FILL
    outputs = [
        (17, "Facility utilization", "=IFERROR(E6/E5,0)", PCT),
        (18, "Expected loss", "=E7*E8*E9", CUR),
        (19, "Risk-adjusted margin", "=E10-E18-E11", CUR),
        (20, "Cash conversion days", "='Working Capital Cycle'!C15", "0.0"),
        (21, "Approximate working capital need", "='Working Capital Cycle'!C16", CUR),
    ]
    for row, label, formula, number_format in outputs:
        credit.cell(row, 2, label)
        credit.cell(row, 5, formula)
        credit.cell(row, 5).number_format = number_format
        credit.cell(row, 5).border = BORDER
    credit.freeze_panes = "B5"
    credit.sheet_view.showGridLines = False

    doc_position = workbook.sheetnames.index("LC & Factoring Cost") + 1
    docs = workbook.create_sheet("Documentary Controls", doc_position)
    set_col_widths(docs, [4, 38, 18, 18, 48])
    docs["B2"] = "Documentary Credit Examination and Exception Register"
    docs["B2"].font = TITLE
    for column, value in enumerate(["Control", "Input / metric", "Status", "Evidence / action"], start=2):
        docs.cell(4, column, value)
    style_header_row(docs, 4, 4, start_col=2)
    controls = [
        (5, "Days from shipment to presentation", 10.0, '=IF(C5<=21,"PASS","REVIEW")', "compare against credit terms and applicable presentation period"),
        (6, "Document discrepancies identified", 0.0, '=IF(C6=0,"PASS","REVIEW")', "retain discrepancy list, waiver, refusal, or cure evidence"),
        (7, "Sanctions / restricted-party screening complete", 1.0, '=IF(C7=1,"PASS","BREACH")', "1=yes; evidence must be dated and corridor-specific"),
        (8, "Transport / title document matched", 1.0, '=IF(C8=1,"PASS","BREACH")', "1=yes; verify issuer, consignee, dates, quantity, and goods description"),
        (9, "Insurance document matched where required", 1.0, '=IF(C9=1,"PASS","REVIEW")', "1=yes; review insured amount, risks, currency, and date"),
        (10, "Refusal / discrepancy notice within required period", 1.0, '=IF(C10=1,"PASS","BREACH")', "1=yes; retain timestamp and complete discrepancy statement"),
        (11, "Counterparty waiver documented", 1.0, '=IF(OR(C6=0,C11=1),"PASS","BREACH")', "1=yes when discrepant documents are accepted"),
        (12, "Original documents / electronic presentation controlled", 1.0, '=IF(C12=1,"PASS","BREACH")', "1=yes; preserve authenticity, version, and presentation evidence"),
    ]
    for row, label, value, status, action in controls:
        docs.cell(row, 2, label)
        docs.cell(row, 3, value)
        docs.cell(row, 3).font = BLUE
        docs.cell(row, 3).fill = YELLOW_FILL
        docs.cell(row, 3).number_format = NUM
        docs.cell(row, 3).border = BORDER
        docs.cell(row, 4, status)
        docs.cell(row, 4).border = BORDER
        docs.cell(row, 5, action)
    docs["B14"] = "This register operationalizes documentary review but is not a substitute for legal advice or the controlling credit text."
    docs["B14"].font = ITALIC_GRAY
    docs.freeze_panes = "B5"
    docs.sheet_view.showGridLines = False

    checks = workbook.create_sheet("Decision & Checks", doc_position + 1)
    set_col_widths(checks, [4, 40, 18, 18, 50])
    checks["B2"] = "Trade Finance Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(["Check / decision", "Metric", "Status", "Interpretation / action"], start=2):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "Cash-conversion identity residual", "='Working Capital Cycle'!C15-('Working Capital Cycle'!C12+'Working Capital Cycle'!C13-'Working Capital Cycle'!C14)", '=IF(OR(NOT(ISNUMBER(C5)),ABS(C5)<0.000001),"PASS","FAIL")', "DSO plus DIO less DPO must equal the reported cash-conversion cycle."),
        (6, "Facility utilization", "='Credit & Facility'!E17", '=IF(C6<=\'Credit & Facility\'!E12,"PASS",IF(C6<=1,"REVIEW","BREACH"))', "Escalate excess utilization and contingent-exposure conversion."),
        (7, "Expected loss residual", "='Credit & Facility'!E18-'Credit & Facility'!E7*'Credit & Facility'!E8*'Credit & Facility'!E9", '=IF(ABS(C7)<0.000001,"PASS","FAIL")', "Expected loss must equal EAD multiplied by PD and LGD."),
        (8, "Risk-adjusted margin", "='Credit & Facility'!E19", '=IF(C8>=0,"PASS","BREACH")', "A transaction that loses money after credit and country risk should not be approved on nominal margin."),
        (9, "Cash-conversion days", "='Credit & Facility'!E20", '=IF(NOT(ISNUMBER(C9)),"REVIEW",IF(C9<=\'Credit & Facility\'!E13,"PASS","REVIEW"))', "Longer cycles increase funding and performance risk."),
        (10, "Annualized LC cost", "='LC & Factoring Cost'!C10", '=IF(ISNUMBER(C10),"PASS","REVIEW")', "Confirm tenor, issuance, confirmation, amendment, and discrepancy fees."),
        (11, "Effective factoring APR", "='LC & Factoring Cost'!C21", '=IF(ISNUMBER(C11),"PASS","REVIEW")', "Compare fee to net proceeds and actual collection period."),
        (12, "Documentary-control exceptions", "=COUNTIF('Documentary Controls'!D5:D12,"<>PASS")", '=IF(C12=0,"PASS","REVIEW")', "No financing-cost comparison overrides unresolved documentary or sanctions controls."),
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
        (17, "Cash conversion days", "='Working Capital Cycle'!C15", "0.0"),
        (18, "Working capital required", "='Working Capital Cycle'!C16", CUR),
        (19, "Facility utilization", "='Credit & Facility'!E17", PCT),
        (20, "Expected loss", "='Credit & Facility'!E18", CUR),
        (21, "Risk-adjusted margin", "='Credit & Facility'!E19", CUR),
        (22, "Cheapest financing channel", "='Financing Cost Comparison'!C19", "General"),
        (23, "Cheapest annualized cost", "='Financing Cost Comparison'!C20", PCT),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_trade_finance_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("TRADE_FINANCE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
