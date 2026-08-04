# Model Card: Commodities

## Identity

- Model ID: 15
- Domain: Commodities
- Version: 2.2.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: trading_daily

## Intended use

### Approved uses

- Physical balance, storage, basis and cost-of-carry analysis
- Hedge-ratio and contract-alignment stress
- Historical market-dislocation comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `15_Commodities/_template_COMMODITIES.xlsx`
- Reproducible builder: `tools/builders/build_commodities_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `trading_daily`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `15_Commodities/sources/source_register.csv`
- Frozen snapshots: `15_Commodities/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `forward_curve` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `carry_storage` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `roll_yield` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `physical_balance` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `hedging` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `basis_risk` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `scenario_pnl` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| trader | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| producer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| consumer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Annual prices and weekly storage data are simplified into a static workbook snapshot
- Location, quality, timing and optionality basis require contract-level data
- Physical operations and margin calls require daily treasury evidence

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| basis_move | 10.0 | 25.0 | Reconcile location, quality, timing and liquidity basis |
| storage_utilization | 0.75 | 0.9 | Escalate logistics, financing and hedge-roll plan |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `15_Commodities/validation.md`
- Stakeholder sign-off: `15_Commodities/governance/signoff.json`
- Lifecycle record: `15_Commodities/governance/lifecycle.json`
- Retirement trigger: Contract specification, delivery point, storage or hedging program changes materially
