# Debt Finance — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3  
**Service priority**: P1 (with Private Credit)

## Present

- [x] Template + builder path in inventory
- [x] Model card + validation
- [x] Governance / sources / instances / outcomes folders

## Gaps to M3

- [ ] Real reference instance (public issuer maturity ladder / refinancing case)
- [ ] Real adversarial instance (refinancing gap / maturity wall)
- [ ] Source register populated with EDGAR / prospectus citations
- [ ] Checks green after recalc
- [ ] Stakeholder sign-off

## Next actions

1. Pick one public IG or HY issuer with clear maturity schedule in 10-K.
2. Run `python tools/scaffold_model_evidence.py 06_Debt_Finance` if any template files missing.
3. Mirror the Private Credit agent pattern: `debt_finance_issue` tool stub after first instance exists.
4. Reuse `tools/data_fabric/edgar_company_facts.py` for LongTermDebt / InterestExpense provenance.
