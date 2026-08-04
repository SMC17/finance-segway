"""Release-grade crypto workbook with supply, treasury, custody, and liquidity controls."""
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
        "Supply Rollforward & Unlocks",
        "Treasury & Runway",
        "Custody & Liquidity",
        "Decision & Checks",
    ):
        if name in workbook.sheetnames:
            del workbook[name]

    valuation = workbook["Valuation"]
    valuation["B16"] = "Network value / annualized transaction volume"
    valuation["D16"] = (
        "Market cap divided by trailing daily transaction volume annualized; "
        "this is a valuation-to-usage ratio, not transaction velocity."
    )
    valuation["D16"].font = ITALIC_GRAY

    supply_position = workbook.sheetnames.index("Tokenomics") + 1
    supply = workbook.create_sheet("Supply Rollforward & Unlocks", supply_position)
    set_col_widths(supply, [4, 42, 18, 18, 18, 46])
    supply["B2"] = "Token Supply Conservation, Unlocks, and Dilution"
    supply["B2"].font = TITLE
    supply["B3"] = "Active scenario"
    supply["C3"] = "Base"
    supply["C3"].font = BLUE
    supply["C3"].fill = YELLOW_FILL
    supply["C3"].border = BORDER
    for column, value in enumerate(
        ["Metric", "Base", "Downside", "Active", "Owner / interpretation"],
        start=2,
    ):
        supply.cell(4, column, value)
    style_header_row(supply, 4, 5, start_col=2)
    inputs = [
        ("Beginning total supply", 1000.0, 1000.0, NUM, "opening on-chain total supply"),
        ("Protocol issuance", 20.0, 50.0, NUM, "newly minted non-staking issuance"),
        ("Scheduled token unlocks", 30.0, 250.0, NUM, "vested tokens becoming transferable"),
        ("Staking / validator rewards", 10.0, 40.0, NUM, "inflationary security rewards"),
        ("Burns", 5.0, 0.0, NUM, "verifiably destroyed supply"),
        ("Locked / non-circulating supply", 300.0, 100.0, NUM, "contractually or technically restricted"),
        ("Maximum one-period unlock rate", 0.10, 0.10, PCT, "unlocks / beginning supply"),
        ("Maximum annualized staking dilution", 0.08, 0.08, PCT, "staking rewards / pre-reward circulating supply"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        supply.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = supply.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        supply.cell(row, 5, f'=IF($C$3="Downside",D{row},C{row})')
        supply.cell(row, 5).number_format = number_format
        supply.cell(row, 5).border = BORDER
        supply.cell(row, 6, note)
    supply["B15"] = "Derived outputs"
    supply["B15"].font = BOLD
    supply["B15"].fill = GRAY_FILL
    outputs = [
        (16, "Ending total supply", "=E5+E6+E7+E8-E9", NUM),
        (17, "Circulating supply", "=E16-E10", NUM),
        (18, "Unlock rate", "=IFERROR(E7/E5,0)", PCT),
        (19, "Staking dilution", "=IFERROR(E8/MAX(E17-E8,0.000001),0)", PCT),
        (20, "Locked supply %", "=IFERROR(E10/E16,0)", PCT),
        (21, "Net supply growth", "=IFERROR(E16/E5-1,0)", PCT),
    ]
    for row, label, formula, number_format in outputs:
        supply.cell(row, 2, label)
        supply.cell(row, 5, formula)
        supply.cell(row, 5).number_format = number_format
        supply.cell(row, 5).border = BORDER
    supply["B23"] = (
        "Unlocks are a transferability event, not new issuance. They still create float, "
        "liquidity, governance, and price-pressure risk and must remain separate from minting."
    )
    supply["B23"].font = ITALIC_GRAY
    supply.freeze_panes = "B5"
    supply.sheet_view.showGridLines = False

    treasury_position = workbook.sheetnames.index("Valuation") + 1
    treasury = workbook.create_sheet("Treasury & Runway", treasury_position)
    set_col_widths(treasury, [4, 42, 18, 18, 46])
    treasury["B2"] = "Treasury Composition, Operating Runway, and Obligations"
    treasury["B2"].font = TITLE
    for column, value in enumerate(
        ["Metric", "Base", "Downside", "Control / interpretation"], start=2
    ):
        treasury.cell(4, column, value)
    style_header_row(treasury, 4, 4, start_col=2)
    inputs = [
        ("Cash and insured deposits", 30.0, 10.0, CUR, "unrestricted operating cash"),
        ("High-quality stablecoins", 10.0, 3.0, CUR, "haircut for issuer, reserve, and redemption risk"),
        ("Native / treasury token value", 80.0, 20.0, CUR, "mark separately from liquid operating resources"),
        ("Other liquid digital assets", 10.0, 2.0, CUR, "haircut for volatility and market depth"),
        ("Restricted / earmarked assets", 20.0, 20.0, CUR, "not available for general operations"),
        ("Monthly operating burn", 5.0, 7.0, CUR, "cash operating outflow"),
        ("Thirty-day contractual obligations", 20.0, 25.0, CUR, "payroll, vendors, debt, grants, and settlement"),
        ("Minimum cash runway (months)", 18.0, 18.0, "0.0", "approved warning threshold"),
        ("Minimum liquid coverage", 1.25, 1.25, MULT, "liquid resources / thirty-day obligations"),
        ("Stablecoin haircut", 0.15, 0.35, PCT, "issuer and redemption stress"),
        ("Other digital-asset haircut", 0.35, 0.65, PCT, "market-depth and volatility stress"),
    ]
    for row, (label, base, downside, number_format, note) in enumerate(inputs, start=5):
        treasury.cell(row, 2, label)
        for column, value in ((3, base), (4, downside)):
            cell = treasury.cell(row, column, value)
            cell.font = BLUE
            cell.fill = YELLOW_FILL
            cell.number_format = number_format
            cell.border = BORDER
        treasury.cell(row, 5, note)
    treasury["B18"] = "Haircut-adjusted liquid resources"
    treasury["C18"] = "=C5+C6*(1-C14)+C8*(1-C15)"
    treasury["D18"] = "=D5+D6*(1-D14)+D8*(1-D15)"
    treasury["B19"] = "Operating runway (months)"
    treasury["C19"] = "=IFERROR(C18/C10,0)"
    treasury["D19"] = "=IFERROR(D18/D10,0)"
    treasury["B20"] = "Thirty-day liquid coverage"
    treasury["C20"] = "=IFERROR(C18/C11,0)"
    treasury["D20"] = "=IFERROR(D18/D11,0)"
    treasury["B21"] = "Treasury-token concentration"
    treasury["C21"] = "=IFERROR(C7/SUM(C5:C9),0)"
    treasury["D21"] = "=IFERROR(D7/SUM(D5:D9),0)"
    treasury["B22"] = "Downside status"
    treasury["C22"] = '=IF(AND(D19>=D12,D20>=D13),"PASS","BREACH")'
    for row in range(18, 23):
        for column in (3, 4):
            treasury.cell(row, column).border = BORDER
    for row in (18,):
        treasury.cell(row, 3).number_format = CUR
        treasury.cell(row, 4).number_format = CUR
    for row in (19,):
        treasury.cell(row, 3).number_format = "0.0"
        treasury.cell(row, 4).number_format = "0.0"
    for row in (20,):
        treasury.cell(row, 3).number_format = MULT
        treasury.cell(row, 4).number_format = MULT
    for row in (21,):
        treasury.cell(row, 3).number_format = PCT
        treasury.cell(row, 4).number_format = PCT
    treasury["B24"] = (
        "Native-token marks may support long-horizon optionality but are excluded from "
        "operating runway unless monetization capacity and governance authority are documented."
    )
    treasury["B24"].font = ITALIC_GRAY
    treasury.sheet_view.showGridLines = False

    custody = workbook.create_sheet("Custody & Liquidity", treasury_position + 1)
    set_col_widths(custody, [4, 42, 18, 18, 50])
    custody["B2"] = "Custody, Key Management, Counterparty, and Market-Liquidity Controls"
    custody["B2"].font = TITLE
    for column, value in enumerate(
        ["Control / metric", "Input", "Status", "Evidence / action"], start=2
    ):
        custody.cell(4, column, value)
    style_header_row(custody, 4, 4, start_col=2)
    controls = [
        (5, "Material wallets using approved multi-party authorization (%)", 1.00, '=IF(C5=1,"PASS","BREACH")', "retain signer policy, quorum, key rotation, and recovery evidence"),
        (6, "Private-key recovery exercise completed within policy period", 1.00, '=IF(C6=1,"PASS","BREACH")', "1=yes; retain dated recovery test"),
        (7, "Assets held with unapproved custodians / exchanges (%)", 0.00, '=IF(C7=0,"PASS","BREACH")', "separate custody, venue, settlement, and rehypothecation exposure"),
        (8, "Largest custodian / venue concentration (%)", 0.25, '=IF(C8<=0.40,"PASS","REVIEW")', "review legal entity, jurisdiction, segregation, and withdrawal capacity"),
        (9, "Thirty-day unlocks / trailing daily market volume", 5.00, '=IF(C9<=10,"PASS",IF(C9<=25,"REVIEW","BREACH"))', "days of volume before haircut, participation, and price impact"),
        (10, "Smart-contract / bridge concentration (%)", 0.20, '=IF(C10<=0.35,"PASS","REVIEW")', "measure assets dependent on a single contract, oracle, bridge, or admin key"),
        (11, "Stablecoin issuer concentration (%)", 0.30, '=IF(C11<=0.50,"PASS","REVIEW")', "look through issuer, reserve, banking, and redemption dependencies"),
        (12, "Critical incident remediation overdue", 0.00, '=IF(C12=0,"PASS","BREACH")', "retain owner, severity, containment, remediation, and verification"),
    ]
    for row, label, value, status, action in controls:
        custody.cell(row, 2, label)
        custody.cell(row, 3, value)
        custody.cell(row, 3).font = BLUE
        custody.cell(row, 3).fill = YELLOW_FILL
        custody.cell(row, 3).number_format = PCT if row not in (9, 12) else "0.00"
        custody.cell(row, 3).border = BORDER
        custody.cell(row, 4, status)
        custody.cell(row, 4).border = BORDER
        custody.cell(row, 5, action)
    custody["B14"] = (
        "Control completion must be supported by retained operational evidence. "
        "This sheet is not a representation of regulatory compliance or asset safety."
    )
    custody["B14"].font = ITALIC_GRAY
    custody.freeze_panes = "B5"
    custody.sheet_view.showGridLines = False

    checks = workbook.create_sheet("Decision & Checks", treasury_position + 2)
    set_col_widths(checks, [4, 42, 18, 18, 50])
    checks["B2"] = "Crypto / Digital Asset Decision Dashboard and Independent Checks"
    checks["B2"].font = TITLE
    for column, value in enumerate(
        ["Check / decision", "Metric", "Status", "Interpretation / action"], start=2
    ):
        checks.cell(4, column, value)
    style_header_row(checks, 4, 4, start_col=2)
    rows = [
        (5, "Supply-conservation residual", "='Supply Rollforward & Unlocks'!E16-('Supply Rollforward & Unlocks'!E5+'Supply Rollforward & Unlocks'!E6+'Supply Rollforward & Unlocks'!E7+'Supply Rollforward & Unlocks'!E8-'Supply Rollforward & Unlocks'!E9)", '=IF(ABS(C5)<0.000001,"PASS","FAIL")', "Total supply must reconcile across issuance, unlocks, rewards, and burns."),
        (6, "Locked-supply bound", "='Supply Rollforward & Unlocks'!E16-'Supply Rollforward & Unlocks'!E10", '=IF(C6>=0,"PASS","FAIL")', "Locked supply may not exceed ending total supply."),
        (7, "Unlock rate", "='Supply Rollforward & Unlocks'!E18", '=IF(C7<=\'Supply Rollforward & Unlocks\'!E11,"PASS","BREACH")', "Escalate unlock cliffs and market-liquidity mismatch."),
        (8, "Staking dilution", "='Supply Rollforward & Unlocks'!E19", '=IF(C8<=\'Supply Rollforward & Unlocks\'!E12,"PASS","REVIEW")', "Inflationary staking yield is not equivalent to real economic yield."),
        (9, "Net staking yield", "='Staking Yield'!C14", '=IF(ISNUMBER(C9),IF(C9>=0,"PASS","REVIEW"),"REVIEW")', "Separate fee-funded yield from dilution and price risk."),
        (10, "Downside operating runway", "='Treasury & Runway'!D19", '=IF(C10>=\'Treasury & Runway\'!D12,"PASS","BREACH")', "Treasury-token marks and restricted funds do not fund payroll or obligations by themselves."),
        (11, "Downside liquid coverage", "='Treasury & Runway'!D20", '=IF(C11>=\'Treasury & Runway\'!D13,"PASS","BREACH")', "Haircut-adjusted liquid resources must cover near-term obligations."),
        (12, "Custody / liquidity exceptions", "=COUNTIF('Custody & Liquidity'!D5:D12,"<>PASS")", '=IF(C12=0,"PASS","REVIEW")', "Valuation and tokenomics do not override unresolved key, venue, bridge, or incident risk."),
        (13, "FDV / circulating market cap", "=IFERROR(Valuation!C12/Valuation!C11,0)", '=IF(C13<=2,"PASS",IF(C13<=5,"REVIEW","BREACH"))', "Large FDV overhang requires explicit unlock, liquidity, and incentive analysis."),
    ]
    for row, label, formula, status, action in rows:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).border = BORDER
        checks.cell(row, 4, status)
        checks.cell(row, 4).border = BORDER
        checks.cell(row, 5, action)
    checks["B15"] = "Overall model status"
    checks["B15"].font = BOLD
    checks["C15"] = _overall("D5:D13")
    checks["C15"].font = BOLD
    checks["C15"].border = BORDER
    checks["B17"] = "Primary decision outputs"
    checks["B17"].font = BOLD
    checks["B17"].fill = GRAY_FILL
    outputs = [
        (18, "Ending total supply", "='Supply Rollforward & Unlocks'!E16", NUM),
        (19, "Circulating supply", "='Supply Rollforward & Unlocks'!E17", NUM),
        (20, "Unlock rate", "='Supply Rollforward & Unlocks'!E18", PCT),
        (21, "Circulating market cap", "=Valuation!C11", CUR),
        (22, "Fully diluted valuation", "=Valuation!C12", CUR),
        (23, "Net staking yield", "='Staking Yield'!C14", PCT),
        (24, "Downside runway", "='Treasury & Runway'!D19", "0.0"),
        (25, "Downside liquid coverage", "='Treasury & Runway'!D20", MULT),
    ]
    for row, label, formula, number_format in outputs:
        checks.cell(row, 2, label)
        checks.cell(row, 3, formula)
        checks.cell(row, 3).number_format = number_format
        checks.cell(row, 3).border = BORDER
    checks.freeze_panes = "B5"
    checks.sheet_view.showGridLines = False


def build(output: Path) -> None:
    build_release("build_crypto_template.py", output, enrich)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("CRYPTO_template.xlsx"))
    arguments = parser.parse_args()
    build(arguments.output)
    print(f"saved {arguments.output}")
