# Private Credit — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3 then M4  
**Service priority**: P0 (near-term revenue path)

## Present

- [x] Canonical template + builder
- [x] Model card (`model_card.md`)
- [x] Validation record (`validation.md`)
- [x] Governance / releases / sources / outcomes folders
- [x] Domain engines listed (CFADS, covenants, yield/OID, recovery/LGD, downside)

## Gaps to M3

- [ ] At least one **real** reference instance (public BDC holding, public credit agreement proxy, or fully sourced public borrower case)
- [ ] At least one **adversarial** real or public-derived instance
- [ ] Source register fully populated for material inputs (no live URL without as-of)
- [ ] Checks sheet green on instances after LibreOffice recalc
- [ ] Stakeholder sign-off recorded (currently PENDING in model card)

## Gaps to M4

- [ ] Three material RefreshLog entries
- [ ] One outcome comparison (e.g. predicted DSCR/recovery vs realized)
- [ ] Dated release with reproducible builder hash

## Agent tool

Thin stub: `tools/agents/private_credit_underwrite.py`  
Contract: `docs/AGENT_TOOL_CONTRACT.md`

## Next concrete actions

1. Select one public credit name or BDC portfolio company with redistributable facts.
2. Populate `instances/<slug>/` with workbook + source_register + snapshots.
3. Run Checks; fix until PASS.
4. Record first RefreshLog entry.
