"""Build the integrated public-finance credit archetype.

The workbook preserves both public-finance lenses: sovereign / issuer debt
sustainability and municipal / revenue-bond debt-service coverage. It adds
scenario switching, a five-year operating forecast, borrowing and reserves,
coverage tests, sensitivity analysis, source registration, and visible checks.

Usage:
    python tools/builders/build_public_finance_template.py --output PUBLIC_FINANCE_template.xlsx
"""
from __future__ import annotations

import argparse
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from institutional_helpers import (
    BLUE, CUR, DARK, INTFMT, LIGHT_GRENN, LIGHT_RED, MULT, PCT,
    add_cover, add_refresh_log, add_status_rules, finalize,
    formula_cell, header, input_cell, set_widths, title, total_row,
)

SHEETS = [
    "Cover", "Assumptions", "Debt Sustainability", "Revenue & Expenditure",
    "Debt Service", "Coverage", "Scenarios", "Sensitivity", "Checks", "Sources", "RefreshLog",
]


def build(output: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for name in SHEETS:
        wb.create_sheet(name)

    add_cover(wb, "[ISSUER] — Public Finance Credit Model", [
        ("Issuer:", "[Sovereign / state / municipality / authority]"),
        ("Instrument:", "GO / revenue bond / sovereign note"),
        ("Last refreshed:", "[date]"),
        ("Next payment / issuance date:", "[date]"),
        ("Refresh cadence:", "Weekly"),
        ("Active scenario:", "Base"),
        ("Units:", "$ in millions unless noted"),
    ])

    # Assumptions -----------------------------------------------------------------
    ws = wb["Assumptions"]
    title(ws, "B2:F2", "Public Finance Assumptions")
    header(ws, 4, 2, ["Assumption", "Base", "Downside", "Active", "Units / source"])
    assumptions = [
        ("Population / service base", 1_000_000, 950_000, "people / accounts", INTFMT),
        ("Recurring revenue", 1_200.0, 1_080.0, "$mm", CUR),
        ("Recurring expenditure", 1_050.0, 1_090.0, "$mm", CUR),
        ("Capital expenditure", 180.0, 220.0, "$mm", CUR),
        ("Cash & unrestricted reserves", 300.0, 220.0, "$mm", CUR),
        ("Gross debt outstanding", 2_500.0, 2_500.0, "$mm", CUR),
        ("Annual scheduled principal", 125.0, 125.0, "$mm", CUR),
        ("Pledged revenue", 420.0, 360.0, "$mm", CUR),
        ("Intergovernmental transfers", 150.0, 120.0, "$mm", CUR),
        ("Revenue growth", 0.03, -0.02, "%", PCT),
        ("Expenditure growth", 0.035, 0.05, "%", PCT),
        ("Effective interest rate", 0.045, 0.06, "%", PCT),
        ("Maximum debt / revenue", 2.50, 2.50, "x", MULT),
        ("Minimum DSCR", 1.50, 1.50, "x", MULT),
        ("Minimum days cash", 90.0, 90.0, "days", "0.0"),
        ("Pension / OPEB contribution", 90.0, 110.0, "$mm", CUR),
        ("Nominal GDP / revenue-base growth (g)", 0.03, 0.00, "%", PCT),
        ("Current primary balance", 0.01, -0.03, "% of revenue base", PCT),
        ("Debt-service reserve fund", 50.0, 40.0, "$mm", CUR),
    ]
    for row, (label, base, downside, units, fmt) in enumerate(assumptions, start=5):
        ws.cell(row=row, column=2, value=label)
        input_cell(ws.cell(row=row, column=3, value=base), fmt)
        input_cell(ws.cell(row=row, column=4, value=downside), fmt)
        formula_cell(ws.cell(row=row, column=5, value=f'=IF(Cover!$C$9="Downside",D{row},C{row})'), fmt, cross_sheet=True)
        ws.cell(row=row, column=6, value=units)
    set_widths(ws, {"A": 4, "B": 42, "C": 15, "D": 15, "E": 15, "F": 30})
    ws.freeze_panes = "A5"

    # Debt sustainability ---------------------------------------------------------
    ws = wb["Debt Sustainability"]
    title(ws, "B2:F2", "Debt Sustainability Analysis")
    header(ws, 4, 2, ["Metric", "Current / Active", "Downside", "Units", "Interpretation"])
    rows = [
        ("Debt ratio (debt / revenue base)", "=IFERROR(Assumptions!E10/Assumptions!E6,0)", "=IFERROR(Assumptions!D10/Assumptions!D6,0)", "x", "Debt burden against recurring revenue / GDP proxy", MULT),
        ("Effective interest rate (r)", "=Assumptions!E16", "=Assumptions!D16", "%", "Weighted effective rate on debt", PCT),
        ("Nominal growth (g)", "=Assumptions!E21", "=Assumptions!D21", "%", "Nominal growth of tax / revenue base", PCT),
        ("r - g", "=C6-C7", "=D6-D7", "%", "Positive differential raises stabilization burden", PCT),
        ("Current primary balance", "=Assumptions!E22", "=Assumptions!D22", "% of base", "Surplus positive; deficit negative", PCT),
        ("Debt-stabilizing primary balance", "=IFERROR((C6-C7)/(1+C7)*C5,0)", "=IFERROR((D6-D7)/(1+D7)*D5,0)", "% of base", "Minimum primary balance to stabilize ratio", PCT),
        ("Primary-balance gap", "=C9-C10", "=D9-D10", "% of base", "Positive = stronger than stabilizing requirement", PCT),
        ("One-year projected debt ratio", "=IFERROR((1+C6)/(1+C7)*C5-C9,0)", "=IFERROR((1+D6)/(1+D7)*D5-D9,0)", "x", "Standard one-period debt-dynamics identity", MULT),
        ("Debt trajectory", '=IF(C12<=C5,"STABILIZING / FALLING","RISING")', '=IF(D12<=D5,"STABILIZING / FALLING","RISING")', "status", "Directional screen; review stock-flow adjustments", None),
    ]
    for row, (label, active, downside, units, note, fmt) in enumerate(rows, start=5):
        ws.cell(row=row, column=2, value=label)
        ws.cell(row=row, column=3, value=active)
        ws.cell(row=row, column=4, value=downside)
        if fmt:
            ws.cell(row=row, column=3).number_format = fmt
            ws.cell(row=row, column=4).number_format = fmt
        ws.cell(row=row, column=5, value=units)
        ws.cell(row=row, column=6, value=note)
    ws.conditional_formatting.add("C13:D13", FormulaRule(formula=['C13="STABILIZING / FALLING"'], fill=PatternFill("solid", fgColor=LIGHT_GREEN)))
    ws.conditional_formatting.add("C13:D13", FormulaRule(formula=['C13="RISING"'], fill=PatternFill("solid", fgColor=LIGHT_RED)))
    set_widths(ws, {"A": 4, "B": 40, "C": 17, "D": 17, "E": 16, "F": 52})

    # Operating forecast ----------------------------------------------------------
    ws = wb["Revenue & Expenditure"]
    title(ws, "B2:H2", "Operating Forecast")
    header(ws, 4, 2, ["$mm", "Current", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"])
    labels = [
        "Recurring revenue", "Revenue growth", "Recurring expenditure", "Expenditure growth",
        "Operating surplus", "Operating margin", "Pension / OPEB contribution",
        "Net operating result", "Capital expenditure", "Free cash flow before debt service",
    ]
    for row, label in enumerate(labels, start=5):
        ws.cell(row=row, column=2, value=label)
    for row in (5, 9, 12, 14):
        ws.cell(row=row, column=2).font = Font(name="Arial", size=10, bold=True, color=DARK)
    formula_cell(ws.cell(5, 3, "=Assumptions!E6"), CUR, cross_sheet=True)
    formula_cell(ws.cell(7, 3, "=Assumptions!E7"), CUR, cross_sheet=True)
    ws["C9"] = "=C5-C7"; ws["C9"].number_format = CUR
    ws["C10"] = "=IFERROR(C9/C5,0)"; ws["C10"].number_format = PCT
    formula_cell(ws.cell(11, 3, "=Assumptions!E20"), CUR, cross_sheet=True)
    ws["C12"] = "=C9-C11"; ws["C12"].number_format = CUR
    formula_cell(ws.cell(13, 3, "=Assumptions!E8"), CUR, cross_sheet=True)
    ws["C14"] = "=C12-C13"; ws["C14"].number_format = CUR
    for col in range(4, 9):
        letter, prev = get_column_letter(col), get_column_letter(col - 1)
        formulas = {
            5: f"={prev}5*(1+Assumptions!$E$14)",
            6: f"=IFERROR({letter}5/{prev}5-1,0)",
            7: f"={prev}7*(1+Assumptions!$E$15)",
            8: f"=IFERROR({letter}7/{prev}7-1,0)",
            9: f"={letter}5-{letter}7",
            10: f"=IFERROR({letter}9/{letter}5,0)",
            11: "=Assumptions!$E$20",
            12: f"={letter}9-{letter}11",
            13: "=Assumptions!$E$8",
            14: f"={letter}12-{letter}13",
        }
        for row, formula in formulas.items():
            ws.cell(row=row, column=col, value=formula)
            ws.cell(row=row, column=col).number_format = PCT if row in (6, 8, 10) else CUR
    for row in (9, 12, 14):
        total_row(ws, row, 2, 8, CUR)
    set_widths(ws, {"A": 4, "B": 40, **{get_column_letter(c): 13 for c in range(3, 9)}})
    ws.freeze_panes = "A5"

    # Debt service, borrowing, reserves --------------------------------------------------
    ws = wb["Debt Service"]
    title(ws, "B2:G2", "Debt Service, Borrowing & Reserves")
    header(ws, 4, 2, ["$mm", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"])
    labels = [
        "Beginning debt", "Scheduled principal", "Cash interest", "Total debt service",
        "FCF before debt service", "New borrowing / funding gap", "Ending debt",
        "Beginning reserves", "Ending reserves", "Pledged revenue", "Revenue-bond DSCR",
    ]
    for row, label in enumerate(labels, start=5):
        ws.cell(row=row, column=2, value=label)
    for row in (8, 11, 13, 15):
        ws.cell(row=row, column=2).font = Font(name="Arial", size=10, bold=True, color=DARK)
    for col in range(3, 8):
        letter, prev = get_column_letter(col), get_column_letter(col - 1)
        op_col = get_column_letter(col + 1)
        year_index = col - 2
        formulas = {
            5: "=Assumptions!E10" if col == 3 else f"={prev}11",
            6: f"=MIN({letter}5,Assumptions!$E$11)",
            7: f"={letter}5*Assumptions!$E$16",
            8: f"={letter}6+{letter}7",
            9: f"='Revenue & Expenditure'!{op_col}14",
            10: f"=MAX(0,{letter}8-{letter}9)",
            11: f"={letter}5-{letter}6+{letter}10",
            12: "=Assumptions!E9"  if col == 3 else f"={prev}13",
            13: f"=MAX(0,{letter}12+{letter}9-{letter}8+{letter}10)",
            14: f"=Assumptions!$E$12*(1+Assumptions!$E$14)^{year_index}",
            15: f"=IFERROR({letter}14/{letter}8,0)",
      }
        for row, formula in formulas.items():
            ws.cell(row=row, column=col, value=formula)
            ws.cell(row=row, column=col).number_format = MULT if row == 15 else CUR
            if row == 9:
                formula_cell(ws.cell(row=row, column=col), CUR, cross_sheet=True)
    for row in (8, 11, 13):
        total_row(ws, row, 2, 7, CUR)
    set_widths(ws, {"A": 4, "B": 42, **{get_column_letter(c): 13 for c in range(3, 8)}})
    ws.freeze_panes = "A5"

    # Coverage ----------------------------------------------------------------------------
    ws = wb["Coverage"]
    title(ws, "B2:G2", "Coverage, Liquidity & Debt Burden")
    header(ws, 4, 2, ["Metric", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"])
    labels = [
        "Debt / recurring revenue", "Maximum debt / revenue", "Debt burden headroom",
        "Revenue-bond DSCR", "Minimum DSCR", "DSCR headroom", "Days cash on hand",
        "Minimum days cash", "Liquidity headroom", "Pension burden / revenue", "Covenant status",
    ]
    for row, label in enumerate(labels, start=5):
        ws.cell(row=row, column=2, value=label)
    for row in (7, 10, 13, 15):
        ws.cell(row=row, column=2).font = Font(name="Arial", size=10, bold=True, color=DARK)
    for col in range(3, 8):
        letter = get_column_letter(col)
        op_col = get_column_letter(col + 1)
        formulas = {
            5: f"=IFERROR('Debt Service'!{letter}11/'Revenue & Expenditure'!{op_col}5,0)",
            6: "=Assumptions!E17",
            7: f"={letter}6-{letter}5",
            8: f"='Debt Service'!{letter}15",
            9: "=Assumptions!E18",
            10: f"={letter}8-{letter}9",
            11: f"=IFERROR('Debt Service'!{letter}13/('Revenue & Expenditure'!{op_col}7/365),0)",
            12: "=Assumptions!E19",
            13: f"={letter}11-{letter}12",
            14: f"=IFERROR('Revenue & Expenditure'!{op_col}11/'Revenue & Expenditure'!{op_col}5,0)",
            15: f'=IF(AND({letter}7>=0,{letter}10>=0,{letter}13>=0),"PASS","FAIL")',
        }
        for row, formula in formulas.items():
            ws.cell(row=row, column=col, value=formula)
            if row <= 10:
                ws.cell(row=row, column=col).number_format = MULT
            elif row <= 13:
                ws.cell(row=row, column=col).number_format = "0.0"
            elif row == 14:
                ws.cell(row=row, column=col).number_format = PCT
    add_status_rules(ws, "C15:G15")
    set_widths(ws, {"A": 4, "B": 42, **{get_column_letter(c): 13 for c in range(3, 8)}})
    ws.freeze_panes = "A5"

    # Scenario summary and sensitivity --------------------------------------------
    ws = wb["Scenarios"]
    title(ws, "B2:E2", "Scenario Summary")
    header(ws, 4, 2, ["Metric", "Base", "Downside", "Threshold / interpretation"])
    rows = [
        ("Operating surplus", "=Assumptions!C6-Assumptions!C7-Assumptions!C20", "=Assumptions!D6-Assumptions!D7-Assumptions!D20", "> 0", CUR),
        ("Debt / revenue", "=IFERROR(Assumptions!C10/Assumptions!C6,0)", "=IFERROR(Assumptions!D10/Assumptions!D6,0)", "<= maximum", MULT),
        ("Revenue-bond DSCR", "=IFERROR(Assumptions!C12/(Assumptions!C11+Assumptions!C10*Assumptions!C16),0)", "=IFERROR(Assumptions!D12/(Assumptions!D11+Assumptions!D10*Assumptions!D16),0)", ">= minimum", MULT),
        ("Days cash on hand", "=IFERROR(Assumptions!C9/(Assumptions!C7/365),0)", "=IFERROR(Assumptions!D9/(Assumptions!D7/365),0)", ">= minimum", "0.0"),
        ("Debt-stabilizing primary balance", "=IFERROR((Assumptions!C16-Assumptions!C21)/(1+Assumptions!C21)*(Assumptions!C10/Assumptions!C6),0)", "=IFERROR((Assumptions!D16-Assumptions!D21)/(1+Assumptions!D21)*(Assumptions!D10/Assumptions!D6),0)", "Lower is better", PCT),
        ("Overall status", '=IF(AND(C5>0,C6<=Assumptions!C17,C7>=Assumptions!C18,C8>=Assumptions!C19),"PASS","REVIEW")', '=IF(AND(D5>0,D6<=Assumptions!D17,D7>=Assumptions!D18,D8>=Assumptions!D19),"PASS","REVIEW")', "PASS / REVIEW", None),
    ]
    for row, (label, base, downside, threshold, fmt) in enumerate(rows, start=5):
        ws.cell(row=row, column=2, value=label)
        ws.cell(row=row, column=3, value=base)
        ws.cell(row=row, column=4, value=downside)
        ws.cell(row=row, column=5, value=threshold)
        if fmt:
            ws.cell(row=row, column=3).number_format = fmt
            ws.cell(row=row, column=4).number_format = fmt
    add_status_rules(ws, "C10:D10")
    set_widths(ws, {"A": 4, "B": 42, "C": 18, "D": 18, "E": 34})

    ws = wb["Sensitivity"]
    title(ws, "B2:G2", "Debt Ratio Sensitivity — One-Year Projection")
    header(ws, 4, 2, ["Primary balance / r-g differential", -0.02, 0.00, 0.02, 0.04, 0.06])
    for col in range(3, 8):
        ws.cell(row=4, column=col).number_format = PCT
    for row, primary in enumerate((-0.05, -0.025, 0.0, 0.025, 0.05), start=5):
        ws.cell(row=row, column=2, value=primary).number_format = PCT
        for col in range(3, 8):
            letter = get_column_letter(col)
            ws.cell(row=row, column=col, value=f"='Debt Sustainability'!$C$5*(1+{letter}$4)-$B{row}")
            ws.cell(row=row, column=col).number_format = MULT
    ws.conditional_formatting.add("C5:G9", ColorScaleRule(start_type="min", start_color="E2F0D9", mid_type="percentile", mid_value=50, mid_color="FFF2CC", end_type="max", end_color="FCE4D6"))
    set_widths(ws, {"A": 4, "B": 40, **{get_column_letter(c): 12 for c in range(3, 8)}})

    # Checks and sources -----------------------------------------------------------
    ws = wb["Checks"]
    title(ws, "B2:C2", "Model Checks")
    header(ws, 4, 2, ["Check", "Status"])
    checks = [
        ("Debt balance nonnegative", '=IF(MIN(\'Debt Service\'!C11:G11)>=0,"PASS","FAIL")'),
        ("Reserve balance nonnegative", '=IF(MIN(\'Debt Service\'!C13:G13)>=0,"PASS","FAIL")'),
        ("Coverage metrics finite", '=IF(AND(MAX(Coverage!C5:G14)<1000,MIN(Coverage!C5:G14)>-1000),"PASS","FAIL")'),
        ("No covenant failures", '=IF(COUNTIF(Coverage!C15:G15,"FAIL")=0,"PASS","REVIEW")'),
        ("Debt-dynamics identity bounded", '=IF(AND(\'Debt Sustainability\'!C12>=0,\'Debt Sustainability\'!C12<10),"PASS","REVIEW")'),
        ("Overall model status", '=IF(COUNTIF(C5:C9,"FAIL")+COUNTIF(C5:C9,"REVIEW")=0,"PASS","REVIEW")'),
    ]
    for row, (label, formula) in enumerate(checks, start=5):
        ws.cell(row=row, column=2, value=label)
        ws.cell(row=row, column=3, value=formula)
    add_status_rules(ws, "C5:C10")
    set_widths(ws, {"A": 4, "B": 46, "C": 18})

    ws = wb["Sources"]
    title(ws, "B2:E2", "Source Register")
    header(ws, 4, 2, ["Input / dataset", "Source URL", "As-of", "Notes"])
    sources = [
        ("Official statements / continuing disclosures", "https://emma.msrb.org/", "[period]", "Issuer financials, debt schedules, covenant disclosures"),
        ("Government accounting standards", "https://www.gasb.org/", "[date]", "Map reported figures consistently"),
        ("Economic and demographic data", "https://fred.stlouisfed.org/", "[period]", "Document series IDs and release dates"),
        ("Treasury benchmark rates", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "[date]", "Relative value and refinancing assumptions"),
        ("Sovereign DSA methodology", "https://www.imf.org/external/pubs/ft/dsa/", "[date]", "Debt-dynamics and stress-testing framework"),
    ]
    for row, values in enumerate(sources, start=5):
        for col, value in enumerate(values, start=2):
            ws.cell(row=row, column=col, value=value).font = Font(name="Arial", size=10, color=BLUE)
    set_widths(ws, {"A": 4, "B": 36, "C": 58, "D": 16, "E": 44})

    add_refresh_log(wb)
    finalize(wb, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("PUBLIC_FINANCE_template.xlsx"))
    args = parser.parse_args()
    build(args.output)
    print(f"saved {args.output}")
