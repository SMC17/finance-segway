# Data Grounding Pass — 2026-08-05

## Actions

1. **EDGAR companyfacts refresh (prefer-annual)** via polished `edgar_company_facts.py`
   - **ARCC** (Ares Capital, CIK 0001287750) → FY2025 10-K facts (Assets 31.235 bn, Equity 14.318 bn, Net Income 1.299 bn, LT Debt 15.991 bn, etc.). Snapshot: `tools/data_fabric/out/ARCC_facts_selected.json`.
   - **AAPL** → FY2025 10-K (ended 2025-09-27). 29 concepts.
   - **MSFT** → FY2026 10-K (ended 2026-06-30). 28 concepts.

2. **HVPE public NAV grounding**
   - 31 May 2026 headline: NAV/share **$59.89**, net assets ≈ **$4.2 bn**.
   - **Full March 2026 factsheet parse** (26 metrics): portfolio $4,356 m, cash $222 m, facility drawn $570 m / undrawn $630 m, pipeline $6,632 m (159% of NAV), distribution pool $204 m, look-through borrowing $527 m, valuation lag mix 6/86/8, etc.

3. **Domain source_register updates**
   - Private Credit: active FY2025 ARCC row + MAIN / GBDC / BXSL peer rows.
   - Fund of Funds: primary March factsheet + secondary May headline.

## Extension pass (same day)

### 1. Ares instance refresh
- Re-ran `private_credit_underwrite.py --use-ares-fixture` against FY2025 10-K companyfacts.
- Opening gross debt proxy = $15,991 m; Opening cash = $638 m; as_of = 2025-12-31.
- Checks Overall = REVIEW (expected). Manifest / receipt / thesis updated.
- Workbook regenerated locally; re-run agent after pull to materialize xlsx if needed.

### 2. HVPE full factsheet parse
- Parsed official 31 March 2026 Monthly Factsheet PDF (5 pages).
- Snapshot: `tools/data_fabric/out/HVPE_20260331_public_facts.json`.

### 3. Additional BDC + peer EDGAR pulls
- MAIN, GBDC, BXSL companyfacts under `tools/data_fabric/out/`.
- Private Credit source_register extended with active peer rows.

## Quality / maturity impact

Real public data is governed for Private Credit (ARCC + peers) and Fund of Funds (HVPE). Existing public instances remain correctly classified; no maturity promotion claimed. Validators and Issue #7 human sign-off still gate M3/M4.
