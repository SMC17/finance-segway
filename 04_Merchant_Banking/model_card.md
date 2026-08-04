# Model Card: Merchant Banking

## Identity

- Model ID: 04
- Domain: Merchant Banking
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

- Principal-investment underwriting
- Holdco/opco capital-structure analysis
- Long-duration ownership and add-on analysis
- Investment-committee scenario comparison

### Prohibited or unsupported uses

- Regulated-bank capital planning
- Transaction opinion work
- Use without legal review of structural subordination

## Scope and methodology

- Canonical workbook: `04_Merchant_Banking/_template_LBO.xlsx`
- Reproducible builder: `tools/builders/build_lbo_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `04_Merchant_Banking/sources/source_register.csv`
- Frozen snapshots: `04_Merchant_Banking/sources/snapshots/`
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
| principal | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| management | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investment_committee | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Holdco leakage and restricted-payment baskets require deal-specific documents
- No consolidated tax-sharing agreement model
- No minority-governance or bespoke preferred-equity legal terms

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| holdco_interest_coverage | 1.5 | 1.0 | Suspend distributions and run liquidity remediation |
| structural_subordination_ratio | 0.35 | 0.5 | Escalate to IC and legal counsel |
| exit_multiple_dependency | 0.4 | 0.6 | Require returns case with no multiple expansion |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `04_Merchant_Banking/validation.md`
- Stakeholder sign-off: `04_Merchant_Banking/governance/signoff.json`
- Lifecycle record: `04_Merchant_Banking/governance/lifecycle.json`
- Retirement trigger: Investment exits or legal/capital structure is superseded
