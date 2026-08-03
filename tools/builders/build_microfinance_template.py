import openpyxl
from template_helpers import *

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[MFI] — Microfinance Model", [
    ("Institution:", "[fill in]"),
    ("Region:", "[fill in]"),
    ("Last refreshed:", "[date]"),
    ("Refresh cadence:", "Weekly"),
])

# ---------------- LOAN PORTFOLIO ----------------
ws = wb.create_sheet("Loan Portfolio")
set_col_widths(ws, [4, 30, 16, 40])
ws["B2"] = "Loan Portfolio Overview"; ws["B2"].font = TITLE
inputs = [
    ("Gross loan portfolio (GLP, $)", 0, CUR),
    ("Number of active borrowers", 0, NUM),
    ("Portfolio at risk >30 days ($)", 0, CUR),
    ("Portfolio at risk >90 days ($)", 0, CUR),
    ("Write-offs this period ($)", 0, CUR),
    ("Average loan balance ($)", 0, CUR),
]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B12"] = "Portfolio Quality"; ws["B12"].font = BOLD; ws["B12"].fill = GRAY_FILL
ws["B13"] = "PAR 30 %"; ws["C13"] = "=IFERROR(C7/C5,\"-\")"; ws["C13"].number_format = PCT
ws["B14"] = "PAR 90 %"; ws["C14"] = "=IFERROR(C8/C5,\"-\")"; ws["C14"].number_format = PCT
ws["B15"] = "Write-off ratio (annualized)"; ws["C15"] = "=IFERROR(C9/C5,\"-\")"; ws["C15"].number_format = PCT
ws["B16"] = "Avg loan / borrower check"; ws["C16"] = "=IFERROR(C5/C6,\"-\")"; ws["C16"].number_format = CUR
for r2 in range(13, 17):
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- SUSTAINABILITY RATIOS ----------------
ws = wb.create_sheet("Sustainability")
set_col_widths(ws, [4, 34, 16, 40])
ws["B2"] = "Operational & Financial Self-Sufficiency (OSS/FSS)"; ws["B2"].font = TITLE
ws["B4"] = "Inputs"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
inputs = [
    ("Financial revenue (interest + fees, $)", 0, CUR),
    ("Financial expense (cost of funds, $)", 0, CUR),
    ("Loan loss provision expense ($)", 0, CUR),
    ("Operating expense ($)", 0, CUR),
    ("Cost of capital at market rate (imputed, $)", 0, CUR),
]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["B11"] = "Outputs"; ws["B11"].font = BOLD; ws["B11"].fill = GRAY_FILL
ws["B12"] = "Operational Self-Sufficiency (OSS) = Rev / (Fin exp + Loss prov + Opex)"
ws["C12"] = "=IFERROR(C5/(C6+C7+C8),\"-\")"; ws["C12"].font = BOLD; ws["C12"].number_format = PCT
ws["D12"] = ">100% = covering costs from operations, not subsidy-dependent"
ws["D12"].font = ITALIC_GRAY
ws["B13"] = "Financial Self-Sufficiency (FSS) = Rev / (Fin exp + Loss prov + Opex + imputed cost of capital)"
ws["C13"] = "=IFERROR(C5/(C6+C7+C8+C9),\"-\")"; ws["C13"].font = BOLD; ws["C13"].number_format = PCT
ws["D13"] = "Stricter than OSS — adjusts for subsidized funding cost vs. commercial rate"
ws["D13"].font = ITALIC_GRAY
ws["B14"] = "Portfolio yield (Rev / avg GLP)"
ws["C14"] = "=IFERROR(C5/'Loan Portfolio'!C5,\"-\")"; ws["C14"].number_format = PCT
for r2 in range(12, 15):
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

add_refresh_log(wb)
out_path = "/home/claude/model_shop/MICROFINANCE_template.xlsx"
wb.save(out_path)
print("saved", out_path)
