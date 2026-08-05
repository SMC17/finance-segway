# Debt Finance — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3  
**Service priority**: P1 (with Private Credit)

## Present (corrected 2026-08-05 — verified against actual repo state, not just claimed)

- [x] Template + builder path in inventory
- [x] Model card + validation
- [x] Governance / sources / instances / outcomes folders
- [x] **Real reference instance**: `instances/public_microsoft_2024.xlsx` (Microsoft FY2024 Form 10-K)
- [x] **Real adversarial instance**: `instances/public_carnival_2020_stress.xlsx` (Carnival FY2020 Form 10-K, COVID-era liquidity stress)
- [x] Source register populated: `sources/source_register.csv` — both cases with real SEC EDGAR URLs, as-of dates, and SHA-256 snapshot hashes

## Gaps to M3

- [ ] Both instances currently show Checks **REVIEW** after a real LibreOffice recalc (verified via `tools/verify_public_case_status.py`), not PASS — including the Microsoft reference case. Not yet root-caused to the same depth as the Insurance false-negative fix; needs the same "read every failing check line, trace the formula, confirm it's a real signal not a formula defect" pass before claiming this is either correct or a bug.
- [ ] Stakeholder sign-off (currently PENDING in model card)

## Gaps to M4

- [ ] Three material RefreshLog entries
- [ ] One outcome comparison

## Next actions

1. Recalculate both instances and read the individual (not just Overall) Checks line items — same method used to find and fix the Insurance triangle bug — to determine whether the REVIEW status is a genuine signal or another false negative.
2. Record RefreshLog entries once the above is resolved.
3. Stakeholder sign-off remains the real blocker for M3 either way.
