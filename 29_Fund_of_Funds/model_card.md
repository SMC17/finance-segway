# Model Card: Fund of Funds

## Identity

- Model ID: 29
- Domain: Fund of Funds
- Archetype: FOF
- Version: 1.0.0
- As-of date: 2026-08-05
- Owner: SMC17 / repository owner
- Developer: Claude Code
- Independent validator: workbook-contract and LibreOffice recalculation checks (see Checks sheet); no independent-oracle coverage yet
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: **M2** (one real, sourced, LibreOffice-recalculated public case — see "Real public case" below)
- Intended horizon: long_term_10y

## Intended use

### Approved uses

- Look-through portfolio review of a fund-of-funds' underlying fund positions
- FoF-level NAV roll-forward and fee-layering ("fees on fees") analysis
- Diversification and single-fund concentration screening
- Historical public-vehicle comparison (once a real instance exists)

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating a populated instance as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `29_Fund_of_Funds/_template_FOF.xlsx`
- Reproducible builder: `tools/builders/build_fund_of_funds_institutional.py`
- Methodology: standard private-markets fund accounting (NAV roll-forward: beginning NAV + capital called − distributions − fees +/− realized/unrealized gain = ending NAV) applied at two layers — the underlying-fund ("look-through") layer and the FoF's own layer to its LPs — with the spread between look-through gross TVPI and FoF net TVPI reported explicitly as fee-layering drag.
- Time-step and timeline: `long_term_10y`, modeled as a single-period snapshot (most recent reporting period) rather than a full multi-year cash-flow simulation — matches how a real FoF's own quarterly/annual LP report is structured (a portfolio table plus one period's cash-flow roll-forward), not a forecast.
- Public cases: 1 — `fof-public-hlpaf-2026` (Hamilton Lane Private Assets Fund). See "Real public case" below.

## Real public case

A prior session attempted to source a real case from closed-end, London-listed vehicles (HarbourVest Global Private Equity, Pantheon International) via HVPE's own factsheet PDF and the UK FCA's National Storage Mechanism filing archive; both returned HTTP 403 and that attempt was documented rather than papered over.

This case instead uses **Hamilton Lane Private Assets Fund (HLPAF)**, CIK 0001803491 — a real, SEC-registered (1940 Act) non-traded interval fund investing across direct PE/credit positions and secondary fund-of-funds stakes, sourced from its N-CSR (accession 0001213900-26-066804, filed 2026-06-09, period ended 2026-03-31) via SEC EDGAR, the same filing type already used successfully elsewhere in this repo (ETF domain's KWEB case, Software domain's UiPath case).

What's real: the top 8 (of 159 disclosed) secondary-fund positions by fair value, each with real cost and fair value extracted programmatically from the Consolidated Schedule of Investments; FoF-level beginning/ending NAV, this-year realized and unrealized gain, this-year distributions, this-year net capital-share transactions, and paid-in capital, all from the Consolidated Statements of Changes in Net Assets.

What's not disclosed, and not invented: per-position Commitment/Called/Distributed history — a secondaries buyer reports only its own cost and fair value, not the original LP's commitment schedule — so Cost substitutes for both Commitment and Called (defensible: cost is what HLPAF itself paid), and per-position Distributed stays 0, a real, stated gap. Per-position vintage year is not disclosed either; HLPAF's own acquisition date is used as a labeled proxy, not a claim about the underlying fund's actual vintage. Cumulative "distributions to date" sums only the two most recently disclosed fiscal years, not a full since-inception figure. FoF management fee, carried interest, and hurdle stay at this template's own illustrative defaults — HLPAF's real fee structure (management fee + incentive fee + per-class distribution fees, applied across three share classes) does not map onto this template's simplified two-line fee model.

That mismatch shows up honestly in the Checks sheet: **NAV roll-forward reconciles = FAIL** (Overall: BREACH), with a computed-vs-reported ending-NAV residual of roughly $77.8mm (~1.3% of ending NAV) — the simplified fee model applied to a real, complex multi-share-class fund's real gross investment gains does not reproduce the real reported ending NAV exactly. That is the correct, informative signal for this case, not a modeling bug — the same "honest imperfection" pattern already established elsewhere in this repo's evidence registry (Private Credit's Yellow Corp REVIEW, ETF's KWEB sector-band REVIEW).

## Inputs and sources

- Source register: `29_Fund_of_Funds/sources/source_register.csv` — one real entry, `fof-public-hlpaf-2026`
- Frozen snapshots: `29_Fund_of_Funds/sources/snapshots/fof-public-hlpaf-2026.json`
- Input classes: observed, derived, or modeler-owned assumption (same three-way convention used across the repo).
- Underlying-fund portfolio table (`Underlying Fund Portfolio` sheet): commitment, called, distributed, and NAV are intended to be observed, per-fund figures from GP capital account statements; gross TVPI is derived.
- FoF-level roll-forward (`NAV Rollforward & Fee Layering` sheet): beginning NAV, period calls/distributions, realized/unrealized gain, and reported ending NAV are intended to be observed from the FoF's own administrator NAV package; FoF management fee and carry are derived from the LPA's stated rates.

## Material assumptions

| Assumption | Base | Downside | Owner | Evidence | Review trigger |
|---|---:|---:|---|---|---|
| FoF management fee (% of commitments, p.a.) | 0.75% | 0.75% | Modeler (illustrative) | LPA fee letter, once sourced | Fee-letter amendment |
| FoF carried interest (% of profit above hurdle) | 5% | 5% | Modeler (illustrative) | LPA, once sourced | LPA amendment |
| FoF preferred return / hurdle | 8% | 8% | Modeler (illustrative) | LPA, once sourced | LPA amendment |
| Underlying-fund NAV markdown (stress) | 0% | 25% | Modeler | Comparable public-market stress episodes | New stress scenario approved |
| Maximum single-fund concentration limit | 20% of NAV | 20% of NAV | Modeler (illustrative) | Investment policy, once sourced | Policy amendment |

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `look_through_portfolio` | `Underlying Fund Portfolio` | Implemented | Concentration and called-capital checks |
| `nav_rollforward` | `NAV Rollforward & Fee Layering` | Implemented | Reconciliation-residual check (computed vs. reported ending NAV) |
| `fee_layering` | `NAV Rollforward & Fee Layering`, `Performance & Multiples` | Implemented | Fee-layering-drag-nonnegative check |
| `fund_multiples` | `Performance & Multiples` | Implemented | TVPI = DPI + RVPI identity check |
| `concentration` | `Underlying Fund Portfolio`, `Checks` | Implemented | Single-fund concentration check |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Key conflicts or reconciliations |
|---|---|---|
| fof_gp | Fee income (management fee + carry), AUM growth, LP relationship | Fee-layering drag directly reduces what fof_lp receives — visible tension with fof_gp's own economics |
| underlying_lp | Look-through gross TVPI, DPI, RVPI at the underlying-fund level | Underlying_lp's return is what fof_lp receives before the FoF's own fee layer |
| fof_lp | Net TVPI, DPI, RVPI after both fee layers; diversification and concentration risk | The FoF's value proposition (access, diversification, manager selection) must be weighed against the fee-layering drag it imposes |

## Outputs and decisions

- Primary outputs: FoF net TVPI/DPI/RVPI to LPs; look-through gross TVPI; fee-layering drag (multiple and dollar terms); single-fund concentration.
- Decision thresholds: fee-layering drag must be nonnegative (a negative reading indicates a modeling or data-consistency error, not a real FoF economic outcome); single-fund concentration must not exceed the policy limit.
- Liquidity outputs: none yet — a future extension could add uncalled-commitment and capital-call-pacing analysis.

## Checks and controls

- NAV roll-forward reconciles: computed ending NAV (built forward from independently-sourced beginning NAV, period cash flows, fees, and realized/unrealized gain) is checked against a separately-reported ending NAV, not solved backward as a plug — mirrors the pattern used to fix a real defect in the BlackRock AUM-rollforward case elsewhere in this repo's evidence registry.
- TVPI = DPI + RVPI identity, at the FoF-net level.
- Fee-layering drag (look-through gross TVPI − FoF net TVPI) must be nonnegative.
- Single-fund concentration must not exceed the policy limit.
- Portfolio-level and FoF-level called capital must each stay within their respective commitment ceilings.
- External workbook links and literal Excel errors are prohibited (enforced by `tools/validate_model_inventory.py`).

## Limitations and failure modes

- The one real public case (`fof-public-hlpaf-2026`) trips the NAV roll-forward reconciliation check (FAIL / Overall: BREACH) — a real, honest residual from applying this template's simplified two-line fee model to a real fund's actual multi-share-class fee structure, not a data error. See "Real public case" above.
- Single-period snapshot, not a multi-year cash-flow simulation — a genuine capital-call/distribution J-curve projection is future work.
- The Base/Downside scenario toggle only stresses the underlying-fund portfolio's marked NAV; it does not re-derive the FoF-level roll-forward's own reported figures under stress, since those are meant to be actual observed data, not a scenario lever. Under Downside, this can — correctly — trip the fee-layering-drag check, signaling that a hypothetical markdown hasn't yet flowed through to the FoF's own reported NAV. That is an intentional, honest signal, not a bug, but should be understood before treating a Downside BREACH as equivalent to a Base-case one.
- FoF carried interest is modeled with a simplified hurdle-then-carry calculation (no catch-up tranche) — a real LPA's waterfall may differ.

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| nav_rollforward_residual | 0.01 | 0.05 | Reconcile sourced cash flows, fees, and gain/loss against the FoF's reported ending NAV |
| single_fund_concentration | 0.15 | 0.20 | Escalate diversification review before further commitments to that GP |

## Release record

- Active release: 1.0.0
- Rollback release: none yet (initial release)
- Validation record: `29_Fund_of_Funds/validation.md`
- Stakeholder sign-off: pending
- Retirement trigger: Fee structure, waterfall methodology, or look-through reporting convention is superseded
