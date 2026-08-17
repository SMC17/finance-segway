"""Idempotent release entrypoint for the final six public evidence packs.

Scoped entirely to the original 01-24 domain cohort (see
final_public_evidence.EXPECTED_ALL_IDS). Cases for any later domain (25,
29-31, and whatever comes after) are preserved across the run rather than
being reconstructed -- this tool has no model of what those domains'
evidence should look like, so it must not silently drop them.
"""
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


def _cases_outside_known_cohort(index: dict) -> list[dict]:
    """Cases for domains this release tool has no concept of (everything
    past the original 01-24 cohort -- see EXPECTED_ALL_IDS). Must be
    preserved across restore_verified_36_case_baseline()/materialize(),
    both of which only know how to reconstruct the 36+12=48-case, 24-model
    ledger from that one historical release."""
    known_ids = final_public_evidence.EXPECTED_ALL_IDS
    return [item for item in index.get("cases", []) if item.get("model_id") not in known_ids]


def _restore_preserved_cases(preserved: list[dict]) -> dict:
    index = final_public_evidence.read_json(final_public_evidence.PUBLIC_INDEX)
    if not preserved:
        return index
    by_case = {item["case_id"]: item for item in index.get("cases", [])}
    for item in preserved:
        by_case.setdefault(item["case_id"], item)
    cases = sorted(
        by_case.values(),
        key=lambda item: (item["model_id"], item["case_type"], item["case_id"]),
    )
    combined = {
        **index,
        "case_count": len(cases),
        "evidence_models": len({item["model_id"] for item in cases}),
        "cases": cases,
    }
    _write(final_public_evidence.PUBLIC_INDEX, combined)
    return combined


def restore_verified_36_case_baseline() -> dict:
    index = final_public_evidence.read_json(final_public_evidence.PUBLIC_INDEX)
    expected_models = (
        final_public_evidence.EXPECTED_ORIGINAL_IDS
        | final_public_evidence.EXPECTED_FRONTIER_IDS
    )
    cases = [item for item in index.get("cases", []) if item.get("model_id") in expected_models]
    models = {item["model_id"] for item in cases}
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
    original_index = final_public_evidence.read_json(final_public_evidence.PUBLIC_INDEX)
    preserved = _cases_outside_known_cohort(original_index)
    restore_verified_36_case_baseline()
    final_public_evidence.materialize(generate_instances)
    _restore_preserved_cases(preserved)
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
