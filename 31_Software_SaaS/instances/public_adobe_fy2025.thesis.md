# Thesis — software-public-adobe-fy2025

## Classification

**external_historical_case** reference instance (public-company operating
case run through the software / SaaS engine). `counts_toward_M4: false`;
human stakeholder sign-off (Issue #7) remains pending, as on every
instance in this repository.

Generated entirely by `tools/build_software_adobe_case.py` from
`tools/data_fabric/out/ADBE_facts_annual_series.json` (SEC XBRL company
facts, CIK 0000796343). No value in the manifest was typed by hand. Re-run
the generator against the same snapshot and it reproduces byte for byte.

## Why this case exists, and what it is honestly not

The software model's headline engine is an ARR cohort roll-forward. **No
issuer tags ARR in XBRL** — not Adobe, not anyone. ARR is a management
metric with no fixed definition, and neither are net revenue retention,
gross churn, expansion ARR, or the subscription/services revenue split.
A survey of the 102 companies harvested into `tools/data_fabric/out/`
found exactly one structured forward-revenue concept present across the
set: `RevenueRemainingPerformanceObligation`.

That fact drove two decisions:

1. The model gained an **RPO & Bookings** engine (this same change), because
   RPO is the one contracted-future-revenue quantity that is a required
   ASC 606 disclosure with a fixed definition and an XBRL tag.
2. This case sources the **entire GAAP cost and RPO layer** and leaves the
   ARR cohort layer as declared drivers. It is deliberately a partial case,
   and the partition is stated per cell rather than blurred.

Calling this "an Adobe model" without that caveat would be exactly the
failure this repository exists to prevent.

## The three-way input partition

Every one of the 45 candidate input cells is now in one of three states.
**Zero cells are unexamined** — a first for any case in this repo other
than QQQ.

| State | Cells | Meaning |
|---|---:|---|
| `observed` / `derived` | 28 | Read off, or arithmetic on, disclosed facts |
| declared driver | 17 | No disclosure exists; reason stated per cell |
| unexamined | 0 | — |

Coverage: **62.2% real**. The 17 drivers earn no coverage credit and are
not meant to — an ungrounded driver is still an ungrounded number.

## Sourced inputs (Base column)

| Cell | Driver | Value | Kind | Basis |
|---|---|---:|---|---|
| `C5` | Beginning ARR | 20,878.6 | derived | FY2024 Revenues (21,505) net of the services-mix driver — **proxy, see below** |
| `C9` | Gross churn | 0.054722 | derived | Balancing residual pinning net ARR growth to disclosed revenue growth |
| `C11` | Subscription gross margin | 0.908956 | derived | Solved so blended GM equals disclosed 21,218 / 23,769 |
| `C13` | S&M / revenue | 0.272961 | observed | 6,488 / 23,769 |
| `C14` | R&D / revenue | 0.187261 | derived | Opex residual — **broader than reported R&D, see below** |
| `C15` | G&A / revenue | 0.066179 | observed | 1,573 / 23,769 |
| `C16` | SBC / revenue | 0.081703 | observed | 1,942 / 23,769 |
| `C17` | Capex / revenue | 0.007531 | observed | 179 / 23,769 |
| `C18` | Tax rate | 0.183650 | derived | 1,604 / (7,130 + 1,604) — effective GAAP, **not cash** |
| `C20` | Beginning RPO | 19,960.0 | observed | FY2024 `RevenueRemainingPerformanceObligation` |
| `C21` | RPO coverage | 0.947453 | derived | 22,520 / 23,769 |
| `C23` | Contract liability / revenue | 0.295763 | derived | 7,030 / 23,769 |

## Pinning aggregates when components are undisclosed

The technique that makes this case more than half-empty: where a component
is undisclosed but an aggregate of it is disclosed, the component stays a
driver and the aggregate is **pinned** by solving one cell for it.

- **Blended gross margin.** Subscription and services margins are not
  separately disclosed, and neither is the revenue mix between them. But
  `GrossProfit / Revenues` is. So services mix (`C10`) and services margin
  (`C12`) stay drivers, and subscription margin (`C11`) is *solved* so the
  weighted average lands on the disclosed 0.892675.
- **Net ARR growth.** The four flow rates are individually undisclosed.
  Their net is pinned to Adobe's disclosed revenue growth (0.105278) with
  gross churn (`C9`) carrying the constraint as the balancing residual.
  That is why gross churn is the one flow rate with a real basis.
- **Downside column.** Not an invented stress. Each downside value is the
  least favourable of that same ratio across Adobe's three most recent
  disclosed fiscal years (FY2023 / FY2024 / FY2025), direction set per
  ratio. The stress case is bounded by what this company actually did.

## Two caveats stated loudly rather than buried

### 1. R&D is an opex residual, and it is broader than reported R&D

Adobe's XBRL company facts contain **no `ResearchAndDevelopmentExpense`
concept**. `C14` is therefore backed out as:

```
GrossProfit − OperatingIncomeLoss − SellingAndMarketingExpense − GeneralAndAdministrativeExpense
= 21,218 − 8,706 − 6,488 − 1,573 = 4,451
```

That residual absorbs amortization of intangibles and any other separately
reported operating expense, so it is **larger than Adobe's reported R&D
line**. The compensating benefit is real: modelled GAAP operating margin
ties to the disclosed 0.366275 *exactly*, which a hand-picked R&D
percentage never would. Do not read `C14` as Adobe's R&D intensity.

### 2. The ARR scale is a proxy, and the error is measured

ARR is undisclosed, so the opening balance is proxied from FY2024 revenue
net of the services mix. Revenue is a period-average *flow*; ARR is a
point-in-time contracted *balance*. For a growing business the proxy
understates exit ARR, and the gap is not hidden:

| | Modelled | Disclosed FY2025 | Delta |
|---|---:|---:|---:|
| Total revenue ($mm) | 22,637 | 23,769 | **−4.76%** |

Every ratio ties to the filing to six decimal places. **Absolute dollar
levels on this case carry that −4.76%.** The figure is recorded
machine-readably in the snapshot under `reconciliation_to_disclosure`, so
it moves visibly if the case ever gets worse.

## Verification

| Check | Result |
|---|---|
| Blended gross margin vs disclosed | ties to 6 dp |
| GAAP operating margin vs disclosed | ties to 6 dp |
| S&M, SBC, contract-liability ratios vs disclosed | tie to 6 dp |
| RPO coverage vs disclosed | ties to 6 dp |
| ARR growth vs disclosed revenue growth | ties to 6 dp |
| FY1 revenue level vs disclosed | −4.76% (documented proxy error) |
| Workbook `Checks` sheet (13 checks) | all PASS |
| LibreOffice recalculation | 307 formulas, 0 errors |
| Independent Python oracles (ARR + RPO) | PASS |

## What would close the remaining 17 drivers

Not more effort against the same source — the data is not in XBRL. Closing
them requires a different source tier:

- **ARR, NRR, GRR, churn, expansion**: Adobe's quarterly earnings
  materials and investor decks disclose Digital Media ARR narratively.
  Parsing those is a separate ingestion problem, not a modeling one.
- **Subscription vs services split**: the revenue disaggregation note in
  the 10-K, which is tabular HTML rather than tagged facts.
- **Current portion of RPO**: disclosed as narrative text in the revenue
  note ("approximately X% expected to be recognised within twelve months"),
  not tagged.
- **Cash taxes paid**: supplemental cash-flow disclosure.

Until those exist as recorded snapshots, these cells stay drivers. That is
the correct state, not a gap to paper over.
