# Fundamentals benchmark — the ladder on the registry's own metric class

The forecast-protocol benchmark measured the four-rung ladder on country
macro indicators. This one measures it on what the registry actually
contains: company fundamentals. Panel: 62 large-cap issuers (diversified
sectors; ARCC itself has too short an XBRL history to join any cell -
BDC companyfacts start in 2021) x annual **Assets / Revenue / Net income** distilled
from SEC EDGAR companyfacts (`data/panel.json`, ~58KB, harvested by
`harvest.py`; latest-filed value per fiscal year, so restatements win and
every rung sees the same series; values $bn; observations keyed by the
calendar year the fiscal year ends in). Grid: 3 metrics x 4 targets
(2019/2021/2023/2025), evidence = target-5..target-2. Alongside Spearman and
MAE skill, every rung reports **median-APE skill** vs carry-forward — sizes
span three orders of magnitude and the scale-free line keeps giants from
dominating the read.

## Headline: you cannot backtest an LLM on public-company fundamentals

Zero-evidence recall — no history in the prompt, just "what was each
company's X for fiscal {year}" — scores **12/12 cells positive with mean
median-APE skill 0.977**; pre-2025 cells average 0.995 and even the 2025
cells sit at 0.86-0.999 (FY2025 10-Ks were filed before the model's
knowledge cutoff, so no target year in a backtest is clean). That is not
forecasting. Large-cap financials saturate the training data, and the rung
that was a genuine two-edged probe on Factbook editions (+0.78 to −5.43,
collapsing in regime breaks) is a **database lookup** here. The
evidence-in-prompt statistician rung also lands 12/12 positive (mean
median-APE skill 0.536) — but with recall this contaminated, no
past-target-year cell can distinguish protocol skill from leakage.

Consequence, and the reason this benchmark ships anyway: **backtests cannot
substitute for the forecast registry on this metric class.** The only clean
measurement of LLM forward skill on company fundamentals is a forecast whose
target did not exist at prompt time — pre-registered, content-hashed,
resolved by a future filing (`standards/forecasts/`). This measurement
closes the "why not just backtest it?" objection with data.

Supporting reads, still clean (the naive rungs are arithmetic — no
contamination):

- **Carry-forward stays the right registered baseline even on trending
  fundamentals.** Linear drift: 8/12 MAE-positive but only 5/12
  median-APE-positive (mean −0.170), and it detonates in regime-break years
  (assets/2023: −1.021 MAE skill; net income/2023: −1.285 median-APE skill).
  Growth trends help drift on the giants; the typical company is better
  served by persistence. The #56 registrations' drift-vs-carry question
  stays genuinely open for FY2026.
- **Where the boundary shows at all, it shows in the right direction**:
  recall's weakest cells are 2025 (net income 0.86, revenue 0.91 vs a 0.995
  pre-2025 average) - memory thins slightly where filings are newest, but
  never enough to make any backtest year clean.

## Reproduce

```bash
python3 tools/fundamentals_benchmark.py --no-llm   # naive rungs; stdlib-only
python3 tools/fundamentals_benchmark.py            # full grid; needs an authenticated Claude Code CLI
standards/fundamentals_benchmark/harvest.py        # re-harvest from EDGAR (open API, needs a UA header)
```

Committed results: `results/benchmark_results.json` (claude-opus-5,
2026-08-05). The committed naive rungs are reproduced byte-for-byte by
`--no-llm` from the frozen panel; tests pin this plus the results schema.
