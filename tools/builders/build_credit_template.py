"""
Builds CREDIT_template.xlsx — shared archetype for Private Credit (05) and
Debt Finance (06). Direct-lending / leveraged-loan mechanics: facility
assumptions, covenant headroom, a multi-year debt schedule, and lender yield
including OID. Distinct from the LBO archetype (03/04): this is the lender's
side of the table, not the sponsor's — no returns waterfall, covenants
instead of a cash sweep as the central object.
"""
import openpyxl
from template_helpers import *

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[BORROWER] — Private Credit / Debt Finance Model", [
    ("Borrower / issuer:", "[fill in]"),
    ("Facility type:", "[term loan B / unitranche / revolver / notes]"),
    ("Last refreshed:", "[date]"),
    ("Next covenant test date:", "[date]"),
    ("Refresh cadence:", "Weekly"),
])

# ---------------- ASSUMPTIONS ----------------
ws = wb.create_sheet("Assumptions")
set_col_widths(ws, [4, 32, 16, 40])
ws["B2"] = "Facility Assumptions"; ws["B2"].font = TITLE
ws["B4"] = "Facility"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
facility = [
    ("Facility size / committed amount ($)", 0, CUR),
    ("Amount drawn ($)", 0, CUR),
    ("Base rate (e.g. SOFR) %", 0.05, PCT2),
    ("Spread (%)", 0.045, PCT2),
    ("OID (price at issue, per 100)", 99.0, '0.00'),
    ("Maturity (yrs)", 7, NUM),
    ("Mandatory amortization (% of face / yr)", 0.01, PCT),
]
r = 5
for label, default, fmt in facility:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B13"] = "Borrower financials"; ws["B13"].font = BOLD; ws["B13"].fill = GRAY_FILL
financials = [
    ("EBITDA ($)", 0, CUR),
    ("Cash flow available for debt service (CFADS, $)", 0, CUR),
]
r = 14
for label, default, fmt in financials:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B18"] = "Derived"; ws["B18"].font = BOLD; ws["B18"].fill = GRAY_FILL
ws["B19"] = "All-in interest rate (base + spread)"
ws["C19"] = "=C7+C8"; ws["C19"].number_format = PCT2; ws["C19"].border = BORDER
ws["B20"] = "Annual interest expense ($)"
ws["C20"] = "=C6*C19"; ws["C20"].number_format = CUR; ws["C20"].border = BORDER
ws["B21"] = "Total debt ($, = drawn amount)"
ws["C21"] = "=C6"; ws["C21"].font = GREEN; ws["C21"].number_format = CUR; ws["C21"].border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- COVENANTS ----------------
ws = wb.create_sheet("Covenants")
set_col_widths(ws, [4, 34, 14, 14, 14, 40])
ws["B2"] = "Covenant Headroom"; ws["B2"].font = TITLE
for i, h in enumerate(["", "Covenant", "Threshold", "Actual", "Headroom", "Note"], start=1):
    ws.cell(row=4, column=i, value=h)
style_header_row(ws, 4, 5, start_col=2)

ws["B5"] = "Max leverage (Total Debt / EBITDA)"
ws["C5"] = 5.0; ws["C5"].font = BLUE; ws["C5"].fill = YELLOW_FILL; ws["C5"].number_format = MULT
ws["D5"] = "=IFERROR(Assumptions!C21/Assumptions!C14,\"-\")"; ws["D5"].font = GREEN; ws["D5"].number_format = MULT
ws["E5"] = "=IFERROR(C5-D5,\"-\")"; ws["E5"].number_format = MULT
ws["F5"] = "Lower actual is better — headroom = covenant minus actual"
ws["F5"].font = ITALIC_GRAY

ws["B6"] = "Min interest coverage (EBITDA / Interest)"
ws["C6"] = 2.5; ws["C6"].font = BLUE; ws["C6"].fill = YELLOW_FILL; ws["C6"].number_format = MULT
ws["D6"] = "=IFERROR(Assumptions!C14/Assumptions!C20,\"-\")"; ws["D6"].font = GREEN; ws["D6"].number_format = MULT
ws["E6"] = "=IFERROR(D6-C6,\"-\")"; ws["E6"].number_format = MULT
ws["F6"] = "Higher actual is better — headroom = actual minus covenant"
ws["F6"].font = ITALIC_GRAY

ws["B7"] = "Min DSCR (CFADS / Debt Service)"
ws["C7"] = 1.2; ws["C7"].font = BLUE; ws["C7"].fill = YELLOW_FILL; ws["C7"].number_format = MULT
ws["D7"] = ("=IFERROR(Assumptions!C15/(Assumptions!C6*Assumptions!C9+Assumptions!C20),\"-\")")
ws["D7"].font = GREEN; ws["D7"].number_format = MULT
ws["E7"] = "=IFERROR(D7-C7,\"-\")"; ws["E7"].number_format = MULT
ws["F7"] = "Debt service = mandatory amort + interest"
ws["F7"].font = ITALIC_GRAY

for row in (5, 6, 7):
    for c in range(3, 6):
        ws.cell(row=row, column=c).border = BORDER

ws["B9"] = "Status"; ws["B9"].font = BOLD; ws["B9"].fill = GRAY_FILL
ws["B10"] = "Leverage covenant"
ws["C10"] = '=IF(NOT(ISNUMBER(D5)),"-",IF(D5<=C5,"PASS","BREACH"))'; ws["C10"].font = BOLD
ws["B11"] = "Interest coverage covenant"
ws["C11"] = '=IF(NOT(ISNUMBER(D6)),"-",IF(D6>=C6,"PASS","BREACH"))'; ws["C11"].font = BOLD
ws["B12"] = "DSCR covenant"
ws["C12"] = '=IF(NOT(ISNUMBER(D7)),"-",IF(D7>=C7,"PASS","BREACH"))'; ws["C12"].font = BOLD
ws.sheet_view.showGridLines = False

# ---------------- DEBT SCHEDULE ----------------
ws = wb.create_sheet("Debt Schedule")
set_col_widths(ws, [4, 26, 12, 12, 12, 12, 12, 12])
ws["B2"] = "Debt Schedule"; ws["B2"].font = TITLE
for i, h in enumerate(["", "", "Yr0", "Yr1", "Yr2", "Yr3", "Yr4", "Yr5"], start=1):
    ws.cell(row=4, column=i, value=h)
style_header_row(ws, 4, 6, start_col=3)

ws["B5"] = "Beginning balance"; ws["B5"].font = BLACK
ws["C5"] = "=Assumptions!C6"; ws["C5"].font = GREEN; ws["C5"].number_format = CUR
for col in range(4, 9):
    letter = get_column_letter(col - 1)
    ws.cell(row=5, column=col, value=f"={letter}8").number_format = CUR

ws["B6"] = "Mandatory amortization"; ws["B6"].font = BLACK
for col in range(3, 9):
    ws.cell(row=6, column=col, value="=Assumptions!$C$6*Assumptions!$C$9").number_format = CUR

ws["B7"] = "Cash sweep (excess CFADS, if any)"; ws["B7"].font = BLACK
for col in range(3, 9):
    ws.cell(row=7, column=col, value=0).number_format = CUR

ws["B8"] = "Ending balance"; ws["B8"].font = BOLD
for col in range(3, 9):
    letter = get_column_letter(col)
    ws.cell(row=8, column=col, value=f"={letter}5-{letter}6-{letter}7").number_format = CUR

ws["B9"] = "Interest expense (all-in rate x avg balance)"; ws["B9"].font = BLACK
for col in range(3, 9):
    letter = get_column_letter(col)
    ws.cell(row=9, column=col,
            value=f"=AVERAGE({letter}5,{letter}8)*Assumptions!$C$19").number_format = CUR

ws["B11"] = "Leverage (ending debt / EBITDA)"; ws["B11"].font = BOLD
for col in range(3, 9):
    letter = get_column_letter(col)
    ws.cell(row=11, column=col,
            value=f'=IFERROR({letter}8/Assumptions!$C$14,"-")').number_format = MULT
    ws.cell(row=11, column=col).fill = YELLOW_FILL

for row in (5, 6, 7, 8, 9, 11):
    for c in range(3, 9):
        ws.cell(row=row, column=c).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- YIELD & SPREAD ----------------
ws = wb.create_sheet("Yield & Spread")
set_col_widths(ws, [4, 34, 16, 44])
ws["B2"] = "Lender Yield (incl. OID)"; ws["B2"].font = TITLE
ws["B4"] = "Coupon rate (base + spread, %)"
ws["C4"] = "=Assumptions!C19"; ws["C4"].font = GREEN; ws["C4"].number_format = PCT2
ws["B5"] = "Issue price (per 100)"
ws["C5"] = "=Assumptions!C9"; ws["C5"].font = GREEN; ws["C5"].number_format = '0.00'
ws["B6"] = "Maturity (yrs)"
ws["C6"] = "=Assumptions!C10"; ws["C6"].font = GREEN; ws["C6"].number_format = NUM
ws["B8"] = "Approx. yield-to-maturity"; ws["B8"].font = BOLD
ws["C8"] = "=IFERROR((C4*100+(100-C5)/C6)/((100+C5)/2),\"-\")"
ws["C8"].font = BOLD; ws["C8"].number_format = PCT2
ws["D8"] = "Standard bond-math approximation: (Coupon$+(100-Price)/n)/((100+Price)/2). At par (Price=100) this collapses to the coupon rate exactly — sanity check."
ws["D8"].font = ITALIC_GRAY
for r2 in (4, 5, 6, 8):
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

add_refresh_log(wb)
out_path = "CREDIT_template.xlsx"
wb.save(out_path)
print("saved", out_path)
