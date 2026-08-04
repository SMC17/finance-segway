# 06 Debt Finance

**Archetype:** `_template_CREDIT.xlsx`  
**Canonical builder:** `tools/builders/build_debt_finance_template.py`  
**Current maturity:** M2 Decision Model

Issuer- and arranger-side financing model covering current capital structure, contractual maturity ladder, refinancing Sources & Uses, pro forma leverage and coverage, interest-rate and spread sensitivity, covenant and rating screens, and claim recovery/LGD.

Debt Finance is no longer a copy of the Private Credit archetype. It answers how an issuer should structure, refinance, size, price, and sequence debt instruments; Private Credit answers whether a lender should underwrite and hold the exposure.

Instances live in `/instruments/`. Copy the template, rename it to the issuer or financing code, complete the Cover and Sources tabs, populate blue inputs, and run:

```bash
python tools/recalc.py 06_Debt_Finance/instruments/<financing>.xlsx
python tools/weekly_refresh_check.py 06_Debt_Finance
```

M3 promotion still requires instrument-level documentation, model card, independent validation, stakeholder challenge, reviewed source snapshots, and reference/adversarial public instances.
