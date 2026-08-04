# Model Card: Equity Finance

## Identity

- Model ID: 12
- Domain: Equity Finance
- Version: 2.2.0-evidence
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

- Primary issuance, rights, convert and dilution analysis
- Ownership and proceeds reconciliation
- Historical financing-structure comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `12_Equity_Finance/_template_BASE.xlsx`
- Reproducible builder: `tools/builders/build_equity_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `12_Equity_Finance/sources/source_register.csv`
- Frozen snapshots: `12_Equity_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `three_statement` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cap_table` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `dilution` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `rights_issuance` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `convertibles` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `valuation` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| issuer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| shareholder | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| advisor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- A public underwritten offering is used as a primary-issuance proxy rather than a literal rights offering
- Anti-dilution, registration and voting terms require executed documents
- Market impact and investor allocation are not observed from offering proceeds alone

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| fully_diluted_ownership_change | 0.1 | 0.25 | Escalate dilution attribution and shareholder protections |
| proceeds_reconciliation_residual | 0.01 | 0.05 | Reconcile gross proceeds, fees and balance-sheet receipt |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `12_Equity_Finance/validation.md`
- Stakeholder sign-off: `12_Equity_Finance/governance/signoff.json`
- Lifecycle record: `12_Equity_Finance/governance/lifecycle.json`
- Retirement trigger: Capital structure, security terms, or ownership architecture is superseded
