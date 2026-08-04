# 07 Public Finance

**Archetype:** `_template_PUBLIC_FINANCE.xlsx`  
**Canonical builder:** `tools/builders/build_public_finance_template.py`  
**Current maturity:** M2 Decision Model

Integrated sovereign and municipal credit model with two complementary lenses:

- debt sustainability: effective interest rate, nominal growth, debt-stabilizing primary balance, primary-balance gap, and projected debt trajectory;
- issuer and revenue-bond credit: five-year revenue/expenditure forecast, pension/OPEB burden, capital spending, debt service, new borrowing, reserve roll-forward, debt/revenue, DSCR, days cash, liquidity headroom, scenarios, and sensitivity.

The two lenses remain visible rather than being collapsed into one score. The workbook includes explicit Sources, Checks, and RefreshLog sheets.

Instances live in `/issuers/`. Copy the template, rename it to the issuer or financing code, complete the Cover and Sources tabs, populate blue inputs, and run:

```bash
python tools/recalc.py 07_Public_Finance/issuers/<issuer>.xlsx
python tools/weekly_refresh_check.py 07_Public_Finance
```

M3 promotion still requires a complete model card, independent validation, rating-agency/taxpayer/DFI challenge, reviewed source snapshots, and reference/adversarial public instances.
