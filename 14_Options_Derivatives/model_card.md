# Model Card: Options & Derivatives

## Identity

- Model ID: 14
- Domain: Options & Derivatives
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: trading_intraday

## Intended use

### Approved uses

- European and American option valuation
- Implied-volatility and Greek analysis
- Portfolio scenario P&L
- Model-versus-market diagnostic review

### Prohibited or unsupported uses

- Exotic path-dependent valuation
- Production market making without live surface and execution systems
- Use outside documented day-count/dividend conventions

## Scope and methodology

- Canonical workbook: `14_Options_Derivatives/_template_OPTIONS.xlsx`
- Reproducible builder: `tools/builders/build_options_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `trading_intraday`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `14_Options_Derivatives/sources/source_register.csv`
- Frozen snapshots: `14_Options_Derivatives/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `black_scholes` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `implied_volatility` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `american_option` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `volatility_surface` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `portfolio_greeks` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `scenario_pnl` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `strategy_payoff` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| trader | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| market_maker | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| portfolio_manager | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Surface is illustrative rather than exchange-calibrated
- No stochastic volatility or jump diffusion
- Discrete dividends require explicit adjustment

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| put_call_parity_residual | 0.01 | 0.05 | Block valuation release |
| implied_vol_solver_residual | 0.0001 | 0.001 | Escalate solver and quote quality |
| model_market_price_error_pct | 0.05 | 0.15 | Review surface, dividends, borrow, and microstructure |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `14_Options_Derivatives/validation.md`
- Stakeholder sign-off: `14_Options_Derivatives/governance/signoff.json`
- Lifecycle record: `14_Options_Derivatives/governance/lifecycle.json`
- Retirement trigger: Pricing model is replaced or product scope becomes exotic
