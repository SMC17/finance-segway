# Instance: public_ares_capital_2024

| Field | Value |
|-------|-------|
| Domain | 05 Private Credit |
| Class | real_public (BDC portfolio proxy) |
| As-of | 2026-03-31 (10-Q companyfacts) |
| Tool | `tools/agents/private_credit_underwrite.py --use-ares-fixture` |
| Maturity impact | Counts toward real-instance evidence; does **not** alone promote to M3 |

## Regenerate

```bash
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750
python tools/agents/private_credit_underwrite.py --use-ares-fixture
```

Then run domain Checks / LibreOffice recalc before treating outputs as decision-grade.
