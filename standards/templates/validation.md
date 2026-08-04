# Independent Validation: <Model Name>

## Validation identity

- Model ID and version:
- Workbook checksum:
- Builder commit:
- Validation date:
- Validator:
- Validator independence statement:
- Risk tier:
- Scope of validation:

## Executive conclusion

- Approved / Approved with limitations / Remediation required / Rejected
- Declared maturity supported: Yes / No
- Material findings:
- Required compensating controls:
- Revalidation trigger:

## 1. Conceptual soundness

- Is the selected methodology appropriate for the intended use?
- Are economic identities and market conventions correctly specified?
- Are units, currencies, signs, timing, and day-count conventions consistent?
- Are assumptions supported and appropriately uncertain?
- Are boundary conditions and nonlinearities understood?
- Are omitted risks material?

### Findings

| ID | Severity | Finding | Evidence | Remediation | Owner | Due date |
|---|---|---|---|---|---|---|
| | | | | | | |

## 2. Data and source validation

- Source provenance and as-of dates
- Completeness and reconciliation
- Transformation checks
- Point-in-time integrity
- Missing-data treatment
- Licensing and redistribution restrictions

## 3. Implementation verification

- Builder-to-workbook parity
- Formula and cross-sheet-link review
- External-link scan
- Circularity and iterative-calculation review
- Accounting / cash-flow / waterfall identities
- Error guards and edge cases
- Reproducibility from a clean environment

## 4. Independent benchmarking

| Model output | Workbook result | Independent result | Tolerance | Residual | Status |
|---|---:|---:|---:|---:|---|
| | | | | | |

Independent calculations must not reuse the workbook formula implementation.

## 5. Sensitivity and stress behavior

- Base, downside, severe downside
- Break-even
- Reverse stress
- Monotonicity
- Discontinuities
- Liquidity and covenant failure
- Tail or regime stress

## 6. Outcomes analysis

Where outcomes exist:

| Forecast / model output | As-of date | Realized outcome | Error | Explanation | Action |
|---|---|---|---:|---|---|
| | | | | | |

Where outcomes do not yet exist, define the future test and preservation method.

## 7. Use and governance

- Named owner and approver
- Approved use and prohibited use
- User documentation
- Change classification
- Monitoring thresholds
- Escalation and retirement rules

## 8. Limitations

List unresolved limitations, their materiality, and compensating controls.

## Sign-off

- Developer response:
- Validator conclusion:
- Owner decision:
- Approval date:
- Next validation date or trigger:
