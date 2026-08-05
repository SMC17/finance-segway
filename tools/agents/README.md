# Agent tools (L3)

Fail-closed, provenance-required interfaces over flagship domain builders.

See `docs/AGENT_TOOL_CONTRACT.md` and `docs/AI_NATIVE_GOLDMAN_ROADMAP.md`.

| Tool | Domain | Status |
|------|--------|--------|
| `private_credit_underwrite.py` | 05 Private Credit | **Wired** — provenance enforced; invokes builder; writes instance dir + receipt + RefreshLog |
| `lbo_underwrite` | 03 PE | Planned |
| `restructuring_screen` | 24 Distressed | Planned |
| `dcf_comps` | 01 IB | Planned |

## Private Credit

```bash
# Refresh EDGAR facts
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750

# Materialize / refresh the public BDC reference instance
python tools/agents/private_credit_underwrite.py --use-ares-fixture

# Demo path (synthetic facts — not for clients)
python tools/agents/private_credit_underwrite.py --demo
```

Instance package: `05_Private_Credit/instances/public_ares_capital_2024/`  
Also on disk: `instances/public_ares_2024.xlsx` + receipt (release workbook sibling).

Agents must not invent numbers. Excel remains the receipt. Checks stay NOT_RUN until LibreOffice recalc + domain contracts pass.
