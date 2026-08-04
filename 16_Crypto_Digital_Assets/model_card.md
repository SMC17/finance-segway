# Model Card: Crypto & Digital Assets

## Identity

- Model ID: 16
- Domain: Crypto & Digital Assets
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

- Supply, unlock, staking, treasury and liquidity diagnostics
- Custody, venue, bridge and counterparty stress
- Historical public-platform comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `16_Crypto_Digital_Assets/_template_CRYPTO.xlsx`
- Reproducible builder: `tools/builders/build_crypto_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `perpetual`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `16_Crypto_Digital_Assets/sources/source_register.csv`
- Frozen snapshots: `16_Crypto_Digital_Assets/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `token_supply` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `unlock_schedule` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `staking_dilution` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `treasury_runway` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `velocity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `onchain_multiples` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| protocol | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| validator | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| market_maker | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Custodied customer assets are a platform-scale proxy rather than a native token supply schedule
- On-chain ownership, validator and unlock data require protocol-specific snapshots
- Custody controls require independent operating and security evidence

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| unlock_to_liquidity_ratio | 0.25 | 0.5 | Escalate unlock concentration and market-depth plan |
| custody_counterparty_concentration | 0.25 | 0.5 | Re-underwrite custody, venue and key-management concentration |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `16_Crypto_Digital_Assets/validation.md`
- Stakeholder sign-off: `16_Crypto_Digital_Assets/governance/signoff.json`
- Lifecycle record: `16_Crypto_Digital_Assets/governance/lifecycle.json`
- Retirement trigger: Protocol economics, custody architecture or market structure is superseded
