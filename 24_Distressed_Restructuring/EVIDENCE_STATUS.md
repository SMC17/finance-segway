# Distressed & Restructuring — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3  
**Service priority**: P1 (service revenue cluster with 05/06)

## Present (corrected 2026-08-05 — verified against actual repo state, not just claimed)

- [x] Template + builder path in inventory
- [x] Model card + validation
- [x] Governance / sources / instances / outcomes folders
- [x] **Real reference instance**: `instances/public_hertz_2021_reorganization.xlsx` (Hertz FY2021 Form 10-K, post-Chapter-11 reorganization)
- [x] **Real adversarial instance**: `instances/public_bbby_2022_liquidity.xlsx` (Bed Bath & Beyond 2022 10-Q + Chapter 11 disclosure statement)
- [x] Source register populated: `sources/source_register.csv` — both cases with real SEC EDGAR URLs, as-of dates, and SHA-256 snapshot hashes

## Gaps to M3

- [ ] Both instances currently show Checks **REVIEW** after a real LibreOffice recalc (verified via `tools/verify_public_case_status.py`). Plausibly a genuine signal here specifically — both real cases are inherently about companies under real financial stress (reorganization / liquidity crisis) — but not yet individually traced line-by-line the way the Insurance false-negative was, so don't treat "REVIEW" as confirmed-correct without that pass.
- [ ] Stakeholder sign-off (currently PENDING in model card)

## Gaps to M4

- [ ] Three material RefreshLog entries
- [ ] One outcome comparison
- [ ] Zero genuine forecast evidence: both outcome cases in
      `tools/frontier_evidence_registry.py` are `forecast_kind:
      "hindsight_restated_fact"` (Hertz's Chapter 11 emergence and BBBY's
      Chapter 11 filing are both known historical facts restated as
      "forecast" — no independent prediction was ever made). Tracked in
      `KNOWN_HINDSIGHT_ONLY_MODELS` in that file. Needs a genuinely
      independent forecast (e.g. a liquidity-runway or fulcrum-security
      projection derived from the pre-event 10-Q/10-K and compared against
      the real outcome) before this domain has any real predictive-evidence
      component of `outcomes_analysis`.

## Next actions

1. Recalculate both instances and read the individual (not just Overall) Checks line items to confirm the REVIEW status reflects real distress signals rather than a formula defect.
2. Record RefreshLog entries once the above is resolved.
3. Stakeholder sign-off remains the real blocker for M3 either way.
