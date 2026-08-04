from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import unittest

from openpyxl import Workbook

from tools.generate_release_evidence import build_evidence


class ReleaseEvidenceTests(unittest.TestCase):
    def create_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        workbook = Workbook()
        workbook.active["A1"] = 1
        workbook.active["A2"] = "=A1+1"
        workbook.save(root / "model.xlsx")
        (root / "builder.py").write_text("print('builder')\n", encoding="utf-8")
        standards = root / "standards"
        standards.mkdir()
        inventory = {
            "version": "test",
            "models": [{
                "id": "01",
                "domain": "Test",
                "workbook": "model.xlsx",
                "builder": "builder.py",
                "declared_maturity": "M2",
                "required_engines": ["engine"],
                "required_perspectives": ["owner"],
                "reference_checks": ["check"],
            }],
        }
        (standards / "model_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "fixture"],
            cwd=root,
            check=True,
        )

    def test_release_evidence_hashes_artifact_and_builder(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_repo(root)
            evidence = build_evidence(root, "test-release", ["01"])
            self.assertEqual(evidence["status"], "PASS")
            self.assertEqual(len(evidence["models"]), 1)
            artifact = evidence["models"][0]
            self.assertEqual(len(artifact["workbook_sha256"]), 64)
            self.assertEqual(len(artifact["builder_sha256"]), 64)
            self.assertEqual(artifact["formula_count"], 1)

    def test_missing_model_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_repo(root)
            with self.assertRaisesRegex(ValueError, "missing inventory models"):
                build_evidence(root, "test-release", ["99"])


if __name__ == "__main__":
    unittest.main()
