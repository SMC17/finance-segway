# 30 ETF Construction & Management

**Archetype:** `_template_ETF.xlsx`

Portfolio construction (look-through holdings and sector weights), creation-unit and authorized-participant arbitrage economics, and a fund-return-vs.-benchmark tracking-difference bridge (expense drag, securities-lending offset, cash drag, sampling/optimization error).

Declared maturity: **M2**. Two real, sourced instances:

- `etf-public-qqq-2026` (Invesco QQQ Trust, conventional/Base) — AUM, net expense ratio, dividend yield, market price, all 105 disclosed holdings (top 30 named + real aggregate remainder), and all 11 disclosed sector weights are real, sourced figures from the fund's own disclosed profile data.
- `etf-public-kweb-2026-stress` (KraneShares CSI China Internet ETF, adversarial/Downside) — AUM, net expense ratio, dividend yield, market price (Alpha Vantage), 30 disclosed holdings + real remainder, and sector weights (the fund's own SEC Form N-CSR annual shareholder report). Realized outcome: the fund's own disclosed 5-year average annual total return of **-15.07%** through 2026-03-31. The fund's sector weights cover investments only and sum to 102.6%; its own disclosed `OTHER ASSETS LESS LIABILITIES` line of (2.6)% is carried beside them, so the composition grid reconciles to exactly 100% and every check passes on its merits. Both figures come from the same filing — nothing is smoothed.

Creation unit size, securities-lending revenue offset, cash drag, and sampling-error estimates remain illustrative template defaults on both instances — see `model_card.md`.

Instances live in `instances/`. Copy the template, populate `Assumptions` and `Portfolio Construction` with real, sourced data, then run `tools/model_instances.py` against a manifest and `tools/recalc.py`.
