# Research Universe Visualizations

Excel workbooks that help humans see the synthetic (and later real) universes used by the RAM risk rail and the kdb regime exports.

## Rules

- These workbooks are **research visualization tools only**.
- They are **not** governed decision models.
- They do **not** appear in `standards/model_inventory.json` and must never be given an M0–M4 maturity claim.
- They follow core Excel conventions (Cover sheet, clear labels, blue for parameters where relevant) so they feel familiar, but they live under `research/`.

## Stage 0 workbook

```bash
python research/ram/build_universe_viz.py
```

Produces `_universe_viz_stage0.xlsx` with sheets:

| Sheet | Content |
|-------|--------|
| Cover | Purpose, limitations, explicit non-governed status |
| Universe | 10 synthetic names, vols, equal-weight and inverse-vol weights |
| Covariance | Full matrix + PSD status |
| Risk Summary | Equal-weight vs inverse-vol variance and volatility |
| Regime Summary | Contract-1 metrics (illustrative) |
| Notes | Regeneration and evidence pointers |

## Future

When the RAM rail reaches Stage 1 (≤50 names) and Stage 2 (S&P 100), new visualization builders will be added with the same discipline: clear Cover, explicit non-governed status, and links back to the risk skeleton and evidence notes.
