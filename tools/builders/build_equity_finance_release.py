"""Release-grade equity-finance workbook with issuance, rights, and convert controls."""
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from tools.builders.legacy_release_adapter import build_release
    from tools.builders.template_helpers import (
        BLUE,
        BOLD,
        BORDER,
        CUR,
        CUR2,
        GRAY_FILL,
        ITALIC_GRAY,
        MULT,
        NUM,
        PCT,
        PCT2,
        TITLE,
        YELLOW_FILL,
        set_col_widths,
        style_header_row,
    )
except ModuleNotFoundError:
    from legacy_release_adapter import build_release
    from template_helpers import (
        BLUE,
        BOLD,
        BORDER,
        CUR,
        CUR2,
        GRAY_FILL,
        ITALIC_GRAY,
        MULT,
        NUM,
        PCT,
        PCT2,
        TITLE,
        YELLOW_FILL,
        set_col_widths,
        style_header_row,
    )


def _overall(check_range: str) -> str:
    return f'=IF(COUNTIF({check_range},"FAIL")+COUNTIF({check_range},"BREACH")>0,"BREACH",IF(COUNTIF({check_range},"REVIEW")>0,"REVIEW","PASS"))'


def enrich(workbook) -> None:
    for name in (
        "Cap Table & Dilution",
        "Rights Offering",
        "Convertible Securities",
        "Decision & Checks",
    ):
        if name in workbook.sheetnames:
            del workbook[name]

    cover = workbook["Cover"]
    cover["B2"] = "[ISSUER] — Equity Finance, Dilution, and Capital Structure"
    cover["B2"].font = TITLE
    cover["B4"] = "Issuer / security:"
    cover["C4"] = "[fill in]"
    cover["B7"] = "Next financing / shareholder date:"

    cap_position = workbook.sheetnames.index("Assumptions") + 1
    cap = workbook.create_sheet("Cap Table & Dilution", cap_position)
    set_col_widths(cap, [4, 42, 18, 18, 18, 46])
    cap["B2"] = "Fully Diluted Cap Table and Ownership Attribution"
    cap["B2"].font = TITLE
    cap["B3"] = "Active scenario"
    cap["C3"] = "Base"
    cap["C3"].font = BLUE
    cap["C3"].fill = YELLOW_FILL
    cap["C3"].border = BORDER
    for column, value in enumerate(
        ["Metric", "Base", "Adversarial", "Active", "Owner / interpretation"],
        start=2,
    ):
        cap.cell(4, column, value)
    style_header_row(cap, 4, 5, start_col=2)
    inputs = [
        ("Existing common shares", 100.0, 100.0, NUM, "pre-transaction issued common"),
        ("In-the-money options / RSUs", 5.0, 20.0, NUM, "treasury-stock or approved dilution method"),
        ("Primary shares issued", 20.0, 150.0, NUM, "new-money common issuance"),
        ("Rights shares issued", 25.0, 100.0, NUM, "shares issued under rights offering"),
        ("Convertible principal", 100.0, 500.0, CUR, "principal subject to conversion"),
        ("Conversion price", 10.0, 5.0, CUR2, "contractual or adjusted conversion price"),
        ("Primary issue price", 11.0, 4.0, CUR2, "gross primary price per share"),
        ("Transaction fees", 5.0, 20.0, CUR, "underwriting, legal, exchange, and other costs"),
        ("Maximum existing-holder dilution", 0.35, 0.35, PCT, "approved decision threshold"),
        ("Maximum option / RSU overhang", 0.10, 0.10, PCT, "options and RSUs / fully diluted shares"),
    ]
    for row, (label, base, adverse, number_format, note) in enumerate(inputs, start=5):
        cap.cell(row, 2, label)
        for column, value in ((3, base), (4, adverse)):
            cell = cap.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        cap.cell(row, 5, f'=IF($C$3="Adversarial",D{row},C{row})')
        cap.cell(row, 5).number_format = number_format
        cap.cell(row, 5).border = BORDER
        cap.cell(row, 6, note)
    cap["B17"] = "Derived outputs"
    cap["B17"].font = BOLD
    cap["B17"].fill = GRAY_FILL
    outputs = [
        (18, "Converted shares", "=IFERROR(E9/E10,0)", NUM),
        (19, "Fully diluted post-money shares", "=SUM(E5:E8)+E18", NUM),
        (20, "Existing common ownership", "=IFERROR(E5/E19,0)", PCT),
        (21, "Existing-holder dilution", "=1-E20", PCT),
        (22, "Option / RSU overhang", "=IFERROR(E6/E19,0)", PCT),
        (23, "Gross primary proceeds", "=E7*E11", CUR),
        (24, "Net primary proceeds", "=E23-E12", CUR),
        (25, "Share-conservation residual", "=E19-E5-E6-E7-E8-E18", NUM),
    ]
    for row, label, formula, number_format in outputs:
        cap.cell(row, 2, label)
        cap.cell(row, 5, formula)
        cap.cell(row, 5).number_format = number_format
        cap.cell(row, 5).border = BORDER
    cap["B27"] = (
        "The fully diluted denominator must use the security-specific treasury-stock, "
        "if-converted, contingently issuable, and anti-dilution conventions approved for the analysis."
    )
    cap["B27"].font = ITALIC_GRAY
    cap.freeze_panes = "B5"
    cap.sheet_view.showGridLines = False

    rights = workbook.create_sheet("Rights Offering", cap_position + 1)
    set_col_widths(rights, [4, 42, 18, 18, 46])
    rights["B2"] = "Rights Offering Economics and Holder Choices"
    rights["B2"].font = TITLE
    for column, value in enumerate(
        ["Metric", "Base", "Adversarial", "Interpretation"], start=2
    ):
        rights.cell(4, column, value)
    style_header_row(rights, 4, 4, start_col=2)
    inputs = [
        ("Existing shares entitled", "='Cap Table & Dilution'!C5", "='Cap Table & Dilution'!D5", NUM, "record-date eligible shares"),
        ("Rights shares offered", "='Cap Table & Dilution'!C8", "='Cap Table & Dilution'!D8", NUM, "new shares available through rights"),
        ("Cum-rights market price", 12.0, 10.0, CUR2, "unaffected reference price"),
        ("Subscription price", 9.0, 3.0, CUR2, "cash exercise price"),
        ("Expected participation", 0.90, 0.45, PCT, "take-up before standby / rump placement"),
        ("Standby / backstop fee", 0.02, 0.08, PCT, "% of underwritten proceeds"),
    ]
    for row, (label, base, adverse, number_format, note) in enumerate(inputs, start=5):
        rights.cell(row, 2, label)
        for column, value in ((3, base), (4, adverse)):
            cell = rights.cell(row, column, value)
            if not isinstance(value, str):
                cell.font = BLUE
                cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        rights.cell(row, 5, note)
    rights["B13"] = "Theoretical ex-rights price"
    rights["C13"] = "=IFERROR((C5*C7+C6*C8)/(C5+C6),0)"
    rights["D13"] = "=IFERROR((D5*D7+D6*D8)/(D5+D6),0)"
    rights["B14"] = "Theoretical value per right / existing share"
    rights["C14"] = "=C7-C13"
    rights["D14"] = "=D7-D13"
    rights["B15"] = "Subscription discount"
    rights["C15"] = "=IFERROR(1-C8/C7,0)"
    rights["D15"] = "=IFERROR(1-D8/D7,0)"
    rights["B16"] = "Expected subscribed shares"
    rights["C16"] = "=C6*C9"
    rights["D16"] = "=D6*D9"
    rights["B17"] = "Expected gross proceeds"
    rights["C17"] = "=C16*C8"
    rights["D17"] = "=D16*D8"
    rights["B18"] = "Expected standby fee"
    rights["C18"] = "=(C6-C16)*C8*C10"
    rights["D18"] = "=(D6-D16)*D8*D10"
    rights["B19"] = "Expected net rights proceeds"
    rights["C19"] = "=C17-C18"
    rights["D19"] = "=D17-D18"
    for row in range(13, 20):
        for column in (3, 4):
            rights.cell(row, column).border = BORDER
            rights.cell(row, column).number_format = PCT if row == 15 else (NUM if row == 16 else CUR)
    rights["B21"] = (
        "TERP is a frictionless reference. Actual value depends on trading, eligibility, taxes, "
        "participation, backstop terms, execution leakage, and the use of proceeds."
    )
    rights["B21"].font = ITALIC_GRAY
    rights.sheet_view.showGridLines = False

    converts = workbook.create_sheet("Convertible Securities", cap_position + 2)
    set_col_widths(converts, [4, 42, 18, 18, 46])
    converts["B2"] = "Convertible Security Economics and If-Converted Dilution"
    converts["B2"].font = TITLE
    for column, value in enumerate(
        ["Metric", "Base", "Adversarial", "Interpretation"], start=2
    ):
        converts.cell(4, column, value)
    style_header_row(converts, 4, 4, start_col=2)
    inputs = [
        ("Principal", "='Cap Table & Dilution'!C9", "='Cap Table & Dilution'!D9", CUR, "outstanding principal"),
        ("Conversion price", "='Cap Table & Dilution'!C10", "='Cap Table & Dilution'!D10", CUR2, "post-adjustment conversion price"),
        ("Current share price", 12.0, 4.0, CUR2, "market reference"),
        ("Cash coupon", 0.04, 0.08, PCT, "annual cash interest"),
        ("Remaining tenor", 3.0, 1.0, "0.0", "years"),
        ("Redemption premium", 0.05, 0.15, PCT, "premium to principal at maturity / redemption"),
        ("Anti-dilution adjusted price", 9.5, 3.5, CUR2, "approved modeled adjustment"),
    ]
    for row, (label, base, adverse, number_format, note) in enumerate(inputs, start=5):
        converts.cell(row, 2, label)
        for column, value in ((3, base), (4, adverse)):
            cell = converts.cell(row, column, value)
            if not isinstance(value, str):
                cell.font = BLUE
                cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        converts.cell(row, 5, note)
    converts["B14"] = "Contractual converted shares"
    converts["C14"] = "=IFERROR(C5/C6,0)"
    converts["D14"] = "=IFERROR(D5/D6,0)"
    converts["B15"] = "Anti-dilution adjusted shares"
    converts["C15"] = "=IFERROR(C5/C11,0)"
    converts["D15"] = "=IFERROR(D5/D11,0)"
    converts["B16"] = "Conversion value"
    converts["C16"] = "=C14*C7"
    converts["D16"] = "=D14*D7"
    converts["B17"] = "Redemption value"
    converts["C17"] = "=C5*(1+C10)"
    converts["D17"] = "=D5*(1+D10)"
    converts["B18"] = "Conversion parity"
    converts["C18"] = "=IFERROR(C16/C5,0)"
    converts["D18"] = "=IFERROR(D16/D5,0)"
    converts["B19"] = "Incremental anti-dilution shares"
    converts["C19"] = "=C15-C14"
    converts["D19"] = "=D15-D14"
    converts["B20"] = "Annual cash coupon"
    converts["C20"] = "=C5*C8"
    converts["D20"] = "=D5*D8"
    for row in range(14, 21):
        for column in (3, 4):
            converts.cell(row, column).border = BORDER
            converts.cell(row, column).number_format = NUM if row in (14, 15, 19) else (MULT if row == 18 else CUR)
    converts["B22"] = (
        "This sheet models if-converted economics, not the full value of optionality. "
        "Call features, soft calls, resets, make-wholes, caps, floors, and settlement elections require explicit terms."
    )
    converts["B22"].font = ITALIC_GRAY
    converts.sheet_view.showGridLines = False

    assumptions = workbook["Assumptions"]
    for column in range(3, 8):
        assumptions.cell(12, column, "='Cap Table & Dilution'!E19")
        assumptions.cell(12, column).number_format = NUM

    checks = workbook.create_sheet("Decision & Checks", cap_position + 3)
    set_col_widths(checks, [4, 44, 18, 18, 52])
    checks["B2"] = "Equity Finance Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(
        ["Check / decision", "Metric", "Status", "Interpretation / action"], start=2
    ):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "Share-conservation residual", "='Cap Table & Dilution'!E25", '=IF(ABS(C5)<0.000001,"PASS","FAIL")', "Fully diluted shares must reconcile to every issued and contingently issuable security."),
        (6, "Ownership / dilution identity", "='Cap Table & Dilution'!E20+'Cap Table & Dilution'!E21-1", '=IF(ABS(C6)<0.000001,"PASS","FAIL")', "Existing ownership plus dilution must equal one."),
        (7, "Existing-holder dilution", "='Cap Table & Dilution'!E21", '=IF(C7<=\'Cap Table & Dilution\'!E13,"PASS","BREACH")', "A financing that exceeds approved dilution requires explicit board and shareholder analysis."),
        (8, "Option / RSU overhang", "='Cap Table & Dilution'!E22", '=IF(C8<=\'Cap Table & Dilution\'!E14,"PASS","REVIEW")', "Track employee, acquisition, and contingent-equity dilution separately."),
        (9, "Net primary proceeds", "='Cap Table & Dilution'!E24", '=IF(C9>=0,"PASS","BREACH")', "Fees and discounts may not exceed gross proceeds."),
        (10, "Rights TERP residual", "='Rights Offering'!C13-(('Rights Offering'!C5*'Rights Offering'!C7+'Rights Offering'!C6*'Rights Offering'!C8)/('Rights Offering'!C5+'Rights Offering'!C6))", '=IF(ABS(C10)<0.000001,"PASS","FAIL")', "TERP must reconcile from old and new shares and their respective prices."),
        (11, "Rights value", "='Rights Offering'!C14", '=IF(C11>=0,"PASS","REVIEW")', "Negative theoretical right value indicates inconsistent market or subscription inputs."),
        (12, "Adversarial rights participation", "='Rights Offering'!D9", '=IF(C12>=0.75,"PASS",IF(C12>=0.50,"REVIEW","BREACH"))', "Low participation creates rump-placement, backstop, execution, and control risk."),
        (13, "Converted-share reconciliation", "='Convertible Securities'!C14-'Cap Table & Dilution'!C18", '=IF(ABS(C13)<0.000001,"PASS","FAIL")', "Cap table and convertible schedule must use the same principal and conversion price."),
        (14, "Incremental anti-dilution shares", "='Convertible Securities'!D19", '=IF(C14<=0,"PASS","REVIEW")', "Reset and anti-dilution provisions can materially expand fully diluted shares in downside cases."),
    ]
    for row, label, formula, status, action in rows:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).border = BORDER
        checks.cell(row, 4, status)
        checks.cell(row, 4).border = BORDER
        checks.cell(row, 5, action)
    checks["B16"] = "Overall model status"
    checks["B16"].font = BOLD
    checks["C16"] = _overall("D5:D14")
    checks["C16"].font = BOLD
    checks["C16"].border = BORDER
    checks["B18"] = "Primary decision outputs"
    checks["B18"].font = BOLD
    checks["B18"].fill = GRAY_FILL
    outputs = [
        (19, "Fully diluted shares", "='Cap Table & Dilution'!E19", NUM),
        (20, "Existing-holder dilution", "='Cap Table & Dilution'!E21", PCT),
        (21, "Net primary proceeds", "='Cap Table & Dilution'!E24", CUR),
        (22, "Base TERP", "='Rights Offering'!C13", CUR2),
        (23, "Expected net rights proceeds", "='Rights Offering'!C19", CUR),
        (24, "Contractual converted shares", "='Convertible Securities'!C14", NUM),
        (25, "Adversarial anti-dilution shares", "='Convertible Securities'!D15", NUM),
        (26, "Adversarial redemption value", "='Convertible Securities'!D17", CUR),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("EQUITY_FINANCE_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
