"""Naive baselines, the measured LLM elicitation protocol, and skill scoring.

Companion to the forecast registry: this module supplies (1) the naive
baseline generators a registration freezes, (2) the elicitation protocol an
agent should use when producing a forward estimate, and (3) ladder scoring at
resolution. It deliberately contains NO inference calls - agents bring their
own model; the repository ships the protocol contract and the arithmetic, so
CI needs no API credentials and the recipe is testable as plain code.

Why this exact protocol: it was measured, adversarially, on held-out public
behavioral data (UCI bank-marketing and census-income segments, 2026-08-05;
a companion in-repo benchmark on country macro indicators lives under
standards/forecast_protocol_benchmark/). Single-shot per-unit prompting -
the naive default - scored BELOW a no-AI groupby (0.483 vs
0.563 median Spearman on 148 bank-marketing segments). The same model, given
(a) every unit in one prompt (comparative context) and (b) each unit's
observed historical evidence with sample sizes, and asked to IMPROVE the
noisy estimates, scored 0.680 - above every classical engine measured,
with +0.117 of genuine skill over echoing the evidence it was shown,
improvements concentrated on small samples (in-context shrinkage), 0.42pp
rerun drift, replicated on a second dataset (0.869 vs baseline 0.817).
The two design rules that follow, and that this module enforces:

  1. An LLM forward estimate without evidence in the prompt is bounded by
     the zero-data lines - never let an agent ship one for a unit whose
     history exists in the repository.
  2. An LLM estimate WITH evidence is in-context statistics and must be
     benchmarked as statistics: register it with the naive ladder frozen
     alongside, and let resolution decide.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class LadderBaselines:
    carry_forward: float
    linear_drift: float


def naive_ladder(history: Sequence[tuple[str, float]]) -> LadderBaselines:
    """Baselines from an ordered (period_label, value) history.

    carry_forward - the last observed value (the persistence bar; on the
    Factbook country panel it is the hardest naive rung to beat).
    linear_drift - ordinary least squares over the observation index,
    projected one step past the last observation.
    """
    if len(history) < 2:
        raise ValueError("naive_ladder needs at least two observations")
    values = [float(v) for _, v in history]
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom
    intercept = mean_y - slope * mean_x
    return LadderBaselines(
        carry_forward=values[-1],
        linear_drift=slope * n + intercept,
    )


def statistician_prompt(
    metric_label: str,
    units: str,
    target_period: str,
    rows: Sequence[dict],
) -> str:
    """Build the measured batch-evidence elicitation prompt.

    rows: one dict per unit -
      {"id": str, "description": str,
       "history": [(period_label, value), ...],
       "sample_note": str | None}   # e.g. "n=54 quarterly observations"

    Contract (each clause exists because removing it measurably hurt):
    - EVERY unit in one prompt: comparative context alone was worth +0.07
      Spearman over single-shot elicitation.
    - Evidence inline per unit: the evidence-in-prompt condition was worth
      a further +0.13 and turns the task into auditable in-context
      statistics rather than recall.
    - Ask for improvement of noisy estimates, not generation from nothing:
      the model's measured edge is shrinkage - small, surgical adjustments
      concentrated where samples are noisy.
    - Compact JSON out, ids only: parse failures at 148 units were zero
      under this shape.
    """
    lines = []
    for row in rows:
        hist = ", ".join(f"{p}: {float(v):g}" for p, v in row["history"])
        note = f" [{row['sample_note']}]" if row.get("sample_note") else ""
        lines.append(f"{row['id']} ({row['description']}): {hist}{note}")
    example_ids = [r["id"] for r in rows[:2]] or ["u1", "u2"]
    example = "{" + ", ".join(f'"{i}": 3.2' for i in example_ids) + "}"
    return (
        f'Forecast "{metric_label}" ({units}) for {target_period} for every '
        "unit below.\n"
        "You are given each unit's observed history. Treat the observations "
        "as noisy evidence of the underlying level: use the trend, "
        "mean-reversion, and cross-unit comparison to produce your best "
        "estimate of the TRUE value - small samples deserve shrinkage toward "
        "comparable units. Do not use knowledge of events after the last "
        "observation shown.\n"
        f"Units:\n" + "\n".join(lines) + "\n"
        f"Return ONLY a compact JSON object mapping EVERY unit id to its "
        f"forecast numeric value in {units}, like {example} - all "
        f"{len(rows)} ids, no other text."
    )


def murphy_skill(forecast: float, baseline: float, realized: float) -> float | None:
    """1 - |forecast err| / |baseline err|; None when the baseline is exact."""
    baseline_err = abs(baseline - realized)
    if baseline_err == 0.0:
        return 0.0 if forecast == realized else None
    return 1.0 - abs(forecast - realized) / baseline_err


def score_ladder(
    forecast: float,
    realized: float,
    baselines: LadderBaselines,
) -> dict:
    """Score one resolved forecast against every naive rung."""
    return {
        "error": forecast - realized,
        "abs_error": abs(forecast - realized),
        "skill_vs_carry_forward": murphy_skill(
            forecast, baselines.carry_forward, realized
        ),
        "skill_vs_linear_drift": murphy_skill(
            forecast, baselines.linear_drift, realized
        ),
    }
