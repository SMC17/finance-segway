# Evidence Status Board — All 24 Domains

**Policy**: `docs/DOMAIN_MAX_POLICY.md` — every domain to max evidence-supported maturity; flagships first.

**Last verified**: 2026-08-05, by actually recalculating all 48 real public-case workbooks via LibreOffice and reading their genuine computed status (`tools/verify_public_case_status.py`) — not by re-stating prior claims. This table was previously stale: it said "TBD" or "—" for real instances and evidence packs in domains that already had both, because it predated the real-only evidence rewrite (PR #17) that populated all 48 cases. Corrected below.

## What "real instance" means here, precisely

Every domain has exactly one **conventional** (reference) and one **adversarial** (stress) public case — 48 workbooks total, each built from real SEC-filed facts via the governed manifest path, each recalculating with 0 formula errors. That much is uniformly true and verified.

What is *not* uniformly true: whether the facts sourced are the ones that actually drive the model's decision, or just enough to satisfy the minimum input count. A manifest that overrides an offer price and a share count is "real" in the sense that those two numbers are genuinely SEC-sourced — but if the DCF discount rate, terminal growth, and EPS-accretion assumptions underneath are still template defaults, the model's *conclusion* isn't really about that company. That distinction is what the table below tracks, because it's exactly the thing that was invisible until this pass: no CI gate before `verify_public_case_status.py` ever recalculated a workbook and read its actual decision.

## Status legend

- **Differentiated** — conventional and adversarial cases produce genuinely different, individually-verified decision outcomes (checked line-by-line, not just at the Overall/summary level).
- **Thin** — conventional and adversarial cases land on the *identical* concerning status (FAIL/BREACH), the signature of a manifest that only source-addresses a couple of deal-specific cells while the decision-driving assumptions stay on template defaults. Tracked explicitly in `tools/verify_public_case_status.py`'s `KNOWN_THIN_CASES` — CI fails if a new case matches this pattern and isn't listed, or if a listed case is fixed and not delisted.
- **Same non-concerning status, not yet individually verified** — conventional and adversarial land on the same PASS or REVIEW status. Not flagged by the automated thin-detection heuristic (which only fires on FAIL/BREACH matches), but that is a *negative* result, not a positive one — it means this specific check didn't fire, not that the case has been read line-by-line and confirmed genuine the way Private Credit and Insurance have.

| ID | Domain | Declared | Real instances | Status | Notes |
|----|--------|----------|-----------------|--------|-------|
| 01 | Investment Banking | M2 | HP/Autonomy 2012 (adv.) + MSFT/LinkedIn 2016 (conv.) | **Thin** | Manifests source-address ~3 Transaction Analysis cells (offer price, deal value, share count); discount rate, terminal growth, EPS-accretion drivers are template defaults on both |
| 02 | Corporate Finance | M2 | Intel 2024 (adv.) + Microsoft 2024 (conv.) | **Thin** | Same BASE-template pattern as 01 |
| 03 | Private Equity | M2 | Macy's 2020 (adv.) + Home Depot 2023 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 04 | Merchant Banking | M2 | WeWork 2022 (adv.) + Alleghany 2021 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 05 | Private Credit | M2 | Yellow 2022 stress (adv., REVIEW) + Ares Capital 2024 (conv., PASS) + Ares Capital portfolio proxy (agent-drafted, REVIEW) | **Differentiated** | Verified this pass: Yellow's REVIEW is correct (real covenant breach, real Chapter 11); L3 tool rewired to actually recalculate and read Checks instead of hardcoding NOT_RUN |
| 06 | Debt Finance | M2 | Carnival 2020 stress (adv.) + Microsoft 2024 (conv.) | Same non-concerning status | Both REVIEW, including the Microsoft reference case — not yet individually traced; see domain `EVIDENCE_STATUS.md` |
| 07 | Public Finance | M2 | Sri Lanka 2023 stress (adv.) + Jamaica 2024 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 08 | Asset Management | M2 | BlackRock 2022 stress (adv.) + BlackRock 2023 (conv.) | **Thin** | Same BASE-template pattern |
| 09 | Risk Management | M2 | FRED COVID 2020 (adv.) + FRED balanced 2024 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 10 | Trade Finance | M2 | Boeing 2020 stress (adv.) + Boeing 2019 (conv.) | Same non-concerning status | Both REVIEW; not individually verified this pass |
| 11 | Microfinance | M2 | ASA Zambia stress (adv.) + ASA 2025 (conv.) | **Thin** | Same BASE-template pattern |
| 12 | Equity Finance | M2 | AMC 2020 dilution (adv.) + Tesla 2020 offering (conv.) | **Thin** | Same BASE-template pattern |
| 13 | Venture Capital | M2 | Instacart 2023 down-round (adv.) + Snowflake 2020 (conv.) | **Thin** | Same BASE-template pattern |
| 14 | Options & Derivatives | M2 | SPX 2020-03-16 (adv.) + SPX 2024-01-02 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 15 | Commodities | M2 | WTI April 2020 (adv.) + WTI 2023 (conv.) | **Thin** | Same BASE-template pattern |
| 16 | Crypto & Digital Assets | M2 | Coinbase 2022 stress (adv.) + Coinbase 2023 (conv.) | **Thin** | Same BASE-template pattern |
| 17 | Real Estate & REIT | M2 | WeWork 2022 stress (adv.) + Realty Income 2023 (conv.) | **Thin** | Same BASE-template pattern |
| 18 | Insurance & Actuarial | M2 | AIG 2008 (adv.) + Chubb 2023 (conv.) | **Differentiated** | Fixed this pass: a false-negative in the "Paid triangle cumulative" check failed both instances unconditionally regardless of data (blank cells beyond each accident year's observed periods were read as 0). Both now genuinely PASS; AIG additionally shows a real REVIEW on capital coverage |
| 19 | Structured Finance & Securitization | M2 | Fed mortgage 2009 (adv.) + Fed mortgage 2024 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 20 | Project Finance | M2 | Vogtle delay (adv.) + NREL solar 2024 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 21 | Fixed Income & Rates | M2 | Treasury 2022 shock (adv.) + Treasury 2025-12-01 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 22 | Quantitative & Systematic | M2 | S&P 500 2020-2024 capacity (adv.) + S&P 500 2019-2023 (conv.) | Same non-concerning status | Both PASS; not individually verified this pass |
| 23 | Fintech & Payments | M2 | FIS/Worldpay 2023 stress (adv.) + Visa 2023 (conv.) | **Thin** | Same BASE-template pattern |
| 24 | Distressed & Restructuring | M2 | BBBY 2022 liquidity (adv.) + Hertz 2021 reorganization (conv.) | Same non-concerning status | Both REVIEW — plausibly a genuine signal given both real cases are inherently about companies under real distress, but not yet individually traced; see domain `EVIDENCE_STATUS.md` |

**Summary**: 2 domains individually verified and differentiated (05, 18); 10 domains flagged thin and tracked in the CI gate's allowlist (01, 02, 08, 11, 12, 13, 15, 16, 17, 23); 12 domains show a matching non-concerning status that has not yet been individually traced the way 05 and 18 were.

## Why the thin domains are all the same shape

Domains 01, 02, 08, 11, 12, 13, 15, 16, 17, 23 all share the "BASE" archetype template (`tools/builders/legacy_frontier_release.py`), which builds a Base/Adversarial column pair into every workbook regardless of which real company's manifest is applied. The "Adversarial" column's own template defaults (discount rate below terminal growth, aggressive dilution/financing assumptions) are *deliberately* invalid, to demonstrate the Decision & Checks sheet catching a bad scenario in the template's out-of-the-box state. But no public-case manifest for these ten domains overrides those specific cells with real, per-company assumptions — so every real instance in these domains inherits the template's own baked-in stress scenario rather than a stress scenario grounded in that company's real numbers.

## Sourcing status: blocked on network access, not abandoned

Attempted to source real DCF/valuation assumptions (WACC, terminal growth, EPS-accretion drivers) for the Investment Banking pair as a starting point, using both SEC EDGAR's XBRL companyfacts API (`data.sec.gov`) and direct filing retrieval (`www.sec.gov`). Both hosts are blocked by this session's egress policy (confirmed via the proxy status endpoint: `connect_rejected`, "policy denial", on both hosts). `tools/data_fabric/out/ARCC_facts_selected.json` and `HD_facts_selected.json` already in this repo were fetched in an earlier session that had that access; this one doesn't.

Real per-company deal terms (offer price, share counts) are already sourced and correct for the thin cases — what's missing is the assumptions a banker's fairness opinion would disclose (DCF discount rate range, terminal growth) or a deal announcement would report (target/buyer earnings, synergies, financing cost), which requires either restored SEC EDGAR access or manual sourcing from an accessible mirror. Not fabricating placeholder "real" figures to close this gap cosmetically — an unresolved gap, honestly tracked, is worth more than a false one.

## Recent progress (2026-08-05)

- Fixed a false-negative in Insurance's "Paid triangle cumulative" check that failed both real instances unconditionally, in two separate builder copies of the formula (`build_insurance_institutional.py` and the release wrapper that was silently re-breaking the first fix)
- Added `tools/verify_public_case_status.py` + `.github/workflows/public-case-status.yml`: the first CI gate that actually recalculates a real instance and reads its genuine computed decision status, rather than checking only hashes (`evidence_receipt_integrity.py`) or manifest schema (`final_public_evidence.py`)
- Landed content from three PRs that showed "merged" on GitHub but never reached `main` due to a stacked-PR base-branch trap (consulting-OS functional kernels + capability catalog, and the private-credit L3 tool synthesis)
- Corrected this board and the Debt Finance / Distressed & Restructuring evidence-status docs, which understated already-complete work (real instances and source registers existed but were marked as gaps)
- Attempted real-data sourcing for the thin Investment Banking manifests; blocked on SEC EDGAR network access this session (see above)
