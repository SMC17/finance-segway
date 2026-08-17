"""Guardrails for the Fund of Funds domain's real public case (HLPAF)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "fof-public-hlpaf-2026"
MANIFEST_PATH = ROOT / "standards" / "public_cases" / f"{CASE_ID}.json"
SNAPSHOT_PATH = ROOT / "29_Fund_of_Funds" / "sources" / "snapshots" / f"{CASE_ID}.json"
NCSR_PATH = ROOT / "tools" / "data_fabric" / "out" / "HLPAF_sec_ncsr_annual_report.json"


class FofHlpafCaseTests(unittest.TestCase):
    def test_registered_in_index(self) -> None:
        index = json.loads((ROOT / "standards/public_cases/index.json").read_text(encoding="utf-8"))
        matches = [c for c in index["cases"] if c["case_id"] == CASE_ID]
        self.assertEqual(1, len(matches))
        entry = matches[0]
        self.assertEqual("29", entry["model_id"])
        self.assertFalse(entry["counts_toward_m4"])
        self.assertEqual((ROOT / entry["output"]).exists(), True)

    def test_manifest_sources_real_sec_filing(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual("external_historical_case", manifest["classification"])
        self.assertFalse(manifest["counts_toward_M4"])
        for source in manifest["sources"]:
            self.assertIn("sec.gov", source["url"])
        self.assertFalse(manifest["lineage"]["synthetic_benchmark_inputs_allowed"])

    def test_no_fabricated_position_level_history(self) -> None:
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

    def test_underlying_positions_trace_to_ncsr_source_data(self) -> None:
        ncsr = json.loads(NCSR_PATH.read_text(encoding="utf-8"))
        holdings = ncsr["captured_values"]["top_8_secondary_fund_positions_usd"]
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        names = {
            item["value"] for item in manifest["inputs"]
            if item["sheet"] == "Underlying Fund Portfolio" and item["cell"].startswith("B")
        }
        self.assertEqual({h["name"] for h in holdings}, names)


if __name__ == "__main__":
    unittest.main()
