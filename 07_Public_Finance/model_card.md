# Model Card: Public Finance

## Identity

- Model ID: 07
- Domain: Public Finance
- Version: 3.0.0-evidence
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

- Debt-sustainability and primary-balance diagnostics
- Debt-service and reserve-coverage stress
- Historical sovereign reform and distress comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `07_Public_Finance/_template_PUBLIC_FINANCE.xlsx`
- Reproducible builder: `tools/builders/build_public_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `long_term_30y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `07_Public_Finance/sources/source_register.csv`
- Frozen snapshots: `07_Public_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `sovereign_dsa` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `revenue_expenditure` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `debt_service` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `reserves` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `dscr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `pension_burden` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `scenario_analysis` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| issuer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| taxpayer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| dfi | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Sovereign ratios are simplified into a static fiscal-debt model
- Nominal interest, growth and debt-service paths require country-specific debt-stock detail
- IMF program projections are conditional scenarios rather than guarantees

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| projected_debt_ratio | 0.9 | 1.0 | Escalate fiscal, financing and debt-treatment analysis |
| primary_balance_gap | 0.0 | -0.02 | Re-underwrite revenue, expenditure and financing assumptions |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `07_Public_Finance/validation.md`
- Stakeholder sign-off: `07_Public_Finance/governance/signoff.json`
- Lifecycle record: `07_Public_Finance/governance/lifecycle.json`
- Retirement trigger: Fiscal framework, debt treatment, program assumptions or reporting basis changes materially
