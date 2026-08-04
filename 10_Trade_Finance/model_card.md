# Model Card: Trade Finance

## Identity

- Model ID: 10
- Domain: Trade Finance
- Version: 2.2.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: short_term_1y

## Intended use

### Approved uses

- Working-capital-cycle and borrowing-need diagnostics
- Documentary, country, facility and expected-loss stress
- Historical exporter and supply-chain comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `10_Trade_Finance/_template_TRADE_FINANCE.xlsx`
- Reproducible builder: `tools/builders/build_trade_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `short_term_1y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `10_Trade_Finance/sources/source_register.csv`
- Frozen snapshots: `10_Trade_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `cash_conversion` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `facility_utilization` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `lc_cost` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `factoring` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `counterparty_risk` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `country_risk` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| bank | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| borrower | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| insurer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| dfi | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public statements aggregate multiple products and jurisdictions
- LC, factoring and facility terms remain modeler assumptions without executed documents
- Inventory includes program and production effects beyond trade-finance mechanics

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| cash_conversion_cycle_days | 120 | 180 | Re-underwrite inventory, receivables, payables and facility availability |
| facility_utilization | 0.85 | 1.0 | Escalate borrowing base and liquidity remediation |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `10_Trade_Finance/validation.md`
- Stakeholder sign-off: `10_Trade_Finance/governance/signoff.json`
- Lifecycle record: `10_Trade_Finance/governance/lifecycle.json`
- Retirement trigger: Documentary-credit, facility or working-capital architecture changes materially
