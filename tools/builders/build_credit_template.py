"""Build the shared private-credit / debt-finance underwriting archetype.

Usage:
    python tools/builders/build_credit_template.py --output CREDIT_template.xlsx
"""
from __future__ import annotations

import argparse
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill

from template_helpers import (
    BLACK, BLUE, BOLD, BORDER, CUR, GRAY_FILL, GREEN, HEADER_FILL,
    MULT, PCT, TITLE, YELLOW_FILL, add_cover, add_refresh_log,
    set_col_widths, style_header_row,
)

RED_FILL = PatternFill("solid", fgColor="FCE4D6")
GREEN_FILL = PatternFill("solid", fgColor="E2F0D9")


def _section(ws, row: int, title: str, end_col: str = "H") -> None:
    ws.merge_cells(f"B{row}:{end_col}{row}")
    cell = ws[f"B{row}"]
    cell.value = title
    cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="left")


def _status_rules(ws, cell_range: str) -> None:
    ws.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="equal", formula=['"PASS"'], fill=GREEN_FILL),
    )
    ws.conditional_formatting.add(
        cell_range,
        CellIsRule(operator="equal", formula=['"FAIL"'], fill=RED_FILL),
    )


def build(output: Path) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    add_cover(
        wb,
        "[BORROWER] — Credit Underwriting Model",
        [
            ("Model type:", "Private credit / debt finance"),
            ("Borrower:", "[Name]"),
            ("Deal code:", "[Code]"),
            ("Last refreshed:", "[date]"),
            ("Next material date:", "[date]"),
            ("Refresh cadence:", "Weekly"),
            ("Units:", "$ in millions unless noted"),
        ],
    )

    ws = wb.create_sheet("Assumptions")
    set_col_widths(ws, [4, 34, 16, 16, 22])
    ws["B2"] = "Underwriting Assumptions"; ws["B2"].font = TITLE
    ws.append([None, "Assumption", "Base case", "Downside", "Units / source"])
    style_header_row(ws, 3, 4, 2)
    assumptions = [
        ("Revenue (LTM)", 500.0, 500.0, "$mm"),
        ("EBITDA margin", 0.20, 0.16, "%"),
        ("Revenue growth", 0.04, -0.05, "%"),
        ("Maintenance capex / revenue", 0.03, 0.035, "%"),
        ("Cash taxes / EBT", 0.24, 0.20, "%"),
        ("Change in NWC / revenue growth", 0.08, 0.10, "%"),
        ("Opening cash", 25.0, 20.0, "$mm"),
        ("Opening gross debt", 350.0, 350.0, "$mm"),
        ("SOFR / base rate", 0.045, 0.055, "%"),
        ("Cash spread", 0.055, 0.070, "%"),
        ("OID / upfront fee", 0.02, 0.02, "%"),
        ("PIK spread", 0.00, 0.02, "%"),
        ("Mandatory amortization", 0.01, 0.00, "% of opening"),
        ("Cash sweep", 0.50, 0.25, "% of excess cash"),
        ("Minimum cash", 15.0, 20.0, "$mm"),
        ("Maximum leverage covenant", 6.00, 5.50, "x"),
        ("Minimum interest coverage covenant", 1.75, 1.50, "x"),
        ("Recovery multiple on EBITDA", 5.0, 4.0, "x"),
        ("Enterprise value haircut", 0.20, 0.35, "%"),
    ]
    for r, row in enumerate(assumptions, 4):
        for c, value in enumerate(row, 2):
            ws.cell(r, c, value)
        for c in (3, 4):
            ws.cell(r, c).font = BLUE
            ws.cell(r, c).fill = YELLOW_FILL
            ws.cell(r, c).border = BORDER
    for r in list(range(5, 10)) + list(range(12, 18)) + [22]:
        ws.cell(r, 3).number_format = PCT; ws.cell(r, 4).number_format = PCT
    for r in (19, 20, 21):
        ws.cell(r, 3).number_format = MULT; ws.cell(r, 4).number_format = MULT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Operating Case")
    set_col_widths(ws, [4, 34] + [13] * 6)
    ws["B2"] = "Operating Case & CFADS"; ws["B2"].font = TITLE
    for c, value in enumerate(["$mm", "LTM", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2):
        ws.cell(4, c, value)
    style_header_row(ws, 4, 7, 2)
    labels = ["Revenue", "Growth", "EBITDA", "EBITDA margin", "Less: cash interest",
              "Less: cash taxes", "Less: maintenance capex", "Less: change in NWC",
              "Cash flow available for debt service", "Cash sweep available"]
    for r, label in enumerate(labels, 5):
        ws.cell(r, 2, label).font = BOLD if label in {"Revenue", "EBITDA", "Cash flow available for debt service", "Cash sweep available"} else BLACK
    ws["C5"] = "=Assumptions!C4"; ws["C7"] = "=C5*Assumptions!C5"; ws["C8"] = "=IFERROR(C7/C5,0)"
    for c in range(4, 9):
        col = openpyxl.utils.get_column_letter(c); prev = openpyxl.utils.get_column_letter(c - 1)
        ws[f"{col}5"] = f"={prev}5*(1+Assumptions!C6)"
        ws[f"{col}6"] = f"=IFERROR({col}5/{prev}5-1,0)"
        ws[f"{col}7"] = f"={col}5*Assumptions!C5"
        ws[f"{col}8"] = f"=IFERROR({col}7/{col}5,0)"
        ws[f"{col}9"] = f"='Debt Schedule'!{col}12"
        ws[f"{col}10"] = f"=MAX(0,({col}7-{col}9)*Assumptions!C8)"
        ws[f"{col}11"] = f"={col}5*Assumptions!C7"
        ws[f"{col}12"] = f"=MAX(0,({col}5-{prev}5)*Assumptions!C9)"
        ws[f"{col}13"] = f"={col}7-{col}9-{col}10-{col}11-{col}12"
        ws[f"{col}14"] = f"=MAX(0,{col}13-Assumptions!C18)"
    for row in range(5, 15):
        for c in range(3, 9): ws.cell(row, c).number_format = CUR
    for c in range(3, 9):
        ws.cell(6, c).number_format = PCT; ws.cell(8, c).number_format = PCT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Debt Schedule")
    set_col_widths(ws, [4, 36] + [13] * 6)
    ws["B2"] = "Debt Schedule"; ws["B2"].font = TITLE
    for c, value in enumerate(["$mm", "Close", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 7, 2)
    labels = ["Beginning debt", "Mandatory amortization", "Cash sweep", "PIK accrual", "Ending debt",
              "Average debt", "Cash interest rate", "Cash interest expense", "PIK interest expense", "Total interest expense"]
    for r, label in enumerate(labels, 5): ws.cell(r, 2, label).font = BOLD if label in {"Ending debt", "Total interest expense"} else BLACK
    ws["C5"] = "=Assumptions!C11"; ws["C9"] = "=C5"; ws["C10"] = "=C5"; ws["C11"] = "=Assumptions!C12+Assumptions!C13"
    for c in range(4, 9):
        col = openpyxl.utils.get_column_letter(c); prev = openpyxl.utils.get_column_letter(c - 1)
        ws[f"{col}5"] = f"={prev}9"
        ws[f"{col}6"] = f"=MIN({col}5,Assumptions!C11*Assumptions!C16)"
        ws[f"{col}7"] = f"=MIN(MAX(0,{col}5-{col}6),'Operating Case'!{col}14*Assumptions!C17)"
        ws[f"{col}8"] = f"=MAX(0,{col}5-{col}6-{col}7)*Assumptions!C15"
        ws[f"{col}9"] = f"=MAX(0,{col}5-{col}6-{col}7+{col}8)"
        ws[f"{col}10"] = f"=AVERAGE({col}5,{col}9)"
        ws[f"{col}11"] = "=Assumptions!C12+Assumptions!C13"
        ws[f"{col}12"] = f"={col}5*{col}11"
        ws[f"{col}13"] = f"={col}5*Assumptions!C15"
        ws[f"{col}14"] = f"={col}12+{col}13"
    for row in range(5, 15):
        for c in range(3, 9): ws.cell(row, c).number_format = CUR
    for c in range(3, 9): ws.cell(11, c).number_format = PCT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Covenants")
    set_col_widths(ws, [4, 36] + [13] * 5)
    ws["B2"] = "Covenant Compliance"; ws["B2"].font = TITLE
    for c, value in enumerate(["Metric", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 6, 2)
    labels = ["Gross leverage", "Maximum leverage covenant", "Leverage headroom", "Interest coverage",
              "Minimum coverage covenant", "Coverage headroom", "Debt service coverage ratio", "Minimum DSCR", "Covenant status"]
    for r, label in enumerate(labels, 5): ws.cell(r, 2, label).font = BOLD if label in {"Leverage headroom", "Coverage headroom", "Covenant status"} else BLACK
    for c in range(3, 8):
        col = openpyxl.utils.get_column_letter(c); dcol = openpyxl.utils.get_column_letter(c + 1)
        ws[f"{col}5"] = f"=IFERROR('Debt Schedule'!{dcol}9/'Operating Case'!{dcol}7,0)"
        ws[f"{col}6"] = "=Assumptions!C19"
        ws[f"{col}7"] = f"={col}6-{col}5"
        ws[f"{col}8"] = f"=IFERROR('Operating Case'!{dcol}7/'Debt Schedule'!{dcol}14,0)"
        ws[f"{col}9"] = "=Assumptions!C20"
        ws[f"{col}10"] = f"={col}8-{col}9"
        ws[f"{col}11"] = f"=IFERROR('Operating Case'!{dcol}13/('Debt Schedule'!{dcol}6+'Debt Schedule'!{dcol}12),0)"
        ws[f"{col}12"] = 1.0
        ws[f"{col}13"] = f'=IF(AND({col}7>=0,{col}10>=0,{col}11>={col}12),"PASS","FAIL")'
        for r in range(5, 13): ws.cell(r, c).number_format = MULT
    _status_rules(ws, "C13:G13")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Recovery")
    set_col_widths(ws, [4, 38, 16, 16])
    ws["B2"] = "Recovery & Loss Analysis"; ws["B2"].font = TITLE
    for c, value in enumerate(["Recovery bridge", "Base", "Downside"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 3, 2)
    rows = [
        ("Stressed EBITDA", "='Operating Case'!H7", "='Operating Case'!H7*0.8"),
        ("Recovery multiple", "=Assumptions!C21", "=Assumptions!D21"),
        ("Gross enterprise value", "=C5*C6", "=D5*D6"),
        ("Less: EV haircut", "=C7*Assumptions!C22", "=D7*Assumptions!D22"),
        ("Net distributable value", "=C7-C8", "=D7-D8"),
        ("Debt claim", "='Debt Schedule'!H9", "='Debt Schedule'!H9"),
        ("Recovery value", "=MIN(C9,C10)", "=MIN(D9,D10)"),
        ("Recovery rate", "=IFERROR(C11/C10,0)", "=IFERROR(D11/D10,0)"),
        ("Loss given default", "=1-C12", "=1-D12"),
    ]
    for r, (label, base, downside) in enumerate(rows, 5):
        ws.cell(r, 2, label); ws.cell(r, 3, base); ws.cell(r, 4, downside)
        ws.cell(r, 3).number_format = PCT if r >= 12 else (MULT if r == 6 else CUR)
        ws.cell(r, 4).number_format = ws.cell(r, 3).number_format
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Sensitivity")
    set_col_widths(ws, [4, 28] + [12] * 5)
    ws["B2"] = "Recovery Sensitivity"; ws["B2"].font = TITLE
    for c, value in enumerate(["EBITDA haircut / recovery multiple", 3.0, 4.0, 5.0, 6.0, 7.0], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 6, 2)
    for r, haircut in enumerate([0.0, 0.1, 0.2, 0.3, 0.4], 5):
        ws.cell(r, 2, haircut).number_format = PCT
        for c in range(3, 8):
            col = openpyxl.utils.get_column_letter(c)
            ws.cell(r, c, f"=IFERROR(MIN(1,MAX(0,('Operating Case'!$H$7*(1-$B{r})*{col}$4)/'Debt Schedule'!$H$9)),1)")
            ws.cell(r, c).number_format = PCT
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Checks")
    set_col_widths(ws, [4, 42, 18])
    ws["B2"] = "Model Checks"; ws["B2"].font = TITLE
    ws["B4"] = "Check"; ws["C4"] = "Status"; style_header_row(ws, 4, 2, 2)
    checks = [
        ("Debt never below zero", '=IF(MIN(\'Debt Schedule\'!D9:H9)>=0,"PASS","FAIL")'),
        ("CFADS nonnegative", '=IF(MIN(\'Operating Case\'!D13:H13)>=0,"PASS","FAIL")'),
        ("Recovery rate bounded", '=IF(AND(MIN(Recovery!C12:D12)>=0,MAX(Recovery!C12:D12)<=1),"PASS","FAIL")'),
        ("No covenant failures", '=IF(COUNTIF(Covenants!C13:G13,"FAIL")=0,"PASS","REVIEW")'),
        ("Overall model status", '=IF(COUNTIF(C5:C8,"FAIL")+COUNTIF(C5:C8,"REVIEW")=0,"PASS","REVIEW")'),
    ]
    for r, (label, formula) in enumerate(checks, 5): ws.cell(r, 2, label); ws.cell(r, 3, formula)
    _status_rules(ws, "C5:C9")
    ws.sheet_view.showGridLines = False

    ws = wb.create_sheet("Sources")
    set_col_widths(ws, [4, 28, 50, 18, 34])
    ws["B2"] = "Source Register"; ws["B2"].font = TITLE
    for c, value in enumerate(["Input / dataset", "Source URL", "As-of", "Notes"], 2): ws.cell(4, c, value)
    style_header_row(ws, 4, 4, 2)
    sources = [
        ("Financial statements / filings", "https://www.sec.gov/edgar/sec-api-documentation", "[period]", "Reconcile to audited statements"),
        ("Base rates / Treasury yields", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", "[date]", "Document selected reference rate"),
        ("Loan documentation", "[data room or public filing URL]", "[date]", "Covenants, baskets, amortization, collateral"),
        ("Recovery methodology", "https://www.ivsc.org/standards/", "[date]", "Document EV and recovery bridge"),
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
    parser.add_argument("--output", type=Path, default=Path("CREDIT_template.xlsx"))
    args = parser.parse_args()
    build(args.output)
    print(f"saved {args.output}")
