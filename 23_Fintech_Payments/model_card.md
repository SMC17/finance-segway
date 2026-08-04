# Model Card: Fintech & Payments

## Identity

- Model ID: 23
- Domain: Fintech & Payments
- Version: 2.2.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: corporate_10y

## Intended use

### Approved uses

- Payment-volume, network, unit-economics and cohort diagnostics
- Fraud, chargeback, capital and settlement-liquidity stress
- Historical payment-network and platform-disposal comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `23_Fintech_Payments/_template_FINTECH.xlsx`
- Reproducible builder: `tools/builders/build_fintech_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_10y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `23_Fintech_Payments/sources/source_register.csv`
- Frozen snapshots: `23_Fintech_Payments/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `volume_take_rate` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `unit_economics` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cohorts` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `ltv_cac` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `losses_fraud` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `network_effects` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `capital_requirements` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| operator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| partner | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| regulator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public network scale is annual and aggregated while the workbook labels monthly unit economics
- The Worldpay case uses sale proceeds and impairments as capital-stress proxies
- Product-level fraud, safeguarding and settlement data require operating records

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| fraud_bps | 50 | 100 | Escalate fraud controls, pricing and merchant exposure |
| liquidity_coverage | 1.1 | 1.0 | Escalate unrestricted liquidity and settlement obligations |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `23_Fintech_Payments/validation.md`
- Stakeholder sign-off: `23_Fintech_Payments/governance/signoff.json`
- Lifecycle record: `23_Fintech_Payments/governance/lifecycle.json`
- Retirement trigger: Payment network, safeguarding, capital or product architecture changes materially
