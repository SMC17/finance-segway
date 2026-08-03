import openpyxl
from template_helpers import *

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[INSURER] — Insurance / Actuarial Model", [
    ("Line of business:", "P&C / Life / Health / Reinsurance"),
    ("Last refreshed:", "[date]"),
    ("Refresh cadence:", "Weekly (quarterly for reserves)"),
])

# ---------------- UNDERWRITING RATIOS ----------------
ws = wb.create_sheet("Underwriting Ratios")
set_col_widths(ws, [4, 30, 16, 40])
ws["B2"] = "Underwriting Performance"; ws["B2"].font = TITLE
inputs = [
    ("Earned premium ($)", 0, CUR),
    ("Incurred losses ($)", 0, CUR),
    ("Loss adjustment expenses ($)", 0, CUR),
    ("Underwriting expenses ($)", 0, CUR),
]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1
ws["B10"] = "Loss ratio"; ws["C10"] = "=IFERROR((C6+C7)/C5,\"-\")"; ws["C10"].number_format = PCT
ws["B11"] = "Expense ratio"; ws["C11"] = "=IFERROR(C8/C5,\"-\")"; ws["C11"].number_format = PCT
ws["B12"] = "Combined ratio"; ws["C12"] = "=IFERROR(C10+C11,\"-\")"; ws["C12"].font = BOLD; ws["C12"].number_format = PCT
ws["D12"] = "<100% = underwriting profit; >100% = underwriting loss (offset by investment income)"
ws["D12"].font = ITALIC_GRAY
for r2 in (10, 11, 12):
    ws.cell(row=r2, column=3).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- LOSS RESERVE TRIANGLE ----------------
ws = wb.create_sheet("Loss Reserve Triangle")
set_col_widths(ws, [4, 16] + [12]*6)
ws["B2"] = "Loss Development Triangle (cumulative paid losses, $)"; ws["B2"].font = TITLE
ws["B4"] = "Accident Yr \\ Dev Yr"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
dev_years = [f"Dev {i}" for i in range(1, 7)]
for i, dy in enumerate(dev_years, start=3):
    c = ws.cell(row=4, column=i, value=dy); c.font = BOLD; c.fill = GRAY_FILL
acc_years = [f"AY{2020+i}" for i in range(6)]
for j, ay in enumerate(acc_years, start=5):
    c = ws.cell(row=j, column=2, value=ay); c.font = BOLD; c.fill = GRAY_FILL
    # only fill lower-triangle cells that would actually exist (older years have more dev periods)
    n_periods = 6 - (j - 5)
    for i in range(3, 3 + n_periods):
        cell = ws.cell(row=j, column=i, value=0)
        cell.font = BLUE
        cell.number_format = CUR
        cell.border = BORDER
ws["B12"] = "Age-to-age development factors (link ratios) go below once 2+ diagonals of data exist"
ws["B12"].font = ITALIC_GRAY
ws["B13"] = "Ultimate loss = latest diagonal x cumulative development factor (chain-ladder method)"
ws["B13"].font = ITALIC_GRAY
ws.sheet_view.showGridLines = False

# ---------------- EMBEDDED VALUE ----------------
ws = wb.create_sheet("Embedded Value")
set_col_widths(ws, [4, 32, 16, 40])
ws["B2"] = "Embedded Value (life/health simplified)"; ws["B2"].font = TITLE
inputs = [
    ("Adjusted net asset value (ANAV, $)", 0, CUR),
    ("PV of future profits on in-force business ($)", 0, CUR),
    ("Cost of holding required capital ($)", 0, CUR),
    ("Risk margin / cost of non-hedgeable risk ($)", 0, CUR),
]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1
ws["B10"] = "Embedded Value = ANAV + PVFP - CoC - Risk margin"
ws["C10"] = "=C5+C6-C7-C8"; ws["C10"].font = BOLD; ws["C10"].number_format = CUR
ws["C10"].border = BORDER
ws["B12"] = "Value of new business (VNB) this period"; ws["C12"] = 0; ws["C12"].font = BLUE
ws["C12"].number_format = CUR; ws["C12"].fill = YELLOW_FILL; ws["C12"].border = BORDER
ws.sheet_view.showGridLines = False

add_refresh_log(wb)
out_path = "/home/claude/model_shop/INSURANCE_template.xlsx"
wb.save(out_path)
print("saved", out_path)
