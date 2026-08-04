# Model Card: Asset Management

## Identity

- Model ID: 08
- Domain: Asset Management
- Version: 2.2.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: perpetual

## Intended use

### Approved uses

- Fund and manager performance diagnostics
- NAV, fee-waterfall, exposure and liquidity review
- Historical public-manager stress comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `08_Asset_Management/_template_AM.xlsx`
- Reproducible builder: `tools/builders/build_asset_management_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `perpetual`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `08_Asset_Management/sources/source_register.csv`
- Frozen snapshots: `08_Asset_Management/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `nav` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `subscriptions_redemptions` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `fee_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `carry` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `attribution` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidity_budget` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| gp | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lp | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| operations | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public-manager AUM is a proxy for a fund-level NAV rollforward
- AUM flow disclosures do not provide transaction-level fee and carry terms
- Liquidity and unfunded-commitment cells remain sensitivity inputs unless explicitly sourced

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| aum_rollforward_residual | 0.01 | 0.05 | Reconcile flows, markets, FX, acquisitions and distributions |
| liquidity_coverage | 1.2 | 1.0 | Escalate redemption and unfunded-commitment funding plan |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `08_Asset_Management/validation.md`
- Stakeholder sign-off: `08_Asset_Management/governance/signoff.json`
- Lifecycle record: `08_Asset_Management/governance/lifecycle.json`
- Retirement trigger: Performance methodology, fee structure, or liquidity architecture is superseded
