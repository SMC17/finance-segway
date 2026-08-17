# Model Card: ETF Construction & Management

## Identity

- Model ID: 30
- Domain: ETF Construction & Management
- Archetype: ETF
- Version: 1.0.0
- As-of date: 2026-08-17
- Owner: SMC17 / repository owner
- Developer: Claude Code
- Independent validator: workbook-contract and LibreOffice recalculation checks (see Checks sheet); no independent-oracle coverage yet
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: **M2** (integrated mechanics, two real sourced public instances -- conventional and adversarial -- independent reference checks, clear decision outputs)
- Intended horizon: perpetual (open-end, exchange-traded fund)

## Intended use

### Approved uses

- Look-through portfolio review of an ETF's disclosed holdings and sector allocation
- Creation-unit basket economics and authorized-participant (AP) arbitrage sizing
- Fund-return-vs.-benchmark tracking-difference decomposition (expense drag, securities-lending offset, cash drag, sampling/optimization error)
- Historical public-vehicle comparison using a fund's own disclosed profile data

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions (creation unit size, securities-lending revenue, cash drag, sampling error) as disclosed prospectus facts
- Treating the market-price NAV proxy as the fund's own officially calculated NAV -- real intraday differences exist and are not captured here

## Scope and methodology

- Canonical workbook: `30_ETF_Construction_Management/_template_ETF.xlsx`
- Reproducible builder: `tools/builders/build_etf_construction_institutional.py`
- Methodology: standard open-end ETF mechanics -- (1) look-through portfolio construction from disclosed holdings and sector weights; (2) creation-unit basket valuation and AP arbitrage-profit sizing at a given premium/discount to NAV; (3) a fund-return-vs.-benchmark tracking-difference bridge (expense ratio drag, securities-lending revenue offset, cash-drag cost, sampling/optimization tracking error).
- Time-step and timeline: `perpetual`, modeled as a single-period snapshot (most recent disclosed holdings and price) rather than a multi-year simulation -- matches how an ETF issuer's own fact sheet and holdings disclosure are structured.
- Public cases: two real instances -- `etf-public-qqq-2026` (conventional/Base, Invesco QQQ Trust) and `etf-public-kweb-2026-stress` (adversarial/Downside, KraneShares CSI China Internet ETF -- a real, sourced instance of the "concentrated ETF under real disclosed stress" case this card's earlier draft called out as future work).

## Inputs and sources

- Source register: `30_ETF_Construction_Management/sources/source_register.csv`
- Frozen snapshot: `30_ETF_Construction_Management/sources/snapshots/etf-public-qqq-2026.json`
- Raw recorded evidence: `tools/data_fabric/out/QQQ_alphavantage_etf_profile.json`, `tools/data_fabric/out/QQQ_alphavantage_global_quote.json`
- Input classes: observed, derived, or modeler-owned assumption (same three-way convention used across the repo).

### What's real in `etf-public-qqq-2026`

| Input | Value | Source |
|---|---:|---|
| Fund net assets (AUM) | $490,100mm | Invesco QQQ Trust ETF profile (Alpha Vantage), 2026-08-06 |
| Net expense ratio | 0.18% | Same |
| Trailing 12-month dividend yield | 0.43% | Same |
| Market price (last close) | $717.30 | Alpha Vantage `GLOBAL_QUOTE`, 2026-08-05 |
| Top 30 holdings by weight (of 105 disclosed) | 74.95% of AUM | Same fund profile source |
| All 11 disclosed sector weights | sum to 96.7% (real; the remainder reflects cash, futures, and unclassified positions the fund itself discloses separately) | Same |

### What's illustrative (template defaults, not overridden with real data)

- Standard creation unit size (50,000 shares) -- a typical large-cap equity ETF creation unit size, not verified against QQQ's own prospectus/SAI in this pass (no EDGAR/prospectus access in this session's network environment)
- Current premium/discount to NAV (0.0%) -- assumes a well-arbitraged, highly liquid fund; the real fund's own officially calculated daily NAV was not available through this session's data sources, only market price
- Securities-lending revenue offset, cash-drag cost, sampling/optimization tracking error -- typical-range estimates, not the fund's own disclosed realized tracking-difference statistics (which require a full-year return-vs.-benchmark comparison this session did not source)

## Material assumptions

| Assumption | Base | Downside | Owner | Evidence | Review trigger |
|---|---:|---:|---|---|---|
| Standard creation unit size | 50,000 shares | 50,000 shares | Modeler (illustrative) | Prospectus/SAI, once sourced | Prospectus amendment |
| Current premium/(discount) to NAV | 0.00% | (0.25%) | Modeler (illustrative) | Daily NAV vs. market price, once sourced | New stress scenario approved |
| Securities-lending revenue offset | 0.02% p.a. | 0.01% p.a. | Modeler (illustrative) | Fund annual report securities-lending disclosure, once sourced | Annual report update |
| Cash-drag cost | 0.02% p.a. | 0.08% p.a. | Modeler (illustrative) | Realized tracking-difference statement, once sourced | Annual report update |
| Sampling/optimization tracking error | 0.10% p.a. | 0.50% p.a. | Modeler (illustrative) | Realized tracking-difference statement, once sourced | Annual report update |
| AP arbitrage action threshold | 0.10% | 0.25% | Modeler (illustrative) | Typical bid-ask/arbitrage literature | Market-structure change |

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `portfolio_construction` | `Portfolio Construction` | Implemented, real instance | Holdings-weight and sector-weight reconciliation checks against real disclosed data |
| `creation_redemption_mechanics` | `Creation & Redemption` | Implemented | Creation-unit-basket-positive check; AP arbitrage-profit sizing |
| `tracking_error_decomposition` | `Tracking Error & Costs` | Implemented | Net-tracking-difference plausible-band check |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Key conflicts or reconciliations |
|---|---|---|
| etf_issuer | Expense-ratio fee revenue, AUM growth, tracking-difference reputation | Tighter tracking (lower sampling error, higher securities-lending revenue passthrough) competes with fee revenue economics |
| authorized_participant | Creation-unit basket value, arbitrage profit at a given premium/discount, in-kind vs. cash creation costs | AP profit only exists once the premium/discount exceeds the action threshold -- otherwise no economic incentive to arbitrage |
| etf_investor | Net tracking difference (after all costs), premium/discount paid at execution, holdings/sector concentration | The investor bears the full tracking-difference bridge, not just the headline expense ratio |

## Outputs and decisions

- Primary outputs: net tracking difference (fund return vs. benchmark return); creation-unit basket value and AP arbitrage-profit sizing; holdings and sector concentration.
- Decision thresholds: net tracking difference should sit within a plausible band; AP arbitrage-profit sizing signals whether the current premium/discount is expected to persist or compress.
- Liquidity outputs: none yet -- a future extension could add bid-ask spread cost and average daily volume relative to creation-unit size.

## Checks and controls

- Holdings weights (shown + aggregated remainder) sum to ~100%.
- Disclosed sector weights sum within a plausible band (90%-101%) -- a genuine, non-tautological check against real disclosed data, which for QQQ sums to 96.7% (not exactly 100%, since cash and futures positions are excluded from the sector table but included in holdings).
- Implied shares outstanding (AUM / market price) is positive.
- Creation unit basket value is positive.
- Net expense ratio is nonnegative and below 3%.
- Net estimated tracking difference sits within a plausible band (-2% to +0.5%).
- External workbook links and literal Excel errors are prohibited (enforced by `tools/validate_model_inventory.py`).

## Limitations and failure modes

- `etf-public-kweb-2026-stress`'s sector table (sourced from the fund's own N-CSR) sums to 102.6%, outside the workbook's own 90%-101% plausible band -- a real, disclosed artifact (securities-lending collateral appears to double-count against a sector bucket), not a sourcing error in this case. It correctly resolves the Checks sheet's sector-weight check to REVIEW rather than PASS; that is the expected, honest outcome for an adversarial case, exactly like the Private Credit domain's Yellow Corp REVIEW on covenant breach.
- KWEB's realized outcome (5-year average annual total return) is a total-return figure the fund itself discloses, not an independently computed peak-to-trough price drawdown -- the free-tier market-data source used elsewhere in this repo only serves ~100 days of price history, insufficient to reach the 2021 peak.
- Market price used as a NAV proxy, not the fund's own officially calculated daily NAV -- real (typically small) differences exist for a liquid ETF like QQQ and are not captured.
- Creation unit size, securities-lending revenue, cash drag, and sampling error remain illustrative -- see "What's illustrative" above. A future pass with prospectus/SAI and annual-report access could source these for real.
- Single-period snapshot, not a time-series tracking-difference backtest against the fund's actual realized return history.

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| net_tracking_difference | -1.0% | -2.0% | Reconcile expense ratio, securities-lending revenue, cash drag, and sampling error against the fund's own disclosed tracking-difference statistics |
| premium_discount_to_nav | 0.25% | 0.50% | Escalate authorized-participant arbitrage review; confirm creation/redemption activity is functioning normally |

## Release record

- Active release: 1.0.0
- Rollback release: none yet (initial release)
- Validation record: `30_ETF_Construction_Management/validation.md`
- Stakeholder sign-off: pending
- Retirement trigger: Creation/redemption mechanics, tracking-cost decomposition methodology, or index-replication convention is superseded
