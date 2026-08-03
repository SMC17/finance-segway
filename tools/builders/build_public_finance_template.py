"""Build the public-finance credit archetype.

Usage:
    python tools/builders/build_public_finance_template.py --output PUBLIC_FINANCE_template.xlsx
"""
from __future__ import annotations

import argparse
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill

from template_helpers import (
    BLACK, BLUE, BOLD, BORDER, CUR, HEADER_FILL, MULT, PCT, TITLE,
    YELLOW_FILL, add_cover, add_refresh_log, set_col_widths,
    style_header_row,
)

RED_FILL = PatternFill("solid", fgColor="FCE4D6")
GREEN_FILL = PatternFill("solid", fgColor="E2F0D9")


def _status_rules(ws, cell_range: str) -> None:
    ws.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="equal", formula=['"PASS"'], fill=GREEN_FILL),
    )
    ws.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="equal", formula=['"FAIL"'], fill=RED_FILL),
    )
    ws.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="equal", formula=['"REVIEW"'], fill=YELLOW_FILL),
    )


def build(output: Path) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_cover(
        wb,
        "[ISSUER] — Public Finance Credit Model",
        [
            ("Model type:", "Municipal / sovereign / project revenue credit"),
            ("Issuer:", "[Name]"),
            ("Security / CUSIP:", "[Code]"),
            ("Last refreshed:", "[date]"),
            ("Next material date:", "[date]"),
            ("Refresh cadence:", "Weekly"),
            ("Units:", "$ in millions unless noted"),
        ],
    )

    ws = wb.create_sheet("Assumptions")
    set_col_widths(ws, [4, 38, 16, 16, 24])
    ws["B2"] = "Public Finance Assumptions"; ws["B2"].font = TITLE
    for c, value in enumerate(["Assumption", "Base", "Stress", "Units / source"], 2):
        ws.cell(4, c, value)
    style_header_row(ws, 4, 4, 2)
    assumptions = [
        ("Population / service base", 1_000_000, 950_000, "people / accounts"),
        ("Recurring revenue", 1_200.0, 1_080.0, "$mm"),
        ("Recurring expenditure", 1_050.0, 1_090.0, "$mm"),
        ("Capital expenditure", 180.0, 220.0, "$mm"),
        ("Cash & unrestricted reserves", 300.0, 220.0, "$mm"),
        ("Gross debt outstanding", 2_500.0, 2_500.0, "$mm"),
        ("Annual debt service", 210.0, 230.0, "$mm"),
        ("Pledged revenue", 420.0, 360.0, "$mm"),
        ("Intergovernmental transfers", 150.0, 120.0, "$mm"),
        ("Revenue growth", 0.03, -0.02, "%"),
        ("Expenditure growth", 0.035, 0.05, "%"),
        ("Interest rate on new debt", 0.045, 0.06, "%"),
        ("Maximum debt / revenue", 2.50, 2.50, "x"),
        ("Minimum DSCR", 1.50, 1.50, "x"),
        ("Minimum days cash", 90.0, 90.0, "days"),
        ("Pension / OPEB contribution", 90.0, 110.0, "$mm"),
    ]
    for r, row in enumerate(assumptions, 5):
        for c, value in enumerate(row, 2): ws.cell(r, c, value)
        for c in (3, 4):
            ws.cell(r, c).font = BLUE; ws.cell(r, c).fill = YELLOW_FILL; ws.cell(r, c).border = BORDER
    for r in (14, 15, 16):
        ws.cell(r, 3).number_format = PCT; ws.cell(r, 4).number_format = PCT
    for r in (17, 18):
        ws.cell(r, 3).number_format = MULT; ws.cell(r, 4).number_format = MULT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Revenue & Expenditure")
    set_col_widths(ws, [4, 36] + [13] * 6)
    ws["B2"] = "Operating Forecast"; ws["B2"].font = TITLE
    for c, value in enumerate(["$mm", "Current", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 7, 2)
    labels = ["Recurring revenue", "Revenue growth", "Recurring expenditure", "Expenditure growth",
              "Operating surplus", "Operating margin", "Pension / OPEB contribution",
              "Net operating result", "Capital expenditure", "Free cash flow before debt service"]
    for r, label in enumerate(labels, 5):
        ws.cell(r, 2, label).font = BOLD if label in {"Recurring revenue", "Operating surplus", "Net operating result", "Free cash flow before debt service"} else BLACK
    ws["C5"] = "=Assumptions!C6"; ws["C7"] = "=Assumptions!C7"; ws["C9"] = "=C5-C7"
    ws["C10"] = "=IFERROR(C9/C5,0)"; ws["C11"] = "=Assumptions!C20"; ws["C12"] = "=C9-C11"
    ws["C13"] = "=Assumptions!C8"; ws["C14"] = "=C12-C13"
    for c in range(4, 9):
        col = openpyxl.utils.get_column_letter(c); prev = openpyxl.utils.get_column_letter(c - 1)
        ws[f"{col}5"] = f"={prev}5*(1+Assumptions!C14)"
        ws[f"{col}6"] = f"=IFERROR({col}5/{prev}5-1,0)"
        ws[f"{col}7"] = f"={prev}7*(1+Assumptions!C15)"
        ws[f"{col}8"] = f"=IFERROR({col}7/{prev}7-1,0)"
        ws[f"{col}9"] = f"={col}5-{col}7"
        ws[f"{col}10"] = f"=IFERROR({col}9/{col}5,0)"
        ws[f"{col}11"] = "=Assumptions!C20"
        ws[f"{col}12"] = f"={col}9-{col}11"
        ws[f"{col}13"] = "=Assumptions!C8"
        ws[f"{col}14"] = f"={col}12-{col}13"
    for r in range(5, 15):
        for c in range(3, 9): ws.cell(r, c).number_format = CUR
    for c in range(3, 9):
        ws.cell(6, c).number_format = PCT; ws.cell(8, c).number_format = PCT; ws.cell(10, c).number_format = PCT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Debt Service")
    set_col_widths(ws, [4, 36] + [13] * 5)
    ws["B2"] = "Debt Service & Amortization"; ws["B2"].font = TITLE
    for c, value in enumerate(["$mm", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 6, 2)
    labels = ["Beginning debt", "Scheduled principal", "New borrowing", "Ending debt", "Cash interest",
              "Total debt service", "Pledged revenue", "Revenue-bond DSCR"]
    for r, label in enumerate(labels, 5): ws.cell(r, 2, label).font = BOLD if label in {"Ending debt", "Total debt service", "Revenue-bond DSCR"} else BLACK
    for c in range(3, 8):
        col = openpyxl.utils.get_column_letter(c); prev = openpyxl.utils.get_column_letter(c - 1)
        op_col = openpyxl.utils.get_column_letter(c + 1)
        ws[f"{col}5"] = "=Assumptions!C10" if c == 3 else f"={prev}8"
        ws[f"{col}6"] = f"=MIN({col}5,Assumptions!C11*30%)"
        ws[f"{col}7"] = f"=MAX(0,-'Revenue & Expenditure'!{op_col}14)"
        ws[f"{col}8"] = f"={col}5-{col}6+{col}7"
        ws[f"{col}9"] = f"=AVERAGE({col}5,{col}8)*Assumptions!C16"
        ws[f"{col}10"] = f"={col}6+{col}9"
        ws[f"{col}11"] = "=Assumptions!C12"
        ws[f"{col}12"] = f"=IFERROR({col}11/{col}10,0)"
        for r in range(5, 12): ws.cell(r, c).number_format = CUR
        ws[f"{col}12"].number_format = MULT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Coverage")
    set_col_widths(ws, [4, 40] + [13] * 5)
    ws["B2"] = "Coverage, Liquidity & Debt Burden"; ws["B2"].font = TITLE
    for c, value in enumerate(["Metric", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 6, 2)
    labels = ["Debt / recurring revenue", "Maximum debt / revenue", "Debt burden headroom",
              "Revenue-bond DSCR", "Minimum DSCR", "DSCR headroom", "Days cash on hand",
              "Minimum days cash", "Liquidity headroom", "Covenant status"]
    for r, label in enumerate(labels, 5):
        ws.cell(r, 2, label).font = BOLD if label in {"Debt burden headroom", "DSCR headroom", "Liquidity headroom", "Covenant status"} else BLACK
    for c in range(3, 8):
        col = openpyxl.utils.get_column_letter(c); op_col = openpyxl.utils.get_column_letter(c + 1)
        ws[f"{col}5"] = f"=IFERROR('Debt Service'!{col}8/'Revenue & Expenditure'!{op_col}5,0)"
        ws[f"{col}6"] = "=Assumptions!C17"; ws[f"{col}7"] = f"={col}6-{col}5"
        ws[f"{col}8"] = f"='Debt Service'!{col}12"; ws[f"{col}9"] = "=Assumptions!C18"; ws[f"{col}10"] = f"={col}8-{col}9"
        ws[f"{col}11"] = f"=IFERROR(Assumptions!C9/('Revenue & Expenditure'!{op_col}7/365),0)"
        ws[f"{col}12"] = "=Assumptions!C19"; ws[f"{col}13"] = f"={col}11-{col}12"
        ws[f"{col}14"] = f'=IF(AND({col}7>=0,{col}10>=0,{col}13>=0),"PASS","FAIL")'
        for r in range(5, 11): ws.cell(r, c).number_format = MULT
        for r in range(11, 14): ws.cell(r, c).number_format = "0.0"
    _status_rules(ws, "C14:G14")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Scenarios")
    set_col_widths(ws, [4, 36, 16, 16, 18])
    ws["B2"] = "Scenario Summary"; ws["B2"].font = TITLE
    for c, value in enumerate(["Metric", "Current / Base", "Stress", "Threshold"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 4, 2)
    rows = [
        ("Operating surplus", "='Revenue & Expenditure'!H9", "=Assumptions!D6-Assumptions!D7", "> 0"),
        ("Debt / revenue", "=Coverage!G5", "=Assumptions!D10/Assumptions!D6", "<= max"),
        ("Revenue-bond DSCR", "=Coverage!G8", "=Assumptions!D12/Assumptions!D11", ">= min"),
        ("Days cash on hand", "=Coverage!G11", "=Assumptions!D9/(Assumptions!D7/365)", ">= min"),
        ("Overall status", '=IF(AND(C5>0,C6<=Assumptions!C17,C7>=Assumptions!C18,C8>=Assumptions!C19),"PASS","REVIEW")', '=IF(AND(D5>0,D6<=Assumptions!D17,D7>=Assumptions!D18,D8>=Assumptions!D19),"PASS","REVIEW")', "Review"),
    ]
    for r, (label, base, stress, threshold) in enumerate(rows, 5):
        ws.cell(r, 2, label); ws.cell(r, 3, base); ws.cell(r, 4, stress); ws.cell(r, 5, threshold)
    ws["C5"].number_format = CUR; ws["D5"].number_format = CUR
    for cell in ("C6", "D6", "C7", "D7"): ws[cell].number_format = MULT
    for cell in ("C8", "D8"): ws[cell].number_format = "0.0"
    _status_rules(ws, "C9:D9")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Checks")
    set_col_widths(ws, [4, 42, 18])
    ws["B2"] = "Model Checks"; ws["B2"].font = TITLE
    ws["B4"] = "Check"; ws["C4"] = "Status"; style_header_row(ws, 4, 2, 2)
    checks = [
        ("Debt balance nonnegative", '=IF(MIN(\'Debt Service\'!C8:G8)>=0,"PASS","FAIL")'),
        ("Debt service positive", '=IF(MIN(\'Debt Service\'!C10:G10)>0,"PASS","REVIEW")'),
        ("Coverage metrics finite", '=IF(AND(MAX(Coverage!C5:G13)<1000,MIN(Coverage!C5:G13)>-1000),"PASS","FAIL")'),
        ("No covenant failures", '=IF(COUNTIF(Coverage!C14:G14,"FAIL")=0,"PASS","REVIEW")'),
        ("Overall model status", '=IF(COUNTIF(C5:C8,"FAIL")+COUNTIF(C5:C8,"REVIEW")=0,"PASS","REVIEW")'),
    ]
    for r, (label, formula) in enumerate(checks, 5): ws.cell(r, 2, label); ws.cell(r, 3, formula)
    _status_rules(ws, "C5:C9")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Sources")
    set_col_widths(ws, [4, 30, 50, 18, 34])
    ws["B2"] = "Source Register"; ws["B2"].font = TITLE
    for c, value in enumerate(["Input / dataset", "Source URL", "As-of", "Notes"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 4, 2)
    sources = [
        ("Issuer financial statements / ACFR", "https://emma.msrb.org/", "[period]", "Official statements and continuing disclosures"),
        ("Economic and demographic data", "https://fred.stlouisfed.org/", "[period]", "Document series IDs and release dates"),
        ("Government accounting standards", "https://www.gasb.org/", "[date]", "Map reported figures consistently"),
        ("Treasury benchmark rates", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "[date]", "Relative value and refinancing assumptions"),
    ]
    for r, row in enumerate(sources, 5):
        for c, value in enumerate(row, 2): ws.cell(r, c, value).font = BLUE
    ws.sheet_view.showGridLines = False

    add_refresh_log(wb)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("PUBLIC_FINANCE_template.xlsx"))
    args = parser.parse_args()
    build(args.output)
    print(f"saved {args.output}")
