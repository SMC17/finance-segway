# Model Card: Project Finance

## Identity

- Model ID: 20
- Domain: Project Finance
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: long_term_40y

## Intended use

### Approved uses

- Construction funding and IDC analysis
- Debt sculpting and DSRA sizing
- DSCR/LLCR/PLCR underwriting
- Delay, cost-overrun, and availability stress

### Prohibited or unsupported uses

- Engineering certification
- Legal conclusion on concession or offtake contracts
- Live financing without transaction documents and tax model

## Scope and methodology

- Canonical workbook: `20_Project_Finance/_template_PROJECT_FINANCE.xlsx`
- Reproducible builder: `tools/builders/build_project_finance_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `long_term_40y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `20_Project_Finance/sources/source_register.csv`
- Frozen snapshots: `20_Project_Finance/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `construction_draw` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `interest_during_construction` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `sources_uses` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `operating_cfads` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `debt_sculpting` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `dsra` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `dscr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `llcr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `plcr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `sensitivity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| sponsor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| independent_engineer | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| offtaker | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| dfi | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Construction schedule is aggregated
- No tax-equity or partnership-flip module
- Public benchmark costs are not a substitute for EPC and independent-engineer diligence

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| construction_cost_variance | 0.1 | 0.2 | Rebase funding plan and completion support |
| minimum_dscr | 1.2 | 1.0 | Escalate lock-up/default and restructuring case |
| schedule_delay_months | 3 | 6 | Recalculate IDC, liquidity, and covenant dates |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `20_Project_Finance/validation.md`
- Stakeholder sign-off: `20_Project_Finance/governance/signoff.json`
- Lifecycle record: `20_Project_Finance/governance/lifecycle.json`
- Retirement trigger: Project reaches final maturity, is refinanced, or is abandoned
