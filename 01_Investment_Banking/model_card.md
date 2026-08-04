# Model Card: Investment Banking

## Identity

- Model ID: 01
- Domain: Investment Banking
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

- Transaction valuation and offer-premium diagnostics
- Accretion, dilution, synergy and financing stress
- Historical announced and completed transaction comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `01_Investment_Banking/_template_BASE.xlsx`
- Reproducible builder: `tools/builders/build_investment_banking_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `01_Investment_Banking/sources/source_register.csv`
- Frozen snapshots: `01_Investment_Banking/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `three_statement` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `dcf` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `trading_comps` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `precedent_transactions` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| owner | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| board | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| advisor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public merger consideration is simplified into a static transaction model
- Fairness, tax, legal, regulatory and purchase-accounting conclusions require transaction-specific diligence
- Unsourced DCF, synergy, financing and share-issuance cells remain modeler assumptions

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| offer_premium | 0.3 | 0.5 | Reconcile unaffected price, control premium and synergy support |
| eps_accretion | 0.0 | -0.1 | Escalate financing, synergy and share-issuance assumptions |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `01_Investment_Banking/validation.md`
- Stakeholder sign-off: `01_Investment_Banking/governance/signoff.json`
- Lifecycle record: `01_Investment_Banking/governance/lifecycle.json`
- Retirement trigger: Transaction terms, capital structure, forecasts, or closing conditions are superseded
