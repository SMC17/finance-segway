"""Repository-level guardrails for the real-data-only evidence policy."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _walk_json(value: object, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "synthetic" and child is True:
                violations.append(child_path)
            violations.extend(_walk_json(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(_walk_json(child, f"{path}[{index}]"))
    return violations


class RealDataOnlyTests(unittest.TestCase):
    def test_synthetic_business_evidence_corpus_is_absent(self) -> None:
        self.assertFalse((ROOT / "standards" / "benchmark_cases").exists())
        artifacts = sorted(
            path.relative_to(ROOT).as_posix()
            for path in ROOT.glob("[0-9][0-9]_*/instances/benchmark_*")
        )
        self.assertEqual([], artifacts)

    def test_synthetic_generators_and_research_artifacts_are_absent(self) -> None:
        named_synthetic = sorted(
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "synthetic" in path.name.lower()
            and "tests" not in path.parts
        )
        self.assertEqual([], named_synthetic)

        research_data = sorted(
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "research", ROOT / "analytics")
            if root.exists()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".csv", ".parquet", ".xlsx", ".json"}
        )
        self.assertEqual([], research_data)

    def test_committed_json_does_not_assert_synthetic_evidence(self) -> None:
        violations: list[str] = []
        for path in sorted(ROOT.rglob("*.json")):
            if ".git" in path.parts:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            for location in _walk_json(payload):
                violations.append(f"{path.relative_to(ROOT)}:{location}")
        self.assertEqual([], violations)

    def test_public_case_index_is_complete_and_real_only(self) -> None:
        index = json.loads(
            (ROOT / "standards" / "public_cases" / "index.json").read_text(
                encoding="utf-8"
            )
        )
        cases = index["cases"]
        # Ratchet floors, not exact counts: the corpus grows as new domains and
        # adversarial pairs land, so an exact assertEqual here breaks on every
        # legitimate addition (this test itself was that stale assertion until
        # the etf-public-kweb-2026-stress case tripped it). What must always
        # hold: the index's own summary fields are not allowed to drift from
        # what's actually in the list, and the corpus never shrinks.
        self.assertGreaterEqual(len(cases), 50)
        self.assertGreaterEqual(len({case["model_id"] for case in cases}), 26)
        self.assertEqual(index["case_count"], len(cases))
        self.assertEqual(
            index["evidence_models"], len({case["model_id"] for case in cases})
        )
        for case in cases:
            manifest = json.loads(
                (ROOT / case["manifest"]).read_text(encoding="utf-8")
            )
            self.assertFalse(
                manifest.get("lineage", {}).get(
                    "synthetic_benchmark_inputs_allowed", True
                ),
                case["manifest"],
            )


if __name__ == "__main__":
    unittest.main()
