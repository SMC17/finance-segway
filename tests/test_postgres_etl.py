"""Contract tests for the optional real-only Postgres query layer."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools import postgres_etl


ROOT = Path(__file__).resolve().parents[1]


class PostgresETLTests(unittest.TestCase):
    def test_registry_is_real_only_and_all_workbooks_exist(self) -> None:
        postgres_etl.validate_registry()
        self.assertEqual(
            {"home_depot_2023", "macys_2020_adversarial"},
            set(postgres_etl.DEALS),
        )
        for metadata in postgres_etl.DEALS.values():
            self.assertEqual("real_public", metadata["classification"])
            self.assertTrue((ROOT / metadata["path"]).is_file())

    def test_synthetic_registry_entry_fails_closed(self) -> None:
        registry = {
            "invalid": {
                "path": "03_Private_Equity/instances/benchmark_case.xlsx",
                "classification": "synthetic_benchmark",
            }
        }
        with self.assertRaisesRegex(ValueError, "only 'real_public' is accepted"):
            postgres_etl.validate_registry(registry)

    def test_registered_workbooks_extract_required_outputs(self) -> None:
        for deal_id, metadata in postgres_etl.DEALS.items():
            payload = postgres_etl.extract_deal(deal_id, metadata["path"])
            self.assertTrue(payload["assumptions"], deal_id)
            self.assertTrue(payload["sources_uses"], deal_id)
            self.assertTrue(payload["debt_schedule"], deal_id)
            selected = postgres_etl.selected_return_summary(payload)
            self.assertIn("Sponsor MOIC", selected, deal_id)
            self.assertIn("Sponsor IRR", selected, deal_id)

    def test_schema_accepts_real_public_only(self) -> None:
        schema = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
        self.assertIn("CHECK (classification = 'real_public')", schema)
        self.assertNotIn("synthetic_benchmark", schema)


if __name__ == "__main__":
    unittest.main()
