# Private Credit — Evidence Status (Flagship)

**Declared maturity**: M2  
**Target**: M3 then M4  
**Service priority**: P0 (near-term revenue path)

## Present

- [x] Canonical template + builder (`build_private_credit_release.py`)
- [x] Model card (`model_card.md`) + validation record (`validation.md`)
- [x] Governance / releases / sources / outcomes folders
- [x] Domain engines listed (CFADS, covenants, yield/OID, recovery/LGD, downside)
- [x] L3 tool wired to the governed builder path: `tools/agents/private_credit_underwrite.py`
  (validates provenance against live Assumptions labels, writes via
  `tools/model_instance_release.py`'s manifest machinery, recalculates for
  real via LibreOffice, reads Checks back — never invents math)

## Real instances (verified this pass, LibreOffice recalc just re-run)

| Instance | Class | As-of | Checks Overall |
|---|---|---|---|
| `instances/public_ares_2024.xlsx` | real reference | 2024-12-31 | **PASS** |
| `instances/public_yellow_2022_stress.xlsx` | real adversarial | 2022-12-31 | **REVIEW** on "No covenant breach" — correct: Yellow Corporation actually breached covenants and filed Chapter 11, so a clean PASS here would be the wrong answer for a genuinely stressed real case |
| `instances/public_ares_capital_2024.xlsx` | real, `agent_tool_draft` | 2026-03-31 | **REVIEW** (5 covenant breaches) — a real ARCC balance sheet substituted against unmodified template revenue/EBITDA defaults; expected and documented, not a defect (see `instances/public_ares_capital_2024.thesis.md`) |

Source register (`sources/source_register.csv`) has all three cases with
real SEC EDGAR URLs, as-of dates, and SHA-256 snapshot hashes.

## Gaps to M3

- [ ] `public_ares_capital_2024` needs real portfolio-level CFADS / revenue
  construction (not just the two balance-sheet facts currently sourced)
  before it can move past REVIEW, or else needs to stay explicitly
  scoped as a mechanics/wiring proof rather than a decision instance
- [ ] Stakeholder sign-off recorded — still PENDING (`governance/signoff.json`:
  `promotion_blocked: true`). This is the Issue #7 human gate; no agent
  can close it, including for the two instances already at PASS/REVIEW

## Gaps to M4

- [x] One outcome comparison recorded per case in `outcomes/outcome_log.csv`
  (Ares portfolio fair value forecast-vs-realized; Yellow Chapter 11
  binary outcome, forecast 0 / realized 1)
- [ ] Three material RefreshLog entries — currently zero in the canonical
  template's RefreshLog sheet (header row only). Genuine gap.
- [~] Dated release with reproducible builder hash — `releases/CHANGELOG.md`
  has a dated entry but no builder/workbook hash matching the per-instance
  `.receipt.json` pattern yet. Worth tightening, not blocking.

## Agent tool

`tools/agents/private_credit_underwrite.py` — fully wired, not a stub.
Every manifest it writes is tagged `classification: "agent_tool_draft"`,
`counts_toward_M4: false` unconditionally, so nothing it produces is
silently counted as reviewed evidence ahead of Issue #7.

```bash
# Illustrative, fictional borrower -> .agent-tool-scratch/ (never committed)
PYTHONPATH=. python tools/agents/private_credit_underwrite.py --demo

# Real Ares Capital (ARCC) portfolio-proxy instance from EDGAR companyfacts
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750
PYTHONPATH=. python tools/agents/private_credit_underwrite.py --use-ares-fixture
```

Contract: `docs/AGENT_TOOL_CONTRACT.md`

## Next concrete actions

1. Record three material RefreshLog entries in `_template_CREDIT.xlsx` to
   start the M4 append-only history.
2. Add a builder/workbook hash to the release changelog to match the
   per-instance receipt pattern.
3. Decide `public_ares_capital_2024`'s scope: either source real
   portfolio-level revenue/CFADS facts to let it clear REVIEW honestly, or
   keep it explicitly labeled as a wiring/mechanics proof rather than a
   decision-grade instance.
4. Stakeholder sign-off remains the real blocker for M3 on every instance
   here — needs a named human owner, reviewer, and validator, not more
   agent work.
