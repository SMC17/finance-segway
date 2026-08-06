# Independent Validation: Software & SaaS

## Validation identity

- Model ID and version: 31 / 1.0.0
- Builder: `tools/builders/build_software_saas_institutional.py`
- Validation date: 2026-08-06
- Validator: `tools/verify_reference_calcs.py::check_software_arr_rollforward` — an independent pure-Python oracle that regenerates the expected series from the Assumptions drivers and compares cell-for-cell against the LibreOffice-recalculated workbook
- Independence statement: the oracle does not read the workbook's formulas or reuse its intermediate values. It recomputes the ARR cohort, retention metrics, revenue split and blended margin from first principles.
- Risk tier: Tier 1
- Scope: template mechanics only. No real instance exists, so this is conceptual and implementation verification, not benchmarking against a disclosed outcome.

## Executive conclusion

- **Approved with limitations at M1.**
- M2 not supported: requires a real, sourced public case (see model card, Limitations).
- Compensating control: no capital or fiduciary use without named human owner and approver.

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

## 4. Sensitivity and stress behaviour

Base and Downside both run cleanly. Downside raises churn and contraction while
cutting new and expansion ARR, which drives NRR below 100% — the installed base
shrinks before new logos, and the model surfaces that rather than masking it in
a blended growth rate.

## 5. Outcomes analysis

None yet — no real instance. A future case should record ARR and retention as of
its filing date as a same-period reproduction check, following the convention
already used elsewhere in this repository, not as a hindsight-restated forecast.

## 6. Limitations

See model card. The material ones for M2: no public instance, single cohort
rather than per-vintage, and no billings/RPO bridge.

## Sign-off

- Developer response: implemented mechanics, oracle check, and this record.
- Validator conclusion: approved with limitations at M1.
- Owner decision: **PENDING** · Approval date: **PENDING**
- Next validation trigger: a real public case is sourced, or the methodology changes.
