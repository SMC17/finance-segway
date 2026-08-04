# Model Card: Insurance & Actuarial

## Identity

- Model ID: 18
- Domain: Insurance & Actuarial
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

- Reserve-method comparison
- Underwriting profitability and combined-ratio analysis
- Embedded-value and capital stress
- Management and rating-agency challenge

### Prohibited or unsupported uses

- Signed actuarial opinion
- Statutory filing
- Line-level pricing without granular exposure and claims data

## Scope and methodology

- Canonical workbook: `18_Insurance_Actuarial/_template_INSURANCE.xlsx`
- Reproducible builder: `tools/builders/build_insurance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `long_term_30y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `18_Insurance_Actuarial/sources/source_register.csv`
- Frozen snapshots: `18_Insurance_Actuarial/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `paid_triangle` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `chain_ladder` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `bornhuetter_ferguson` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `underwriting` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `embedded_value` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `capital_requirement` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `stress_testing` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| actuary | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| underwriter | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| management | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| regulator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public filings do not provide a complete statutory triangle
- Tail factors and prior expectations require actuarial ownership
- Capital aggregation is simplified

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| reserve_development_pct | 0.05 | 0.1 | Re-estimate development factors and BF prior |
| combined_ratio | 0.98 | 1.05 | Escalate underwriting and pricing remediation |
| capital_coverage_ratio | 1.5 | 1.2 | Escalate capital plan and dividend constraints |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `18_Insurance_Actuarial/validation.md`
- Stakeholder sign-off: `18_Insurance_Actuarial/governance/signoff.json`
- Lifecycle record: `18_Insurance_Actuarial/governance/lifecycle.json`
- Retirement trigger: Statutory data architecture or reserving methodology is replaced
