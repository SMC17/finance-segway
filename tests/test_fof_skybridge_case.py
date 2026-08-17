"""Guardrails for the Fund of Funds domain's adversarial public case (SkyBridge)."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "fof-public-skybridge-fy2023-stress"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / "29_Fund_of_Funds" / "sources" / "snapshots" / f"{CASE_ID}.json"
RAW_PATH = ROOT / "tools" / "data_fabric" / "out" / "SKYBRIDGE_sec_ncsr_fy2023_stress.json"


class FofSkybridgeCaseTests(unittest.TestCase):
    def test_registered_in_index(self) -> None:
        index = json.loads((ROOT / "standards/public_cases/index.json").read_text(encoding="utf-8"))
        matches = [c for c in index["cases"] if c["case_id"] == CASE_ID]
        self.assertEqual(1, len(matches))
        entry = matches[0]
        self.assertEqual("29", entry["model_id"])
        self.assertEqual("adversarial", entry["case_type"])
        self.assertFalse(entry["counts_toward_m4"])
        self.assertTrue((ROOT / entry["output"]).exists())

    def test_two_cases_satisfy_release_shape(self) -> None:
        index = json.loads((ROOT / "standards/public_cases/index.json").read_text(encoding="utf-8"))
        domain_29_cases = [c for c in index["cases"] if c["model_id"] == "29"]
        self.assertEqual(2, len(domain_29_cases))
        self.assertEqual(
            {"conventional", "adversarial"}, {c["case_type"] for c in domain_29_cases}
        )

    def test_manifest_sources_real_sec_filing(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual("external_historical_case", manifest["classification"])
        self.assertFalse(manifest["counts_toward_M4"])
        for source in manifest["sources"]:
            self.assertIn("sec.gov", source["url"])
        self.assertFalse(manifest["lineage"]["synthetic_benchmark_inputs_allowed"])

    def test_ftx_position_is_real_and_written_to_zero(self) -> None:
        raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        holdings = raw["captured_values"]["top_8_positions_by_cost_usd"]
        ftx = next(h for h in holdings if "FTX" in h["name"])
        self.assertGreater(ftx["cost"], 0)
        self.assertEqual(0, ftx["fair_value"])

    def test_top_8_selected_by_cost_not_fair_value(self) -> None:
        raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        holdings = raw["captured_values"]["top_8_positions_by_cost_usd"]
        costs = [h["cost"] for h in holdings]
        self.assertEqual(costs, sorted(costs, reverse=True))
        fair_values = [h["fair_value"] for h in holdings]
        self.assertFalse(fair_values == sorted(fair_values, reverse=True))

    def test_no_fabricated_position_level_distribution_history(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        distributed_cells = [
            item for item in manifest["inputs"]
            if item["sheet"] == "Underlying Fund Portfolio" and item["cell"].startswith("G")
        ]
        self.assertEqual(8, len(distributed_cells))
        for item in distributed_cells:
            self.assertEqual(0.0, item["value"])

    def test_snapshot_hash_matches_index(self) -> None:
        index = json.loads((ROOT / "standards/public_cases/index.json").read_text(encoding="utf-8"))
        entry = next(c for c in index["cases"] if c["case_id"] == CASE_ID)
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(entry["snapshot_sha256"], snapshot["snapshot_sha256"])

    def test_realized_outcome_matches_disclosed_return(self) -> None:
        index = json.loads((ROOT / "standards/public_cases/index.json").read_text(encoding="utf-8"))
        entry = next(c for c in index["cases"] if c["case_id"] == CASE_ID)
        raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            raw["captured_values"]["one_year_total_return_series_g"],
            entry["outcome"]["realized"],
        )
        self.assertEqual("recorded", entry["outcome"]["status"])


if __name__ == "__main__":
    unittest.main()
