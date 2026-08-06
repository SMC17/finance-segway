"""The universe's sector assignment: sourced, complete, and empirically honest."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import build_universe_taxonomy as builder  # noqa: E402
import validate_universe_taxonomy as validator  # noqa: E402

TAXONOMY = ROOT / "standards" / "universe" / "taxonomy.json"
CROSSWALK = ROOT / "standards" / "universe" / "sic_crosswalk.json"
SNAPSHOT = ROOT / "tools" / "data_fabric" / "out" / "QQQ_sec_sic_classifications.json"


def _taxonomy() -> dict:
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def _crosswalk() -> dict:
    return json.loads(CROSSWALK.read_text(encoding="utf-8"))


def _snapshot_companies() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))["companies"]


class SicClassificationTests(unittest.TestCase):
    def test_every_modelable_company_is_classified_with_citations(self) -> None:
        for company in _taxonomy()["companies"]:
            if not company["modelable"]:
                continue
            label = company["symbol"]
            self.assertTrue(company.get("sector_id"), f"{label}: unclassified")
            source = company.get("sector_source") or ""
            self.assertIn("SEC EDGAR SIC", source, label)
            self.assertIn("sic_crosswalk.json", source, label)
            self.assertTrue(company.get("sic"), f"{label}: no SIC recorded")
            self.assertTrue(company.get("cik"), f"{label}: no CIK recorded")

    def test_crosswalk_covers_every_snapshot_sic(self) -> None:
        crosswalk = _crosswalk()
        mapped = set(crosswalk["sic_to_bucket"])
        overridden = set(crosswalk["ambiguous_sic_overrides"])
        for symbol, meta in _snapshot_companies().items():
            self.assertTrue(
                meta["sic"] in mapped or symbol in overridden,
                f"{symbol}: SIC {meta['sic']} ({meta['sic_description']}) unmapped",
            )

    def test_no_dead_overrides(self) -> None:
        # An override whose symbol the snapshot lacks is silently ignored by
        # the builder - a written rationale that never executes.
        snapshot = _snapshot_companies()
        for symbol in _crosswalk()["ambiguous_sic_overrides"]:
            self.assertIn(symbol, snapshot, f"{symbol}: override has no snapshot row")

    def test_every_override_carries_a_rationale(self) -> None:
        for symbol, override in _crosswalk()["ambiguous_sic_overrides"].items():
            self.assertTrue(override.get("rationale", "").strip(), symbol)
            self.assertTrue(override.get("bucket"), symbol)

    def test_crosswalk_targets_are_declared_sectors(self) -> None:
        sector_ids = {s["id"] for s in _taxonomy()["sectors"]}
        crosswalk = _crosswalk()
        for sic, bucket in crosswalk["sic_to_bucket"].items():
            self.assertIn(bucket, sector_ids, f"SIC {sic} -> {bucket}")
        for symbol, override in crosswalk["ambiguous_sic_overrides"].items():
            self.assertIn(override["bucket"], sector_ids, symbol)

    def test_check_spec_is_pinned(self) -> None:
        # The gate's strictness must not drift silently: the exact committed
        # values are pinned here, and the validator bounds them at runtime.
        spec = _crosswalk()["bucket_weight_check"]
        self.assertEqual(spec["relative_tolerance"], 0.12)
        self.assertEqual(spec["absolute_floor"], 0.003)

    def test_names_cohere_between_profile_and_sec(self) -> None:
        # Ticker->CIK resolution is a string lookup; a recycled ticker would
        # attribute another issuer's SIC. Where both names exist, their first
        # tokens must roughly agree, so a mismatch fails loudly.
        for company in _taxonomy()["companies"]:
            name, name_sec = company.get("name"), company.get("name_sec")
            if not name or not name_sec:
                continue
            def first_token(value: str) -> str:
                tokens = value.upper().replace(",", " ").split()
                if tokens and tokens[0] == "THE":
                    tokens = tokens[1:]
                return tokens[0].strip(".") if tokens else ""

            a, b = first_token(name), first_token(name_sec)
            self.assertTrue(
                a.startswith(b[:4]) or b.startswith(a[:4]),
                f"{company['symbol']}: profile '{name}' vs SEC '{name_sec}'",
            )

    def test_committed_taxonomy_reproduces_from_the_generator(self) -> None:
        rebuilt = builder.build()
        committed = _taxonomy()
        self.assertEqual(rebuilt["companies"], committed["companies"])
        self.assertEqual(rebuilt["sectors"], committed["sectors"])


class ValidatorGateTests(unittest.TestCase):
    """Mutation tests: each doctored taxonomy must FAIL the real validator."""

    def _validate(self, taxonomy: dict) -> dict:
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False
        ) as handle:
            json.dump(taxonomy, handle)
            path = Path(handle.name)
        try:
            return validator.validate(path)
        finally:
            path.unlink()

    def test_committed_taxonomy_passes(self) -> None:
        report = self._validate(_taxonomy())
        self.assertEqual(report["status"], "PASS", report["errors"])

    def test_emptied_small_bucket_fails(self) -> None:
        # The vacuous-tolerance counterexample from review: reassigning a
        # micro-bucket's only member must fail, not slip under tolerance.
        taxonomy = copy.deepcopy(_taxonomy())
        for company in taxonomy["companies"]:
            if company.get("sector_id") == "materials":
                company["sector_id"] = "healthcare"
        report = self._validate(taxonomy)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(
            any("materials" in e and "no member" in e for e in report["errors"]),
            report["errors"],
        )

    def test_large_reassignment_fails(self) -> None:
        taxonomy = copy.deepcopy(_taxonomy())
        for company in taxonomy["companies"]:
            if company.get("symbol") in {"GOOGL", "GOOG", "META"}:
                company["sector_id"] = "information_technology"
        report = self._validate(taxonomy)
        self.assertEqual(report["status"], "FAIL")

    def test_fully_unclassified_taxonomy_fails(self) -> None:
        # Fail-open regression: losing the classification layer must be an
        # error, never a warned PASS.
        taxonomy = copy.deepcopy(_taxonomy())
        for company in taxonomy["companies"]:
            company["sector_id"] = None
            company["sector_source"] = None
        report = self._validate(taxonomy)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("unclassified taxonomy" in e for e in report["errors"]))

    def test_shared_cik_surfaces_as_warning(self) -> None:
        report = self._validate(_taxonomy())
        self.assertTrue(
            any("0001652044" in w for w in report["warnings"]),
            "Alphabet's dual listing must be visible to coverage accounting",
        )


if __name__ == "__main__":
    unittest.main()
