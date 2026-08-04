# 05 Private Credit

**Archetype:** `_template_CREDIT.xlsx`  
**Canonical builder:** `tools/builders/build_private_credit_template.py`  
**Current maturity:** M2 Decision Model

Lender-side underwriting model with an explicit Base/Downside selector, five-year operating and CFADS forecast, debt-and-cash schedule, mandatory amortization, PIK accrual, cash sweep, leverage/coverage/DSCR covenants, lender yield and OID analysis, recovery/LGD bridge, recovery sensitivity, visible checks, dated sources, and refresh history.

This domain answers whether a lender should extend, price, hold, amend, or restructure credit. It is intentionally distinct from the sponsor-return LBO model and from the issuer-focused Debt Finance model.

Instances live in `/deals/`. Copy the template, rename it to the borrower or deal code, complete the Cover and Sources tabs, populate blue inputs, and run:

```bash
python tools/recalc.py 05_Private_Credit/deals/<deal>.xlsx
python tools/weekly_refresh_check.py 05_Private_Credit
```

M3 promotion still requires a completed model card, independent validation record, stakeholder challenge, reviewed source snapshots, and reference/adversarial public instances.
