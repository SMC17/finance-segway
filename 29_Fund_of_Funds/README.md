# 29 Fund of Funds

**Archetype:** `_template_FOF.xlsx`

Look-through underlying-fund portfolio, FoF-level NAV roll-forward, and fee-layering ("fees on fees") analysis: FoF net TVPI/DPI/RVPI to LPs vs. the look-through weighted-average gross TVPI of the underlying funds, plus single-fund concentration screening.

Declared maturity: **M1**. No real public instance yet — see `model_card.md`, "Why M1, not M2," for what's blocking M2 and why the gap is documented rather than papered over.

Instances live in `instances/`. Copy the template, populate `Underlying Fund Portfolio` and `NAV Rollforward & Fee Layering` with real, sourced data, then run `tools/recalc.py`.
