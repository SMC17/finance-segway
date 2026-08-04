from __future__ import annotations

import unittest

from tools import validate_committed_frontier_release


class CommittedFrontierReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = validate_committed_frontier_release.validate()

    def test_committed_release_passes(self):
        self.assertEqual(self.report["status"], "PASS", msg=self.report["errors"])

    def test_exact_release_shape(self):
        self.assertEqual(self.report["inventory_models"], 24)
        self.assertEqual(self.report["maturity_distribution"], {"M2": 24})
        self.assertEqual(self.report["canonical_models"], 6)
        self.assertEqual(self.report["benchmark_instances"], 12)
        self.assertEqual(self.report["total_release_workbooks"], 18)
        self.assertEqual(self.report["benchmark_index_instances"], 48)
        self.assertEqual(set(self.report["benchmark_counts"].values()), {2})

    def test_all_committed_contracts_surfaces_and_audits_pass(self):
        self.assertEqual(len(self.report["contracts"]), 18)
        self.assertTrue(
            all(item["status"] == "PASS" for item in self.report["contracts"])
        )
        self.assertTrue(
            all(not item["errors"] for item in self.report["surfaces"])
        )
        self.assertTrue(all(not item["errors"] for item in self.report["audits"]))

    def test_all_twelve_receipts_bind_to_workbooks(self):
        self.assertEqual(len(self.report["receipts"]), 12)
        self.assertTrue(all(not item["errors"] for item in self.report["receipts"]))


if __name__ == "__main__":
    unittest.main()
