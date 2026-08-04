# Model Card: Debt Finance

## Identity

- Model ID: 06
- Domain: Debt Finance
- Version: 3.0.0-evidence
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

- Debt rollforward, maturity and refinancing diagnostics
- Weighted-cost and interest-coverage stress
- Historical investment-grade and emergency-financing comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `06_Debt_Finance/_template_CREDIT.xlsx`
- Reproducible builder: `tools/builders/build_debt_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `06_Debt_Finance/sources/source_register.csv`
- Frozen snapshots: `06_Debt_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `issuance` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `refinancing` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `maturity_ladder` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `interest_rate_risk` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `covenants` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `recovery_lgd` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| issuer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| arranger | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public debt balances aggregate secured, unsecured, fixed, floating and convertible instruments
- Maturity buckets and committed facilities require instrument-level confirmation
- Pricing, covenant and refinancing assumptions remain modeler-owned unless sourced

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| refinancing_gap | 0.0 | 1.0 | Escalate maturity, liquidity and capital-markets plan |
| interest_coverage | 2.5 | 2.0 | Re-underwrite earnings, rates and debt capacity |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `06_Debt_Finance/validation.md`
- Stakeholder sign-off: `06_Debt_Finance/governance/signoff.json`
- Lifecycle record: `06_Debt_Finance/governance/lifecycle.json`
- Retirement trigger: Debt structure, maturity schedule, liquidity or refinancing plan is superseded
