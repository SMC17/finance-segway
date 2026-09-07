"""Tests for the standards conformance layer.

Weighted deliberately toward NEGATIVE tests. Every tool here exists to refuse
something, so the property that matters is not "it passes on the current
repository" -- that is easy and it will keep being true right up until it
silently stops mattering. The property that matters is "it still refuses the
thing it was built to refuse."

So most of what follows constructs a register or a document that ought to be
rejected and asserts that it is.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import verify_accessibility  # noqa: E402
import verify_ai_documentation  # noqa: E402
import verify_controlled_vocabulary as vocab  # noqa: E402
import verify_data_conventions as conventions  # noqa: E402
import verify_dataset_metadata as metadata  # noqa: E402
import verify_standards_conformance as conformance  # noqa: E402


def load_register() -> dict:
    return json.loads(conformance.REGISTER.read_text(encoding="utf-8"))


class RegisterFailsClosedTests(unittest.TestCase):
    """The register must refuse claims that nothing supports."""

    def _run_with(self, register: dict) -> dict:
        with patch.object(conformance, "load_register", return_value=register):
            return conformance.run(execute_checks=False)

    def test_conformant_without_a_check_is_refused(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "iso-8601":
                row["evidence"] = {"check": None, "asserts": None}
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("names no check" in f for f in result["failures"]), result["failures"]
        )

    def test_conformant_naming_a_missing_check_is_refused(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "iso-8601":
                row["evidence"]["check"] = "tools/does_not_exist.py"
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("does not exist" in f for f in result["failures"]))

    def test_claim_on_a_summary_only_basis_is_refused(self) -> None:
        # The rule that caught a real overclaim during this work: ISO 8000 was
        # set to 'partial' while its requirements were only summarised.
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "iso-iec-42001":
                row["status"] = "conformant"
                row["evidence"] = {
                    "check": "tools/verify_data_conventions.py",
                    "asserts": "something",
                }
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any("summary_only" in f and "cannot be one we claim" in f for f in result["failures"])
        )

    def test_partial_with_no_gaps_is_refused(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "iso-25964":
                row["gaps"] = []
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("no gaps listed" in f for f in result["failures"]))

    def test_conformant_with_gaps_is_refused(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "iso-8601":
                row["gaps"] = ["something is missing"]
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("is 'partial'" in f for f in result["failures"]))

    def test_deleting_a_required_standard_is_refused(self) -> None:
        # A standard must not be disposable. Removing the row is the easiest
        # way to make an inconvenient obligation disappear.
        register = load_register()
        register["standards"] = [
            r for r in register["standards"] if r["id"] != "asd-ste100"
        ]
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("asd-ste100" in f and "no row" in f for f in result["failures"]))

    def test_not_applicable_requires_a_reason(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "openapi":
                row["reason"] = ""
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("no reason" in f for f in result["failures"]))

    def test_not_yet_requires_a_plan(self) -> None:
        register = load_register()
        for row in register["standards"]:
            if row["id"] == "nist-ai-rmf":
                row["plan"] = ""
        result = self._run_with(register)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(any("no plan" in f for f in result["failures"]))

    def test_unverified_rows_are_always_surfaced(self) -> None:
        result = conformance.run(execute_checks=False)
        unverified = [
            row["id"] for row in load_register()["standards"]
            if row["requirement_basis"] == "unverified"
        ]
        self.assertTrue(unverified, "expected some standards to be honestly unverified")
        for name in unverified:
            self.assertTrue(
                any(name in w for w in result["warnings"]),
                f"{name} is unverified but was not surfaced to the reader",
            )

    def test_live_register_passes(self) -> None:
        result = conformance.run(execute_checks=False)
        self.assertEqual("PASS", result["status"], result["failures"])
        self.assertEqual(64, result["standards_registered"])

    def test_every_claim_is_backed_by_a_check_that_exists(self) -> None:
        for row in load_register()["standards"]:
            if row["status"] in {"conformant", "partial"}:
                check = (row.get("evidence") or {}).get("check")
                self.assertTrue(check, f"{row['id']} claims {row['status']} with no check")
                self.assertTrue(
                    (ROOT / check).exists(), f"{row['id']} names missing check {check}"
                )


class EntryPointTests(unittest.TestCase):
    def test_llms_txt_and_agents_md_links_resolve(self) -> None:
        self.assertEqual([], conformance.check_entry_points())

    def test_agents_md_states_the_fabrication_prohibition(self) -> None:
        # The single most important sentence in the repository. If it is ever
        # edited away, this fails.
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        self.assertIn("never write a financial number that is not real", text)


class DataConventionTests(unittest.TestCase):
    def test_iso8601_classifier_accepts_the_forms_in_use(self) -> None:
        self.assertEqual("extended_date", conventions.classify_date("2026-09-07"))
        self.assertEqual("basic_datetime", conventions.classify_date("20260817T230452Z"))
        self.assertEqual(
            "extended_datetime", conventions.classify_date("2026-09-07T14:32:00Z")
        )

    def test_iso8601_classifier_rejects_non_iso_dates(self) -> None:
        for value in ("07/09/2026", "Sept 7 2026", "2026-9-7", "20260907"):
            self.assertIsNone(conventions.classify_date(value), value)

    def test_registry_declares_every_suffix_the_repository_uses(self) -> None:
        report = conventions.run()
        registry = conventions.load_registry()
        declared = set(registry["magnitude_suffixes"]) | set(
            registry["dimensionless_conventions"]
        ) | {"<units>"}
        for suffix in report["magnitude_suffixes_used"]:
            self.assertIn(suffix, declared, f"{suffix!r} is used but not declared")

    def test_repository_has_no_hard_notation_failures(self) -> None:
        report = conventions.run()
        self.assertEqual([], report["failures"])

    def test_mm_is_recorded_as_ucum_unsafe(self) -> None:
        # The collision matters: a UCUM parser reads 'mm' as millimetre. If
        # someone ever marks it safe, this fails.
        registry = conventions.load_registry()
        self.assertFalse(registry["magnitude_suffixes"]["mm"]["ucum_safe"])
        self.assertEqual(1000000, registry["magnitude_suffixes"]["mm"]["multiplier"])


class ControlledVocabularyTests(unittest.TestCase):
    def test_live_vocabulary_passes(self) -> None:
        report = vocab.run()
        self.assertEqual("PASS", report["status"], report["failures"])
        self.assertEqual([], report["warnings"], "deprecated values remain in the data")

    def test_circular_definition_is_refused(self) -> None:
        glossary = json.loads(vocab.GLOSSARY.read_text(encoding="utf-8"))
        glossary["concepts"][0]["definition"] = (
            f"A {glossary['concepts'][0]['prefLabel']} used within the system."
        )
        problems = vocab.check_concept_system(glossary)
        self.assertTrue(any("circular" in p for p in problems), problems)

    def test_gloss_definition_is_refused(self) -> None:
        glossary = json.loads(vocab.GLOSSARY.read_text(encoding="utf-8"))
        glossary["concepts"][0]["definition"] = "Is when a thing happens in the model."
        problems = vocab.check_concept_system(glossary)
        self.assertTrue(any("substitutable" in p for p in problems), problems)

    def test_dangling_broader_reference_is_refused(self) -> None:
        glossary = json.loads(vocab.GLOSSARY.read_text(encoding="utf-8"))
        glossary["concepts"][0]["broader"] = "no-such-concept"
        problems = vocab.check_concept_system(glossary)
        self.assertTrue(any("unknown concept" in p for p in problems), problems)

    def test_homograph_without_a_resolution_is_refused(self) -> None:
        glossary = json.loads(vocab.GLOSSARY.read_text(encoding="utf-8"))
        glossary["homographs"] = [
            {"designation": "x", "concepts": ["a", "b"], "resolution": "", "status": "open"}
        ]
        problems = vocab.check_homographs(glossary)
        self.assertTrue(any("no resolution" in p for p in problems), problems)

    def test_risk_tier_homograph_is_recorded_and_resolved(self) -> None:
        glossary = json.loads(vocab.GLOSSARY.read_text(encoding="utf-8"))
        entry = next(
            h for h in glossary["homographs"] if h["designation"] == "risk_tier"
        )
        self.assertEqual("resolved", entry["status"])
        # And the resolution was actually applied, not merely declared.
        catalog = json.loads(
            (ROOT / "standards" / "consulting" / "capability_catalog.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn('"risk_tier"', json.dumps(catalog))

    def test_skos_export_is_structurally_sound(self) -> None:
        payload = vocab.to_skos(json.loads(vocab.GLOSSARY.read_text(encoding="utf-8")))
        concepts = [n for n in payload["@graph"] if n.get("@type") == "skos:Concept"]
        identifiers = {n["@id"] for n in concepts}
        self.assertTrue(concepts)
        for node in concepts:
            self.assertIn("skos:prefLabel", node)
            self.assertIn("skos:definition", node)
            if "skos:broader" in node:
                self.assertIn(node["skos:broader"]["@id"], identifiers)
            for related in node.get("skos:related", []):
                self.assertIn(related["@id"], identifiers)


class DatasetMetadataTests(unittest.TestCase):
    def test_live_catalogue_matches_the_repository(self) -> None:
        report = metadata.run()
        self.assertEqual("PASS", report["status"], report["failures"])

    def test_stale_record_count_is_caught(self) -> None:
        catalog = json.loads(metadata.CATALOG.read_text(encoding="utf-8"))
        for node in catalog["@graph"]:
            if node.get("dcterms:identifier") == "public-cases":
                node["repo:recordCount"] = 999999
        with patch.object(metadata, "load", return_value=catalog):
            report = metadata.run()
        self.assertEqual("FAIL", report["status"])
        self.assertTrue(any("stale" in f for f in report["failures"]))

    def test_missing_dublin_core_element_is_caught(self) -> None:
        catalog = json.loads(metadata.CATALOG.read_text(encoding="utf-8"))
        for node in catalog["@graph"]:
            if node.get("dcterms:identifier") == "vocabulary":
                node.pop("dcterms:license", None)
        with patch.object(metadata, "load", return_value=catalog):
            report = metadata.run()
        self.assertEqual("FAIL", report["status"])
        self.assertTrue(any("dcterms:license" in f for f in report["failures"]))

    def test_unstated_fair_letter_is_caught(self) -> None:
        catalog = json.loads(metadata.CATALOG.read_text(encoding="utf-8"))
        for node in catalog["@graph"]:
            if node.get("dcterms:identifier") == "vocabulary":
                node["repo:fair"]["reusable"] = ""
        with patch.object(metadata, "load", return_value=catalog):
            report = metadata.run()
        self.assertEqual("FAIL", report["status"])
        self.assertTrue(any("reusable" in f for f in report["failures"]))


class AccessibilityTests(unittest.TestCase):
    def test_no_status_is_conveyed_by_colour_alone(self) -> None:
        report = verify_accessibility.run()
        self.assertEqual("PASS", report["status"], report["failures"][:5])
        self.assertGreater(report["totals"]["status_cells"], 0)

    def test_every_status_row_carries_a_text_label(self) -> None:
        report = verify_accessibility.run()
        self.assertEqual(0, report["totals"]["unlabelled_rows"])


class AiDocumentationTests(unittest.TestCase):
    def test_model_cards_and_datasheet_pass(self) -> None:
        report = verify_ai_documentation.run()
        self.assertEqual("PASS", report["status"], report["failures"][:5])
        self.assertEqual(27, report["model_cards_checked"])
        self.assertEqual(7, report["datasheet_sections_present"])

    def test_section_parser_includes_subsections(self) -> None:
        # The bug this guards against failed all 27 model cards: a section whose
        # content sits under subheadings read as empty.
        markdown = "# T\n\n## Intended use\n\n### Approved\n\nReal content here.\n\n## Next\n\nx\n"
        sections = verify_ai_documentation.sections(markdown)
        self.assertIn("Real content here.", sections["Intended use"])

    def test_empty_section_counts_as_missing(self) -> None:
        markdown = "# T\n\n## Intended use\n\n## Next\n\nx\n"
        sections = verify_ai_documentation.sections(markdown)
        self.assertLess(
            verify_ai_documentation.word_count(sections["Intended use"]),
            verify_ai_documentation.MIN_SECTION_WORDS,
        )

    def test_unmapped_model_card_sections_are_declared_not_hidden(self) -> None:
        unmapped = [k for k, v in verify_ai_documentation.MODEL_CARD_SECTIONS.items() if v is None]
        self.assertTrue(unmapped)
        report = verify_ai_documentation.run()
        self.assertEqual(sorted(unmapped), report["unmapped_sections"])


if __name__ == "__main__":
    unittest.main()
