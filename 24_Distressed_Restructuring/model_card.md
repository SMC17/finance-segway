# Model Card: Distressed & Restructuring

## Identity

- Model ID: 24
- Domain: Distressed & Restructuring
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

- 13-week liquidity and rescue-financing analysis
- Claim waterfall, fulcrum and priority diagnostics
- Historical reorganization and failure-path comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `24_Distressed_Restructuring/_template_RESTRUCTURING.xlsx`
- Reproducible builder: `tools/builders/build_restructuring_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `24_Distressed_Restructuring/sources/source_register.csv`
- Frozen snapshots: `24_Distressed_Restructuring/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `capital_structure` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidity_13_week` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `recovery_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `fulcrum_security` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `reorg_value` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidation_value` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `new_money` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| creditor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| debtor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| advisor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| court | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public filings do not replace claim schedules, cash receipts and legal opinions
- New-money economics and priority require executed documents and court orders
- Historical outcomes cannot establish feasibility for a different debtor

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| minimum_13_week_liquidity | 1.2 | 1.0 | Escalate funding, disbursement and filing plan |
| waterfall_conservation_residual | 0.01 | 0.05 | Block release and reconcile claims, value and distributions |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `24_Distressed_Restructuring/validation.md`
- Stakeholder sign-off: `24_Distressed_Restructuring/governance/signoff.json`
- Lifecycle record: `24_Distressed_Restructuring/governance/lifecycle.json`
- Retirement trigger: Plan, capital structure, court status or operating case is superseded
