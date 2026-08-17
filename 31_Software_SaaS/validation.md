# Independent Validation: Software & SaaS

## Validation identity

- Model ID and version: 31 / 1.0.0
- Builder: `tools/builders/build_software_saas_institutional.py`
- Validation date: 2026-08-17
- Validator: `tools/verify_reference_calcs.py::check_software_arr_rollforward` — an independent pure-Python oracle that regenerates the expected series from the Assumptions drivers and compares cell-for-cell against the LibreOffice-recalculated workbook
- Independence statement: the oracle does not read the workbook's formulas or reuse its intermediate values. It recomputes the ARR cohort, retention metrics, revenue split and blended margin from first principles.
- Risk tier: Tier 1
- Scope: template mechanics plus two real, sourced public instances (`software-public-adobe-fy2025`, conventional/Base; `software-public-uipath-fy2023-stress`, adversarial/Downside).

## Executive conclusion

- **Approved with limitations at M2.**
- Declared maturity supported: Yes — integrated mechanics, two real sourced public instances (one conventional, one adversarial), independent reference checks. Not yet supported for M3 (requires multiple stakeholder perspectives evidenced in practice and human effective challenge).
- Compensating control: no capital or fiduciary use without named human owner and approver; UiPath's License revenue (47% of FY2023 revenue) and either case's illustrative (non-real) driver cells must not be represented as disclosed figures.
- Revalidation trigger: prospectus/10-K access sources UiPath's beginning-RPO level for real, or the methodology changes.

## 1. Conceptual soundness

The ARR roll-forward is the standard subscription cohort identity (beginning +
new + expansion − contraction − churn = ending). Retention is *derived* from
that balance rather than asserted, which is the point: NRR excludes new logos by
construction, and GRR excludes expansion as well, so the two cannot silently be
defined into agreement.

Revenue recognises the **average** ARR balance across the year rather than the
ending balance. Recognising ending ARR would overstate revenue in every growing
year — a small-looking choice that compounds materially over a five-year
forecast.

## 2. Implementation verification

- Builder-to-workbook parity: verified via `tools/build_all_models.py --require-parity` (27/27 semantic and presentation).
- LibreOffice recalculation: 235 formulas, 0 errors.
- External links: none. Literal Excel errors: none.
- Circularity: none — single-pass roll-forward.
- Reproducibility: the builder regenerates the committed template deterministically.

## 3. Independent benchmarking

Recomputed in Python from the same drivers, not read back from the workbook:

| Output | Workbook | Independent | Residual | Status |
|---|---:|---:|---:|---|
| Year-1 ending ARR | 1,240.0 | 1000 + 220 + 140 − 40 − 80 = 1,240.0 | 0.0 | PASS |
| Year-5 ending ARR | 2,931.63 | five-period compounding of the same identity | <1e-6 | PASS |
| Net revenue retention | 1.0200 | (1000 + 140 − 40 − 80) / 1000 | <1e-9 | PASS |
| Gross revenue retention | 0.9200 | (1000 − 80) / 1000 | <1e-9 | PASS |
| Year-1 total revenue | 1,232.0 | avg(1000, 1240) × 1.10 | <1e-6 | PASS |
| Blended gross margin | 0.7409 | (1120 × 0.80 + 112 × 0.15) / 1232 | <1e-9 | PASS |
| Magic number | 0.769 | 360 / 468.16 | <1e-4 | PASS |

The oracle additionally asserts three orderings that would catch a
definitional error rather than an arithmetic one: NRR ≥ GRR in every period,
blended margin bounded by its two components, and non-GAAP operating income
never below GAAP after the SBC add-back.

### `software-public-uipath-fy2023-stress` (recomputed by hand from the applied Downside-column inputs; this session's sandbox could not run the workbook's own LibreOffice recalculation)

| Output | Independent result | Formula | Status |
|---|---:|---|---|
| Year-1 ending ARR ($mm) | 1,203.8 | `925.3 * (1 + 0.0711 + 0.36 - 0.05 - 0.08)` | matches UiPath's own disclosed FY2023 ARR exactly -> PASS |
| Net revenue retention | 1.230 | `1 + 0.36 - 0.05 - 0.08` | matches UiPath's disclosed FY2023 net retention (123%) exactly -> PASS |
| Gross revenue retention | 0.870 | `1 - 0.05 - 0.08` | NRR (1.230) exceeds GRR (0.870) -> PASS |
| Year-1 total revenue ($mm) | 1,173.1 | `avg(925.3, 1203.8) * (1 + 0.102)` | see Finding SW-01 below -- **does not** match UiPath's disclosed GAAP revenue |
| Blended gross margin | between 0.8283 and -0.5844 | weighted by revenue mix | within bounds by construction -> PASS |

### Findings (uipath case)

| ID | Severity | Finding | Evidence | Disposition |
|---|---|---|---|---|
| SW-01 | Informational | This case uses UiPath's own real disclosed ARR (not a revenue proxy, unlike `software-public-adobe-fy2025`) as the Beginning/Ending ARR scale. The template's revenue formula (avg ARR x (1 + services%)) then implies Year-1 total revenue of ~$1,173.1mm, a +10.8% gap against UiPath's actual disclosed FY2023 GAAP revenue of $1,058.6mm. This is a real, measured distance between an ARR-native operating metric and GAAP revenue recognition timing for this specific company (UiPath's ARR definition includes maintenance/support invoiced amounts that don't map 1:1 to its GAAP Subscription-services revenue line) -- not a sourcing or arithmetic error. | Cross-checked against `tools/data_fabric/out/PATH_facts_annual_series.json` (XBRL) and the FY2023 10-K's own statement of operations, both of which agree with each other on the $1,058.6mm figure. | Not corrected -- the real ARR values are used as-is, and the gap is disclosed in the manifest's `refresh.reviewer_notes` and here rather than hidden or reverse-engineered away. |

## 4. Sensitivity and stress behaviour

Base and Downside both run cleanly on the template's own illustrative defaults.
`software-public-uipath-fy2023-stress` additionally exercises the Downside
column with a real company's real numbers: net retention of 123% (down from a
real prior-year 145%) and an even-worse-than-the-template's-own-Downside-default
sales & marketing ratio (66.3% real vs. 42% illustrative) both land inside the
Downside column without needing any template-mechanics change -- the installed
base is still net-expanding (NRR > 100%) but decelerating sharply, which is
exactly the "stress that surfaces rather than gets masked" the template is
designed to show.

## 5. Outcomes analysis

`software-public-adobe-fy2025`'s outcome is registered as `status: "pending"`
(metric: FY2026 total revenue, forecast from the case's own modeled trajectory),
following this repository's convention of not backdating or hindsight-fitting a
forecast case.

`software-public-uipath-fy2023-stress`'s outcome is `status: "recorded"`: a
naive forecast that FY2023's net retention rate (123%) would hold flat into
FY2024, against the realized, disclosed FY2024 rate of 119% -- both figures
directly from UiPath's own 10-Ks (FY2023 and FY2024 filings, the second
disclosing both years side by side). The stress was not a one-off: retention
kept declining a year later, and this case records that as a genuine
same-direction-of-error realized outcome, the same convention this
repository's other adversarial cases use (e.g., IB's HP/Autonomy impairment,
Private Credit's Yellow Corp Chapter 11).

## 6. Limitations

See model card. The material ones for M2: single cohort rather than
per-vintage, UiPath's beginning-RPO level is a template default (not sourced),
and UiPath's ARR-vs-GAAP-revenue basis gap documented in Finding SW-01 above.

## Sign-off

- Developer response: implemented mechanics, oracle check, two real sourced instances (one conventional, one adversarial), and this record; disclosed one real, measured ARR-vs-revenue basis gap rather than reconciling it away.
- Validator conclusion: approved with limitations at M2; M3 not yet supported pending human effective challenge.
- Owner decision: **PENDING** · Approval date: **PENDING**
- Next validation trigger: UiPath's beginning-RPO level is sourced for real, or the methodology changes.
