"""Release-shape gate: is the committed public ledger the shape it claims to be?

Three questions, none of which a frozen total can answer:

1. Has the evidenced cohort regressed?  Floors, never exact counts.
2. Do the ledger's own summary fields still describe the list beneath them?
3. Does every model carry the number of public cases its declared maturity
   promises?

Question 3 is the one that motivated extracting this out of inline workflow
YAML.  The previous form asserted ``case_count == 2 * evidence_models`` over
the whole ledger, which cannot distinguish "a domain launched an hour ago and
its adversarial pair is in the next PR" from "a model has been claiming M2
while carrying a single case for a week".  It reddened main for the entire
window between a domain launching and its pair landing, and it stayed silent
whenever one model's shortfall happened to be offset by another's surplus.

Pairing is a per-model property keyed to what each model claims: a model at M2
or above asserts it is evidenced, so it must carry its conventional/adversarial
pair; a model still launching at M1 may carry none or one while its pair is
built.

Living in a module rather than a heredoc also means the rule is unit-testable,
which the aggregate form never was.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "standards" / "model_inventory.json"
PUBLIC_INDEX = ROOT / "standards" / "public_cases" / "index.json"
BENCHMARK_DIR = ROOT / "standards" / "benchmark_cases"

#: The frontier cohort as released: 24 models at M2, two public cases each.
#: Floors, so the cohort can grow but never shrink.
M2_COHORT_FLOOR = 24
LEDGER_CASE_FLOOR = 48
LEDGER_MODEL_FLOOR = 24

#: A model at these levels asserts it is evidenced, so it owes a full pair.
EVIDENCED_LEVELS = frozenset({"M2", "M3", "M4"})
VALID_LEVELS = frozenset({"M1", "M2", "M3", "M4"})
CASES_PER_EVIDENCED_MODEL = 2


def check(
    inventory: dict[str, Any],
    index: dict[str, Any],
    *,
    benchmark_dir_exists: bool = False,
) -> list[str]:
    """Return every way the committed shape violates the contract, or []."""
    errors: list[str] = []
    models = inventory.get("models", [])
    declared = {model["id"]: model["declared_maturity"] for model in models}
    maturity = Counter(declared.values())
    cases = index.get("cases", [])
    cases_by_model = Counter(case["model_id"] for case in cases)

    if maturity.get("M2", 0) < M2_COHORT_FLOOR:
        errors.append(f"M2 cohort regressed below {M2_COHORT_FLOOR}: {dict(maturity)}")

    invalid = sorted(level for level in maturity if level not in VALID_LEVELS)
    if invalid:
        errors.append(f"invalid declared maturities: {invalid}")

    case_count = index.get("case_count", 0)
    evidence_models = index.get("evidence_models", 0)
    if case_count < LEDGER_CASE_FLOOR or evidence_models < LEDGER_MODEL_FLOOR:
        errors.append(
            f"public ledger regressed below {LEDGER_CASE_FLOOR} cases / "
            f"{LEDGER_MODEL_FLOOR} models: {case_count}/{evidence_models}"
        )

    # The summary fields may not drift from the list they summarise. A gate
    # that reads only the summary can be satisfied by a lie.
    if case_count != len(cases):
        errors.append(
            f"index case_count {case_count} disagrees with {len(cases)} listed cases"
        )
    if evidence_models != len(cases_by_model):
        errors.append(
            f"index evidence_models {evidence_models} disagrees with "
            f"{len(cases_by_model)} distinct models in the list"
        )

    unpaired: list[str] = []
    for model_id, level in sorted(declared.items()):
        found = cases_by_model.get(model_id, 0)
        if level in EVIDENCED_LEVELS and found != CASES_PER_EVIDENCED_MODEL:
            unpaired.append(
                f"{model_id} ({level}) has {found} public cases, expected "
                f"{CASES_PER_EVIDENCED_MODEL}"
            )
        elif level == "M1" and found > CASES_PER_EVIDENCED_MODEL:
            unpaired.append(
                f"{model_id} ({level}) has {found} public cases, expected at most "
                f"{CASES_PER_EVIDENCED_MODEL}"
            )
    if unpaired:
        errors.append(
            "every model at M2 or above carries exactly two public cases: "
            + "; ".join(unpaired)
        )

    orphans = sorted(set(cases_by_model) - set(declared))
    if orphans:
        errors.append(
            f"public cases reference models absent from the inventory: {orphans}"
        )

    if benchmark_dir_exists:
        errors.append("retired synthetic benchmark directory was reintroduced")

    return errors


def report() -> dict[str, Any]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    index = json.loads(PUBLIC_INDEX.read_text(encoding="utf-8"))
    errors = check(inventory, index, benchmark_dir_exists=BENCHMARK_DIR.exists())
    maturity = Counter(model["declared_maturity"] for model in inventory["models"])
    cases_by_model = Counter(case["model_id"] for case in index["cases"])
    return {
        "status": "PASS" if not errors else "FAIL",
        "maturity": dict(sorted(maturity.items())),
        "public_cases": index.get("case_count"),
        "evidenced_models": len(cases_by_model),
        "cases_by_model": dict(sorted(cases_by_model.items())),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the JSON report here")
    args = parser.parse_args()
    payload = report()
    if args.report:
        args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
