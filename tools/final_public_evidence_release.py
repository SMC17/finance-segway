"""Idempotent release entrypoint for the final six public evidence packs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from tools import final_public_evidence
except ModuleNotFoundError:
    import final_public_evidence


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def restore_verified_36_case_baseline() -> dict:
    index = final_public_evidence.read_json(final_public_evidence.PUBLIC_INDEX)
    cases = [
        item
        for item in index.get("cases", [])
        if item.get("model_id") not in final_public_evidence.EXPECTED_FINAL_IDS
    ]
    models = {item["model_id"] for item in cases}
    expected_models = (
        final_public_evidence.EXPECTED_ORIGINAL_IDS
        | final_public_evidence.EXPECTED_FRONTIER_IDS
    )
    if len(cases) != 36:
        raise ValueError(
            f"expected 36 verified baseline cases after removing final cohort, found {len(cases)}"
        )
    if models != expected_models:
        raise ValueError(
            f"baseline model ids {sorted(models)} do not match expected {sorted(expected_models)}"
        )
    baseline = {
        "schema_version": "1.1",
        "as_of": index.get("as_of"),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": 36,
        "evidence_models": 18,
        "cases": sorted(
            cases,
            key=lambda item: (
                item["model_id"],
                item["case_type"],
                item["case_id"],
            ),
        ),
    }
    _write(final_public_evidence.PUBLIC_INDEX, baseline)
    return baseline


def run(*, generate_instances: bool, require_instances: bool) -> dict:
    restore_verified_36_case_baseline()
    final_public_evidence.materialize(generate_instances)
    return final_public_evidence.validate(require_instances)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-instances", action="store_true")
    parser.add_argument("--require-instances", action="store_true")
    args = parser.parse_args()
    report = run(
        generate_instances=args.generate_instances,
        require_instances=args.require_instances,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "total_evidence_models": report["total_evidence_models"],
                "total_public_cases": report["total_public_cases"],
                "errors": report["errors"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
