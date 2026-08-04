from pathlib import Path
import unittest

from tools.run_consulting_reference_case import DEFAULT_CASE, run_case


class ConsultingReferenceCaseTests(unittest.TestCase):
    def test_synthetic_case_integrates_value_chain_portfolio_agent_and_evidence(self):
        result = run_case(DEFAULT_CASE)
        self.assertTrue(result["synthetic"])
        self.assertTrue(result["evidence"]["ledger_valid"])
        self.assertEqual(result["quote_control"]["status"], "completed")
        self.assertTrue(result["operating_model"]["bottlenecks"])
        self.assertTrue(result["initiative_portfolio"]["selection"]["selected_case_ids"])
        self.assertEqual(result["knowledge"]["results"][0]["document_id"], "pricing-policy")
        self.assertGreater(float(result["refounding"]["annual_value_created"]), 0)
        self.assertEqual(
            result["limitations"][2],
            "No external system was read, written, or contacted.",
        )

    def test_reference_case_is_committed_and_synthetic(self):
        self.assertTrue(Path(DEFAULT_CASE).is_file())


if __name__ == "__main__":
    unittest.main()
