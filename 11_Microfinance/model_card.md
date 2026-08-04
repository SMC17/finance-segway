# Model Card: Microfinance

## Identity

- Model ID: 11
- Domain: Microfinance
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

- Portfolio-quality and sustainability diagnostics
- PAR, provisioning, funding and client-conduct stress
- Historical MFI comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `11_Microfinance/_template_MICROFINANCE.xlsx`
- Reproducible builder: `tools/builders/build_microfinance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `11_Microfinance/sources/source_register.csv`
- Frozen snapshots: `11_Microfinance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `portfolio_rollforward` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `par30_90` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `vintage` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `credit_loss` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `oss_fss` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `funding_liquidity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| regulator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| dfi | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public regional disclosures may not provide complete reserve or funding schedules
- Average loan size is derived from rounded portfolio and client counts
- Affordability and conduct conclusions require borrower-level evidence

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| par30 | 0.05 | 0.1 | Escalate collections, provisioning and client-protection review |
| operational_self_sufficiency | 1.05 | 1.0 | Re-underwrite pricing, cost base and subsidy dependence |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `11_Microfinance/validation.md`
- Stakeholder sign-off: `11_Microfinance/governance/signoff.json`
- Lifecycle record: `11_Microfinance/governance/lifecycle.json`
- Retirement trigger: Portfolio definitions, lending methodology, funding or conduct standards change materially
