import openpyxl
from template_helpers import *

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[PROPERTY/REIT] — Real Estate Model", [
    ("Property type:", "Office / Multifamily / Industrial / Retail"),
    ("Location:", "[fill in]"),
    ("Last refreshed:", "[date]"),
    ("Refresh cadence:", "Weekly"),
])

# ---------------- PROPERTY PRO FORMA ----------------
ws = wb.create_sheet("Property Pro Forma")
set_col_widths(ws, [4, 30, 14, 14, 14])
ws["B2"] = "Property Pro Forma (annual, $)"; ws["B2"].font = TITLE
rows = ["Gross potential rent", "- Vacancy & credit loss", "Effective gross income",
        "+ Other income (parking, fees)", "Total revenue",
        "- Operating expenses (taxes, insurance, mgmt, R&M)", "Net Operating Income (NOI)",
        "- Capex reserve", "- Debt service (P&I)", "Cash flow before tax"]
r = 5
for label in rows:
    is_bold = label in ("Net Operating Income (NOI)", "Cash flow before tax", "Total revenue")
    ws.cell(row=r, column=2, value=label).font = BOLD if is_bold else BLACK
    c = ws.cell(row=r, column=3, value=0)
    c.font = BLUE; c.number_format = CUR; c.border = BORDER
    r += 1
# wire formulas: EGI = gross - vacancy; total rev = EGI + other; NOI = total rev - opex; CF = NOI - capex - debt service
ws["C7"] = "=C5+C6"; ws["C7"].font = BLACK  # effective gross income
ws["C9"] = "=C7+C8"; ws["C9"].font = BOLD  # total revenue
ws["C11"] = "=C9+C10"; ws["C11"].font = BOLD  # NOI (opex entered negative)
ws["C14"] = "=C11+C12+C13"; ws["C14"].font = BOLD  # CF before tax
ws.sheet_view.showGridLines = False

# ---------------- CAP RATE & VALUATION ----------------
ws = wb.create_sheet("Cap Rate & Valuation")
set_col_widths(ws, [4, 30, 16, 40])
ws["B2"] = "Cap Rate Valuation"; ws["B2"].font = TITLE
ws["B4"] = "NOI (from pro forma)"; ws["C4"] = "='Property Pro Forma'!C11"; ws["C4"].font = GREEN; ws["C4"].number_format = CUR
ws["B5"] = "Market cap rate %"; ws["C5"] = 0.06; ws["C5"].font = BLUE; ws["C5"].fill = YELLOW_FILL; ws["C5"].number_format = PCT
ws["B6"] = "Implied value (NOI / cap rate)"; ws["C6"] = "=IFERROR(C4/C5,\"-\")"; ws["C6"].font = BOLD; ws["C6"].number_format = CUR
ws["B8"] = "Purchase price ($)"; ws["C8"] = 0; ws["C8"].font = BLUE; ws["C8"].number_format = CUR
ws["B9"] = "Going-in cap rate (NOI / price)"; ws["C9"] = "=IFERROR(C4/C8,\"-\")"; ws["C9"].number_format = PCT
ws["B10"] = "Debt amount"; ws["C10"] = 0; ws["C10"].font = BLUE; ws["C10"].number_format = CUR
ws["B11"] = "Cash-on-cash return"; ws["C11"] = "=IFERROR('Property Pro Forma'!C14/(C8-C10),\"-\")"; ws["C11"].number_format = PCT
for r2 in [4,5,6,8,9,10,11]:
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- REIT FFO/AFFO ----------------
ws = wb.create_sheet("REIT FFO-AFFO")
set_col_widths(ws, [4, 34, 16, 40])
ws["B2"] = "REIT FFO / AFFO"; ws["B2"].font = TITLE
ws["B4"] = "Net income (GAAP)"; ws["C4"] = 0; ws["C4"].font = BLUE; ws["C4"].number_format = CUR
ws["B5"] = "+ Real estate depreciation & amortization"; ws["C5"] = 0; ws["C5"].font = BLUE; ws["C5"].number_format = CUR
ws["B6"] = "- Gains on property sales"; ws["C6"] = 0; ws["C6"].font = BLUE; ws["C6"].number_format = CUR
ws["B7"] = "FFO (Funds From Operations)"; ws["C7"] = "=C4+C5+C6"; ws["C7"].font = BOLD; ws["C7"].number_format = CUR
ws["B9"] = "- Recurring capex / leasing costs"; ws["C9"] = 0; ws["C9"].font = BLUE; ws["C9"].number_format = CUR
ws["B10"] = "- Straight-line rent adjustment"; ws["C10"] = 0; ws["C10"].font = BLUE; ws["C10"].number_format = CUR
ws["B11"] = "AFFO (Adjusted FFO)"; ws["C11"] = "=C7+C9+C10"; ws["C11"].font = BOLD; ws["C11"].number_format = CUR
ws["D11"] = "AFFO is the better proxy for sustainable dividend-paying capacity"
ws["D11"].font = ITALIC_GRAY
ws["B13"] = "Shares/units outstanding"; ws["C13"] = 1; ws["C13"].font = BLUE; ws["C13"].number_format = NUM
ws["B14"] = "FFO / share"; ws["C14"] = "=IFERROR(C7/C13,\"-\")"; ws["C14"].number_format = CUR2
ws["B15"] = "AFFO / share"; ws["C15"] = "=IFERROR(C11/C13,\"-\")"; ws["C15"].number_format = CUR2
for r2 in [4,5,6,7,9,10,11,13,14,15]:
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

add_refresh_log(wb)
out_path = "/home/claude/model_shop/REAL_ESTATE_template.xlsx"
wb.save(out_path)
print("saved", out_path)
