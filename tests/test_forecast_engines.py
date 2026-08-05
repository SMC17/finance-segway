"""The naive ladder, the elicitation contract, and skill arithmetic."""
from __future__ import annotations

import json
import unittest

from tools.forecast_engines import (
    LadderBaselines,
    murphy_skill,
    naive_ladder,
    score_ladder,
    statistician_prompt,
)


class NaiveLadderTests(unittest.TestCase):
    def test_carry_forward_is_last_observation(self) -> None:
        ladder = naive_ladder([("2023", 10.0), ("2024", 12.0), ("2025", 11.0)])
        self.assertEqual(ladder.carry_forward, 11.0)

    def test_linear_drift_extends_a_perfect_trend(self) -> None:
        ladder = naive_ladder([("q1", 1.0), ("q2", 2.0), ("q3", 3.0)])
        self.assertAlmostEqual(ladder.linear_drift, 4.0, places=10)

    def test_flat_history_drifts_nowhere(self) -> None:
        ladder = naive_ladder([("a", 5.0), ("b", 5.0), ("c", 5.0)])
        self.assertAlmostEqual(ladder.linear_drift, 5.0, places=10)
        self.assertEqual(ladder.carry_forward, 5.0)

    def test_single_observation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            naive_ladder([("only", 1.0)])


class SkillTests(unittest.TestCase):
    def test_beating_the_baseline_is_positive_skill(self) -> None:
        # baseline off by 4, forecast off by 1 -> skill 0.75
        self.assertAlmostEqual(murphy_skill(103.0, 100.0, 104.0), 0.75)

    def test_losing_to_the_baseline_is_negative_skill(self) -> None:
        self.assertLess(murphy_skill(90.0, 100.0, 104.0), 0.0)

    def test_exact_baseline_yields_none_not_division_error(self) -> None:
        self.assertIsNone(murphy_skill(90.0, 104.0, 104.0))
        self.assertEqual(murphy_skill(104.0, 104.0, 104.0), 0.0)

    def test_score_ladder_reports_every_rung(self) -> None:
        result = score_ladder(
            forecast=103.0,
            realized=104.0,
            baselines=LadderBaselines(carry_forward=100.0, linear_drift=102.0),
        )
        self.assertAlmostEqual(result["skill_vs_carry_forward"], 0.75)
        self.assertAlmostEqual(result["skill_vs_linear_drift"], 0.5)
        self.assertAlmostEqual(result["abs_error"], 1.0)


class ElicitationContractTests(unittest.TestCase):
    ROWS = [
        {"id": "u1", "description": "Segment one",
         "history": [("2023", 4.1), ("2024", 4.4)], "sample_note": "n=54"},
        {"id": "u2", "description": "Segment two",
         "history": [("2023", 2.0), ("2024", 1.8)], "sample_note": None},
    ]

    def test_every_unit_appears_with_its_evidence(self) -> None:
        prompt = statistician_prompt("Inflation", "%", "2025", self.ROWS)
        self.assertIn("u1 (Segment one): 2023: 4.1, 2024: 4.4 [n=54]", prompt)
        self.assertIn("u2 (Segment two): 2023: 2, 2024: 1.8", prompt)

    def test_contract_clauses_present(self) -> None:
        # Each clause is load-bearing per the measured ablations - pin them.
        prompt = statistician_prompt("Inflation", "%", "2025", self.ROWS)
        self.assertIn("noisy evidence", prompt)                 # improve, don't generate
        self.assertIn("shrinkage toward", prompt)               # the measured mechanism
        self.assertIn("Do not use knowledge of events after", prompt)  # leak guard
        self.assertIn("ONLY a compact JSON object", prompt)     # parse contract
        self.assertIn("all 2 ids", prompt)

    def test_example_json_is_valid(self) -> None:
        prompt = statistician_prompt("Inflation", "%", "2025", self.ROWS)
        start = prompt.rfind("like ") + len("like ")
        end = prompt.index("}", start) + 1
        parsed = json.loads(prompt[start:end])
        self.assertIn("u1", parsed)


if __name__ == "__main__":
    unittest.main()
