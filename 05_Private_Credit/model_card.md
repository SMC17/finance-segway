# Model Card: Private Credit

## Identity

- Model ID: 05
- Domain: Private Credit
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

- Portfolio concentration and leverage diagnostics
- DSCR, PIK, amendment and recovery stress
- Historical performing and distressed credit comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `05_Private_Credit/_template_CREDIT.xlsx`
- Reproducible builder: `tools/builders/build_private_credit_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_5y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `05_Private_Credit/sources/source_register.csv`
- Frozen snapshots: `05_Private_Credit/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `operating_case` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cfads` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `debt_cash_schedule` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `covenants` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `yield_oid` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `recovery_lgd` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `downside_case` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| sponsor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| rating_agency | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| restructuring | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Public BDC and borrower disclosures are portfolio- or company-level proxies
- Recovery values require collateral appraisals, claim schedules and legal priority analysis
- CFADS, covenant and amendment cells remain assumptions unless explicitly sourced

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| downside_dscr | 1.2 | 1.0 | Escalate amendment, liquidity and sponsor-support plan |
| recovery_rate | 0.7 | 0.6 | Re-underwrite collateral, claims and restructuring alternatives |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `05_Private_Credit/validation.md`
- Stakeholder sign-off: `05_Private_Credit/governance/signoff.json`
- Lifecycle record: `05_Private_Credit/governance/lifecycle.json`
- Retirement trigger: Credit agreement, collateral, capital structure or operating case is superseded
