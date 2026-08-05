"""Validate the consulting capability catalog and its implementation claims."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from finance_segway.consulting.schema import BusinessFunction, RiskTier


REQUIRED_LISTS = (
    "decisions", "agent_archetypes", "metrics",
    "diagnostic_questions", "core_engines",
)


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains_synthetic_true(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "synthetic" and child is True)
            or contains_synthetic_true(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_synthetic_true(child) for child in value)
    return False


def validate_catalog(root: Path, catalog_path: Path | None = None) -> list[str]:
    path = catalog_path or root / "standards/consulting/capability_catalog.json"
    catalog = load_catalog(path)
    errors: list[str] = []
    maturities = set(catalog.get("maturity_scale", {}))
    if maturities != {"A0", "A1", "A2", "A3", "A4"}:
        errors.append("invalid_maturity_scale")
    entries = catalog.get("capabilities", [])
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_capability_id")
    expected_functions = {item.value for item in BusinessFunction}
    actual_functions = {entry.get("function") for entry in entries}
    for function in sorted(expected_functions - actual_functions):
        errors.append(f"missing_function:{function}")
    for function in sorted(actual_functions - expected_functions):
        errors.append(f"unknown_function:{function}")
    valid_risks = set(RiskTier.__members__)
    for entry in entries:
        entry_id = entry.get("id") or "<missing>"
        for field in ("executive_owner", "pnl_driver", "decision_rights", "maturity", "risk_tier"):
            if not entry.get(field):
                errors.append(f"{entry_id}:missing:{field}")
        for field in REQUIRED_LISTS:
            if not entry.get(field):
                errors.append(f"{entry_id}:missing:{field}")
        if entry.get("maturity") not in maturities:
            errors.append(f"{entry_id}:invalid_maturity")
        if entry.get("risk_tier") not in valid_risks:
            errors.append(f"{entry_id}:invalid_risk_tier")
        if entry.get("maturity") in {"A1", "A2", "A3", "A4"}:
            test_path = root / str(entry.get("test_path", ""))
            if not test_path.is_file():
                errors.append(f"{entry_id}:missing_test_path")
            for reference in entry.get("core_engines", []):
                try:
                    module_name, object_name = reference.split(":", 1)
                    module = importlib.import_module(module_name)
                    engine = getattr(module, object_name)
                    if not callable(engine):
                        errors.append(f"{entry_id}:not_callable:{reference}")
                except (ValueError, ImportError, AttributeError) as exc:
                    errors.append(f"{entry_id}:invalid_engine:{reference}:{type(exc).__name__}")
    platform_entries = catalog.get("platform_capabilities", [])
    platform_ids = [entry.get("id") for entry in platform_entries]
    if not platform_entries:
        errors.append("missing_platform_capabilities")
    if len(platform_ids) != len(set(platform_ids)):
        errors.append("duplicate_platform_capability_id")
    for entry in platform_entries:
        entry_id = entry.get("id") or "<missing-platform>"
        for field in ("purpose", "decision_rights", "maturity", "risk_tier"):
            if not entry.get(field):
                errors.append(f"{entry_id}:missing:{field}")
        if not entry.get("core_engines"):
            errors.append(f"{entry_id}:missing:core_engines")
        if entry.get("maturity") not in maturities:
            errors.append(f"{entry_id}:invalid_maturity")
        if entry.get("risk_tier") not in valid_risks:
            errors.append(f"{entry_id}:invalid_risk_tier")
        test_path = root / str(entry.get("test_path", ""))
        if not test_path.is_file():
            errors.append(f"{entry_id}:missing_test_path")
        for reference in entry.get("core_engines", []):
            try:
                module_name, object_name = reference.split(":", 1)
                module = importlib.import_module(module_name)
                engine = getattr(module, object_name)
                if not callable(engine):
                    errors.append(f"{entry_id}:not_callable:{reference}")
            except (ValueError, ImportError, AttributeError) as exc:
                errors.append(f"{entry_id}:invalid_engine:{reference}:{type(exc).__name__}")
        evidence_paths = entry.get("evidence_paths", [])
        if entry.get("maturity") in {"A2", "A3", "A4"} and not evidence_paths:
            errors.append(f"{entry_id}:missing_real_evidence_paths")
        for evidence_path in evidence_paths:
            full_path = root / str(evidence_path)
            if not full_path.is_file():
                errors.append(f"{entry_id}:missing_real_evidence:{evidence_path}")
                continue
            try:
                evidence = json.loads(full_path.read_text(encoding="utf-8"))
                if contains_synthetic_true(evidence):
                    errors.append(f"{entry_id}:synthetic_evidence_prohibited:{evidence_path}")
                if evidence.get("classification") not in {
                    "external_historical_case",
                    "public_operational_case",
                    "client_operational_case",
                }:
                    errors.append(f"{entry_id}:invalid_real_evidence_class:{evidence_path}")
                if not evidence.get("sources"):
                    errors.append(f"{entry_id}:missing_sources:{evidence_path}")
            except json.JSONDecodeError:
                errors.append(f"{entry_id}:invalid_evidence_json:{evidence_path}")

    retired_roots = (root / "consulting", root / "standards" / "consulting")
    for retired_root in retired_roots:
        for json_path in sorted(retired_root.rglob("*.json")):
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                errors.append(f"invalid_json:{json_path.relative_to(root)}")
                continue
            if contains_synthetic_true(payload):
                errors.append(f"synthetic_business_evidence:{json_path.relative_to(root)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    errors = validate_catalog(args.root.resolve(), args.catalog)
    report = {"status": "pass" if not errors else "fail", "errors": errors}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
