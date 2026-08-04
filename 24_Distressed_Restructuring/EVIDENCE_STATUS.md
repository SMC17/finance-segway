# Distressed & Restructuring — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3  
**Service priority**: P1 (service revenue cluster with 05/06)

## Present

- [x] Template + builder path in inventory
- [x] Model card + validation
- [x] Governance / sources / instances / outcomes folders

## Gaps to M3

- [ ] Real reference instance (public restructuring with recovery waterfall)
- [ ] Real adversarial / liquidation comparison instance
- [ ] Source register with court docket / 8-K / disclosure statement citations (public only)
- [ ] Checks green (13-week liquidity, waterfall conservation, fulcrum)
- [ ] Stakeholder sign-off

## Natural public seed

Yellow Corporation citations already appear on the Private Credit domain register as stress sources — candidate to formalize under `24_Distressed_Restructuring/instances/` with restructuring-specific engines (fulcrum, recovery waterfall, 13-week).

## Next actions

1. `python tools/scaffold_model_evidence.py 24_Distressed_Restructuring` if needed.
2. Create `instances/public_yellow_2023_reorg/` thesis + source register from public 8-K / docket indexes.
3. Agent stub `restructuring_screen` after first instance path exists.
