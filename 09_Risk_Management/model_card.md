# Model Card: Risk Management

## Identity

- Model ID: 09
- Domain: Risk Management
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

- Daily multi-asset risk aggregation
- Limit monitoring
- Factor and stress contribution analysis
- Liquidity-adjusted risk review

### Prohibited or unsupported uses

- Regulatory capital submission
- Counterparty exposure replacement
- Use with stale positions or unvalidated covariance inputs

## Scope and methodology

- Canonical workbook: `09_Risk_Management/_template_RISK.xlsx`
- Reproducible builder: `tools/builders/build_risk_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `trading_daily`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `09_Risk_Management/sources/source_register.csv`
- Frozen snapshots: `09_Risk_Management/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `position_inventory` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `factor_covariance` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `factor_euler_var` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `position_component_var` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `var` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `expected_shortfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `stress_testing` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidity_risk` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `pnl_explain` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `limit_monitoring` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| trader | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| management | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| regulator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Factor model omits nonlinear path dependence beyond supplied Greeks
- Correlations are scenario inputs rather than estimated dynamically
- Liquidity loss is a simplified impact model

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| var_backtest_exceptions_250d | 4 | 7 | Recalibrate volatility/correlation and escalate limits |
| component_var_reconciliation_abs | 0.01 | 0.05 | Block release and investigate factor mapping |
| liquidity_days_to_exit | 10 | 20 | Escalate concentration and liquidation plan |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `09_Risk_Management/validation.md`
- Stakeholder sign-off: `09_Risk_Management/governance/signoff.json`
- Lifecycle record: `09_Risk_Management/governance/lifecycle.json`
- Retirement trigger: Risk-factor taxonomy or position system is replaced
