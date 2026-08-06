# 30 ETF Construction & Management

**Archetype:** `_template_ETF.xlsx`

Portfolio construction (look-through holdings and sector weights), creation-unit and authorized-participant arbitrage economics, and a fund-return-vs.-benchmark tracking-difference bridge (expense drag, securities-lending offset, cash drag, sampling/optimization error).

Declared maturity: **M2**. Real, sourced instance: `etf-public-qqq-2026` (Invesco QQQ Trust) — AUM, net expense ratio, dividend yield, market price, all 105 disclosed holdings (top 30 named + real aggregate remainder), and all 11 disclosed sector weights are real, sourced figures from the fund's own disclosed profile data. Creation unit size, securities-lending revenue offset, cash drag, and sampling-error estimates remain illustrative template defaults — see `model_card.md`.

Instances live in `instances/`. Copy the template, populate `Assumptions` and `Portfolio Construction` with real, sourced data, then run `tools/model_instances.py` against a manifest and `tools/recalc.py`.
