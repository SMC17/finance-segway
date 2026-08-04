# Model Card: Real Estate & REIT

## Identity

- Model ID: 17
- Domain: Real Estate & REIT
- Version: 2.2.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: long_term_10y

## Intended use

### Approved uses

- NOI, cap-rate, debt, lease-roll and REIT bridge analysis
- DSCR, LTV and refinancing stress
- Historical public-owner and flexible-office comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `17_Real_Estate_REIT/_template_REAL_ESTATE.xlsx`
- Reproducible builder: `tools/builders/build_real_estate_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `long_term_10y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `17_Real_Estate_REIT/sources/source_register.csv`
- Frozen snapshots: `17_Real_Estate_REIT/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `property_proforma` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `lease_roll` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `capex` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `debt` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `cap_rate` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `irr` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `reit_ffo_affo` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| owner | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lender | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| tenant | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| appraiser | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Company-wide public filings are simplified into a property/REIT decision model
- The flexible-office adversarial case is an occupancy-economics proxy and not REIT accounting
- Lease-level rollover, tenant credit and property debt require asset-specific diligence

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| minimum_dscr | 1.25 | 1.0 | Escalate refinance, reserves, capex and asset-sale plan |
| economic_occupancy | 0.9 | 0.8 | Re-underwrite expirations, renewals, downtime and tenant concentration |

## Release record

- Active release: 2.2.0-evidence
- Rollback release: m2-release-2.2.0
- Validation record: `17_Real_Estate_REIT/validation.md`
- Stakeholder sign-off: `17_Real_Estate_REIT/governance/signoff.json`
- Lifecycle record: `17_Real_Estate_REIT/governance/lifecycle.json`
- Retirement trigger: Portfolio, lease, debt or REIT reporting architecture is superseded
