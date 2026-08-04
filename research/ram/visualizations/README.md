# Research Universe Visualizations

Excel workbooks that help humans see the universes used by the RAM risk rail and the kdb regime exports.

## Rules

- These workbooks are **research visualization tools only**.
- They are **not** governed decision models.
- They do **not** appear in `standards/model_inventory.json` and must never be given an M0–M4 maturity claim.
- They follow core Excel conventions (Cover sheet, clear labels) so they feel familiar, but they live under `research/`.

## Stage 0 workbook (real data preferred)

```bash
# 1. Fetch / refresh real mega-cap data and Contract-1 regime export
python research/ram/fetch_real_universe.py

# 2. Build the Excel visualization (reads real cov + regime CSV when present)
python research/ram/build_universe_viz.py
```

Produces `_universe_viz_stage0.xlsx` with sheets:

| Sheet | Content |
|-------|--------|
| Cover | Purpose, real-data provenance, explicit non-governed status |
| Universe | 10 real names, realized vols, equal-weight and inverse-vol weights |
| Covariance | Full realized matrix + Cholesky PSD status |
| Risk Summary | Equal-weight vs inverse-vol variance and volatility from Stage-0 RAM |
| Regime Summary | Contract-1 metrics read from the real kdb export CSV |
| Notes | Regeneration and evidence pointers |

If real data files are missing, the builder falls back to a synthetic example so the template remains executable offline.

## Proof points already demonstrated

- Real Yahoo adjusted-close data → realized covariance → Stage-0 pure-Python risk engine.
- PSD check passes on the real matrix.
- Equal-weight and inverse-vol risk numbers are sensible and consistent with the identities in `simple_covariance.py`.
- Regime CSV matches `research/kdb/INTEGRATION_CONTRACTS.md` Contract 1 and is consumed by the Excel builder.

## Future

When Stage 1 (≤50 names) is promoted, a parallel visualization builder will be added with the same discipline.
