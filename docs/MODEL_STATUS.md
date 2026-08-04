# Finance-Segway Model Status

This file is the human-readable projection of the machine contracts in
`standards/model_inventory.json`, the artifact evidence in
`standards/releases/flagship-2.1.0.json`, and the synthetic benchmark index in
`standards/benchmark_cases/index.json`.

## Current release

- Inventory version: **2.1.0**
- Core archetypes: **24**
- M2 Decision Models: **15**
- M1 Correct Skeletons: **9**
- M3 Institutional Underwriting Models: **0**
- M4 Maintained Production Systems: **0**
- Synthetic engineering benchmark instances: **18**
- Public maintained instances that count toward M4: **0**

The benchmark instances are deliberately excluded from M4. They prove builder,
scenario, source-register, RefreshLog, recalculation, receipt, and adversarial-case
plumbing. They do not substitute for public source snapshots, independent review,
and realized outcome monitoring.

## Engineered flagship release

| Domain | Canonical builder | Artifact | Maturity |
|---|---|---|---|
| Private Equity | `tools/builders/build_lbo_release.py` | `03_Private_Equity/_template_LBO.xlsx` | M2 |
| Merchant Banking | `tools/builders/build_lbo_release.py` | `04_Merchant_Banking/_template_LBO.xlsx` | M2 |
| Risk Management | `tools/builders/build_risk_release.py` | `09_Risk_Management/_template_RISK.xlsx` | M2 |
| Options / Derivatives | `tools/builders/build_options_release.py` | `14_Options_Derivatives/_template_OPTIONS.xlsx` | M2 |
| Insurance / Actuarial | `tools/builders/build_insurance_release.py` | `18_Insurance_Actuarial/_template_INSURANCE.xlsx` | M2 |
| Structured Finance | `tools/builders/build_securitization_institutional.py` | `19_Structured_Finance_Securitization/_template_SECURITIZATION.xlsx` | M2 |
| Project Finance | `tools/builders/build_project_finance_release.py` | `20_Project_Finance/_template_PROJECT_FINANCE.xlsx` | M2 |
| Fixed Income / Rates | `tools/builders/build_fixed_income_release.py` | `21_Fixed_Income_Rates/_template_FIXED_INCOME.xlsx` | M2 |
| Quantitative / Systematic | `tools/builders/build_quant_release.py` | `22_Quantitative_Systematic/_template_QUANT.xlsx` | M2 |

Private Credit, Debt Finance, and Public Finance remain separate reconciled M2
decision systems. Investment Banking, Corporate Finance, Venture Capital, and
the existing verified domains retain their inventory classifications.

## Release gates

The engineered release is accepted only when all of the following pass:

1. Python compile and unit-test suite.
2. Domain-specific workbook contract validators.
3. LibreOffice recalculation of every release workbook.
4. Zero cached literal Excel errors.
5. Post-recalculation contract validation.
6. Full 24-model inventory validation.
7. Semantic builder-to-artifact parity for every inventory model.
8. Whole-library external-link and structural audit.
9. Cryptographic SHA-256 evidence for each workbook and builder.
10. Recalculation of all 18 reference/adversarial benchmark instances.

Permanent CI enforcement lives in:

- `.github/workflows/flagship-validation.yml`
- `.github/workflows/library-parity-required.yml`
- `.github/workflows/library-engineering.yml`
- `.github/workflows/model-governance.yml`
- `.github/workflows/verify-models.yml`

## Promotion boundary

No model is M3 merely because it is deep or has many formulas. M3 still requires:

- completed model card and approved-use statement;
- independent validation and effective challenge record;
- dated external source register and frozen snapshots;
- reviewed release artifact and change log;
- complete stakeholder views and limitations;
- at least one conventional and one adversarial externally sourced instance.

M4 additionally requires maintained instances, repeated RefreshLog history,
outcome comparison, monitoring thresholds, and release discipline over time.
