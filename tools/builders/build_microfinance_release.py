"""Release-grade microfinance workbook with portfolio, funding, and conduct controls."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools.builders.legacy_release_adapter import build_release
    from tools.builders.template_helpers import BLUE, BOLD, BORDER, CUR, GRAY_FILL, ITALIC_GRAY, MULT, NUM, PCT, TITLE, YELLOW_FILL, set_col_widths, style_header_row
except ModuleNotFoundError:
    from legacy_release_adapter import build_release
    from template_helpers import BLUE, BOLD, BORDER, CUR, GRAY_FILL, ITALIC_GRAY, MULT, NUM, PCT, TITLE, YELLOW_FILL, set_col_widths, style_header_row


def _overall(check_range: str) -> str:
    return f'=IF(COUNTIF({check_range},"FAIL")+COUNTIF({check_range},"BREACH")>0,"BREACH",IF(COUNTIF({check_range},"REVIEW")>0,"REVIEW","PASS"))'


def enrich(workbook) -> None:
    for name in ("Portfolio Rollforward", "Funding & Liquidity", "Client & Conduct", "Decision & Checks"):
        if name in workbook.sheetnames:
            del workbook[name]

    portfolio = workbook["Loan Portfolio"]
    portfolio["B15"] = "Write-off ratio (period)"

    position = workbook.sheetnames.index("Loan Portfolio") + 1
    roll = workbook.create_sheet("Portfolio Rollforward", position)
    set_col_widths(roll, [4, 40, 18, 18, 18, 44])
    roll["B2"] = "Gross Loan Portfolio Rollforward and Restructuring"
    roll["B2"].font = TITLE
    roll["B3"] = "Active scenario"
    roll["C3"] = "Base"
    roll["C3"].font = BLUE
    roll["C3"].fill = YELLOW_FILL
    roll["C3"].border = BORDER
    for column, value in enumerate(["Metric", "Base", "Downside", "Active", "Interpretation"], start=2):
        roll.cell(4, column, value)
    style_header_row(roll, 4, 5, start_col=2)
    inputs = [
        ("Beginning gross loan portfolio", 100.0, 100.0, CUR, "opening principal balance"),
        ("Disbursements", 50.0, 10.0, CUR, "new principal advanced"),
        ("Principal collections", 45.0, 20.0, CUR, "cash principal received"),
        ("Write-offs", 2.0, 8.0, CUR, "principal removed under policy"),
        ("PAR >30 balance", 5.0, 35.0, CUR, "outstanding balance past due over 30 days"),
        ("PAR >90 balance", 2.0, 20.0, CUR, "subset past due over 90 days"),
        ("Restructured / rescheduled balance", 1.0, 15.0, CUR, "modified loans tracked separately"),
        ("Credit-risk warning ratio", 0.15, 0.15, PCT, "PAR30 + write-offs + restructures / portfolio"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        roll.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = roll.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        roll.cell(row, 5, f'=IF($C$3="Downside",D{row},C{row})')
        roll.cell(row, 5).number_format = number_format
        roll.cell(row, 5).border = BORDER
        roll.cell(row, 6, note)
    roll["B15"] = "Derived outputs"
    roll["B15"].font = BOLD
    roll["B15"].fill = GRAY_FILL
    outputs = [
        (16, "Ending gross loan portfolio", "=E5+E6-E7-E8", CUR),
        (17, "PAR 30", "=IFERROR(E9/E16,0)", PCT),
        (18, "PAR 90", "=IFERROR(E10/E16,0)", PCT),
        (19, "Write-off ratio", "=IFERROR(E8/AVERAGE(E5,E16),0)", PCT),
        (20, "Restructured ratio", "=IFERROR(E11/E16,0)", PCT),
        (21, "Composite credit-risk ratio", "=E17+E19+E20", PCT),
    ]
    for row, label, formula, number_format in outputs:
        roll.cell(row, 2, label)
        roll.cell(row, 5, formula)
        roll.cell(row, 5).number_format = number_format
        roll.cell(row, 5).border = BORDER
    roll["B23"] = "PAR and write-offs use outstanding balances and policy definitions; restructures remain visible rather than being treated as cured delinquency."
    roll["B23"].font = ITALIC_GRAY
    roll.sheet_view.showGridLines = False

    funding_position = workbook.sheetnames.index("Sustainability") + 1
    funding = workbook.create_sheet("Funding & Liquidity", funding_position)
    set_col_widths(funding, [4, 40, 18, 18, 44])
    funding["B2"] = "Funding Concentration, Maturity, and 30-Day Liquidity"
    funding["B2"].font = TITLE
    for column, value in enumerate(["Metric", "Base", "Downside", "Control / interpretation"], start=2):
        funding.cell(4, column, value)
    style_header_row(funding, 4, 4, start_col=2)
    inputs = [
        ("Liquid assets", 12.0, 4.0, CUR, "unrestricted cash and near-cash assets"),
        ("Committed undrawn funding", 8.0, 2.0, CUR, "available under enforceable facilities"),
        ("Thirty-day contractual outflows", 15.0, 18.0, CUR, "debt, operating, and disbursement obligations"),
        ("Largest funding provider balance", 20.0, 35.0, CUR, "single-provider exposure"),
        ("Total wholesale / institutional funding", 80.0, 70.0, CUR, "denominator for concentration"),
        ("Minimum liquidity coverage", 1.10, 1.10, MULT, "liquid assets plus committed funding / outflows"),
        ("Maximum provider concentration", 0.30, 0.30, PCT, "largest provider / total institutional funding"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        funding.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = funding.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        funding.cell(row, 5, note)
    funding["B14"] = "Liquidity coverage"
    funding["C14"] = "=IFERROR((C5+C6)/C7,0)"
    funding["D14"] = "=IFERROR((D5+D6)/D7,0)"
    funding["B15"] = "Funding gap"
    funding["C15"] = "=C5+C6-C7"
    funding["D15"] = "=D5+D6-D7"
    funding["B16"] = "Largest provider concentration"
    funding["C16"] = "=IFERROR(C8/C9,0)"
    funding["D16"] = "=IFERROR(D8/D9,0)"
    funding["B17"] = "Base status"
    funding["C17"] = '=IF(AND(C14>=C10,C16<=C11),"PASS","BREACH")'
    funding["B18"] = "Downside status"
    funding["C18"] = '=IF(AND(D14>=D10,D16<=D11),"PASS","BREACH")'
    for row in range(14, 19):
        for column in (3, 4):
            funding.cell(row, column).border = BORDER
    for row in (14, 16):
        funding.cell(row, 3).number_format = MULT if row == 14 else PCT
        funding.cell(row, 4).number_format = MULT if row == 14 else PCT
    funding["C15"].number_format = CUR
    funding["D15"].number_format = CUR
    funding.sheet_view.showGridLines = False

    conduct = workbook.create_sheet("Client & Conduct", funding_position + 1)
    set_col_widths(conduct, [4, 40, 18, 18, 48])
    conduct["B2"] = "Client Affordability, Pricing Transparency, and Conduct Controls"
    conduct["B2"].font = TITLE
    for column, value in enumerate(["Metric / control", "Input", "Status", "Evidence / action"], start=2):
        conduct.cell(4, column, value)
    style_header_row(conduct, 4, 4, start_col=2)
    rows = [
        (5, "Median borrower monthly income", 250.0, '=IF(C5>0,"PASS","BREACH")', "document source and update cadence"),
        (6, "Median monthly debt service", 35.0, '=IF(C6/C5<=0.30,"PASS","REVIEW")', "review repayment capacity and household cash-flow volatility"),
        (7, "Effective annualized borrower cost", 0.28, '=IF(C7<=0.40,"PASS","REVIEW")', "include interest, compulsory savings, fees, insurance, and transaction costs"),
        (8, "Clients with multiple active lenders (%)", 0.15, '=IF(C8<=0.25,"PASS","REVIEW")', "monitor over-indebtedness and bureau/data limitations"),
        (9, "Complaints closed within approved SLA (%)", 0.95, '=IF(C9>=0.90,"PASS","REVIEW")', "retain complaint taxonomy, root cause, and remediation"),
        (10, "Restructures receiving affordability reassessment (%)", 1.00, '=IF(C10=1,"PASS","BREACH")', "1.0 means every restructure is reassessed and documented"),
    ]
    for row, label, value, status, action in rows:
        conduct.cell(row, 2, label)
        conduct.cell(row, 3, value)
        conduct.cell(row, 3).font = BLUE
        conduct.cell(row, 3).fill = YELLOW_FILL
        conduct.cell(row, 3).number_format = PCT if row >= 7 else CUR
        conduct.cell(row, 3).border = BORDER
        conduct.cell(row, 4, status)
        conduct.cell(row, 4).border = BORDER
        conduct.cell(row, 5, action)
    conduct["B12"] = "These controls expose borrower harm and conduct risk; they are not a claim that a single universal affordability or pricing threshold applies across jurisdictions."
    conduct["B12"].font = ITALIC_GRAY
    conduct.sheet_view.showGridLines = False

    checks = workbook.create_sheet("Decision & Checks", funding_position + 2)
    set_col_widths(checks, [4, 42, 18, 18, 50])
    checks["B2"] = "Microfinance Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(["Check / decision", "Metric", "Status", "Interpretation / action"], start=2):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "Portfolio rollforward residual", "='Portfolio Rollforward'!E16-('Portfolio Rollforward'!E5+'Portfolio Rollforward'!E6-'Portfolio Rollforward'!E7-'Portfolio Rollforward'!E8)", '=IF(ABS(C5)<0.01,"PASS","FAIL")', "Ending portfolio must conserve across disbursements, collections, and write-offs."),
        (6, "PAR ordering", "='Portfolio Rollforward'!E17-'Portfolio Rollforward'!E18", '=IF(C6>=-0.000001,"PASS","FAIL")', "PAR90 must remain a subset of PAR30."),
        (7, "Composite credit-risk ratio", "='Portfolio Rollforward'!E21", '=IF(C7<=\'Portfolio Rollforward\'!E12,"PASS","BREACH")', "Escalate delinquency, restructures, and write-offs together rather than separately."),
        (8, "Reserve tie residual", "='Provisioning'!C9-'Loan Portfolio'!C5", '=IF(OR(NOT(ISNUMBER(C8)),ABS(C8)<0.01),"PASS","FAIL")', "Aging buckets must tie to the reported gross loan portfolio."),
        (9, "Reserve adequacy", "='Provisioning'!C13", '=IF(NOT(ISNUMBER(C9)),"REVIEW",IF(C9>=1,"PASS","BREACH"))', "Actual reserves must cover the modeled policy requirement."),
        (10, "Operational self-sufficiency", "='Sustainability'!C12", '=IF(NOT(ISNUMBER(C10)),"REVIEW",IF(C10>=1,"PASS","BREACH"))', "OSS below 100% indicates operating dependence on subsidy or capital support."),
        (11, "Financial self-sufficiency", "='Sustainability'!C13", '=IF(NOT(ISNUMBER(C11)),"REVIEW",IF(C11>=1,"PASS","BREACH"))', "FSS also adjusts for subsidized funding and capital costs."),
        (12, "Downside funding gap", "='Funding & Liquidity'!D15", '=IF(C12>=0,"PASS","BREACH")', "A negative 30-day gap requires committed funding, slower disbursement, or contingency liquidity."),
        (13, "Conduct-control exceptions", '=COUNTIF(\'Client & Conduct\'!D5:D10,"<>PASS")', '=IF(C13=0,"PASS","REVIEW")', "Growth and sustainability do not override affordability or conduct failures."),
    ]
    for row, label, formula, status, action in rows:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).border = BORDER
        checks.cell(row, 4, status)
        checks.cell(row, 4).border = BORDER
        checks.cell(row, 5, action)
    checks["B15"] = "Overall model status"
    checks["B15"].font = BOLD
    checks["C15"] = _overall("D5:D13")
    checks["C15"].font = BOLD
    checks["C15"].border = BORDER
    checks["B17"] = "Primary decision outputs"
    checks["B17"].font = BOLD
    checks["B17"].fill = GRAY_FILL
    outputs = [
        (18, "Ending gross loan portfolio", "='Portfolio Rollforward'!E16", CUR),
        (19, "PAR 30", "='Portfolio Rollforward'!E17", PCT),
        (20, "Write-off ratio", "='Portfolio Rollforward'!E19", PCT),
        (21, "OSS", "='Sustainability'!C12", PCT),
        (22, "FSS", "='Sustainability'!C13", PCT),
        (23, "Downside funding gap", "='Funding & Liquidity'!D15", CUR),
        (24, "Reserve adequacy", "='Provisioning'!C13", PCT),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_microfinance_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("MICROFINANCE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
