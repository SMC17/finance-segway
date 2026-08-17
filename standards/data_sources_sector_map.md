# Data Sources & Sector Map

Machine- and human-readable mapping of public data sources to Finance-Segway domains.
Complements `tools/data_fabric/` and the Public Instance Program.

**Primary rails**
- **SEC / EDGAR** – US public company XBRL companyfacts, 10-K/10-Q, Form PF aggregates.
- **U.S. Treasury** – daily par yield curve, bill rates, long-term rates, real (TIPS) curves. Discount/benchmark-rate input to Fixed Income, Options, Project Finance, and any DCF-adjacent domain.
- **Damodaran (NYU Stern)** – industry-average beta, cost of equity/debt, WACC, margins, and PE/PBV/PS multiples (US + regional variants); global country equity risk premiums for cross-border WACC. Cost-of-capital and comps-benchmark input wherever a domain needs an industry or country number a single company's own filings can't supply.
- **HVPE** – HarbourVest Global Private Equity Limited (listed FoF): monthly estimated NAV, annual reports, portfolio composition, cash-flow and allocation disclosures.
- **FCA** – UK Product Sales Data (PSD), FIRDS instrument reference, STS securitisations, Public Ratings Database, NSM regulated disclosures, market-activity summaries.

**Secondary / academic**
- Chicago Booth Fama-Miller Center (academic access), Harvard Business School cases & Dataverse, Wharton WRDS gateway (institutional), NBER, RCFS / SSRN replication packages, Fed / FRB public series, ICAEW & FAST modelling standards (already referenced in repo governance).

All attachments must obey the real-data-only policy and carry full `source_register` provenance.

---

## Domain → Source Mapping

| # | Domain | Primary public sources | Example / priority entities or datasets | Notes for sector analysis |
|---|--------|------------------------|-----------------------------------------|---------------------------|
| 01 | Investment Banking | SEC EDGAR companyfacts + filings + Damodaran (industry PE/PBV/PS for comps, WACC for DCF discount rate) | MSFT, AAPL, GOOGL, major M&A targets (LinkedIn historical, Autonomy stress) | 3-statement + DCF + comps; use prefer-annual for clean historicals |
| 02 | Corporate Finance | SEC EDGAR + Damodaran (industry WACC/beta for cost of capital) | MSFT, INTC, sector peers by GICS | Capital structure, stress tests (Intel 2024-style) |
| 03 | Private Equity | HVPE public NAV/portfolio + SEC of public sponsors & exits + Damodaran (industry WACC as entry/exit discount-rate cross-check) | HVPE monthly/annual; HD, Macy’s-style public cases already present | Look-through via HVPE allocations; LBO templates remain formula-driven |
| 04 | Merchant Banking | HVPE + SEC of principal-investing vehicles | Alleghany, WeWork historical public cases | Principal-investing LBO variant; same provenance rules |
| 05 | Private Credit | SEC of BDCs + HVPE private-credit slice + FCA credit/PSD where relevant | ARCC (already exercised), Ares, Yellow stress | CFADS, covenants, yield/OID, recovery; expand BDC coverage |
| 06 | Debt Finance | SEC issuer filings + FCA ratings / instrument data | Carnival (stress), MSFT debt, UK issuers via NSM | Maturity ladder, refinancing, rate risk |
| 07 | Public Finance | Sovereign / municipal public disclosures + Fed series; FCA where UK local | Jamaica, Sri Lanka stress cases already present | DSA + operating / reserve / coverage lenses |
| 08 | Asset Management | SEC of large managers + HVPE as FoF proxy + Damodaran (industry cost of capital for NAV/attribution benchmarks) | BLK (BlackRock 2022/23 cases) | NAV, fees, carry, attribution |
| 09 | Risk Management | FRED / public market series + SEC for institutional holdings | FRED balanced / COVID adversarial cases | VaR / stress framework; regime citations |
| 10 | Trade Finance | SEC of major exporters / aircraft / commodities houses | Boeing 2019/2020 cases | Cash conversion, LC, factoring |
| 11 | Microfinance | Public MFI reports + FCA retail / protection PSD aggregates | ASA 2025 & Zambia stress cases | PAR, OSS/FSS; UK consumer-credit PSD for benchmarking |
| 12 | Equity Finance | SEC offerings & dilution events | TSLA 2020, AMC 2020 cases | Primary / secondary equity issuance lens |
| 13 | Venture Capital | Public IPO / down-round filings + HVPE venture/growth slice | SNOW 2020, CART 2023 cases | Cap table, SAFE, waterfall; HVPE growth allocation |
| 14 | Options / Derivatives | Public exchange data (CBOE-style) + SEC where corporate | SPX 2020-03-16 adversarial, 2024-01-02 | Black-Scholes, Greeks; keep independent engines |
| 15 | Commodities | Public futures / EIA / inventory series | WTI 2020 & 2023 cases | Curves, carry, roll, hedging |
| 16 | Crypto / Digital Assets | Public exchange + SEC of listed platforms | COIN 2022/23 cases | Token supply, staking, multiples; real-data only |
| 17 | Real Estate / REIT | SEC of REITs + FCA property-related where available | O (Realty Income), WeWork stress | FFO/AFFO, property pro forma |
| 18 | Insurance / Actuarial | SEC of insurers + FCA pure-protection PSD | AIG 2008 adversarial, CB 2023 | Loss ratio, triangle, EV |
| 19 | Structured Finance / Securitization | Fed / agency mortgage data + FCA STS notifications | Fed mortgage 2009/2024 cases | Tranche waterfall, CPR, WAL |
| 20 | Project Finance | Public project disclosures (NREL, utility filings) | NREL solar, Vogtle delay cases | Construction, CFADS, DSCR |
| 21 | Fixed Income / Rates | `treasury_public_facts.py` (par yield/bill/long-term/real curves) + SEC of issuers | Treasury 2022 shock, 2025-12-01 cases | Price, duration, curve. Existing cases were hand-captured from the same home.treasury.gov chart; the fabric script makes that fetch reproducible |
| 22 | Quantitative / Systematic | Public equity / index series | SPX 2019-2023 & capacity cases | Performance, sizing; capacity constraints |
| 23 | Fintech / Payments | SEC of processors + FCA retail-investment / payments-related | V, FIS/Worldpay cases | Unit economics, cohorts |
| 24 | Distressed / Restructuring | SEC bankruptcy / liquidity filings | BBBY 2022, Hertz 2021 cases | Recovery, fulcrum waterfall |
| 29 | Fund of Funds | **HVPE primary** + other listed FoFs | HVPE NAV series, allocation, cash-flow, discount | Look-through, fee layering, commitment pacing |

Non-model frameworks under `25_Frameworks_NonModel/` can reference the same sources for research notes but do not claim M2+ maturity.

---

## Academic & Research-Group Resources (public / academic-use)

| Source | Access model | Typical use in Finance-Segway |
|--------|--------------|-------------------------------|
| Chicago Booth Fama-Miller Center | Academic / WRDS | European firm data (Amadeus), historical GFD, muni, specialised series — methodology & validation only unless institutional licence |
| Harvard Business School cases & Dataverse | Public cases + Dataverse deposits | Case archetypes, replication packages for risk / corporate stability / VC studies |
| Wharton WRDS | Institutional subscription | CRSP, Compustat, Audit Analytics, ExecuComp, Bank Regulatory — cite for methodology; do not commit restricted extracts |
| NBER, SSRN, RCFS Dataverse | Mostly open | Working papers, replication code/data for quant, PE, credit, labour-in-finance studies |
| Fed / FRB, SEC Form PF aggregates | Fully public | Macro, private-fund statistics, stress scenarios |
| ICAEW Financial Modelling Code, FAST Standard | Public standards | Already inform governance; keep citations in model cards |

When an academic dataset is used for an oracle or benchmark, record it in the domain `sources/source_register.csv` with the same provenance fields and note any academic-use restriction.

---

## Implementation notes

1. **EDGAR path** – `python tools/data_fabric/edgar_company_facts.py --ticker TICKER [--prefer-annual] [--extra-concepts ...]`. Attach the resulting CSV rows and keep the JSON snapshot.
2. **HVPE path** – Download latest public factsheet/annual report → extract headline metrics → `record_public_snapshot(...)` (or `--demo` for template). Promote into FoF / PE / AM instances.
3. **FCA path** – Obtain published PSD tables, FIRDS files or STS extracts from official pages → `record_dataset_snapshot(...)`. Especially useful for UK credit, mortgage, protection and instrument reference work.
4. **Promotion** – New sources do not automatically raise maturity. M3/M4 still require model cards, independent validation, effective challenge, and (for M4) maintained instances with outcome monitoring.
5. **CI** – Existing validators (`validate_model_inventory.py`, public-case checks, real-data-only tests) continue to gate any claims that rely on these sources.

Last updated: 2026-08-17 (Treasury + Damodaran data-fabric connectors).
