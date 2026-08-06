"""The fundamentals benchmark: stats pinned, panel frozen, results consistent."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import fundamentals_benchmark as bench

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "standards" / "fundamentals_benchmark"


class StatsTests(unittest.TestCase):
    def test_median_ape_scale_free(self) -> None:
        actual = {"a": 100.0, "b": 10.0, "c": 1.0}
        pred = {"a": 110.0, "b": 11.0, "c": 1.1}  # 10% off everywhere
        self.assertAlmostEqual(bench.median_ape(pred, actual), 0.10, places=12)

    def test_ols_projects_a_perfect_trend(self) -> None:
        self.assertAlmostEqual(
            bench.ols_project([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], 4.0), 8.0, places=10
        )

    def test_score_carry_against_itself_is_zero_skill(self) -> None:
        actual = {f"t{i}": float(i) for i in range(12)}
        carry = {f"t{i}": float(i) + 1.0 for i in range(12)}
        row = bench.score(carry, actual, carry)
        self.assertEqual(row["mae_skill_vs_carry"], 0.0)
        self.assertEqual(row["medape_skill_vs_carry"], 0.0)


class PanelTests(unittest.TestCase):
    def test_frozen_panel_shape(self) -> None:
        panel = bench.load_panel()
        self.assertGreaterEqual(len(panel), 55)
        for ticker, metrics in panel.items():
            self.assertTrue(set(metrics) <= set(bench.METRICS), ticker)
            for series in metrics.values():
                for year, value in series.items():
                    int(year)
                    self.assertIsInstance(value, (int, float), f"{ticker}/{year}")

    def test_every_cell_has_enough_companies(self) -> None:
        panel = bench.load_panel()
        for metric in bench.METRICS:
            for target in bench.TARGETS:
                _, _, actual = bench.cell_units(panel, metric, target)
                self.assertGreaterEqual(
                    len(actual), 25, f"{metric}/{target}: {len(actual)}"
                )


class CommittedResultsTests(unittest.TestCase):
    def test_results_complete_and_consistent(self) -> None:
        results = json.loads((BASE / "results" / "benchmark_results.json").read_text())
        self.assertEqual(set(results), set(bench.METRICS))
        for metric, years in results.items():
            self.assertEqual(set(years), {str(t) for t in bench.TARGETS}, metric)
            for year, row in years.items():
                self.assertGreaterEqual(row["n_companies"], 25, f"{metric}/{year}")
                self.assertEqual(row["carry_forward"]["mae_skill_vs_carry"], 0.0)
                self.assertEqual(row["carry_forward"]["medape_skill_vs_carry"], 0.0)
                for rung in ("carry_forward", "linear_drift"):
                    for stat in ("spearman", "mae_skill_vs_carry",
                                 "medape_skill_vs_carry"):
                        self.assertIn(stat, row[rung], f"{metric}/{year}/{rung}")

    def test_committed_naive_rungs_reproduce_from_frozen_panel(self) -> None:
        results = json.loads((BASE / "results" / "benchmark_results.json").read_text())
        panel = bench.load_panel()
        for metric in bench.METRICS:
            for target in bench.TARGETS:
                fresh = bench.run_cell(panel, metric, target, "unused", llm=False)
                committed = results[metric][str(target)]
                for rung in ("carry_forward", "linear_drift"):
                    self.assertEqual(
                        fresh[rung], committed[rung], f"{metric}/{target}/{rung}"
                    )


if __name__ == "__main__":
    unittest.main()
