"""Company-fundamentals forecast benchmark: the ladder on the registry's own
metric class.

The forecast-protocol benchmark (standards/forecast_protocol_benchmark/)
measured the four-rung ladder on country macro indicators - mean-reverting
rates and ratios. But the registry's live registrations are company
fundamentals: balance-sheet totals and revenue for growing issuers, which
TREND. Whether carry-forward still beats linear drift there, and whether the
statistician protocol's edge transfers, was an open question this benchmark
answers with committed, reproducible measurements.

Panel: 62 large-cap issuers (diversified sectors), annual Assets / Revenue / NetIncome distilled
from SEC EDGAR companyfacts (standards/fundamentals_benchmark/data/panel.json,
harvested by harvest.py; per fiscal year the latest-filed value is kept, so
restatements win - every rung sees the same series, keeping ladder
comparisons fair; values $bn; observations keyed by the calendar year the
fiscal year ends in).

Grid: 3 metrics x 4 target years (2019 / 2021 / 2023 / 2025), evidence =
target-5 .. target-2, exactly the forecast-protocol benchmark's shape. Rungs:
carry-forward, linear drift (OLS), zero-evidence LLM recall, and the
forecast_engines statistician protocol. Alongside Spearman and MAE skill,
each rung reports median-APE skill vs carry-forward - company sizes span
three orders of magnitude, and a scale-free error line keeps one giant from
dominating the read.

Stdlib only. LLM rungs shell out to the Claude Code CLI when present
(committed results are the record; nothing here runs inference in CI).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "standards" / "fundamentals_benchmark"
DATA = BASE / "data" / "panel.json"
CACHE = BASE / "llm_cache"

METRICS = {"assets": "total assets", "revenue": "total revenue",
           "net_income": "net income"}
TARGETS = [2019, 2021, 2023, 2025]
EVIDENCE_OFFSETS = [-5, -4, -3, -2]


# ------------------------------------------------------------------ stats
def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(pred: dict, actual: dict) -> float | None:
    ks = [k for k in actual if k in pred]
    if len(ks) < 10:
        return None
    ra = rank([actual[k] for k in ks])
    rp = rank([pred[k] for k in ks])
    ma, mp = sum(ra) / len(ra), sum(rp) / len(rp)
    num = sum((a - ma) * (p - mp) for a, p in zip(ra, rp))
    da = sum((a - ma) ** 2 for a in ra) ** 0.5
    dp = sum((p - mp) ** 2 for p in rp) ** 0.5
    if da == 0 or dp == 0:
        return None
    return num / (da * dp)


def mae(pred: dict, actual: dict) -> float:
    ks = [k for k in actual if k in pred]
    return sum(abs(pred[k] - actual[k]) for k in ks) / len(ks)


def median_ape(pred: dict, actual: dict) -> float:
    apes = sorted(abs(pred[k] - actual[k]) / abs(actual[k])
                  for k in actual if k in pred and actual[k])
    return apes[len(apes) // 2]


def ols_project(xs: list[float], ys: list[float], x: float) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((v - mx) ** 2 for v in xs)
    slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / denom if denom else 0.0
    return my + slope * (x - mx)


# ------------------------------------------------------------------ data
def load_panel() -> dict:
    return json.loads(DATA.read_text())


def cell_units(panel: dict, metric: str, target: int) -> tuple[list[int], dict, dict]:
    ev_years = [target + o for o in EVIDENCE_OFFSETS]
    ev, actual = {}, {}
    for ticker, metrics in panel.items():
        series = metrics.get(metric, {})
        if str(target) not in series:
            continue
        if any(str(y) not in series for y in ev_years):
            continue
        ev[ticker] = {y: series[str(y)] for y in ev_years}
        actual[ticker] = series[str(target)]
    return ev_years, ev, actual


# ------------------------------------------------------------------ LLM rungs
def claude_available() -> bool:
    return shutil.which("claude") is not None


def call_claude(prompt: str, model: str) -> str:
    out = subprocess.run(["claude", "-p", prompt, "--model", model],
                         capture_output=True, text=True, timeout=1500)
    return out.stdout


def parse(text: str, tickers: list[str]) -> dict | None:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        obj = json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None
    rec = {}
    for t in tickers:
        if t in obj:
            try:
                rec[t] = float(obj[t])
            except (TypeError, ValueError):
                pass
    return rec if len(rec) >= len(tickers) * 0.85 else None


def recall_prompt(label, target, tickers):
    example = json.dumps({tickers[0]: 123.4, tickers[1]: 56.7})
    return (f"From SEC filings, what was each company's {label} (USD billions) "
            f"for its fiscal year ending in calendar {target}?\n"
            f"Tickers: {', '.join(tickers)}\n"
            f"Return ONLY compact JSON mapping every ticker to the value in "
            f"$bn, like {example}. If unsure, give your best estimate. "
            f"All {len(tickers)} tickers, no other text.")


def statistician_prompt(label, target, ev_years, ev, tickers):
    lines = []
    for t in tickers:
        hist = ", ".join(f"FY{y}: {ev[t][y]:g}" for y in ev_years)
        lines.append(f"{t}: {hist}")
    example = json.dumps({tickers[0]: 123.4, tickers[1]: 56.7})
    return (f"Forecast each company's {label} (USD billions) for its fiscal "
            f"year ending in calendar {target}.\n"
            f"You are given the observed values for fiscal years ending "
            f"{ev_years[0]}-{ev_years[-1]}. Use the trend, mean-reversion, "
            f"and what you know about each company UP TO {ev_years[-1]} - do "
            f"not use knowledge of events after {ev_years[-1]}.\n"
            f"History:\n" + "\n".join(lines) + "\n"
            f"Return ONLY compact JSON mapping every ticker to the forecast "
            f"value in $bn, like {example}. All {len(tickers)} tickers, "
            f"no other text.")


# ------------------------------------------------------------------ the grid
def score(pred: dict, actual: dict, carry: dict) -> dict:
    sub_actual = {k: actual[k] for k in pred}
    sub_carry = {k: carry[k] for k in pred}
    return {
        "spearman": round(spearman(pred, sub_actual) or 0.0, 3),
        "mae_skill_vs_carry": round(1 - mae(pred, sub_actual) / mae(sub_carry, sub_actual), 3),
        "medape_skill_vs_carry": round(
            1 - median_ape(pred, sub_actual) / median_ape(sub_carry, sub_actual), 3),
        "n": len(pred),
    }


def run_cell(panel: dict, metric: str, target: int, model: str, llm: bool) -> dict:
    label = METRICS[metric]
    ev_years, ev, actual = cell_units(panel, metric, target)
    tickers = sorted(actual)
    if len(tickers) < 25:
        return {"error": f"only {len(tickers)} companies"}
    carry = {t: ev[t][ev_years[-1]] for t in tickers}
    drift = {t: ols_project([float(y) for y in ev_years],
                            [ev[t][y] for y in ev_years], float(target))
             for t in tickers}
    row: dict = {"n_companies": len(tickers)}
    for name, pred in (("carry_forward", carry), ("linear_drift", drift)):
        row[name] = score(pred, actual, carry)
    if not llm:
        return row
    for mode in ("recall", "statistician"):
        cpath = CACHE / f"{metric}.{target}.{mode}.{model}.json"
        if cpath.exists():
            rec = json.loads(cpath.read_text())
        else:
            prompt = (recall_prompt(label, target, tickers) if mode == "recall"
                      else statistician_prompt(label, target, ev_years, ev, tickers))
            rec = None
            for _ in range(2):
                rec = parse(call_claude(prompt, model), tickers)
                if rec:
                    break
            if rec is None:
                row[f"llm_{mode}"] = {"error": "unparseable"}
                continue
            CACHE.mkdir(exist_ok=True)
            cpath.write_text(json.dumps(rec))
        row[f"llm_{mode}"] = score(rec, actual, carry)
        print(f"[{metric}/{target}/{mode}] {row[f'llm_{mode}']}", flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--no-llm", action="store_true",
                    help="naive rungs only (no CLI required)")
    args = ap.parse_args()
    llm = not args.no_llm and claude_available()
    if not llm and not args.no_llm:
        print("claude CLI not found - running naive rungs only")
    panel = load_panel()
    report = {m: {str(t): run_cell(panel, m, t, args.model, llm)
                  for t in TARGETS} for m in METRICS}
    out = BASE / "results" / ("rerun.json" if llm else "naive_rungs.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
