# 29 Fund of Funds

**Archetype:** `_template_FOF.xlsx`

Look-through underlying-fund portfolio, FoF-level NAV roll-forward, and fee-layering ("fees on fees") analysis: FoF net TVPI/DPI/RVPI to LPs vs. the look-through weighted-average gross TVPI of the underlying funds, plus single-fund concentration screening.

Declared maturity: **M2**. Two real, sourced, LibreOffice-recalculated public cases — `fof-public-hlpaf-2026` (Hamilton Lane Private Assets Fund, conventional) and `fof-public-skybridge-fy2023-stress` (SkyBridge Multi-Adviser Hedge Fund Portfolios, adversarial — real disclosed -30.29% one-year return, FTX position marked to real fair value $0) — see `model_card.md`, "Real public cases," for exactly what's real, what's a labeled proxy, and why both cases' own Checks honestly FAIL/BREACH.

Instances live in `instances/`. Copy the template, populate `Underlying Fund Portfolio` and `NAV Rollforward & Fee Layering` with real, sourced data, then run `tools/recalc.py`.
