"""Stdlib statistics in the benchmark runner, pinned against known values."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import forecast_benchmark as bench

ROOT = Path(__file__).resolve().parents[1]


class StdlibStatsTests(unittest.TestCase):
    def test_spearman_perfect_and_inverse(self) -> None:
        a = {"x": 1.0, "y": 2.0, "z": 3.0, "w": 4.0, "v": 5.0,
             "u": 6.0, "t": 7.0, "s": 8.0, "r": 9.0, "q": 10.0}
        self.assertAlmostEqual(bench.spearman(a, a), 1.0, places=12)
        inv = {k: -v for k, v in a.items()}
        self.assertAlmostEqual(bench.spearman(inv, a), -1.0, places=12)

    def test_spearman_handles_ties_and_small_n(self) -> None:
        tied = {f"k{i}": 1.0 for i in range(12)}
        self.assertIsNone(bench.spearman(tied, {f"k{i}": float(i) for i in range(12)}))
        self.assertIsNone(bench.spearman({"a": 1.0}, {"a": 1.0}))  # n < 10

    def test_rank_averages_ties(self) -> None:
        self.assertEqual(bench.rank([10.0, 20.0, 20.0, 30.0]), [1.0, 2.5, 2.5, 4.0])

    def test_ols_projects_a_perfect_trend(self) -> None:
        self.assertAlmostEqual(
            bench.ols_project([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], 4.0), 8.0, places=10
        )

    def test_mae(self) -> None:
        self.assertAlmostEqual(
            bench.mae({"a": 1.0, "b": 3.0}, {"a": 2.0, "b": 1.0}), 1.5
        )


class CommittedResultsTests(unittest.TestCase):
    def test_results_file_is_complete_and_consistent(self) -> None:
        results = json.loads(
            (ROOT / "standards" / "forecast_protocol_benchmark" / "results"
             / "benchmark_results.json").read_text()
        )
        self.assertEqual(set(results), set(bench.INDICATORS))
        for ind, years in results.items():
            self.assertEqual(set(years), {str(t) for t in bench.TARGETS}, ind)
            for year, row in years.items():
                self.assertGreaterEqual(row["n_countries"], 50, f"{ind}/{year}")
                for rung in ("carry_forward", "linear_drift"):
                    self.assertIn("mae_skill_vs_carry", row[rung])
                # carry-forward's skill against itself is identically zero
                self.assertEqual(row["carry_forward"]["mae_skill_vs_carry"], 0.0)


if __name__ == "__main__":
    unittest.main()
