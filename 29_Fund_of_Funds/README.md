# 29 Fund of Funds

**Archetype:** `_template_FOF.xlsx`

Look-through underlying-fund portfolio, FoF-level NAV roll-forward, and fee-layering ("fees on fees") analysis: FoF net TVPI/DPI/RVPI to LPs vs. the look-through weighted-average gross TVPI of the underlying funds, plus single-fund concentration screening.

Declared maturity: **M1**. One real, sourced, LibreOffice-recalculated public case — `fof-public-hlpaf-2026` (Hamilton Lane Private Assets Fund, SEC N-CSR) — see `model_card.md`, "Real public case," for exactly what's real, what's a labeled proxy, and why the case's own NAV roll-forward check honestly FAILs. `tools/verify_release_shape.py` requires exactly two public cases before M2; a second real case is still needed.

Instances live in `instances/`. Copy the template, populate `Underlying Fund Portfolio` and `NAV Rollforward & Fee Layering` with real, sourced data, then run `tools/recalc.py`.
