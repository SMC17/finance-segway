from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import validate_legacy_release_workbooks


class LegacyReleaseWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="legacy-release-test-")
        cls.output_dir = Path(cls.temp.name)
        cls.report = validate_legacy_release_workbooks.build_and_validate(cls.output_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_all_six_release_workbooks_build(self):
        self.assertEqual(self.report["status"], "PASS", msg=self.report["errors"])
        self.assertEqual(self.report["models"], 6)
        self.assertEqual(
            {item["model_id"] for item in self.report["results"]},
            set(validate_legacy_release_workbooks.SPECS),
        )

    def test_every_release_clears_formula_depth(self):
        for result in self.report["results"]:
            minimum = validate_legacy_release_workbooks.SPECS[result["model_id"]][
                "minimum_formulas"
            ]
            self.assertGreaterEqual(result["formulas"], minimum, msg=result)

    def test_every_required_sheet_is_present(self):
        for model_id, spec in validate_legacy_release_workbooks.SPECS.items():
            path = self.output_dir / spec["filename"]
            result = validate_legacy_release_workbooks.validate_workbook(model_id, path)
            self.assertEqual(result["status"], "PASS", msg=result["errors"])

    def test_inventory_is_not_implicitly_promoted_to_candidate_builders(self):
        inventory = json.loads(
            (validate_legacy_release_workbooks.ROOT / "standards/model_inventory.json").read_text(
                encoding="utf-8"
            )
        )
        inventory_by_id = {item["id"]: item for item in inventory["models"]}
        registry = json.loads(
            (
                validate_legacy_release_workbooks.ROOT
                / "standards/frontier/legacy_engine_registry.json"
            ).read_text(encoding="utf-8")
        )
        for model in registry["models"]:
            self.assertEqual(
                inventory_by_id[model["model_id"]]["builder"],
                model["current_builder"],
            )
            self.assertNotEqual(
                inventory_by_id[model["model_id"]]["builder"],
                model["candidate_builder"],
            )


if __name__ == "__main__":
    unittest.main()
