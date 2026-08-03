"""
Builds PUBLIC_FINANCE_template.xlsx — sovereign/municipal archetype (07).

Two independent lenses, since "public finance" spans two different
questions: is the issuer's overall debt load sustainable (debt sustainability
analysis, IMF/DSA-style), and can this specific revenue-backed bond cover its
own debt service (revenue bond coverage, muni-market-style). Both get their
own tab; neither depends on the other.
"""
import openpyxl
from template_helpers import *

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[ISSUER] — Public Finance Model", [
    ("Issuer:", "[fill in — sovereign, state, muni, agency]"),
    ("Instrument:", "[general obligation / revenue bond / sovereign note]"),
    ("Last refreshed:", "[date]"),
    ("Next payment / issuance date:", "[date]"),
    ("Refresh cadence:", "Weekly"),
])

# ---------------- DEBT SUSTAINABILITY ----------------
ws = wb.create_sheet("Debt Sustainability")
set_col_widths(ws, [4, 40, 14, 46])
ws["B2"] = "Debt Sustainability Analysis (DSA)"; ws["B2"].font = TITLE
ws["B4"] = "Inputs"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
inputs = [
    ("Total public debt / GDP (or Debt/Revenue) ratio (%)", 0.60, PCT),
    ("Effective interest rate on debt, r (%)", 0.05, PCT2),
    ("Nominal GDP (or revenue base) growth rate, g (%)", 0.02, PCT2),
    ("Current primary balance (% of GDP; surplus positive)", 0.00, PCT2),
]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B10"] = "Outputs"; ws["B10"].font = BOLD; ws["B10"].fill = GRAY_FILL
ws["B11"] = "Debt-stabilizing primary balance, pb* = (r-g)/(1+g) x debt ratio"
ws["C11"] = "=IFERROR((C6-C7)/(1+C7)*C5,\"-\")"
ws["C11"].font = BOLD; ws["C11"].number_format = PCT2; ws["C11"].border = BORDER
ws["D11"] = "Standard IMF/DSA formula. If r>g, debt ratio is explosive unless the primary balance is at least this large."
ws["D11"].font = ITALIC_GRAY

ws["B12"] = "Primary balance gap (current minus required)"
ws["C12"] = "=IFERROR(C8-C11,\"-\")"; ws["C12"].number_format = PCT2; ws["C12"].border = BORDER
ws["D12"] = "Negative = running a bigger deficit than needed to stabilize the debt ratio; ratio will rise."
ws["D12"].font = ITALIC_GRAY

ws["B13"] = "Debt trajectory"
ws["C13"] = '=IFERROR(IF(C8>=C11,"STABILIZING/FALLING","RISING"),"-")'; ws["C13"].font = BOLD
ws["D13"] = "Rule of thumb only — ignores stock-flow adjustments, FX-denominated debt, contingent liabilities."
ws["D13"].font = ITALIC_GRAY
ws.sheet_view.showGridLines = False

# ---------------- REVENUE BOND COVERAGE ----------------
ws = wb.create_sheet("Revenue Bond Coverage")
set_col_widths(ws, [4, 40, 14, 46])
ws["B2"] = "Revenue Bond Coverage"; ws["B2"].font = TITLE
ws["B4"] = "Inputs"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
inputs2 = [
    ("Gross pledged revenue ($)", 0, CUR),
    ("Operating & maintenance expense ($)", 0, CUR),
    ("Senior debt service — P&I ($)", 0, CUR),
    ("Subordinate debt service — P&I ($)", 0, CUR),
]
r = 5
for label, default, fmt in inputs2:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B10"] = "Outputs"; ws["B10"].font = BOLD; ws["B10"].fill = GRAY_FILL
ws["B11"] = "Net revenue available for debt service"
ws["C11"] = "=IFERROR(C5-C6,\"-\")"; ws["C11"].number_format = CUR; ws["C11"].border = BORDER
ws["B12"] = "Senior DSCR (Net revenue / Senior debt service)"
ws["C12"] = "=IFERROR(C11/C7,\"-\")"; ws["C12"].font = BOLD; ws["C12"].number_format = MULT
ws["C12"].border = BORDER
ws["B13"] = "All-in DSCR (Net revenue / Total debt service)"
ws["C13"] = "=IFERROR(C11/(C7+C8),\"-\")"; ws["C13"].font = BOLD; ws["C13"].number_format = MULT
ws["C13"].border = BORDER

ws["B15"] = "Additional Bonds Test"; ws["B15"].font = BOLD; ws["B15"].fill = GRAY_FILL
ws["B16"] = "ABT minimum senior DSCR covenant"
c = ws.cell(row=16, column=3, value=1.25); c.font = BLUE; c.fill = YELLOW_FILL; c.number_format = MULT
c.border = BORDER
ws["B17"] = "Headroom (actual minus covenant)"
ws["C17"] = "=IFERROR(C12-C16,\"-\")"; ws["C17"].number_format = MULT; ws["C17"].border = BORDER
ws["B18"] = "Passes ABT?"
ws["C18"] = '=IF(NOT(ISNUMBER(C12)),"-",IF(C12>=C16,"PASS — can issue additional parity debt","FAIL"))'
ws["C18"].font = BOLD
ws.sheet_view.showGridLines = False

add_refresh_log(wb)
out_path = "PUBLIC_FINANCE_template.xlsx"
wb.save(out_path)
print("saved", out_path)
