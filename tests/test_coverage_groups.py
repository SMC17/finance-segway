"""Tests for the coverage-group taxonomy and the public source stack."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from verify_coverage_groups import assess  # noqa: E402

COVERAGE = ROOT / "standards" / "universe" / "coverage_groups.json"
SOURCE_STACK = ROOT / "standards" / "universe" / "source_stack.json"
INVENTORY = ROOT / "standards" / "model_inventory.json"


class CoverageGroupTests(unittest.TestCase):
    def test_report_is_consistent(self) -> None:
        report = assess()
        self.assertEqual("PASS", report["status"], msg=report["errors"])

    def test_every_serving_domain_exists_in_the_inventory(self) -> None:
        inventory_ids = {item["id"] for item in json.loads(INVENTORY.read_text())["models"]}
        coverage = json.loads(COVERAGE.read_text())
        for kind in ("product_groups", "sector_groups"):
            for group in coverage[kind]:
                for model_id in group.get("serving_domains", []):
                    self.assertIn(model_id, inventory_ids, msg=f"{group['id']} -> {model_id}")

    def test_no_firm_names_or_rankings_are_encoded(self) -> None:
        # The source material was a subjective tier list of banks. Only the
        # coverage-group vocabulary was taken from it -- encoding firm names
        # or their relative standing would assert opinion as repo data.
        # Checks structural fields only: the provenance note legitimately
        # mentions rankings in order to disclaim them.
        coverage = json.loads(COVERAGE.read_text())
        structural: list[str] = []
        for kind in ("product_groups", "sector_groups"):
            for group in coverage[kind]:
                structural.append(group["id"])
                structural.append(group["label"])
                structural.extend(group.get("aliases", []))
                structural.extend(group.get("subsectors", []))
        blob = " ".join(structural).lower()

        for firm in (
            "goldman", "morgan stanley", "jpmorgan", "j.p. morgan", "evercore",
            "lazard", "moelis", "centerview", "pjt", "jefferies", "barclays",
            "citi", "ubs", "rothschild", "houlihan", "guggenheim", "macquarie",
        ):
            self.assertNotIn(firm, blob, msg=f"firm name leaked into structure: {firm!r}")
        for token in ("tier", "s++", "ranking", "best "):
            self.assertNotIn(token, blob, msg=f"ranking language in structure: {token!r}")

    def test_every_group_declares_why_it_is_distinct(self) -> None:
        coverage = json.loads(COVERAGE.read_text())
        for group in coverage["sector_groups"]:
            self.assertTrue(
                group.get("distinct_modeling_needs"),
                msg=f"{group['id']} declares no distinct modeling needs -- if it has none, "
                "it is not a separate sector group",
            )
        for group in coverage["product_groups"]:
            self.assertTrue(group.get("core_analytics"), msg=group["id"])

    def test_sector_depth_is_the_reported_gap(self) -> None:
        # Guards the finding this taxonomy exists to surface: product
        # archetypes are broadly covered while sector depth is not.
        report = assess()
        self.assertEqual(report["product_groups"], report["product_groups_covered"])
        self.assertLess(report["sector_groups_covered"], report["sector_groups"])
        self.assertGreater(report["total_subsectors_declared"], 40)


class SourceStackTests(unittest.TestCase):
    def test_every_source_has_a_url_and_states_what_it_grounds(self) -> None:
        stack = json.loads(SOURCE_STACK.read_text())
        self.assertTrue(stack["sources"])
        for source in stack["sources"]:
            self.assertTrue(source.get("url", "").startswith("https://"), msg=source["id"])
            self.assertTrue(source.get("grounds"), msg=source["id"])
            self.assertTrue(source.get("cadence"), msg=source["id"])

    def test_a_driver_grounding_source_exists(self) -> None:
        # Without an industry-statistics source, a driver range can only be
        # invented -- which is the one thing the modeling standard forbids.
        report = assess()
        self.assertTrue(report["driver_grounding_sources"])

    def test_grounding_policy_forbids_untraceable_hardcodes(self) -> None:
        stack = json.loads(SOURCE_STACK.read_text())
        self.assertIn("forbidden", stack["grounding_policy"])
        self.assertIn("no traceable basis", stack["grounding_policy"]["forbidden"])

    def test_redistribution_restricted_source_is_flagged(self) -> None:
        stack = json.loads(SOURCE_STACK.read_text())
        by_id = {item["id"]: item for item in stack["sources"]}
        self.assertIn("restriction_note", by_id["yahoo_finance"])


if __name__ == "__main__":
    unittest.main()
