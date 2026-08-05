"""Register forecasts before their outcomes exist; score them when they resolve.

Every outcome row in the repo today was authored knowing the answer -
retrospective reconstruction is honest evidence of model mechanics, but it can
never demonstrate forward accuracy, and M4 explicitly requires "evidence
generated over time rather than documents generated in one release." This tool
is the mechanism that starts that clock, built on two disciplines the
forecasting-accountability literature (and every prediction platform that has
survived scrutiny) converges on:

1. Pre-registration. A forecast is a dated, content-hashed JSON record
   committed to git BEFORE its resolution window. The registration hash pins
   the payload: editing the point, metric, dates, or baseline after
   registration breaks the hash and fails --check. Git history supplies the
   tamper-evident timestamp; the hash makes drift inside a commit detectable.

2. Baseline skill scoring. Every forecast must declare, at registration, the
   naive baseline it claims to beat (for example last-recorded value or
   random walk) with the baseline's value frozen from data already in the
   repository. At resolution the score is not "how close was the forecast"
   but "how much closer than naive": skill = 1 - |forecast - realized| /
   |baseline - realized| (Murphy skill; positive beats naive, negative loses
   to it). A forecast with no declared baseline is unfalsifiable bragging and
   is rejected.

Registration files live in standards/forecasts/, one JSON per forecast.
outcome_class must be "out_of_sample_forecast" here by construction -
retrospective reconstructions and same-period reproduction checks belong in
the existing outcome logs, not this registry.

Usage:
    python tools/forecast_registration.py --check [--report out.json]
    python tools/forecast_registration.py --register standards/forecasts/f.json
    python tools/forecast_registration.py --resolve <forecast_id> \
        --realized 123.4 --source "Issuer FY2026 Form 10-K"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORECAST_DIR = ROOT / "standards" / "forecasts"

ALLOWED_OUTCOME_CLASSES = {"out_of_sample_forecast"}
ALLOWED_BASIS = {"naive_last_recorded", "naive_random_walk", "modeled"}
ALLOWED_BASELINE_KINDS = {"naive_last_recorded", "naive_random_walk"}
REGISTRATION_FIELDS = (
    "forecast_id",
    "case_id",
    "model_id",
    "metric",
    "outcome_class",
    "point",
    "interval",
    "basis",
    "baseline",
    "registered_on",
    "resolve_by",
    "resolution_source_expected",
)


def _canonical_registration_bytes(record: dict[str, Any]) -> bytes:
    payload = {field: record.get(field) for field in REGISTRATION_FIELDS}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def registration_sha256(record: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_registration_bytes(record)).hexdigest()


def _parse_date(name: str, value: Any, errors: list[str]) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        errors.append(f"{name} must be an ISO date, got {value!r}")
        return None


def validate_record(record: dict[str, Any], *, today: date | None = None) -> list[str]:
    """Return every violation in one registration record (empty = valid)."""
    today = today or date.today()
    errors: list[str] = []
    for field in ("forecast_id", "case_id", "model_id", "metric"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append(f"missing or empty {field}")

    if record.get("outcome_class") not in ALLOWED_OUTCOME_CLASSES:
        errors.append(
            "outcome_class must be 'out_of_sample_forecast' - retrospective "
            "reconstructions belong in the outcome logs, not this registry"
        )
    if record.get("basis") not in ALLOWED_BASIS:
        errors.append(f"basis must be one of {sorted(ALLOWED_BASIS)}")

    point = record.get("point")
    if not isinstance(point, (int, float)) or isinstance(point, bool):
        errors.append("point must be a number")

    interval = record.get("interval")
    if interval is not None:
        if (
            not isinstance(interval, list)
            or len(interval) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in interval)
            or interval[0] > interval[1]
        ):
            errors.append("interval must be null or [low, high] with low <= high")

    baseline = record.get("baseline")
    if not isinstance(baseline, dict):
        errors.append("baseline is required: a forecast without a declared naive baseline is unfalsifiable")
    else:
        if baseline.get("kind") not in ALLOWED_BASELINE_KINDS:
            errors.append(f"baseline.kind must be one of {sorted(ALLOWED_BASELINE_KINDS)}")
        if not isinstance(baseline.get("value"), (int, float)) or isinstance(baseline.get("value"), bool):
            errors.append("baseline.value must be a number frozen at registration")
        if not isinstance(baseline.get("source"), str) or not baseline["source"].strip():
            errors.append("baseline.source must name where the frozen baseline value comes from")

    registered_on = _parse_date("registered_on", record.get("registered_on"), errors)
    resolve_by = _parse_date("resolve_by", record.get("resolve_by"), errors)
    if registered_on and registered_on > today:
        errors.append(f"registered_on {registered_on} is in the future")
    if registered_on and resolve_by and resolve_by <= registered_on:
        errors.append(
            f"resolve_by {resolve_by} must be after registered_on {registered_on}: "
            "a forecast whose window is already closed at registration is hindsight"
        )
    if not isinstance(record.get("resolution_source_expected"), str) or not record["resolution_source_expected"].strip():
        errors.append("resolution_source_expected must name the public document that will resolve this")

    stored_hash = record.get("registration_sha256")
    if stored_hash is not None and stored_hash != registration_sha256(record):
        errors.append(
            "registration_sha256 does not match the payload - a registered "
            "field was edited after registration"
        )

    resolution = record.get("resolution")
    if resolution is not None:
        if not isinstance(resolution, dict):
            errors.append("resolution must be null or an object")
        else:
            if not isinstance(resolution.get("realized"), (int, float)) or isinstance(resolution.get("realized"), bool):
                errors.append("resolution.realized must be a number")
            if not isinstance(resolution.get("realized_source"), str) or not resolution["realized_source"].strip():
                errors.append("resolution.realized_source is required")
            resolved_on = _parse_date("resolution.resolved_on", resolution.get("resolved_on"), errors)
            if resolved_on and registered_on and resolved_on <= registered_on:
                errors.append(
                    "resolution.resolved_on must be after registered_on - a "
                    "forecast resolved the day it was registered is not out-of-sample"
                )
            if isinstance(resolution.get("realized"), (int, float)) and isinstance(point, (int, float)):
                expected = score(record, float(resolution["realized"]))
                for key, value in expected.items():
                    if resolution.get(key) != value:
                        errors.append(
                            f"resolution.{key} is {resolution.get(key)!r} but scoring "
                            f"the registered payload gives {value!r}"
                        )
    return errors


def score(record: dict[str, Any], realized: float) -> dict[str, Any]:
    """Deterministic scores for a resolved forecast."""
    point = float(record["point"])
    baseline_value = float(record["baseline"]["value"])
    error = point - realized
    abs_error = abs(error)
    baseline_abs_error = abs(baseline_value - realized)
    if baseline_abs_error == 0.0:
        skill = 0.0 if abs_error == 0.0 else None
    else:
        skill = 1.0 - abs_error / baseline_abs_error
    interval = record.get("interval")
    interval_hit = None
    if interval is not None:
        interval_hit = bool(interval[0] <= realized <= interval[1])
    return {
        "error": error,
        "abs_error": abs_error,
        "baseline_abs_error": baseline_abs_error,
        "skill_vs_baseline": skill,
        "interval_hit": interval_hit,
    }


def draft_registration(
    *,
    forecast_id: str,
    case_id: str,
    model_id: str,
    metric: str,
    point: float,
    history: list[tuple[str, float]],
    resolve_by: str,
    resolution_source_expected: str,
    interval: list[float] | None = None,
    basis: str = "modeled",
    registered_on: str | None = None,
) -> dict[str, Any]:
    """Build a complete, valid registration record from an estimate + history.

    The bridge an agent tool calls after producing a forward number: the
    naive baseline is frozen automatically as the carry-forward of the most
    recent history observation (period, value), so no caller can forget to
    declare the line it must beat. `interval` is optional [low, high]; the
    honest producer in this repository is a scenario range (e.g. the
    Base/Downside spread of the instance workbook that produced the point) -
    LLM-elicited intervals are not benchmarked and should not be recorded as
    if they were. Raises ValueError with every violation rather than
    returning a record the registry would refuse.
    """
    if not history:
        raise ValueError("history must contain at least one (period, value) observation")
    last_period, last_value = history[-1]
    record: dict[str, Any] = {
        "forecast_id": forecast_id,
        "case_id": case_id,
        "model_id": model_id,
        "metric": metric,
        "outcome_class": "out_of_sample_forecast",
        "point": point,
        "interval": list(interval) if interval is not None else None,
        "basis": basis,
        "baseline": {
            "kind": "naive_last_recorded",
            "value": float(last_value),
            "source": f"carry-forward of {metric} = {last_value} at {last_period}",
        },
        "registered_on": registered_on or date.today().isoformat(),
        "resolve_by": resolve_by,
        "resolution_source_expected": resolution_source_expected,
        "resolution": None,
    }
    errors = validate_record(record)
    if errors:
        raise ValueError("draft would be refused by the registry:\n  " + "\n  ".join(errors))
    return record


def load_all(directory: Path = FORECAST_DIR) -> dict[Path, dict[str, Any]]:
    records: dict[Path, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        records[path] = json.loads(path.read_text(encoding="utf-8"))
    return records


def check_all(directory: Path = FORECAST_DIR) -> dict[str, Any]:
    problems: dict[str, list[str]] = {}
    records = load_all(directory)
    ids = [record.get("forecast_id") for record in records.values()]
    duplicate_ids = sorted({i for i in ids if ids.count(i) > 1})
    resolved = pending = 0
    skills: list[float] = []
    interval_hits: list[bool] = []
    for path, record in records.items():
        errors = validate_record(record)
        if record.get("registration_sha256") is None:
            errors.append("registration_sha256 missing - run --register to stamp it")
        if errors:
            problems[path.name] = errors
        if record.get("resolution") is not None:
            resolved += 1
            skill = (record["resolution"] or {}).get("skill_vs_baseline")
            if isinstance(skill, (int, float)):
                skills.append(float(skill))
            hit = (record["resolution"] or {}).get("interval_hit")
            if isinstance(hit, bool):
                interval_hits.append(hit)
        else:
            pending += 1
    report = {
        "status": "PASS" if not problems and not duplicate_ids else "FAIL",
        "forecasts": len(records),
        "pending": pending,
        "resolved": resolved,
        "mean_skill_vs_baseline": (sum(skills) / len(skills)) if skills else None,
        "interval_coverage": (
            sum(interval_hits) / len(interval_hits) if interval_hits else None
        ),
        "duplicate_forecast_ids": duplicate_ids,
        "problems": problems,
    }
    return report


def register(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("registration_sha256") is not None:
        raise SystemExit(f"{path}: already registered; registrations are immutable")
    record.setdefault("registered_on", date.today().isoformat())
    record.setdefault("resolution", None)
    errors = validate_record(record)
    if errors:
        raise SystemExit(f"{path}: refusing to register:\n  " + "\n  ".join(errors))
    record["registration_sha256"] = registration_sha256(record)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def resolve(forecast_id: str, realized: float, source: str) -> dict[str, Any]:
    for path, record in load_all().items():
        if record.get("forecast_id") != forecast_id:
            continue
        if record.get("resolution") is not None:
            raise SystemExit(f"{forecast_id}: already resolved; resolutions are final")
        resolution = {
            "realized": realized,
            "realized_source": source,
            "resolved_on": date.today().isoformat(),
            **score(record, realized),
        }
        record["resolution"] = resolution
        errors = validate_record(record)
        if errors:
            raise SystemExit(f"{forecast_id}: resolution rejected:\n  " + "\n  ".join(errors))
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return record
    raise SystemExit(f"no registered forecast with id {forecast_id!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--register", type=Path)
    parser.add_argument("--resolve")
    parser.add_argument("--realized", type=float)
    parser.add_argument("--source")
    args = parser.parse_args()

    if args.register:
        record = register(args.register)
        print(json.dumps({"registered": record["forecast_id"], "sha256": record["registration_sha256"]}, indent=2))
        return 0
    if args.resolve:
        if args.realized is None or not args.source:
            parser.error("--resolve requires --realized and --source")
        record = resolve(args.resolve, args.realized, args.source)
        print(json.dumps(record["resolution"], indent=2))
        return 0

    report = check_all()
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
