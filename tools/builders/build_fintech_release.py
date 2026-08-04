"""Release-grade fintech/payments workbook with cohorts, fraud, capital, and controls."""
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
    for name in ("Network & Cohorts", "Capital & Liquidity", "Operational Controls", "Decision & Checks"):
        if name in workbook.sheetnames:
            del workbook[name]

    fraud = workbook["Fraud & Risk"]
    fraud["B10"] = "Fraud warning threshold (bps of TPV)"
    fraud["C10"] = 50.0
    fraud["C10"].font = BLUE
    fraud["C10"].fill = YELLOW_FILL
    fraud["C10"].number_format = NUM
    fraud["C10"].border = BORDER
    fraud["D15"] = "Threshold is model-owned and must be approved for the product, channel, geography, and control environment."
    fraud["D15"].font = ITALIC_GRAY
    fraud["B16"] = "Fraud threshold status"
    fraud["C16"] = '=IF(C6<=C10,"PASS","BREACH")'
    fraud["C16"].font = BOLD
    fraud["C16"].border = BORDER

    cohort_position = workbook.sheetnames.index("Cohort Retention") + 1
    cohort = workbook.create_sheet("Network & Cohorts", cohort_position)
    set_col_widths(cohort, [4, 38, 18, 18, 18, 42])
    cohort["B2"] = "Customer, Merchant, and Network Activity Rollforward"
    cohort["B2"].font = TITLE
    for column, value in enumerate(["Metric", "Base", "Downside", "Active", "Interpretation"], start=2):
        cohort.cell(4, column, value)
    style_header_row(cohort, 4, 5, start_col=2)
    assumptions = [
        ("Starting active users", 100000.0, 100000.0, NUM, "beginning-of-period active customers"),
        ("Retention rate", 0.90, 0.55, PCT, "same-period active retention"),
        ("New users", 20000.0, 5000.0, NUM, "newly activated customers"),
        ("Starting active merchants", 5000.0, 5000.0, NUM, "beginning merchant base"),
        ("Merchant retention rate", 0.94, 0.70, PCT, "merchant-side retention"),
        ("New merchants", 750.0, 100.0, NUM, "newly activated merchants"),
        ("Transactions", 1500000.0, 300000.0, NUM, "successful transactions in period"),
        ("Failed / reversed transactions", 15000.0, 45000.0, NUM, "operational and risk failures"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(assumptions, start=5):
        cohort.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = cohort.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        cohort.cell(row, 5, f'=IF($C$3="Downside",D{row},C{row})')
        cohort.cell(row, 5).number_format = number_format
        cohort.cell(row, 5).border = BORDER
        cohort.cell(row, 6, note)
    cohort["B3"] = "Active scenario"
    cohort["C3"] = "Base"
    cohort["C3"].font = BLUE
    cohort["C3"].fill = YELLOW_FILL
    cohort["C3"].border = BORDER
    cohort["B15"] = "Derived outputs"
    cohort["B15"].font = BOLD
    cohort["B15"].fill = GRAY_FILL
    outputs = [
        (16, "Ending active users", "=E5*E6+E7", NUM),
        (17, "Ending active merchants", "=E8*E9+E10", NUM),
        (18, "Transactions per active user", "=IFERROR(E11/E16,0)", "0.00"),
        (19, "Transactions per active merchant", "=IFERROR(E11/E17,0)", "0.00"),
        (20, "Transaction failure rate", "=IFERROR(E12/(E11+E12),0)", PCT2),
        (21, "Cross-side network density", "=IFERROR(E11/(E16*E17),0)", "0.000000"),
    ]
    for row, label, formula, number_format in outputs:
        cohort.cell(row, 2, label)
        cohort.cell(row, 5, formula)
        cohort.cell(row, 5).number_format = number_format
        cohort.cell(row, 5).border = BORDER
    cohort.freeze_panes = "B5"
    cohort.sheet_view.showGridLines = False

    capital_position = workbook.sheetnames.index("Fraud & Risk") + 1
    capital = workbook.create_sheet("Capital & Liquidity", capital_position)
    set_col_widths(capital, [4, 40, 18, 18, 44])
    capital["B2"] = "Capital, Settlement, and Liquidity Coverage"
    capital["B2"].font = TITLE
    for column, value in enumerate(["Metric", "Base", "Downside", "Units / control"], start=2):
        capital.cell(4, column, value)
    style_header_row(capital, 4, 4, start_col=2)
    inputs = [
        ("Available regulatory / loss-absorbing capital", 20.0, 5.0, CUR, "approved eligible capital"),
        ("Required capital", 10.0, 20.0, CUR, "regulatory or internal risk requirement"),
        ("Unrestricted cash and liquid investments", 25.0, 8.0, CUR, "same-day or near-cash liquidity"),
        ("Thirty-day settlement and operating obligations", 15.0, 25.0, CUR, "cash outflows under stress"),
        ("Restricted customer / safeguarding funds", 30.0, 30.0, CUR, "not available for corporate liquidity"),
        ("Minimum capital coverage", 1.20, 1.20, MULT, "available / required"),
        ("Minimum liquidity coverage", 1.10, 1.10, MULT, "unrestricted liquidity / obligations"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        capital.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = capital.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        capital.cell(row, 5, note)
    capital["B14"] = "Capital coverage"
    capital["C14"] = "=IFERROR(C5/C6,0)"
    capital["D14"] = "=IFERROR(D5/D6,0)"
    capital["B15"] = "Liquidity coverage"
    capital["C15"] = "=IFERROR(C7/C8,0)"
    capital["D15"] = "=IFERROR(D7/D8,0)"
    capital["B16"] = "Capital headroom"
    capital["C16"] = "=C5-C6"
    capital["D16"] = "=D5-D6"
    capital["B17"] = "Liquidity headroom"
    capital["C17"] = "=C7-C8"
    capital["D17"] = "=D7-D8"
    capital["B18"] = "Base status"
    capital["C18"] = '=IF(AND(C14>=C10,C15>=C11),"PASS","BREACH")'
    capital["B19"] = "Downside status"
    capital["C19"] = '=IF(AND(D14>=D10,D15>=D11),"PASS","BREACH")'
    for row in range(14, 20):
        for column in (3, 4):
            capital.cell(row, column).border = BORDER
    for row in (14, 15):
        capital.cell(row, 3).number_format = MULT
        capital.cell(row, 4).number_format = MULT
    for row in (16, 17):
        capital.cell(row, 3).number_format = CUR
        capital.cell(row, 4).number_format = CUR
    capital.sheet_view.showGridLines = False

    controls = workbook.create_sheet("Operational Controls", capital_position + 1)
    set_col_widths(controls, [4, 28, 18, 24, 22, 20, 42])
    controls["B2"] = "Payments Endpoint Security and Fraud-Control Register"
    controls["B2"].font = TITLE
    for column, value in enumerate(["Control", "Owner", "Type", "Metric", "Threshold", "Retained evidence"], start=2):
        controls.cell(4, column, value)
    style_header_row(controls, 4, 6, start_col=2)
    rows = [
        ("Strong authentication and privileged access", "Security", "Prevent", "Privileged-access exceptions", "0 unresolved", "access review and exception log"),
        ("Payment instruction integrity", "Payments Ops", "Prevent", "Unauthorized instruction rate", "approved threshold", "signed instruction and change history"),
        ("Real-time fraud detection", "Risk", "Detect", "Fraud bps / TPV", "Fraud & Risk!C10", "alert, decision, and loss record"),
        ("Settlement reconciliation", "Finance Ops", "Detect", "Unreconciled settlement items", "0 material", "daily reconciliation evidence"),
        ("Incident response and customer protection", "Operations", "Respond", "Time to contain", "approved SLA", "incident timeline and remediation"),
        ("Recovery and continuity", "Engineering", "Recover", "Recovery test result", "PASS", "dated recovery exercise"),
        ("Third-party endpoint governance", "Vendor Risk", "Govern", "Critical vendors overdue", "0", "assessment and remediation record"),
    ]
    for row, values in enumerate(rows, start=5):
        for column, value in enumerate(values, start=2):
            controls.cell(row, column, value)
            controls.cell(row, column).border = BORDER
    controls["B14"] = "Controls are an operating register, not a claim of compliance. Owners must replace illustrative thresholds with approved product-specific limits."
    controls["B14"].font = ITALIC_GRAY
    controls.freeze_panes = "B5"
    controls.sheet_view.showGridLines = False

    checks = workbook.create_sheet("Decision & Checks", capital_position + 2)
    set_col_widths(checks, [4, 38, 18, 18, 48])
    checks["B2"] = "Fintech / Payments Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(["Check / decision", "Metric", "Status", "Interpretation / action"], start=2):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "Revenue identity residual", "='Unit Economics'!C14-'Unit Economics'!C5*'Unit Economics'!C6", '=IF(ABS(C5)<0.01,"PASS","FAIL")', "Revenue must equal TPV multiplied by take rate."),
        (6, "Processing-cost residual", "='Unit Economics'!C15-'Unit Economics'!C5*'Unit Economics'!C7", '=IF(ABS(C6)<0.01,"PASS","FAIL")', "Network and processing costs must reconcile to volume and rate."),
        (7, "Fraud-loss residual", "='Fraud & Risk'!C12-'Fraud & Risk'!C5*'Fraud & Risk'!C6/10000", '=IF(ABS(C7)<0.01,"PASS","FAIL")', "Fraud loss must reconcile from TPV and the bps convention."),
        (8, "LTV / CAC", "='Unit Economics'!C19", '=IF(C8>=3,"PASS",IF(C8>=1,"REVIEW","BREACH"))', "Low unit economics require pricing, retention, channel, or cost remediation."),
        (9, "Contribution after risk losses", "='Unit Economics'!C16-'Fraud & Risk'!C14", '=IF(C9>=0,"PASS","BREACH")', "Volume growth is not valuable when processing, fraud, chargeback, and credit losses consume net revenue."),
        (10, "Maximum retention increase", "=MAX('Cohort Retention'!D9-'Cohort Retention'!C9,'Cohort Retention'!E9-'Cohort Retention'!D9,'Cohort Retention'!F9-'Cohort Retention'!E9,'Cohort Retention'!G9-'Cohort Retention'!F9,'Cohort Retention'!H9-'Cohort Retention'!G9,'Cohort Retention'!I9-'Cohort Retention'!H9,'Cohort Retention'!J9-'Cohort Retention'!I9)", '=IF(C10<=0.000001,"PASS","REVIEW")', "Retention should not improve with age without an explicit reactivation or cohort-definition explanation."),
        (11, "Fraud threshold", "='Fraud & Risk'!C6", '=IF(C11<=\'Fraud & Risk\'!C10,"PASS","BREACH")', "Escalate fraud losses above the approved product threshold."),
        (12, "Downside capital coverage", "='Capital & Liquidity'!D14", '=IF(C12>=\'Capital & Liquidity\'!D10,"PASS","BREACH")', "Capital must remain above the approved requirement in downside conditions."),
        (13, "Downside liquidity coverage", "='Capital & Liquidity'!D15", '=IF(C13>=\'Capital & Liquidity\'!D11,"PASS","BREACH")', "Restricted customer funds may not be counted as corporate liquidity."),
        (14, "Transaction failure rate", "='Network & Cohorts'!E20", '=IF(C14<=0.02,"PASS",IF(C14<=0.05,"REVIEW","BREACH"))', "Operational failure degrades retention, unit economics, and network trust."),
    ]
    for row, label, formula, status, action in rows:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).border = BORDER
        checks.cell(row, 4, status)
        checks.cell(row, 4).border = BORDER
        checks.cell(row, 5, action)
    checks["B16"] = "Overall model status"
    checks["B16"].font = BOLD
    checks["C16"] = _overall("D5:D14")
    checks["C16"].font = BOLD
    checks["C16"].border = BORDER
    checks["B18"] = "Primary decision outputs"
    checks["B18"].font = BOLD
    checks["B18"].fill = GRAY_FILL
    outputs = [
        (19, "TPV", "='Unit Economics'!C5", CUR),
        (20, "Net revenue after processing", "='Unit Economics'!C16", CUR),
        (21, "LTV", "='Unit Economics'!C18", CUR),
        (22, "LTV / CAC", "='Unit Economics'!C19", MULT),
        (23, "Total risk-related loss", "='Fraud & Risk'!C14", CUR),
        (24, "Ending active users", "='Network & Cohorts'!E16", NUM),
        (25, "Base capital coverage", "='Capital & Liquidity'!C14", MULT),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_fintech_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("FINTECH_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
