# Institutional Depth Blueprint

The repository currently has a stronger maintenance and verification system than it has production-depth underwriting models. This blueprint turns that gap into an explicit engineering program.

## Architecture: eight layers

Every M3 archetype should separate the following layers.

1. **Sources and raw inputs**  
   Dated sources, units, currencies, conventions, provenance, and transformation notes.

2. **Assumptions and scenarios**  
   Base, downside, upside, break-even, and reverse-stress cases with named owners.

3. **Domain engine**  
   The mechanics unique to the domain: operating model, option pricer, loss triangle, collateral waterfall, token supply schedule, or portfolio backtest.

4. **Financing and capital structure**  
   Debt, equity, taxes, reserves, fees, covenants, liquidity, dilution, or margin.

5. **Stakeholder lenses**  
   Sponsor, lender, rating agency, LP/IC, regulator, counterparty, taxpayer, operator, or servicer views.

6. **Decision outputs**  
   Valuation, return, coverage, loss, liquidity, risk, break-even, and recommendation-relevant outputs.

7. **Checks and reconciliation**  
   Conservation identities, accounting ties, limit tests, trigger tests, monotonicity, and error flags.

8. **Validation and monitoring**  
   Independent benchmarks, stress behavior, outcome analysis, source freshness, and model-performance thresholds.

## Shared composable engines

The 24 folders should not become 24 isolated codebases. Builders should increasingly depend on shared engines:

- timeline and calendar conventions
- source registry and dated snapshots
- scenario manager
- three-statement model
- working-capital schedule
- tax schedule
- debt instruments and cash sweep
- covenant and coverage engine
- cash-flow waterfall
- yield curve and discounting
- valuation and returns
- portfolio and factor risk
- recovery and loss-given-default
- sensitivity and reverse stress
- model checks and release metadata

A domain builder should compose these engines and add only domain-specific mechanics.

## Flagship sequence

The next phase should create six reference-grade flagships, not lightly expand all domains at once.

### 1. Private Equity / Merchant Banking

Target: full sponsor underwriting model.

Required depth:

- multi-year integrated operating model
- revenue and margin drivers
- working capital and capex
- tax schedule and interest deductibility limits
- multiple debt tranches, PIK, revolver, mandatory amortization, and cash sweep
- covenant headroom
- management equity and option pool
- dividend recap and add-on acquisition cases
- exit waterfall and multiple return definitions
- lender and management views
- Base, Downside, Severe Downside, and reverse-stress cases

### 2. Private Credit / Debt Finance

Target: lender underwriting and instrument structuring system.

Required depth:

- operating case and CFADS
- liquidity runway and borrowing-base or availability mechanics where relevant
- cash and PIK interest
- amortization, sweep, maturity wall, and refinancing
- leverage, fixed-charge coverage, interest coverage, and DSCR
- covenant cures and baskets
- OID, fees, spread, IRR, and duration
- collateral and enterprise-value recovery
- recovery waterfall and LGD
- rating-agency and restructuring views

### 3. Options / Fixed Income / Rates

Target: coherent market-risk and valuation stack.

Required depth:

- European and American options
- implied volatility solver
- full first- and selected higher-order Greeks
- discrete dividends and futures options
- volatility smile/surface representation
- strategy and portfolio aggregation
- bond cash-flow engine
- curve bootstrapping
- key-rate duration, convexity, carry, and rolldown
- spread and default scenarios
- P&L explain and limit monitoring
- independent Python and eventually Zig implementations

### 4. Project Finance / Infrastructure

Target: 20–40 year lender-grade project model.

Required depth:

- monthly construction timeline
- drawdown and interest during construction
- contingency and cost-overrun cases
- commissioning and ramp-up
- operating revenues and costs
- CFADS
- debt sculpting
- DSCR, LLCR, and PLCR
- reserve accounts and cash waterfall
- refinancing and distribution lock-up
- offtake, merchant tail, and curtailment cases
- risk-allocation matrix
- blended-finance concessionality and additionality
- sponsor, lender, government, and DFI lenses

### 5. Structured Finance / Insurance

Target: cash-flow and loss-distribution engines.

Structured finance:

- collateral-level or cohort cash flows
- CPR, CDR, severity, recovery lag
- sequential and pro-rata waterfalls
- triggers, reserve accounts, and credit enhancement
- tranche WAL, yield, loss, and rating stresses
- servicer and investor views

Insurance:

- loss development triangles
- chain-ladder and Bornhuetter-Ferguson
- reserve ranges and adverse development
- premium, acquisition cost, and expense models
- reinsurance layers
- capital and solvency
- embedded value
- catastrophe and tail scenarios

### 6. Quantitative / Systematic / Risk

Target: a backtest and live-risk specification rather than a returns calculator.

Required depth:

- immutable source data and point-in-time joins
- survivorship and look-ahead controls
- train/validation/test and walk-forward design
- transaction costs, market impact, slippage, and borrow
- capacity and crowding
- portfolio construction and constraints
- factor and scenario risk
- drawdown and tail metrics
- benchmark and placebo tests
- regime analysis
- backtest-to-live performance monitoring
- reproducible run manifests

## Domain completion matrix

Every domain’s target engine set is machine-readable in `standards/model_inventory.json`. Promotion should be based on evidence, not a blanket “Built” label.

The matrix deliberately includes perspectives that are often omitted:

- Corporate and LBO models add lender, rating-agency, and management views.
- Project and public finance add government, taxpayer, and DFI views.
- Securitization adds servicer and rating-agency views.
- Trading models add risk, clearing, treasury, and operations views.
- Venture and asset-management models add LP and portfolio-reserve views.

## Real-instance program

A blank template cannot prove maintainability. Each flagship must receive at least two public, reproducible instances.

Each instance should include:

- a frozen as-of date
- public source register
- raw source snapshot or checksum
- assumptions with owner and rationale
- initial thesis
- Base and Downside cases
- completed validation
- at least three material RefreshLog entries over time
- outcome comparison after a relevant event

Suggested instance design:

- **LBO:** one stable cash-generative company and one cyclical or stressed company
- **Credit:** one performing borrower and one stressed capital structure
- **Options/rates:** one equity-volatility event and one rates-curve regime
- **Project finance:** one contracted asset and one merchant-exposure asset
- **Insurance/structured:** one benign vintage and one adverse-loss vintage
- **Quant:** one liquid strategy and one capacity-constrained strategy

Instances should use only public information and must not imply investment advice.

## Multi-horizon support

The architecture must support different clocks:

- intraday or daily trading
- 13-week liquidity
- one-year working-capital and trade-finance cycles
- 5–10 year corporate, LBO, and venture models
- 20–40 year project, public-finance, insurance, and securitization models
- perpetual endowment, pension, SWF, and asset-management models

Timeline conventions belong in a shared engine. Long-horizon models should allow a detailed near term and a coarser terminal period without breaking auditability.

## Total-portfolio layer

Canadian pension and endowment practice suggests a layer above individual deals:

- reference portfolio
- total-fund risk budget
- liquidity budget
- currency and leverage exposure
- factor and economic-regime exposure
- pacing and commitment model
- private-market cash-flow forecasting
- concentration and look-through exposure
- denominator-effect stress
- strategic allocation versus implementation value-add

This should become a new cross-domain portfolio module rather than another disconnected folder.

## Global and development-finance layer

Project, public, trade, and microfinance models should share:

- additionality test
- minimum concessionality calculation
- crowding-in / mobilization
- local-currency and convertibility risk
- political and regulatory risk
- environmental and social risk register
- guarantee and first-loss structures
- economic versus financial return
- distributional and affordability outputs

This adds a genuine DFI lens rather than an ESG label.

## Promotion order

1. Make the inventory and maturity validator mandatory.
2. Reconcile the credit and public-finance institutional builders.
3. Promote LBO, Options, Fixed Income, Credit, and Project Finance to M2 with independent tests.
4. Build two public instances for each flagship.
5. Promote the first two models to M3 only after independent validation.
6. Add the total-portfolio and development-finance shared layers.
7. Expand the remaining domains by reusing the shared engines.

The bar is not “more tabs.” The bar is a model that a skeptical third party can understand, challenge, reproduce, and continue to maintain.
