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

## Gaps to M3 (updated 2026-08-04 -- verified, not just claimed)

- [x] Real reference instance: `instances/public_ares_2024.xlsx` (Ares Capital, FY2024 10-K + Q2 2025 10-Q) -- recalcs clean (0 errors, 293 formulas), Checks sheet: **PASS**
- [x] Real adversarial instance: `instances/public_yellow_2022_stress.xlsx` (Yellow Corporation, FY2022 annual report + bankruptcy 8-K) -- recalcs clean, Checks sheet: **REVIEW** on "No covenant breach" (correct -- Yellow actually breached covenants and filed Chapter 11; a clean PASS here would be the wrong answer for a genuinely stressed real case)
- [x] Source register fully populated: `sources/source_register.csv` has both cases with real SEC EDGAR URLs, as-of dates, and SHA-256 snapshot hashes
- [x] Checks sheet green (or correctly REVIEW-flagged) on both instances after LibreOffice recalc -- reverified independently in this pass
- [ ] Stakeholder sign-off recorded -- still PENDING (`governance/signoff.json`: `promotion_blocked: true`). This is the Issue #7 human gate; no agent can close it.

## Gaps to M4

- [x] One outcome comparison recorded: `outcomes/outcome_log.csv` has both a conventional forecast-vs-realized (Ares portfolio fair value, error tracked) and an adversarial binary outcome (Yellow Chapter 11 filed within 12 months: forecast 0, realized 1)
- [ ] Three material RefreshLog entries -- currently **zero** entries in the canonical template's RefreshLog sheet (header row only). Genuine gap.
- [~] Dated release with reproducible builder hash -- `releases/CHANGELOG.md` has a dated 3.0.0-evidence entry, but doesn't yet record a builder/workbook hash the way the per-instance `.receipt.json` files do. Worth tightening, not blocking.

## Agent tool

Thin stub: `tools/agents/private_credit_underwrite.py`  
Contract: `docs/AGENT_TOOL_CONTRACT.md`

Still a stub, not wired to the domain builder -- see roadmap P1 ("thin L3 tool interface for 05 and 03").

## Next concrete actions

The "select a name, populate instances/" work described here previously is done -- both instances exist, recalc clean, and have real, dated, hashed sources. What's actually left:

1. Record three material RefreshLog entries in `_template_CREDIT.xlsx` (e.g. a source refresh, an assumption change, a methodology note) to start the M4 append-only history.
2. Add a builder/workbook hash to the release changelog to match the per-instance receipt pattern.
3. Wire `tools/agents/private_credit_underwrite.py` to the actual builder path (currently stubbed) per the L3 tool contract.
4. Stakeholder sign-off remains the real blocker for M3 -- needs a named human owner, reviewer, and validator, not more agent work.
