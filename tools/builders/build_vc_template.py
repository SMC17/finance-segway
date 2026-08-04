import openpyxl
from template_helpers import *
from vc_election_solver import add_holder_election_solver

wb = openpyxl.Workbook()
wb.remove(wb.active)

add_cover(wb, "[COMPANY] — Venture Capital Model", [
    ("Sector:", "[fill in]"),
    ("Current stage:", "Seed / A / B / C / Growth"),
    ("Last refreshed:", "[date]"),
    ("Next round expected:", "[date]"),
    ("Refresh cadence:", "Weekly"),
])

# ---------------- CAP TABLE ----------------
ws = wb.create_sheet("Cap Table")
set_col_widths(ws, [4, 28, 14, 14, 14, 14, 18, 14, 20, 16, 12, 16, 18])
ws["B2"] = "Capitalization Table"; ws["B2"].font = TITLE
headers = [
    "", "Holder / Class", "Shares", "% Fully Diluted", "Price paid/sh",
    "Invested $", "Security type", "Liq. pref (x)", "Participation",
    "Participation cap (x)", "Seniority", "Conversion ratio",
    "As-converted shares",
]
for i, h in enumerate(headers, start=1):
    ws.cell(row=4, column=i, value=h)
style_header_row(ws, 4, len(headers))

rows = [
    ("Founders (common)", "Common", 0.0, "N/A", 0.0, 0, 1.0),
    ("Employee option pool", "Common", 0.0, "N/A", 0.0, 0, 1.0),
    ("SAFE holders (pre-conversion)", "SAFE — deal-specific", 0.0, "Deal-specific", 0.0, 0, 0.0),
    ("Seed preferred", "Preferred", 1.0, "Non-participating", 0.0, 1, 1.0),
    ("Series A preferred", "Preferred", 1.0, "Non-participating", 0.0, 2, 1.0),
    ("Series B preferred", "Preferred", 1.0, "Non-participating", 0.0, 3, 1.0),
]
r = 5
for label, security_type, preference, participation, cap, seniority, conversion in rows:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c_sh = ws.cell(row=r, column=3, value=0); c_sh.font = BLUE; c_sh.number_format = NUM; c_sh.border = BORDER
    c_price = ws.cell(row=r, column=5, value=0); c_price.font = BLUE; c_price.number_format = CUR2; c_price.border = BORDER
    c_inv = ws.cell(row=r, column=6, value=f"=C{r}*E{r}"); c_inv.number_format = CUR; c_inv.border = BORDER
    term_values = (security_type, preference, participation, cap, seniority, conversion)
    for column, value in enumerate(term_values, start=7):
        cell = ws.cell(row=r, column=column, value=value)
        cell.font = BLUE
        cell.fill = YELLOW_FILL
        cell.border = BORDER
    ws.cell(row=r, column=8).number_format = MULT
    ws.cell(row=r, column=10).number_format = MULT
    ws.cell(row=r, column=12).number_format = "0.000x"
    ws.cell(row=r, column=13, value=f"=C{r}*L{r}").number_format = NUM
    ws.cell(row=r, column=13).border = BORDER
    r += 1
total_row = r
ws.cell(row=total_row, column=2, value="Total").font = BOLD
ws.cell(row=total_row, column=3, value=f"=SUM(C5:C{total_row-1})").font = BOLD
ws.cell(row=total_row, column=3).number_format = NUM
ws.cell(row=total_row, column=6, value=f"=SUM(F5:F{total_row-1})").font = BOLD
ws.cell(row=total_row, column=6).number_format = CUR
ws.cell(row=total_row, column=13, value=f"=SUM(M5:M{total_row-1})").font = BOLD
ws.cell(row=total_row, column=13).number_format = NUM
for r2 in range(5, total_row):
    cell = ws.cell(row=r2, column=4, value=f"=IFERROR(M{r2}/$M${total_row},\"-\")")
    cell.number_format = PCT
ws.sheet_view.showGridLines = False

# ---------------- ROUND MODELING ----------------
ws = wb.create_sheet("Round Modeling")
set_col_widths(ws, [4, 26, 16, 4, 26, 16])
ws["B2"] = "New Round Modeling"; ws["B2"].font = TITLE
ws["B4"] = "Inputs"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
inputs = [("Pre-money valuation", 0, CUR), ("New money raised", 0, CUR),
          ("New option pool top-up %", 0, PCT), ("Existing fully diluted shares", 0, NUM)]
r = 5
for label, default, fmt in inputs:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.number_format = fmt
    c.fill = YELLOW_FILL; c.border = BORDER
    r += 1

ws["E4"] = "Outputs"; ws["E4"].font = BOLD; ws["E4"].fill = GRAY_FILL
ws["E5"] = "Post-money valuation"; ws["F5"] = "=C5+C6"; ws["F5"].number_format = CUR
ws["E6"] = "Price per share"; ws["F6"] = "=IFERROR(C5/C8,\"-\")"; ws["F6"].number_format = CUR2
ws["E7"] = "New shares issued (investor)"; ws["F7"] = "=IFERROR(C6/F6,\"-\")"; ws["F7"].number_format = NUM
ws["E8"] = "New pool shares (top-up)"; ws["F8"] = "=IFERROR(C7*(C8+F7),\"-\")"; ws["F8"].number_format = NUM
ws["E9"] = "Total post-round shares"; ws["F9"] = "=IFERROR(C8+F7+F8,\"-\")"; ws["F9"].font = BOLD; ws["F9"].number_format = NUM
ws["E10"] = "New investor ownership %"; ws["F10"] = "=IFERROR(F7/F9,\"-\")"; ws["F10"].number_format = PCT
ws["E11"] = "Existing holder dilution %"; ws["F11"] = "=IFERROR(1-C8/F9,\"-\")"; ws["F11"].number_format = PCT
for row in range(5, 12):
    ws.cell(row=row, column=6).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- SAFE CONVERSION ----------------
ws = wb.create_sheet("SAFE Conversion")
set_col_widths(ws, [4, 28, 14, 4, 28, 16])
ws["B2"] = "SAFE / Convertible Note Conversion"; ws["B2"].font = TITLE
ws["B4"] = "SAFE Terms"; ws["B4"].font = BOLD; ws["B4"].fill = GRAY_FILL
terms = [("SAFE investment amount", 0, CUR), ("Valuation cap", 0, CUR), ("Discount %", 0, PCT)]
r = 5
for label, default, fmt in terms:
    ws.cell(row=r, column=2, value=label).font = BLACK
    c = ws.cell(row=r, column=3, value=default); c.font = BLUE; c.fill = YELLOW_FILL
    c.number_format = fmt; c.border = BORDER
    r += 1

ws["E4"] = "At Priced Round"; ws["E4"].font = BOLD; ws["E4"].fill = GRAY_FILL
ws["E5"] = "Priced round price/share"; ws["F5"] = "='Round Modeling'!F6"; ws["F5"].font = GREEN; ws["F5"].number_format = CUR2
ws["E6"] = "Cap price/share (cap / pre-round FD shares)"
ws["F6"] = "=IFERROR(C6/'Round Modeling'!C8,\"-\")"; ws["F6"].number_format = CUR2
ws["E7"] = "Discount price/share"
ws["F7"] = "=IFERROR(F5*(1-C7),\"-\")"; ws["F7"].number_format = CUR2
ws["E8"] = "SAFE conversion price (lower of cap/discount/round)"
ws["F8"] = '=IFERROR(MIN(IF(ISNUMBER(F5),F5,9E99),IF(ISNUMBER(F6),F6,9E99),IF(ISNUMBER(F7),F7,9E99)),"-")'; ws["F8"].font = BOLD; ws["F8"].number_format = CUR2
ws["E9"] = "SAFE shares issued"
ws["F9"] = "=IFERROR(C5/F8,\"-\")"; ws["F9"].font = BOLD; ws["F9"].number_format = NUM
for row in range(5, 10):
    ws.cell(row=row, column=6).border = BORDER
ws.sheet_view.showGridLines = False

# ---------------- EXIT WATERFALL ----------------
ws = wb.create_sheet("Exit Waterfall")
set_col_widths(ws, [4, 40, 18, 18, 14, 18, 14, 18, 18, 18, 18, 18, 18, 14, 14, 16, 18])
ws["B2"] = "Exit Proceeds Waterfall — Independent Preferred-Class Elections"; ws["B2"].font = TITLE
for column, value in enumerate(["Metric", "Base", "Adversarial"], start=2):
    ws.cell(4, column, value)
style_header_row(ws, 4, 3, start_col=2)
ws["B5"] = "Total exit proceeds"
for cell in (ws["C5"], ws["D5"]):
    cell.value = 0
    cell.font = BLUE
    cell.fill = YELLOW_FILL
    cell.border = BORDER
    cell.number_format = CUR
add_holder_election_solver(
    ws,
    base_exit_ref="$C$5",
    adverse_exit_ref="$D$5",
    start_row=8,
)
ws.sheet_view.showGridLines = False

# ---------------- COMPARABLE FINANCINGS ----------------
ws = wb.create_sheet("Comparable Financings")
set_col_widths(ws, [4, 20, 14, 16, 16, 16, 20])
ws["B2"] = "Comparable Financings"; ws["B2"].font = TITLE
for i, h in enumerate(["", "Company", "Round", "Date", "Pre-money", "Amount raised", "Lead investor"], start=1):
    ws.cell(row=4, column=i, value=h)
style_header_row(ws, 4, len(["Company","Round","Date","Pre-money","Amount raised","Lead investor"]))
for r in range(5, 13):
    for c in range(2, 8):
        cell = ws.cell(row=r, column=c, value="[fill in]" if c != 5 and c != 6 else 0)
        cell.font = BLUE
        cell.border = BORDER
        if c in (5, 6):
            cell.number_format = CUR
ws.sheet_view.showGridLines = False

add_refresh_log(wb)

out_path = "VC_template.xlsx"
wb.save(out_path)
print("saved", out_path)
