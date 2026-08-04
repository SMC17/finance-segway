# Private Credit — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3 then M4  
**Service priority**: P0

## Present

- [x] Canonical template + builder (`build_private_credit_release.py`)
- [x] Model card + validation
- [x] Domain source register with Ares + Yellow public citations
- [x] **Real reference instance path**: `instances/public_ares_capital_2024/`
- [x] L3 tool wired to builder: `tools/agents/private_credit_underwrite.py`
- [x] EDGAR companyfacts extract for ARCC attached as provenance

## Gaps to M3

- [ ] Populate CFADS / pricing from portfolio or borrower-level public data (placeholders force REVIEW)
- [ ] LibreOffice recalc + Checks **PASS** on `public_ares_capital_2024`
- [ ] Adversarial real instance fully built (Yellow stress is cited in domain register — promote to instance folder)
- [ ] Stakeholder sign-off (currently PENDING in model card)

## Gaps to M4

- [ ] Three material RefreshLog entries on a maintained instance
- [ ] One outcome comparison
- [ ] Dated release with reproducible builder hash

## Commands

```bash
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750
python tools/agents/private_credit_underwrite.py --use-ares-fixture
```
