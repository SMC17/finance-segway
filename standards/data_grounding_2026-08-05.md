# Data Grounding Pass — 2026-08-05

## Actions

1. **EDGAR companyfacts refresh (prefer-annual)** via polished `edgar_company_facts.py`
   - **ARCC** (Ares Capital, CIK 0001287750) → FY2025 10-K facts (Assets 31.235 bn, Equity 14.318 bn, Net Income 1.299 bn, LT Debt 15.991 bn, etc.). Snapshot: `tools/data_fabric/out/ARCC_facts_selected.json` (sha256 `15af5330…`).
   - **AAPL** → FY2025 10-K (ended 2025-09-27). 29 concepts.
   - **MSFT** → FY2026 10-K (ended 2026-06-30). 28 concepts.
   - Provenance CSVs emitted alongside each JSON.

2. **HVPE public NAV grounding**
   - Recorded 31 May 2026 headline public metrics: NAV/share **$59.89**, net assets ≈ **$4.2 bn**, share price £34.50, discount ≈ 25.9 %, 10y NAV CAGR 13.2 %.
   - Snapshot: `tools/data_fabric/out/HVPE_20260531_public_facts.json` (sha256 `77e8b6d4…`).
   - Source: official hvpe.com website figures + consistent secondary reporting of the monthly estimated NAV series. Not a full PDF parse; sufficient for FoF look-through / NAV roll-forward assumptions.

3. **Domain source_register updates**
   - `05_Private_Credit/sources/source_register.csv` — added active row for the refreshed FY2025 companyfacts.
   - `29_Fund_of_Funds/sources/source_register.csv` — populated with HVPE 31 May 2026 provenance.

## Quality / maturity impact

- Real public data now sits under governed provenance for Private Credit (ARCC) and Fund of Funds (HVPE).
- Existing public instances (Ares 2024, Yellow stress) remain frozen; the new companyfacts layer supplies updated balance-sheet / income inputs that can be attached to future refreshes or new instances.
- No maturity promotion claimed. Validators and model-card gates still apply before any M3/M4 movement.
- Next recommended steps: (a) attach selected ARCC concepts into a refreshed Ares instance workbook if desired, (b) full monthly HVPE factsheet extraction for richer portfolio composition, (c) extend EDGAR pulls to additional BDCs / sector peers.
