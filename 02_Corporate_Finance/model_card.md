# Model Card: Corporate Finance

## Identity

- Model ID: 02
- Domain: Corporate Finance
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

- Treasury, liquidity and capital-allocation diagnostics
- Leverage, coverage and shareholder-distribution stress
- Historical public-company cash deployment comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `02_Corporate_Finance/_template_BASE.xlsx`
- Reproducible builder: `tools/builders/build_corporate_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `02_Corporate_Finance/sources/source_register.csv`
- Frozen snapshots: `02_Corporate_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `three_statement` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `capital_structure` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cost_of_capital` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| treasury | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| board | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Annual public statements do not replace a daily treasury forecast
- Debt issuance and repayment values aggregate multiple instruments
- Minimum cash, leverage and coverage thresholds remain policy assumptions unless separately approved

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| minimum_cash_headroom | 0.2 | 0.0 | Escalate funding, capex and shareholder-distribution plan |
| net_leverage | 3.0 | 3.5 | Re-underwrite capital structure and deleveraging path |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `02_Corporate_Finance/validation.md`
- Stakeholder sign-off: `02_Corporate_Finance/governance/signoff.json`
- Lifecycle record: `02_Corporate_Finance/governance/lifecycle.json`
- Retirement trigger: Capital allocation, liquidity policy, debt structure or operating plan changes materially
