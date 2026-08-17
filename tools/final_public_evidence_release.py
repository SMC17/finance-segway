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


def partition_cases(cases: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Split public cases into (baseline, final cohort, pass-through).

    This release path owns exactly the twenty-four models in EXPECTED_ALL_IDS:
    it regenerates the final cohort from the registries and re-verifies the
    baseline.  Public cases belonging to any *other* domain are pass-through --
    a domain added after the twenty-fourth is built and owned by its own
    builder, and this tool must neither regenerate nor drop it.
    """
    baseline: list[dict] = []
    final_cohort: list[dict] = []
    passthrough: list[dict] = []
    for item in cases:
        model_id = item.get("model_id")
        if model_id in final_public_evidence.EXPECTED_FINAL_IDS:
            final_cohort.append(item)
        elif model_id in final_public_evidence.EXPECTED_ALL_IDS:
            baseline.append(item)
        else:
            passthrough.append(item)
    return baseline, final_cohort, passthrough


def restore_verified_baseline() -> dict:
    """Rewrite the ledger as baseline + pass-through, dropping the final cohort.

    materialize() regenerates the final cohort immediately afterwards; dropping
    it here is what makes the release idempotent.

    Every count below is DERIVED from the registries.  An earlier revision froze
    them as literals -- 36 baseline cases over 18 models here, 48 over 24 in
    materialize() -- which had two consequences.  Every domain launched after
    the twenty-fourth reddened this workflow with a stale-count error that looks
    like an off-by-two typo; and the tempting fix, bumping the literal, would
    have let the write below run with the new domains still absent from
    `expected_models`, silently deleting their cases from the committed ledger.
    The guard was load-bearing, so the fix is to derive the shape rather than
    to re-freeze it at a larger number.
    """
    index = final_public_evidence.read_json(final_public_evidence.PUBLIC_INDEX)
    baseline_cases, _, passthrough = partition_cases(index.get("cases", []))
    expected_models = (
        final_public_evidence.EXPECTED_ORIGINAL_IDS
        | final_public_evidence.EXPECTED_FRONTIER_IDS
    )
    models = {item["model_id"] for item in baseline_cases}
    if models != expected_models:
        raise ValueError(
            f"baseline model ids {sorted(models)} do not match expected {sorted(expected_models)}"
        )
    expected_cases = 2 * len(expected_models)
    if len(baseline_cases) != expected_cases:
        raise ValueError(
            f"expected {expected_cases} verified baseline cases (two per baseline "
            f"model) after removing final cohort, found {len(baseline_cases)}"
        )
    cases = sorted(
        baseline_cases + passthrough,
        key=lambda item: (
            item["model_id"],
            item["case_type"],
            item["case_id"],
        ),
    )
    baseline = {
        "schema_version": "1.1",
        "as_of": index.get("as_of"),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": len(cases),
        "evidence_models": len({item["model_id"] for item in cases}),
        "cases": cases,
    }
    _write(final_public_evidence.PUBLIC_INDEX, baseline)
    return baseline


def run(*, generate_instances: bool, require_instances: bool) -> dict:
    restore_verified_baseline()
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
