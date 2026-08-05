"""Fail-closed guards for the consulting wing's real-data-only policy."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _contains_synthetic_true(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "synthetic" and child is True)
            or _contains_synthetic_true(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_synthetic_true(child) for child in value)
    return False


class ConsultingRealDataPolicyTests(unittest.TestCase):
    def test_synthetic_business_case_directories_are_absent(self) -> None:
        self.assertFalse((ROOT / "consulting" / "reference_cases").exists())
        self.assertFalse((ROOT / "standards" / "consulting" / "benchmarks").exists())

    def test_consulting_json_never_asserts_synthetic_evidence(self) -> None:
        violations: list[str] = []
        for base in (ROOT / "consulting", ROOT / "standards" / "consulting"):
            for path in sorted(base.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                if _contains_synthetic_true(payload):
                    violations.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], violations)

    def test_no_platform_claims_a2_without_real_evidence(self) -> None:
        catalog = json.loads(
            (ROOT / "standards" / "consulting" / "capability_catalog.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {"A1"},
            {entry["maturity"] for entry in catalog["platform_capabilities"]},
        )
        self.assertTrue(
            all(not entry.get("evidence_paths") for entry in catalog["platform_capabilities"])
        )


if __name__ == "__main__":
    unittest.main()
