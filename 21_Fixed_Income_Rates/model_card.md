# Model Card: Fixed Income & Rates

## Identity

- Model ID: 21
- Domain: Fixed Income & Rates
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: trading_daily

## Intended use

### Approved uses

- Bond and portfolio valuation
- Duration, convexity, and key-rate risk
- Carry/roll and curve scenario analysis
- Rates P&L explain

### Prohibited or unsupported uses

- Complex callable/putable valuation
- Regulatory IRRBB submission
- Use without instrument-specific conventions and accrued interest

## Scope and methodology

- Canonical workbook: `21_Fixed_Income_Rates/_template_FIXED_INCOME.xlsx`
- Reproducible builder: `tools/builders/build_fixed_income_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `trading_daily`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `21_Fixed_Income_Rates/sources/source_register.csv`
- Frozen snapshots: `21_Fixed_Income_Rates/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `zero_curve` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `bond_pricing` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `duration` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `convexity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `key_rate_dv01` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `carry_roll` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `curve_scenarios` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `pnl_explain` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| trader | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| portfolio_manager | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| treasury | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Curve is deterministic
- No OAS or embedded-option lattice
- Credit spread and default are simplified

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| price_oracle_residual | 0.0001 | 0.001 | Block valuation release |
| key_rate_reconciliation_pct | 0.02 | 0.05 | Review curve mapping and interpolation |
| pnl_explain_unexplained_pct | 0.1 | 0.2 | Escalate model and market-data review |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `21_Fixed_Income_Rates/validation.md`
- Stakeholder sign-off: `21_Fixed_Income_Rates/governance/signoff.json`
- Lifecycle record: `21_Fixed_Income_Rates/governance/lifecycle.json`
- Retirement trigger: Instrument portfolio or curve methodology is replaced
