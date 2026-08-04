# Independent Validation: Debt Finance

## Validation identity

- Model ID and version: 06 / 3.0.0-evidence
- Validation date: 2026-08-04
- Validator: Finance-Segway independent validation system
- Independence statement: validation uses separate pure-Python oracles, domain contracts, semantic parity, public evidence, and LibreOffice execution rather than trusting workbook formulas alone. Human effective challenge remains a separate unsigned gate.
- Risk tier: Tier 1

## Executive conclusion

- Engineering conclusion: **Engineering and historical public evidence approved with limitations at M2; named stakeholder approval and maintained operating history remain mandatory for M3/M4**
- Declared M2 maturity supported: Yes
- M3 promotion supported: **No — stakeholder approval and repeated operating history remain outstanding**
- Required compensating control: no capital, fiduciary, regulatory, or live-risk use without named human owner and approver.

## 1. Conceptual soundness

Required engines: issuance, refinancing, maturity_ladder, interest_rate_risk, covenants, recovery_lgd.
Required perspectives: issuer, arranger, lender, rating_agency.
The model is accepted only for the approved uses in `model_card.md`; prohibited uses remain out of scope.

## 2. Data and source validation

- Public cases use frozen JSON source snapshots and a CSV source register.
- Inputs are typed as observed, derived, or modeler-owned.
- Snapshot hashes are checked before case generation.
- Synthetic regression cases are excluded from M4 evidence.

## 3. Implementation verification

- Reproducible builder: `tools/builders/build_debt_finance_release.py`
- Canonical workbook: `06_Debt_Finance/_template_CREDIT.xlsx`
- Semantic builder parity: required
- LibreOffice recalculation: required
- External links and literal errors: prohibited

## 4. Public-case benchmarking

| Case | Type | As-of | Outcome status |
|---|---|---|---|
| debt-public-microsoft-2024 | conventional | 2024-06-30 | recorded |
| debt-public-carnival-2020-stress | adversarial | 2020-11-30 | recorded |

## 5. Sensitivity and stress behavior

The conventional and adversarial public cases are retained separately. Modeler-owned assumptions are not represented as observations and must remain inside sensitivity or stress ranges.

## 6. Outcomes analysis

Recorded outcomes are stored in `06_Debt_Finance/outcomes/outcome_log.csv`. A future test is permitted only when no realized observation yet exists and must name the preservation method and trigger.

## 7. Use and governance

- Approved and prohibited uses are explicit.
- Monitoring thresholds and escalation actions are machine-readable.
- Rollback and retirement records are present.
- Human stakeholder sign-off remains pending and blocks M3.

## 8. Unresolved limitations

- Public debt balances aggregate secured, unsecured, fixed, floating and convertible instruments
- Maturity buckets and committed facilities require instrument-level confirmation
- Pricing, covenant and refinancing assumptions remain modeler-owned unless sourced

## Sign-off

- Developer response: implemented evidence, public cases, monitoring, outcomes, and lifecycle controls.
- Validator conclusion: approved with limitations at M2; M3 not yet approved.
- Owner decision: **PENDING**
- Approval date: **PENDING**
- Revalidation trigger: methodology change, structural change, threshold breach, source-definition change, or adverse outcome.
