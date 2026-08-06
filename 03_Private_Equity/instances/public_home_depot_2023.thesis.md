# Thesis — pe-public-home-depot-2023

## Classification

**external_historical_case** reference instance (public-company operating
case run through the LBO underwriting engine). `counts_toward_M4: false`;
human stakeholder sign-off (Issue #7) remains pending, as on every
instance in this repository.

## Why this case

The Home Depot, Inc. (NYSE: HD) reports as a single operating segment
(home improvement retail), so unlike a diversified conglomerate there is
no multi-segment P&L to build product-by-product. Real judgment density
for a case like this has to come from the real, disclosed *narrative* and
operating detail behind the headline revenue/margin numbers, not from
inventing a segment structure the company doesn't report.

## What changed in this refresh (2026-08-05)

The original manifest overrode only three cells (`Assumptions!C5` LTM
revenue, `C6` EBITDA margin, `C7` revenue growth) from the FY2023 Form
10-K, then left every other operating assumption — D&A/revenue,
capex/revenue, cash tax rate — at generic template defaults sized for a
different company. This refresh pulls three more real, sourced inputs
from Home Depot's own Q4/FY2023 earnings call (held 2024-02-20, before
the case's 2024-03-13 `as_of` date) and cross-checks them against
Alpha-Vantage-sourced SEC cash-flow data:

| Cell | Assumption | Old value | New value | Basis |
|---|---|---|---|---|
| `C6` | EBITDA margin | 0.153 | **0.163** | Disclosed operating margin (14.2%, CFO Richard McPhail on the earnings call) + real D&A/revenue (see `C9`). See "Correction" below. |
| `C7` | Annual revenue growth | -0.03 | **0.01** | FY2024 total sales growth guidance ("approximately positive 1%"), disclosed on the same call — see "Growth assumption" below. |
| `C9` | D&A / revenue | 0.025 (template default) | **0.0213** | $3,247mm D&A / $152,669mm revenue, FY2023 (Alpha Vantage `CASH_FLOW`, `fiscalDateEnding=2024-01-31`). |
| `C10` | Capex / revenue | 0.035 (template default) | **0.0211** | $3,226mm capex / $152,669mm revenue, FY2023 — matches management's disclosed "~$3.2 billion" figure. |
| `C12` | Cash tax rate | 0.25 (template default) | **0.24** | "In the fourth quarter and for fiscal 2023, our effective tax rate was 24%" (earnings call). |

### Correction: prior EBITDA margin value

The prior `C6` value of 0.153 matched neither Home Depot's disclosed
FY2023 EBIT (operating) margin of ~14.2% nor its true EBITDA margin of
~16.3% (operating margin + real D&A/revenue of ~2.1%). It sits suspiciously
close to the "15 basis point" gross-margin decline the same 10-K/earnings
materials mention, which is a plausible source of a transcription slip in
the original manifest authoring. Corrected to 0.163 = 0.142 (disclosed
operating margin) + 0.0213 (derived D&A/revenue).

### Growth assumption: guidance over trailing actual

`Assumptions!C7` feeds the Operating Model's forward compounding
(`Revenue[t] = Revenue[t-1] * (1 + C7)` for all 7 forecast years). The
original value (-0.03) was Home Depot's real, correctly-sourced trailing
FY2023 YoY revenue decline — but applying a single historical year's
decline as a *constant seven-year forward* growth rate does not reflect
what a sponsor underwriting a real transaction would use. Home Depot's own
management gave explicit forward guidance on the same call ("total sales
growth of approximately positive 1%... comp sales of approximately
negative 1%" for FY2024). Using that real, dated, disclosed guidance
figure for the model's actual forward-looking mechanic is a more honest
choice than a trailing actual, and it remains 100% sourced (not modeler
judgment).

## What stayed at template defaults, and why

Dollar-denominated LBO structuring assumptions — entry EBITDA multiple
(10.0x), existing net debt refinanced ($100mm), minimum cash ($20mm),
revolver commitment ($75mm), TLB/second-lien opening leverage — remain
template defaults. This case is not a claim about a real transaction
structure for Home Depot (a real going-private LBO of a company this size
would require entry-value and financing assumptions two to three orders
of magnitude larger than the template's defaults). It is a real-financials,
real-margin, real-growth-trajectory stress of the model's mechanics using
Home Depot's actual reported operating scale. Do not read the Sources &
Uses, Debt Schedule, or Returns Waterfall sheets as a real HD take-private
proposal.

## Real operating context disclosed on the call (not modeled as cell overrides, but informs the underwriting narrative)

- Big-ticket discretionary softness: transactions over $1,000 were down
  6.9% YoY in Q4 FY2023; customers "continue to take on smaller projects
  while still deferring larger projects" (flooring, countertops, cabinets
  named specifically).
- Pro vs. DIY: "effectively the same" performance in Q4 FY2023; the
  managed-account Pro segment was the highest-performing customer segment
  of the year.
- Commodity deflation (lumber, copper wire) reduced average ticket by 35
  basis points in Q4; management stated pricing has "essentially settled."
- Inventory discipline: merchandise inventories were $21.0bn at fiscal
  year end, down ~16% YoY, with inventory turns improving to 4.3x from
  4.2x.
- Capital return: ~$8.4bn dividends paid and ~$8.0bn of share repurchases
  in FY2023; ROIC of 36.7%, down from 44.6% in FY2022.
- FY2024 guidance used for `C7` above: total sales growth ~+1% (including
  a 53rd week contributing ~$2.3bn), comp sales ~-1%, gross margin ~33.9%
  (+50bps), operating margin ~14.1%, effective tax rate ~24.5%, capex ~2%
  of sales.

## Sources

- Domain register: `03_Private_Equity/sources/source_register.csv`
  (`pe-public-home-depot-2023` rows).
- Frozen source snapshot:
  `03_Private_Equity/sources/snapshots/pe-public-home-depot-2023.json`.
- Raw recorded evidence:
  `tools/data_fabric/out/HD_alphavantage_earnings_call_2023Q4.json`,
  `tools/data_fabric/out/HD_alphavantage_cash_flow_fy2023.json`.
- Instance manifest / receipt:
  `standards/public_cases/pe-public-home-depot-2023.json`,
  `03_Private_Equity/instances/public_home_depot_2023.receipt.json`.

## Limitations

- Single-segment retailer: there is no real multi-segment P&L to build,
  unlike a diversified target.
- Transaction-structuring assumptions (entry multiple, leverage, debt
  sizing) remain illustrative template defaults, not a real deal proposal.
- Not decision-grade and not counted toward M4 evidence until an
  independent human reviewer promotes it past the current state
  (Issue #7).

## Regenerate

```bash
python tools/refresh_public_case.py pe-public-home-depot-2023
```
