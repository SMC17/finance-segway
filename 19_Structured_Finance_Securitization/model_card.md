# Model Card: Structured Finance & Securitization

## Identity

- Model ID: 19
- Domain: Structured Finance & Securitization
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: long_term_30y

## Intended use

### Approved uses

- Collateral and tranche cash-flow analysis
- OC/IC trigger and waterfall stress
- WAL and loss sensitivity
- Investor/rating-agency challenge

### Prohibited or unsupported uses

- Rating issuance
- Legal interpretation of transaction documents
- Use without loan-level stratification for live capital

## Scope and methodology

- Canonical workbook: `19_Structured_Finance_Securitization/_template_SECURITIZATION.xlsx`
- Reproducible builder: `tools/builders/build_securitization_institutional.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `long_term_30y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `19_Structured_Finance_Securitization/sources/source_register.csv`
- Frozen snapshots: `19_Structured_Finance_Securitization/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `collateral_rollforward` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cpr_cdr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `recovery_lag` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `interest_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `principal_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `oc_ic_triggers` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `wal` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `sensitivity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| issuer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| servicer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| trustee | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public macro delinquency series is a proxy for collateral CDR
- No stochastic prepayment/default dependence
- Servicer advances and transaction-specific triggers require document implementation

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| collateral_loss_pct | 0.05 | 0.1 | Re-run tranche waterfall and rating stresses |
| oc_headroom_pct | 0.02 | 0.0 | Escalate diversion and payment-priority case |
| wal_extension_years | 1.0 | 2.0 | Reassess liquidity, price, and hedge |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `19_Structured_Finance_Securitization/validation.md`
- Stakeholder sign-off: `19_Structured_Finance_Securitization/governance/signoff.json`
- Lifecycle record: `19_Structured_Finance_Securitization/governance/lifecycle.json`
- Retirement trigger: Transaction pays down, terminates, or collateral model is replaced
