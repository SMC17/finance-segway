"""Forecast-protocol benchmark: country macro indicators, four elicitation rungs.

Reproducible evidence base for the forecast-engines protocol and the L3 skill
gate. Task: for each (indicator, target year) cell, predict every country's
year-T value from the CIA World Factbook archive (open API, editions
1990-2026). Ladder per cell:

  carry_forward   value at T-2 - the persistence bar every forecast must beat
  linear_drift    least squares over T-5..T-2 projected to T
  llm_recall      country name + year only, NO evidence: a memorization probe
  llm_statistician the forecast_engines protocol: every country in one prompt,
                  four years of observed history each, asked to improve noisy
                  estimates

Metric: MAE-skill vs carry-forward (1 - MAE/MAE_carry) and rank correlation.
The decisive read across target years 2016/2020/2023/2025: statistician skill
is stable while recall swings wildly - evidence-in-prompt is skill,
zero-evidence recall is memory, and memory inverts in regime breaks.

Stdlib-only (this repository's dependency policy); LLM rungs shell out to the
Claude Code CLI (`claude -p`) and are skipped unless it is installed and
authenticated. Data via standards/forecast_protocol_benchmark/fetch_data.sh. Committed results:
results/benchmark_results.json (run 2026-08-05, claude-opus-5).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "standards" / "forecast_protocol_benchmark"
DATA = BASE / "data"
CACHE = BASE / "llm_cache"

INDICATORS = {
    "inflation": ("Inflation rate, consumer prices", "%"),
    "pop_growth": ("Population growth rate", "%"),
    "gdp_percap": ("Real GDP per capita (PPP)", "$"),
    "mil_pct_gdp": ("Military expenditure", "% of GDP"),
}
TARGETS = [2016, 2020, 2023, 2025]
EVIDENCE_OFFSETS = [-5, -4, -3, -2]


# ----------------------------------------------------------- stdlib statistics
def rank(values: list[float]) -> list[float]:
    """Average ranks (ties shared), 1-indexed."""
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


def spearman(pred: dict[str, float], actual: dict[str, float]) -> float | None:
    ks = [k for k in actual if k in pred]
    if len(ks) < 10:
        return None
    ra, rb = rank([pred[k] for k in ks]), rank([actual[k] for k in ks])
    n = len(ks)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((a - ma) * (b - mb) for a, b in zip(ra, rb))
    va = sum((a - ma) ** 2 for a in ra)
    vb = sum((b - mb) ** 2 for b in rb)
    if va == 0 or vb == 0:
        return None
    return cov / (va * vb) ** 0.5


def mae(pred: dict[str, float], actual: dict[str, float]) -> float:
    ks = [k for k in actual if k in pred]
    return sum(abs(pred[k] - actual[k]) for k in ks) / len(ks)


def ols_project(xs: list[float], ys: list[float], x_target: float) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return slope * x_target + (my - slope * mx)


# ------------------------------------------------------------------- data I/O
def load_year(ind: str, year: int) -> dict[str, float]:
    path = DATA / f"{ind}.{year}.json"
    if not path.exists():
        return {}
    obj = json.loads(path.read_text())
    return {r["iso2"]: float(r["value"]) for r in obj.get("rankings", [])
            if r.get("value") is not None and r.get("iso2")}


def country_names(ind: str, year: int) -> dict[str, str]:
    obj = json.loads((DATA / f"{ind}.{year}.json").read_text())
    return {r["iso2"]: r["country"] for r in obj.get("rankings", [])
            if r.get("iso2")}


# ------------------------------------------------------------------ LLM rungs
def claude_available() -> bool:
    return shutil.which("claude") is not None


def call_claude(prompt: str, model: str) -> str:
    out = subprocess.run(["claude", "-p", prompt, "--model", model],
                         capture_output=True, text=True, timeout=1500)
    return out.stdout


def parse(text: str, countries: list[str]) -> dict[str, float] | None:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        obj = json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None
    rec = {}
    for c in countries:
        if c in obj:
            try:
                rec[c] = float(obj[c])
            except (TypeError, ValueError):
                pass
    return rec if len(rec) >= len(countries) * 0.85 else None


def recall_prompt(label, units, target, names, countries):
    rows = "\n".join(f"{c}: {names.get(c, c)}" for c in countries)
    example = json.dumps({countries[0]: 3.2, countries[1]: -0.5})
    return (f'From the CIA World Factbook, what was each country\'s "{label}" '
            f"({units}) for {target}?\nCountries:\n{rows}\n"
            f"Return ONLY compact JSON mapping every ISO2 code to the numeric "
            f"value in {units}, like {example}. If unsure, give your best "
            f"estimate. All {len(countries)} codes, no other text.")


def statistician_prompt(label, units, target, ev_years, ev, names, countries):
    lines = []
    for c in countries:
        hist = ", ".join(f"{y}: {ev[y][c]:g}" for y in ev_years)
        lines.append(f"{c} ({names.get(c, c)}): {hist}")
    example = json.dumps({countries[0]: 3.2, countries[1]: -0.5})
    return (f'Forecast each country\'s "{label}" ({units}) for {target}.\n'
            f"You are given the observed values for {ev_years[0]}-{ev_years[-1]}. "
            f"Use the trend, mean-reversion, and what you know about each "
            f"economy UP TO {ev_years[-1]} - do not use knowledge of events "
            f"after {ev_years[-1]}.\nHistory:\n" + "\n".join(lines) + "\n"
            f"Return ONLY compact JSON mapping every ISO2 code to the forecast "
            f"numeric value in {units}, like {example}. "
            f"All {len(countries)} codes, no other text.")


def interval_prompt(label, units, target, ev_years, ev, names, countries):
    lines = []
    for c in countries:
        hist = ", ".join(f"{y}: {ev[y][c]:g}" for y in ev_years)
        lines.append(f"{c} ({names.get(c, c)}): {hist}")
    example = json.dumps({countries[0]: [3.2, 2.1, 4.6],
                          countries[1]: [-0.5, -1.4, 0.3]})
    return (f'Forecast each country\'s "{label}" ({units}) for {target}.\n'
            f"You are given the observed values for {ev_years[0]}-{ev_years[-1]}. "
            f"Use the trend, mean-reversion, and what you know about each "
            f"economy UP TO {ev_years[-1]} - do not use knowledge of events "
            f"after {ev_years[-1]}.\nHistory:\n" + "\n".join(lines) + "\n"
            f"For each country return [point, low, high] where [low, high] is "
            f"your central 80% interval: across all countries, the realized "
            f"{target} value should fall inside the interval about 80% of the "
            f"time. Widths must reflect each country's own volatility and your "
            f"uncertainty - volatile histories deserve wide intervals, stable "
            f"ones narrow. Do not give uniformly wide or uniformly narrow "
            f"bands.\nReturn ONLY compact JSON mapping every ISO2 code to "
            f"[point, low, high] in {units}, like {example}. "
            f"All {len(countries)} codes, no other text.")


def parse_intervals(text: str, countries: list[str]) -> dict | None:
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        obj = json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return None
    rec = {}
    for c in countries:
        v = obj.get(c)
        if isinstance(v, list) and len(v) == 3:
            try:
                point, low, high = (float(x) for x in v)
            except (TypeError, ValueError):
                continue
            if low > high:
                low, high = high, low
            rec[c] = (point, low, high)
    return rec if len(rec) >= len(countries) * 0.85 else None


def run_interval_cell(ind: str, target: int, model: str) -> dict:
    label, units = INDICATORS[ind]
    ev_years = [target + o for o in EVIDENCE_OFFSETS]
    ev = {y: load_year(ind, y) for y in ev_years}
    tgt = load_year(ind, target)
    names = country_names(ind, target)
    countries = sorted(set(tgt) & set.intersection(*(set(v) for v in ev.values())))
    if len(countries) < 50:
        return {"error": f"only {len(countries)} countries"}
    actual = {c: tgt[c] for c in countries}
    carry = {c: ev[ev_years[-1]][c] for c in countries}
    cpath = CACHE / f"{ind}.{target}.intervals.{model}.json"
    if cpath.exists():
        rec = {c: tuple(v) for c, v in json.loads(cpath.read_text()).items()}
    else:
        rec = None
        for _ in range(2):
            rec = parse_intervals(
                call_claude(interval_prompt(label, units, target, ev_years, ev,
                                            names, countries), model),
                countries)
            if rec:
                break
        if rec is None:
            return {"error": "unparseable", "n_countries": len(countries)}
        CACHE.mkdir(exist_ok=True)
        cpath.write_text(json.dumps({c: list(v) for c, v in rec.items()}))
    ks = sorted(rec)
    points = {c: rec[c][0] for c in ks}
    inside = [1 if rec[c][1] <= actual[c] <= rec[c][2] else 0 for c in ks]
    widths = sorted(rec[c][2] - rec[c][1] for c in ks)
    sub_actual = {c: actual[c] for c in ks}
    sub_carry_mae = mae({c: carry[c] for c in ks}, sub_actual)
    return {
        "n_countries": len(countries),
        "n_parsed": len(ks),
        "coverage": round(sum(inside) / len(inside), 3),
        "point_skill_vs_carry": round(1 - mae(points, sub_actual) / sub_carry_mae, 3),
        "median_width": round(widths[len(widths) // 2], 4),
        "median_abs_actual": round(sorted(abs(v) for v in sub_actual.values())[len(ks) // 2], 4),
    }


# ------------------------------------------------------------------ the grid
def run_cell(ind: str, target: int, model: str, llm: bool) -> dict:
    label, units = INDICATORS[ind]
    ev_years = [target + o for o in EVIDENCE_OFFSETS]
    ev = {y: load_year(ind, y) for y in ev_years}
    tgt = load_year(ind, target)
    names = country_names(ind, target)
    countries = sorted(set(tgt) & set.intersection(*(set(v) for v in ev.values())))
    if len(countries) < 50:
        return {"error": f"only {len(countries)} countries"}
    actual = {c: tgt[c] for c in countries}
    carry = {c: ev[ev_years[-1]][c] for c in countries}
    drift = {c: ols_project([float(y) for y in ev_years],
                            [ev[y][c] for y in ev_years], float(target))
             for c in countries}

    row: dict = {"n_countries": len(countries)}
    mae_carry = mae(carry, actual)
    for name, pred in (("carry_forward", carry), ("linear_drift", drift)):
        row[name] = {
            "spearman": round(spearman(pred, actual) or 0.0, 3),
            "mae_skill_vs_carry": round(1 - mae(pred, actual) / mae_carry, 3),
        }
    if not llm:
        return row

    for mode in ("recall", "statistician"):
        cpath = CACHE / f"{ind}.{target}.{mode}.{model}.json"
        if cpath.exists():
            rec = json.loads(cpath.read_text())
        else:
            prompt = (recall_prompt(label, units, target, names, countries)
                      if mode == "recall" else
                      statistician_prompt(label, units, target, ev_years, ev,
                                          names, countries))
            rec = None
            for _ in range(2):
                rec = parse(call_claude(prompt, model), countries)
                if rec:
                    break
            if rec is None:
                row[f"llm_{mode}"] = {"error": "unparseable"}
                continue
            CACHE.mkdir(exist_ok=True)
            cpath.write_text(json.dumps(rec))
        sub_actual = {c: actual[c] for c in rec}
        sub_carry_mae = mae({c: carry[c] for c in rec}, sub_actual)
        row[f"llm_{mode}"] = {
            "spearman": round(spearman(rec, sub_actual) or 0.0, 3),
            "mae_skill_vs_carry": round(1 - mae(rec, sub_actual) / sub_carry_mae, 3),
            "n": len(rec),
        }
        print(f"[{ind}/{target}/{mode}] {row[f'llm_{mode}']}", flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--no-llm", action="store_true",
                    help="naive rungs only (no CLI required)")
    ap.add_argument("--intervals", action="store_true",
                    help="interval-calibration grid (requires the CLI); "
                         "writes results/interval_rerun.json")
    args = ap.parse_args()
    if args.intervals:
        if not claude_available():
            raise SystemExit("--intervals requires an authenticated claude CLI")
        report = {ind: {str(t): run_interval_cell(ind, t, args.model)
                        for t in TARGETS} for ind in INDICATORS}
        out = BASE / "results" / "interval_rerun.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return
    llm = not args.no_llm and claude_available()
    if not llm and not args.no_llm:
        print("claude CLI not found - running naive rungs only")
    report = {ind: {str(t): run_cell(ind, t, args.model, llm)
                    for t in TARGETS} for ind in INDICATORS}
    out = BASE / "results" / ("rerun_results.json" if llm else "naive_rungs.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
