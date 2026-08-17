"""Mutation tests for the release-shape gate.

The rule this replaces lived in a workflow heredoc, so nothing could exercise
it. Every test below is a mutation the gate must reject -- including the two
that the old aggregate form (``case_count == 2 * evidence_models``) accepted.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import verify_release_shape

ROOT = Path(__file__).resolve().parents[1]


def inventory(**overrides: str) -> dict:
    """24 models at M2 by default; overrides set a model's declared maturity."""
    models = [{"id": f"{n:02d}", "declared_maturity": "M2"} for n in range(1, 25)]
    models.extend(
        {"id": model_id, "declared_maturity": level}
        for model_id, level in overrides.items()
    )
    return {"models": models}


def index(pairs: dict[str, int]) -> dict:
    """Build a ledger carrying `pairs[model_id]` cases for each model."""
    cases = [
        {
            "case_id": f"case-{model_id}-{n}",
            "model_id": model_id,
            "case_type": "conventional" if n == 0 else "adversarial",
        }
        for model_id, count in pairs.items()
        for n in range(count)
    ]
    return {
        "case_count": len(cases),
        "evidence_models": len({case["model_id"] for case in cases}),
        "cases": cases,
    }


def paired(**overrides: int) -> dict:
    pairs = {f"{n:02d}": 2 for n in range(1, 25)}
    pairs.update(overrides)
    return index({k: v for k, v in pairs.items() if v})


class ReleaseShapeTests(unittest.TestCase):
    def test_released_cohort_passes(self) -> None:
        self.assertEqual([], verify_release_shape.check(inventory(), paired()))

    def test_m1_domain_with_one_case_is_allowed(self) -> None:
        # The regression this gate was rewritten for: a domain launching at M1
        # with its first case, adversarial pair still in the next PR, must not
        # redden main. The old aggregate form failed here (49 != 2 * 25).
        errors = verify_release_shape.check(
            inventory(**{"31": "M1"}), paired(**{"31": 1})
        )
        self.assertEqual([], errors)

    def test_m1_domain_with_no_cases_is_allowed(self) -> None:
        errors = verify_release_shape.check(inventory(**{"29": "M1"}), paired())
        self.assertEqual([], errors)

    def test_m2_model_carrying_one_case_is_named(self) -> None:
        errors = verify_release_shape.check(
            inventory(**{"30": "M2"}), paired(**{"30": 1})
        )
        self.assertEqual(1, len(errors))
        self.assertIn("30 (M2) has 1 public cases, expected 2", errors[0])

    def test_m2_model_carrying_three_cases_is_named(self) -> None:
        errors = verify_release_shape.check(inventory(), paired(**{"07": 3}))
        self.assertEqual(1, len(errors))
        self.assertIn("07 (M2) has 3 public cases, expected 2", errors[0])

    def test_offsetting_shortfall_and_surplus_no_longer_hides(self) -> None:
        # THE blind spot in the aggregate rule: one model at 1 and another at 3
        # still totals 48 cases over 24 models, so `case_count == 2 * models`
        # passed while two models were individually wrong. Both are now named.
        ledger = paired(**{"07": 1, "11": 3})
        self.assertEqual(48, ledger["case_count"])
        self.assertEqual(24, ledger["evidence_models"])
        self.assertEqual(
            ledger["case_count"], 2 * ledger["evidence_models"], "old rule accepted this"
        )
        errors = verify_release_shape.check(inventory(), ledger)
        self.assertEqual(1, len(errors))
        self.assertIn("07 (M2) has 1 public cases", errors[0])
        self.assertIn("11 (M2) has 3 public cases", errors[0])

    def test_summary_case_count_may_not_drift_from_the_list(self) -> None:
        ledger = paired()
        ledger["case_count"] = 999
        errors = verify_release_shape.check(inventory(), ledger)
        self.assertTrue(any("disagrees with 48 listed cases" in e for e in errors))

    def test_summary_model_count_may_not_drift_from_the_list(self) -> None:
        ledger = paired()
        ledger["evidence_models"] = 99
        errors = verify_release_shape.check(inventory(), ledger)
        self.assertTrue(any("disagrees with 24 distinct models" in e for e in errors))

    def test_case_referencing_an_unknown_model_is_caught(self) -> None:
        ledger = paired()
        ledger["cases"].append(
            {"case_id": "ghost", "model_id": "99", "case_type": "conventional"}
        )
        ledger["case_count"] = len(ledger["cases"])
        ledger["evidence_models"] = len({c["model_id"] for c in ledger["cases"]})
        errors = verify_release_shape.check(inventory(), ledger)
        self.assertTrue(any("absent from the inventory: ['99']" in e for e in errors))

    def test_m2_cohort_may_not_shrink(self) -> None:
        shrunk = inventory()
        shrunk["models"] = shrunk["models"][:23]
        ledger = index({f"{n:02d}": 2 for n in range(1, 24)})
        errors = verify_release_shape.check(shrunk, ledger)
        self.assertTrue(any("M2 cohort regressed below 24" in e for e in errors))

    def test_ledger_may_not_regress_below_the_floor(self) -> None:
        ledger = index({f"{n:02d}": 2 for n in range(1, 24)})
        errors = verify_release_shape.check(inventory(), ledger)
        self.assertTrue(any("regressed below 48 cases" in e for e in errors))

    def test_invalid_declared_maturity_is_rejected(self) -> None:
        errors = verify_release_shape.check(
            inventory(**{"30": "M0"}), paired(**{"30": 2})
        )
        self.assertTrue(any("invalid declared maturities: ['M0']" in e for e in errors))

    def test_reintroduced_benchmark_directory_is_rejected(self) -> None:
        errors = verify_release_shape.check(
            inventory(), paired(), benchmark_dir_exists=True
        )
        self.assertTrue(any("synthetic benchmark directory" in e for e in errors))


class CommittedStateTests(unittest.TestCase):
    def test_committed_ledger_satisfies_the_shape_contract(self) -> None:
        payload = verify_release_shape.report()
        self.assertEqual("PASS", payload["status"], payload["errors"])


if __name__ == "__main__":
    unittest.main()
