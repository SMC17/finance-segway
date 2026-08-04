"""Release-grade asset-management workbook with return and liquidity controls."""
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
    for name in ("Return Measurement", "Exposure & Liquidity", "Decision & Checks"):
        if name in workbook.sheetnames:
            del workbook[name]

    waterfall = workbook["Fee Waterfall"]
    waterfall["C16"] = "=MIN(MAX(C10-C14-C15,0),C15*C8/(1-C8)*C9)"
    waterfall["B24"] = "Waterfall conservation residual"
    waterfall["C24"] = "=C10-C21-C22"
    waterfall["C24"].number_format = CUR
    waterfall["C24"].border = BORDER
    waterfall["D24"] = "Gross profit must equal GP take plus LP take; management fee remains separate."
    waterfall["D24"].font = ITALIC_GRAY

    position = workbook.sheetnames.index("Fund Performance") + 1
    returns = workbook.create_sheet("Return Measurement", position)
    set_col_widths(returns, [4, 38, 16, 16, 16, 16, 44])
    returns["B2"] = "Time-Weighted, Money-Weighted, and Benchmark Return Controls"
    returns["B2"].font = TITLE
    for column, value in enumerate(["Metric", "Period 0", "Period 1", "Period 2", "Period 3", "Interpretation"], start=2):
        returns.cell(4, column, value)
    style_header_row(returns, 4, 6, start_col=2)
    labels = ["Beginning NAV", "Contributions", "Distributions", "Ending NAV", "Subperiod return"]
    for offset, label in enumerate(labels, start=5):
        returns.cell(offset, 2, label)
    for index, column in enumerate(range(3, 7), start=0):
        letter = chr(67 + index)
        fund_letter = chr(67 + index)
        returns.cell(5, column, f"='Fund NAV'!{fund_letter}5")
        returns.cell(6, column, f"='Fund NAV'!{fund_letter}6")
        returns.cell(7, column, f"='Fund NAV'!{fund_letter}9")
        returns.cell(8, column, f"='Fund NAV'!{fund_letter}10")
        returns.cell(9, column, f'=IFERROR(({letter}8+{letter}7-{letter}6)/{letter}5-1,"-")')
        for row in range(5, 9):
            returns.cell(row, column).number_format = CUR
            returns.cell(row, column).border = BORDER
        returns.cell(9, column).number_format = PCT
        returns.cell(9, column).border = BORDER
    returns["B12"] = "Time-weighted return"
    returns["C12"] = '=IF(COUNT(C9:F9)<4,"-",PRODUCT(1+C9:F9)-1)'
    returns["C12"].number_format = PCT
    returns["C12"].border = BORDER
    returns["B13"] = "Money-weighted return / IRR"
    returns["C13"] = "='Fund Performance'!C19"
    returns["C13"].number_format = PCT
    returns["C13"].border = BORDER
    returns["B14"] = "Benchmark return"
    returns["C14"] = 0.0
    returns["C14"].font = BLUE
    returns["C14"].fill = YELLOW_FILL
    returns["C14"].number_format = PCT
    returns["C14"].border = BORDER
    returns["B15"] = "Excess return"
    returns["C15"] = '=IF(AND(ISNUMBER(C12),ISNUMBER(C14)),C12-C14,"-")'
    returns["C15"].number_format = PCT
    returns["C15"].border = BORDER
    returns["B17"] = "Time-weighted return neutralizes external cash flows at each subperiod boundary; irregular intra-period flows require dated or daily valuation methods."
    returns["B17"].font = ITALIC_GRAY
    returns.sheet_view.showGridLines = False

    liquidity = workbook.create_sheet("Exposure & Liquidity", position + 1)
    set_col_widths(liquidity, [4, 40, 18, 18, 44])
    liquidity["B2"] = "Exposure, Concentration, Redemptions, and Liquidity Coverage"
    liquidity["B2"].font = TITLE
    for column, value in enumerate(["Metric", "Base", "Downside", "Control / interpretation"], start=2):
        liquidity.cell(4, column, value)
    style_header_row(liquidity, 4, 4, start_col=2)
    inputs = [
        ("Gross exposure", 150.0, 180.0, CUR, "sum of absolute long and short market exposures"),
        ("Net exposure", 60.0, 100.0, CUR, "long less short exposure"),
        ("Current NAV", "='Fund NAV'!F10", "='Fund NAV'!F10", CUR, "linked to current residual value"),
        ("Top-10 position exposure", 35.0, 55.0, CUR, "concentration numerator"),
        ("Illiquid / gated NAV", 15.0, 35.0, CUR, "assets not monetizable inside the review horizon"),
        ("Thirty-day redemption / distribution demand", 12.0, 40.0, CUR, "expected cash demand"),
        ("Unfunded commitments", 8.0, 20.0, CUR, "contractual capital-call exposure"),
        ("Unrestricted liquid assets", 30.0, 15.0, CUR, "cash plus assets monetizable inside thirty days"),
        ("Maximum top-10 concentration", 0.40, 0.40, PCT, "approved limit"),
        ("Maximum illiquid NAV", 0.25, 0.25, PCT, "approved limit"),
        ("Minimum liquidity coverage", 1.20, 1.20, MULT, "liquid assets / redemption plus commitments"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        liquidity.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = liquidity.cell(row, column, value)
            if not isinstance(value, str):
                cell.font = BLUE
                cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        liquidity.cell(row, 5, note)
    liquidity["B18"] = "Gross leverage"
    liquidity["C18"] = "=IFERROR(C5/C7,0)"
    liquidity["D18"] = "=IFERROR(D5/D7,0)"
    liquidity["B19"] = "Net exposure / NAV"
    liquidity["C19"] = "=IFERROR(C6/C7,0)"
    liquidity["D19"] = "=IFERROR(D6/D7,0)"
    liquidity["B20"] = "Top-10 concentration"
    liquidity["C20"] = "=IFERROR(C8/C7,0)"
    liquidity["D20"] = "=IFERROR(D8/D7,0)"
    liquidity["B21"] = "Illiquid NAV"
    liquidity["C21"] = "=IFERROR(C9/C7,0)"
    liquidity["D21"] = "=IFERROR(D9/D7,0)"
    liquidity["B22"] = "Liquidity coverage"
    liquidity["C22"] = "=IFERROR(C12/(C10+C11),0)"
    liquidity["D22"] = "=IFERROR(D12/(D10+D11),0)"
    liquidity["B23"] = "Downside status"
    liquidity["C23"] = '=IF(AND(D20<=D13,D21<=D14,D22>=D15),"PASS","BREACH")'
    for row in range(18, 24):
        for column in (3, 4):
            liquidity.cell(row, column).border = BORDER
    for row in (18, 19, 22):
        liquidity.cell(row, 3).number_format = MULT
        liquidity.cell(row, 4).number_format = MULT
    for row in (20, 21):
        liquidity.cell(row, 3).number_format = PCT
        liquidity.cell(row, 4).number_format = PCT
    liquidity.sheet_view.showGridLines = False

    checks = workbook.create_sheet("Decision & Checks", position + 2)
    set_col_widths(checks, [4, 42, 18, 18, 50])
    checks["B2"] = "Asset Management Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(["Check / decision", "Metric", "Status", "Interpretation / action"], start=2):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "NAV rollforward residual", "='Fund NAV'!F10-('Fund NAV'!F5+'Fund NAV'!F6+'Fund NAV'!F7-'Fund NAV'!F8-'Fund NAV'!F9)", '=IF(ABS(C5)<0.01,"PASS","FAIL")', "Ending NAV must conserve beginning NAV, flows, gains, fees, and distributions."),
        (6, "TVPI identity residual", "='Fund Performance'!C18-'Fund Performance'!C16-'Fund Performance'!C17", '=IF(OR(NOT(ISNUMBER(C6)),ABS(C6)<0.000001),"PASS","FAIL")', "TVPI must equal DPI plus RVPI."),
        (7, "Waterfall conservation residual", "='Fee Waterfall'!C24", '=IF(ABS(C7)<0.01,"PASS","FAIL")', "Gross profit must reconcile between LP and GP allocations."),
        (8, "Carry-rate bounds", "='Fee Waterfall'!C8", '=IF(AND(C8>=0,C8<1),"PASS","FAIL")', "Carry outside zero to one invalidates the waterfall."),
        (9, "Time-weighted return", "='Return Measurement'!C12", '=IF(ISNUMBER(C9),"PASS","REVIEW")', "Use valuation-consistent subperiods and disclose benchmark and composite policy."),
        (10, "Excess return", "='Return Measurement'!C15", '=IF(ISNUMBER(C10),"PASS","REVIEW")', "Benchmark-relative performance must use a documented and appropriate comparison."),
        (11, "Downside top-10 concentration", "='Exposure & Liquidity'!D20", '=IF(C11<=\'Exposure & Liquidity\'!D13,"PASS","BREACH")', "Escalate concentration and correlated exit risk."),
        (12, "Downside illiquid NAV", "='Exposure & Liquidity'!D21", '=IF(C12<=\'Exposure & Liquidity\'!D14,"PASS","BREACH")', "Illiquidity must be reconciled against gates, notice periods, and unfunded obligations."),
        (13, "Downside liquidity coverage", "='Exposure & Liquidity'!D22", '=IF(C13>=\'Exposure & Liquidity\'!D15,"PASS","BREACH")', "Liquid resources must cover modeled redemptions, distributions, and capital calls."),
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
        (18, "Ending NAV", "='Fund NAV'!F10", CUR),
        (19, "DPI", "='Fund Performance'!C16", MULT),
        (20, "RVPI", "='Fund Performance'!C17", MULT),
        (21, "TVPI", "='Fund Performance'!C18", MULT),
        (22, "Net IRR", "='Fund Performance'!C19", PCT),
        (23, "Time-weighted return", "='Return Measurement'!C12", PCT),
        (24, "Downside liquidity coverage", "='Exposure & Liquidity'!D22", MULT),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_am_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("AM_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
