from pathlib import Path
import unittest

from tools.run_consulting_benchmarks import BENCHMARK_DIR, run_all, run_manifest


class ConsultingBenchmarkTests(unittest.TestCase):
    def test_all_committed_benchmarks_pass_a2_control_plane_gate(self):
        result = run_all(BENCHMARK_DIR)
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["benchmark_count"], 2)
        self.assertTrue(result["all_eligible_for_a2"])
        for benchmark in result["benchmarks"]:
            self.assertEqual(benchmark["evaluation"]["pass_rate"], 1)
            self.assertEqual(benchmark["evaluation"]["adversarial_pass_rate"], 1)
            self.assertTrue(benchmark["promotion"]["eligible"])
            self.assertEqual(benchmark["promotion"]["target_maturity"], "A2")
            self.assertGreater(benchmark["process_assessment"]["variant_count"], 1)
            self.assertLess(benchmark["process_assessment"]["conformance_rate"], 1)
            self.assertEqual(
                benchmark["limitations"][2],
                "No external system was read, written, messaged, or mutated.",
            )

    def test_quote_benchmark_underwrites_uncertainty_and_exit_value(self):
        path = BENCHMARK_DIR / "quote_to_cash.json"
        result = run_manifest(path)
        self.assertGreater(result["simulation"]["iterations"], 1000)
        self.assertGreater(result["simulation"]["probability_positive_npv"], 0)
        self.assertGreater(result["capacity_simulation"]["throughput_per_hour"], 0)
        self.assertGreater(result["capacity_simulation"]["total_rework_events"], 0)
        self.assertGreater(result["value_creation"]["bridge"]["equity_value_uplift"], 0)
        self.assertGreater(result["value_creation"]["bridge"]["moic_uplift"], 0)
        self.assertTrue(result["value_creation"]["hundred_day_plan"]["within_100_days"])
        self.assertEqual(result["value_creation"]["hundred_day_plan"]["unresolved_gate_ids"], [])

    def test_benchmark_manifests_are_committed_machine_readable_inputs(self):
        self.assertEqual(
            {path.name for path in Path(BENCHMARK_DIR).glob("*.json")},
            {"procure_to_pay.json", "quote_to_cash.json"},
        )


if __name__ == "__main__":
    unittest.main()
