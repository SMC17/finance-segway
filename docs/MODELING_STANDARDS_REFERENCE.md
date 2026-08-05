# Modeling standards reference (WSP / BIWS / WSO / industry-curriculum conventions)

## Provenance of this document

Everything below is synthesized from `WebSearch` results against public
training-provider and practitioner pages (Wall Street Prep, Breaking Into
Wall Street, Wall Street Oasis, ibinterviewquestions.com, ModelReef,
Macabacus, Proskauer/Sidley covenant commentary). `WebFetch` is
non-functional in this session for general web content (confirmed against
multiple hosts, including Wikipedia), so none of these pages could be
independently re-fetched and read in full — the summaries below are
`WebSearch`'s synthesis of snippets, not a verbatim reading of primary
sources. Treat this as a **directional checklist of well-established,
widely-taught conventions**, not as sourced financial data — nothing here
carries the "observed"/"derived" evidentiary weight this repo requires for
company financials. Sources are listed per section for anyone who wants to
verify directly.

This exists to ground `tools/audit_template_standards.py` (task #29) in
real external criteria instead of house opinion about what a "good" model
looks like.

## 1. Color / provenance conventions

- **Blue font** (often on light-yellow fill): hard-coded inputs / constants
  — "so it is easy to see what numbers can be changed."
- **Black font**: same-sheet formulas.
- **Green font**: cross-sheet references/links (occasionally also used for
  historical-data cells in some houses).
- **Purple font**: links to external files (less universal than the first
  three, but common at bulge-bracket shops).

This repo's own `Cover` sheet legend already states blue/yellow = input,
black = formula, green = cross-sheet link — consistent with the standard.
Purple-for-external-file-links is not currently a documented convention
here and is out of scope (no template currently links to external
workbooks).

Sources: [Wall Street Oasis — Financial Model Color Formatting](https://www.wallstreetoasis.com/resources/financial-modeling/financial-model-color-formatting), [Breaking Into Wall Street — How to Color Code in Excel](https://breakingintowallstreet.com/kb/excel/how-to-color-code-in-excel/), [ibinterviewquestions.com — Formatting Standards and Color Conventions](https://ibinterviewquestions.com/guides/valuation-investment-banking/formatting-standards-color-conventions-ib-models)

## 2. Circularity (debt schedules with revolver/cash-sweep interest)

- Circular references (interest expense depends on average debt balance,
  which depends on cash flow, which depends on interest expense) are
  standard in LBO/credit debt schedules — not a defect by themselves.
- Two accepted resolutions: (a) enable Excel iterative calculation with a
  visible circularity-breaker switch on the assumptions tab, or (b) avoid
  circularity by computing interest on the **opening** balance rather than
  the average balance.
- A `CHOOSE`/toggle switch between "average balance" (correct, circular)
  and "beginning balance" (approximate, non-circular, used to kill a
  runaway circularity error) is a common pattern.
- The balance sheet is the integrity check: if it doesn't balance, an
  upstream formula is wrong.

Audit implication: every debt-schedule template with a cash sweep should
have (a) an explicit, visibly labeled circularity switch/toggle, not a bare
unexplained circular formula, and (b) a balance-check row wired to a
Checks sheet.

Sources: [Wall Street Prep — Standard LBO Modeling Test](https://www.wallstreetprep.com/knowledge/leveraged-buyout-lbo-modeling-1-hour-practice-test/), [Wall Street Oasis — Circular references in LBO models](https://www.wallstreetoasis.com/forum/private-equity/circular-references-in-lbo-models)

## 3. DCF conventions

- **Mid-year convention**: discount exponents of 0.5, 1.5, 2.5... rather
  than 1, 2, 3, applied consistently to both the explicit forecast period
  AND the terminal value discounting (not one and not the other).
- **Terminal value cross-check**: compute both perpetuity-growth (Gordon
  Growth) and exit-multiple methods and reconcile them against each other;
  the exit-multiple method is grounded in observable market comps and
  treated as the primary check on the perpetuity-growth output.
- **Sanity check before the sensitivity table**: flex WACC ±100bps; if
  enterprise value moves less than ~10% on a 200bps WACC swing, the
  terminal-value assumptions are too conservative (insensitive) to be
  useful.
- Sensitivity tables are only meaningful if the base case is internally
  consistent first (matching cash-flow definitions and discount rate,
  explicit timing convention, documented TV method) — otherwise the grid is
  "precise nonsense."

Sources: [ibinterviewquestions.com — Best Practices for Building a DCF Model](https://ibinterviewquestions.com/guides/valuation-investment-banking/best-practices-building-dcf-model-excel), [ModelReef — DCF Sensitivity Analysis](https://modelreef.io/resources/articles/discounted-cash-flow-dcf/dcf-sensitivity-analysis-two-way-tables-wacc-vs-growth-and-interpretation), [ctacquisitions.com — Mid-Year Convention Guide](https://ctacquisitions.com/mid-year-convention/)

## 4. Credit / covenant conventions (private credit, debt finance)

- **Covenant headroom** = distance between the current covenant ratio and
  the credit-agreement threshold, expressed as the EBITDA underperformance
  (vs. the agreed base-case model) that would trigger a breach.
- Typical direct-lending headroom at close: **25-35%** cushion to the
  sponsor/borrower base-case model; 35%+ is "cov-loose," 40%+ is common in
  aggressive large-cap documentation.
- Monitoring convention: credit teams escalate scrutiny once headroom
  drops below **~10%** of the threshold, and treat anything inside **5%**
  as a near-miss.
- Covenants are set by reference to an agreed "base case model" — a
  specific, versioned financial model delivered as a closing condition, not
  a moving target.

Audit implication: private-credit/debt-finance templates should carry an
explicit covenant-headroom output (current ratio vs. threshold vs. %
cushion), not just the raw leverage ratio, and should flag when headroom
crosses the ~10%/5% escalation bands.

Sources: [Sidley Austin — Financial Covenants in Private Credit Transactions](https://www.sidley.com/en/insights/newsupdates/2026/03/financial-covenants-in-private-credit-transactions), [Proskauer — Leverage Covenants and Auto-Resets](https://www.proskauer.com/alert/private-credit-deep-dives-leverage-covenants-and-auto-resets)

## 5. General model hygiene (cross-cutting)

- Every model needs a visible Checks sheet/row with PASS/REVIEW/FAIL
  status kept live, not a one-time manual sign-off (this repo already
  enforces this via `standards/model_inventory.json` and per-model Checks
  sheets — confirmed consistent with the standard, not a gap).
- Inputs isolated from formulas (no hardcoded numbers buried inside a
  formula deep in a calculation sheet) — a hardcode should always be blue
  and always live on an Assumptions/Inputs sheet or a clearly-marked input
  cell, never mid-formula on a calc sheet.

Sources: same as sections 1-2 above.

## How this is used

`tools/audit_template_standards.py` runs these checks (color-convention
consistency, circularity-switch presence on cash-sweep debt schedules,
mid-year-convention consistency in DCF-bearing templates, covenant-headroom
presence in credit templates, and no-hardcodes-outside-inputs) against all
25 domain templates and produces a findings report — see
`docs/EVIDENCE_STATUS_BOARD.md` / the audit output for current status.
