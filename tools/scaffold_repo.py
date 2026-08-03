"""
scaffold_repo.py — builds the full multi-domain finance repo structure.

Run once to create the skeleton. Each domain gets:
  - its template archetype (copied in, ready to duplicate per company/deal)
  - a companies/ or deals/ subfolder to hold instances
  - a README stub naming the archetype and what belongs there

Domains that are NOT spreadsheet-model categories (personal, behavioral,
social finance) get a /frameworks folder for writeups instead of xlsx files —
padding the repo with fake "models" for these would just be noise.
"""
import os
import shutil

BASE = "/home/claude/model_shop/finance_repo"
TEMPLATES_DIR = "/home/claude/model_shop"

DOMAINS = {
    "01_Investment_Banking": {
        "archetype": "_template.xlsx",
        "desc": "3-statement + DCF + comps. Base corp-finance model, sector modules layered on.",
        "instances": "companies",
    },
    "02_Corporate_Finance": {
        "archetype": "_template.xlsx",
        "desc": "Same engine as IB, capital-structure/cost-of-capital lens.",
        "instances": "companies",
    },
    "03_Private_Equity": {
        "archetype": "LBO_template.xlsx",
        "desc": "Sources & uses, debt schedule w/ cash sweep, returns waterfall.",
        "instances": "deals",
    },
    "04_Merchant_Banking": {
        "archetype": "LBO_template.xlsx",
        "desc": "Same LBO engine — merchant banking = principal-investing variant of PE.",
        "instances": "deals",
    },
    "05_Private_Credit": {
        "archetype": "CREDIT_template.xlsx",
        "desc": "Leverage ratios, covenant headroom, debt schedule, lender yield incl. OID.",
        "instances": "deals",
    },
    "06_Debt_Finance": {
        "archetype": "CREDIT_template.xlsx",
        "desc": "Same credit engine — general debt-finance instances live here.",
        "instances": "instruments",
    },
    "07_Public_Finance": {
        "archetype": "PUBLIC_FINANCE_template.xlsx",
        "desc": "Sovereign/muni debt sustainability (IMF/DSA), revenue bond coverage & additional bonds test.",
        "instances": "issuers",
    },
    "08_Asset_Management": {
        "archetype": "AM_template.xlsx",
        "desc": "Fund NAV build, fee waterfall (mgmt fee + carry + hurdle + GP catch-up), performance attribution.",
        "instances": "funds",
    },
    "09_Risk_Management": {
        "archetype": "RISK_template.xlsx",
        "desc": "Parametric & historical VaR, stress scenarios, vol/confidence sensitivity grid.",
        "instances": "portfolios",
    },
    "10_Trade_Finance": {
        "archetype": "TRADE_FINANCE_template.xlsx",
        "desc": "Cash conversion cycle (DSO/DIO/DPO), letter of credit cost, factoring cost.",
        "instances": "counterparties",
    },
    "11_Microfinance": {
        "archetype": "MICROFINANCE_template.xlsx",
        "desc": "Loan portfolio quality (PAR30/90, write-off ratio), OSS/FSS sustainability ratios.",
        "instances": "institutions",
    },
    "12_Equity_Finance": {
        "archetype": "_template.xlsx",
        "desc": "Cap table + dilution overlay on the IB base engine.",
        "instances": "companies",
    },
    "13_Venture_Capital": {
        "archetype": "VC_template.xlsx",
        "desc": "Cap table, round modeling, SAFE conversion, liquidation waterfall.",
        "instances": "companies",
    },
    "14_Options_Derivatives": {
        "archetype": "OPTIONS_template.xlsx",
        "desc": "Black-Scholes pricer, Greeks, strategy payoff tables.",
        "instances": "underlyings",
    },
    "15_Commodities": {
        "archetype": "COMMODITIES_template.xlsx",
        "desc": "Futures curve, contango/backwardation, roll yield, hedge ratio.",
        "instances": "commodities",
    },
    "16_Crypto_Digital_Assets": {
        "archetype": "CRYPTO_template.xlsx",
        "desc": "Tokenomics/supply schedule, on-chain valuation multiples, staking yield.",
        "instances": "protocols",
    },
    "17_Real_Estate_REIT": {
        "archetype": "REAL_ESTATE_template.xlsx",
        "desc": "Property pro forma, cap rate valuation, cash-on-cash return, REIT FFO/AFFO.",
        "instances": "properties",
    },
    "18_Insurance_Actuarial": {
        "archetype": "INSURANCE_template.xlsx",
        "desc": "Loss/expense/combined ratio, loss development triangle, embedded value.",
        "instances": "books",
    },
    "19_Structured_Finance_Securitization": {
        "archetype": "SECURITIZATION_template.xlsx",
        "desc": "Tranche waterfall with credit enhancement, CPR/SMM conversion, WAL schedule.",
        "instances": "deals",
    },
    "20_Project_Finance": {
        "archetype": "PROJECT_FINANCE_template.xlsx",
        "desc": "Construction drawdown + IDC, operating CFADS, DSCR schedule vs. covenant.",
        "instances": "projects",
    },
    "21_Fixed_Income_Rates": {
        "archetype": "FIXED_INCOME_template.xlsx",
        "desc": "Bond pricing (PV-based), modified duration/convexity (shock method), yield curve/2s10s.",
        "instances": "instruments",
    },
    "22_Quantitative_Systematic": {
        "archetype": "QUANT_template.xlsx",
        "desc": "Sharpe/Sortino from return series, Kelly criterion & fixed-fractional position sizing.",
        "instances": "strategies",
    },
    "23_Fintech_Payments": {
        "archetype": "FINTECH_template.xlsx",
        "desc": "Take-rate unit economics, LTV/CAC, payback period, cohort retention grid.",
        "instances": "companies",
    },
    "24_Distressed_Restructuring": {
        "archetype": "RESTRUCTURING_template.xlsx",
        "desc": "Absolute-priority recovery waterfall with fulcrum identification, liquidation vs. reorg NPV.",
        "instances": "situations",
    },
}

FRAMEWORKS_ONLY = {
    "26_Personal_Finance": "Net worth / cash flow trackers — individual-level, not company models.",
    "27_Behavioral_Finance": "Research notes and bias frameworks — not spreadsheet deliverables.",
    "28_Social_Finance": "Impact/ESG frameworks and case writeups — not spreadsheet deliverables.",
}

NOT_YET_BUILT = set()


def scaffold():
    os.makedirs(BASE, exist_ok=True)

    for name, cfg in DOMAINS.items():
        domain_path = os.path.join(BASE, name)
        os.makedirs(domain_path, exist_ok=True)
        os.makedirs(os.path.join(domain_path, cfg["instances"]), exist_ok=True)

        archetype_src = os.path.join(TEMPLATES_DIR, cfg["archetype"])
        clean_name = cfg["archetype"].replace("_template.xlsx", "").replace(".xlsx", "")
        if not clean_name or clean_name == "_":
            clean_name = "BASE"
        archetype_dst = os.path.join(domain_path, f"_template_{clean_name}.xlsx")
        if os.path.exists(archetype_src):
            shutil.copy(archetype_src, archetype_dst)
            status = "template copied"
        else:
            status = "TEMPLATE NOT YET BUILT — placeholder only"

        with open(os.path.join(domain_path, "README.md"), "w") as f:
            f.write(f"# {name.replace('_', ' ')}\n\n")
            f.write(f"**Archetype:** `{cfg['archetype']}` ({status})\n\n")
            f.write(f"{cfg['desc']}\n\n")
            f.write(f"Instances live in `/{cfg['instances']}/`. Copy the template, rename to "
                    f"ticker or deal code, fill in Cover tab, run weekly_refresh_check.py.\n")

    fw_path = os.path.join(BASE, "25_Frameworks_NonModel")
    os.makedirs(fw_path, exist_ok=True)
    for name, desc in FRAMEWORKS_ONLY.items():
        sub = os.path.join(fw_path, name)
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "README.md"), "w") as f:
            f.write(f"# {name.replace('_', ' ')}\n\n{desc}\n\nDeliverables here are markdown "
                    f"writeups, not xlsx models.\n")

    # top-level repo README
    with open(os.path.join(BASE, "README.md"), "w") as f:
        f.write("# Finance Model Library\n\n")
        f.write("Multi-domain repo of financial models, organized by archetype not just ticker.\n\n")
        f.write("## Domains\n\n")
        for name, cfg in DOMAINS.items():
            built = "✅" if os.path.exists(os.path.join(TEMPLATES_DIR, cfg["archetype"])) else "🔲 not yet built"
            f.write(f"- **{name.replace('_', ' ')}** — {cfg['desc']} {built}\n")
        f.write("\n## Non-model frameworks\n\n")
        for name, desc in FRAMEWORKS_ONLY.items():
            f.write(f"- **{name.replace('_', ' ')}** — {desc}\n")
        f.write("\n## Maintenance\n\nRun `weekly_refresh_check.py <domain_folder>` weekly per domain, "
                "or point it at the repo root to scan everything recursively.\n")

    print(f"Scaffolded repo at {BASE}")
    print(f"Templates still to build: {sorted(NOT_YET_BUILT)}")


if __name__ == "__main__":
    scaffold()
