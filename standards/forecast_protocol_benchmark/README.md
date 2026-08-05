# Forecast-protocol benchmark

The reproducible evidence base behind `tools/forecast_engines.py` and the
proposed L3 skill gate: **how an LLM is asked for a forward number matters more
than which model answers**, and zero-evidence answers are memory wearing a
forecast costume.

## Task

Country-level macro indicators (inflation, population growth, real GDP per
capita, military %GDP) from the CIA World Factbook archive - public-domain
data, every edition 1990-2026, open API. For each indicator x target year
(2016 / 2020 / 2023 / 2025), predict every country's year-T value
(67-227 countries per cell; military %GDP runs thinner than the rest). Four rungs per cell:

| Rung | What it is |
|---|---|
| `carry_forward` | the value at T-2 - the persistence bar |
| `linear_drift` | least squares over T-5..T-2 projected to T |
| `llm_recall` | country name + year, NO evidence - a pure memorization probe |
| `llm_statistician` | the `forecast_engines.statistician_prompt` protocol: every country in one prompt, four years of observed history each |

Metric: MAE-skill vs carry-forward, `1 - MAE/MAE_carry` (positive = beats
persistence). Rank correlations are in the results JSON; they are dominated by
persistence on level variables, so skill is the discriminating number.

## Measured results (2026-08-05, claude-opus-5 via the Claude Code CLI)

MAE-skill vs carry-forward, cells ordered 2016 / 2020 / 2023 / 2025:

| Indicator | linear_drift | llm_recall | llm_statistician |
|---|---|---|---|
| inflation | -0.41 / -1.41 / -0.29 / -0.27 | +0.07 / **-5.43** / -0.38 / +0.52 | **+0.36** / -0.98 / **+0.30** / **+0.47** |
| pop_growth | -0.44 / -0.54 / -0.35 / -0.66 | +0.78 / +0.06 / -0.02 / -0.49 | +0.49 / +0.28 / -0.02 / +0.14 |
| gdp_percap | -0.14 / -0.28 / -1.61 / +0.00 | +0.71 / -0.19 / -1.50 / +0.51 | +0.10 / -0.13 / +0.34 / +0.12 |
| mil_pct_gdp | -0.74 / -0.67 / -0.46 / -0.26 | -0.70 / +0.47 / -0.37 / -0.22 | -0.33 / +0.29 / +0.15 / +0.19 |

Full numbers: `results/benchmark_results.json`.

## The four findings

1. **Statistician skill is genuine, and stable across the recency gradient** -
   positive in 12/16 cells including all four 2025 cells. If the protocol's
   edge were training-data recall, it would track the recall row; it does not.
2. **Recall is real and treacherous.** The model genuinely remembers public
   statistics (up to +0.78 skill from nothing but country names) - and inverts
   catastrophically in regime breaks: COVID-year inflation recall scores
   **-5.43** against simple persistence. Where memory fails worst, evidence
   keeps the statistician 4.4 points less wrong. Memory masquerading as
   forecasting fails hardest exactly when the number matters.
3. **2020 humbles everything.** In the regime-break year every rung loses to
   carry-forward on inflation. Skill gates need regime-break humility encoded.
4. **Naive trend extrapolation is harmful** (negative in 15/16 cells) -
   carry-forward is the right default registered baseline.

Companion measurements on held-out public behavioral microdata (UCI
bank-marketing and census-income surveys, 148 + 92 segments, measured outside
this repository): single-shot per-unit prompting scored 0.483 median rank
correlation - below a no-AI groupby at 0.563 - while the statistician protocol
scored 0.680, above tuned statistical engines (0.58) and logistic regression
(0.64), with +0.117 skill over echoing its own evidence, gains concentrated on
small samples, and 0.42pp rerun drift.

## Reproduce

```bash
standards/forecast_protocol_benchmark/fetch_data.sh   # 56 small JSONs (or use the committed snapshot in data/)
python3 tools/forecast_benchmark.py --no-llm          # naive rungs; stdlib-only, no CLI needed
python3 tools/forecast_benchmark.py                   # full grid; needs an authenticated Claude Code CLI
```

The fetch script sends a standard browser User-Agent (the host's CDN rejects
bare curl); the data itself is public domain via an open, unauthenticated API.

The runner is stdlib-only by design (this repository's dependency policy); the
LLM rungs shell out to `claude -p` and cache responses, so a full rerun is
resumable. Nothing here runs in CI - committed results are the record, the
scripts are the protocol.
