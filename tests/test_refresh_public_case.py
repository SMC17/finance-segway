import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import refresh_public_case


class RefreshPublicCaseTests(unittest.TestCase):
    def test_refresh_is_scoped_and_updates_the_receipt_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "standards/public_cases/index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(
                json.dumps(
                    {
                        "case_count": 1,
                        "cases": [
                            {
                                "case_id": "real-case",
                                "manifest": "standards/public_cases/real-case.json",
                                "output": "domain/instances/real-case.xlsx",
                                "receipt": {"workbook_sha256": "old"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            manifest = root / "standards/public_cases/real-case.json"
            manifest.write_text("{}", encoding="utf-8")
            receipt = {"workbook_sha256": "new"}
            with patch.object(
                refresh_public_case, "apply_manifest", return_value=receipt
            ) as generator:
                result = refresh_public_case.refresh_public_cases(
                    root, ["real-case"]
                )

            generator.assert_called_once_with(manifest, root.resolve())
            updated = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["cases"][0]["receipt"], receipt)
            self.assertEqual(result["refreshed"][0]["workbook_sha256"], "new")

    def test_unknown_case_fails_before_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "standards/public_cases/index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(
                json.dumps({"case_count": 0, "cases": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "unknown public case ids"):
                refresh_public_case.refresh_public_cases(root, ["missing"])

    def test_duplicate_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "case ids must be unique"):
                refresh_public_case.refresh_public_cases(
                    Path(directory), ["duplicate", "duplicate"]
                )


if __name__ == "__main__":
    unittest.main()
