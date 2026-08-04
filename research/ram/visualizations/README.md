# Research Universe Visualizations

Excel workbooks that help humans see the universes used by the RAM risk rail and the kdb regime exports.

## Rules

- Research visualization tools only — **not** governed decision models.
- Outside `standards/model_inventory.json`; no M-maturity claim.
- Prefer real data via `fetch_real_universe.py` + `build_universe_viz.py`.

## Stage 0 workbook

```bash
python research/ram/fetch_real_universe.py
python research/ram/build_universe_viz.py
```

Sheets: Cover, Universe, Covariance, Risk Summary, Regime Summary (from real Contract-1 CSV), Notes.

## Second visualization (planned)

**Rolling volatility & correlation heat** — still under the research rail only.

Intent:

- Rolling 21d / 63d realized vol per name
- Rolling average pairwise correlation
- Optional correlation heatmap snapshot at as-of
- Same Cover discipline: explicit non-governed status, link to evidence and regime export

Implementation will live as `build_universe_viz_rolling.py` (or an extra sheet group in the Stage-0/1 builder) once Stage-1 runtime work is underway. No core-domain maturity impact.

## Citation into governed models

See `09_Risk_Management/sources/README_regime_citation.md` and the example `source_register_regime_example.csv` for the correct pattern.
