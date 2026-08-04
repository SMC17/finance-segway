# Model Card: Private Equity

## Identity

- Model ID: 03
- Domain: Private Equity
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: corporate_5y

## Intended use

### Approved uses

- Sponsor acquisition underwriting
- Debt-capacity and covenant analysis
- Investment-committee downside and reverse stress
- Management-equity and exit-waterfall analysis

### Prohibited or unsupported uses

- Fairness opinion
- Tax or legal advice
- Live bid without transaction diligence
- Financial-institution LBO without regulatory capital modules

## Scope and methodology

- Canonical workbook: `03_Private_Equity/_template_LBO.xlsx`
- Reproducible builder: `tools/builders/build_lbo_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `03_Private_Equity/sources/source_register.csv`
- Frozen snapshots: `03_Private_Equity/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `operating_model` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `sources_uses` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `working_capital` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `tax` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `revolver` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `multi_tranche_debt` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `pik` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cash_sweep` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `covenants` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `management_equity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `exit_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `sensitivity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| sponsor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| management | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lp_ic | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- No transaction-specific purchase accounting
- Tax shields and interest deductibility are simplified
- Working capital is modeled as a revenue ratio
- Debt documents and covenant definitions must be replaced with executed terms

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| revenue_forecast_error | 0.1 | 0.2 | Re-underwrite operating case and valuation |
| ebitda_margin_error_bps | 200 | 400 | Revalidate cost structure and covenant headroom |
| net_leverage_headroom | 0.5 | 0.0 | Escalate to IC and lender-remediation case |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `03_Private_Equity/validation.md`
- Stakeholder sign-off: `03_Private_Equity/governance/signoff.json`
- Lifecycle record: `03_Private_Equity/governance/lifecycle.json`
- Retirement trigger: Transaction closes, is abandoned, or the operating/debt architecture is superseded
