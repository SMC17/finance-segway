"""Idempotent release entrypoint for the nine-domain public evidence expansion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from tools import frontier_evidence
except ModuleNotFoundError:
    import frontier_evidence


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def restore_verified_existing_baseline() -> dict:
    """Retain only the original nine flagship cases before regeneration.

    The expansion materializer merges its cases into the existing 18-case
    flagship index. After the first release the committed index contains 36
    cases, so a rerun first reconstructs the verified flagship-only baseline.
    No workbook, manifest, snapshot or receipt is deleted.
    """

    index = frontier_evidence.read_json(frontier_evidence.PUBLIC_INDEX)
    cases = [
        item
        for item in index.get("cases", [])
        if item.get("model_id") in frontier_evidence.EXPECTED_EXISTING_IDS
    ]
    if len(cases) != 18:
        raise ValueError(
            f"expected 18 verified existing flagship cases, found {len(cases)}"
        )
    baseline = {
        "schema_version": "1.0",
        "as_of": index.get("as_of"),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": 18,
        "cases": sorted(
            cases,
            key=lambda item: (
                item["model_id"],
                item["case_type"],
                item["case_id"],
            ),
        ),
    }
    _write(frontier_evidence.PUBLIC_INDEX, baseline)
    return baseline


def run(
    *,
    generate_instances: bool,
    require_instances: bool,
) -> dict:
    restore_verified_existing_baseline()
    frontier_evidence.materialize(generate_instances)
    return frontier_evidence.validate(require_instances)


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
