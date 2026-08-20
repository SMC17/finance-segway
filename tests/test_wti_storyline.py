"""Guardrails for the April 2020 WTI Storyline visual."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from tools import build_wti_storyline as storyline

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "docs" / "storyline" / "public_wti_april_2020"
RECEIPT = ROOT / "15_Commodities" / "instances" / "public_wti_april_2020.receipt.json"
SNAPSHOT = ROOT / "15_Commodities" / "sources" / "snapshots" / "commodities-public-wti-april-2020.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WtiStorylineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.series = storyline.load_series()
        cls.config = storyline.load_json(CASE_DIR / "storyline.json")
        cls.provenance = storyline.load_json(CASE_DIR / "provenance.json")
        cls.weeks = storyline.load_json(CASE_DIR / "source_weeks.json")
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_not_a_new_domain(self) -> None:
        numbered = [path.name for path in ROOT.iterdir() if path.is_dir() and path.name[:2].isdigit()]
        self.assertNotIn("32_Journalism", numbered)
        self.assertFalse(self.provenance["counts_toward_M4"])
        self.assertEqual(
            "external_historical_case_visual", self.provenance["classification"]
        )
        self.assertIn("new_modeling_domain", self.provenance["not"])

    def test_pinned_bytes_match_provenance(self) -> None:
        self.assertEqual(self.provenance["series"]["sha256"], _sha(CASE_DIR / "series.csv"))
        self.assertEqual(
            self.provenance["series"]["source_weeks_sha256"],
            _sha(CASE_DIR / "source_weeks.json"),
        )
        self.assertEqual(
            self.provenance["storyline"]["sha256"], _sha(CASE_DIR / "storyline.json")
        )

    def test_series_rebuilds_from_eia_week_table(self) -> None:
        rebuilt = storyline.expand_weeks(self.weeks)
        self.assertEqual(self.series, rebuilt)
        self.assertEqual(len(self.series), self.provenance["series"]["point_count"])
        self.assertEqual(self.series[0][0].isoformat(), "2020-01-06")
        self.assertEqual(self.series[-1][0].isoformat(), "2020-07-15")

    def test_plotted_print_is_cushing_spot_not_futures_or_intraday(self) -> None:
        values = {value for _day, value in self.series}
        by_date = {day.isoformat(): value for day, value in self.series}
        self.assertEqual(by_date["2020-04-20"], -36.98)
        self.assertEqual(by_date["2020-07-01"], 39.88)
        self.assertEqual(min(self.series, key=lambda item: item[1])[0].isoformat(), "2020-04-20")
        self.assertNotIn(-37.63, values)
        self.assertNotIn(-40.32, values)
        self.assertNotIn(40.0, values)

    def test_storyline_contract(self) -> None:
        self.assertLessEqual(len(self.config["cards"]), storyline.MAX_CARDS)
        self.assertEqual(self.config["data"]["datetime_column_name"], "date")
        self.assertEqual(self.config["data"]["data_column_name"], "wti_usd_per_bbl")
        self.assertEqual(self.config["start_at_card"], 3)
        for card in self.config["cards"]:
            self.assertLessEqual(len(card["text"]), 222)
            day, _value = self.series[card["row_number"]]
            self.assertIn(str(day.year), card["display_date"])

    def test_hashed_cells_match_public_case_receipt(self) -> None:
        receipt_cells = {
            (item["sheet"], item["cell"]): item["value"]
            for item in self.receipt["applied_inputs"]
        }
        self.assertEqual(
            self.provenance["linked_public_case"]["workbook_sha256"],
            self.receipt["workbook_sha256"],
        )
        self.assertEqual(
            self.provenance["linked_public_case"]["snapshot_sha256"],
            self.snapshot["snapshot_sha256"],
        )
        for binding in self.provenance["cell_bindings"]:
            self.assertFalse(binding["plotted"])
            self.assertEqual(
                receipt_cells[(binding["sheet"], binding["cell"])],
                binding["value"],
            )
            snapshot_key = {
                "Hedging!C7": "may_contract_settlement_usd_per_bbl",
                "Hedging!C8": "june_contract_price_usd_per_bbl",
                "Physical Balance & Carry!D14": "cushing_stocks_mm_bbl",
                "Physical Balance & Carry!D18": "storage_utilization",
            }[f"{binding['sheet']}!{binding['cell']}"]
            captured = self.snapshot["sources"][0]["captured_values"][snapshot_key]
            self.assertEqual(captured, binding["value"])

    def test_cards_cite_hashed_cells_without_replacing_the_series(self) -> None:
        negative = self.config["cards"][3]
        cushing = self.config["cards"][2]
        recovery = self.config["cards"][4]
        self.assertIn("-$36.98", negative["text"])
        self.assertIn("-$37.63", negative["text"])
        self.assertIn("-$40.32", negative["text"])
        self.assertIn("Hedging!C7", negative["text"])
        self.assertIn("D14=60.0", cushing["text"])
        self.assertIn("D18=0.76", cushing["text"])
        self.assertIn("39.88", recovery["text"])
        self.assertIn("40.0", recovery["text"])
        html = storyline.render_html(self.series, self.config, self.provenance)
        self.assertIn(self.receipt["workbook_sha256"], html)
        self.assertIn("Hedging!C7", html)
        self.assertNotIn("Bloomberg terminal replacement", html)

    def test_committed_html_matches_builder(self) -> None:
        rendered = storyline.render_html(self.series, self.config, self.provenance)
        committed = (CASE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertEqual(rendered, committed)


if __name__ == "__main__":
    unittest.main()
