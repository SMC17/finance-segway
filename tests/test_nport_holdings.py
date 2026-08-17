"""Second-source holdings: parser pinned offline, cross-check pinned to data."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.data_fabric.nport_holdings import (  # noqa: E402
    cross_check,
    normalize_name,
    parse_holdings,
)

FIXTURE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/nport">
  <formData>
    <genInfo><repPdDate>2026-03-31</repPdDate></genInfo>
    <invstOrSecs>
      <invstOrSec>
        <name>NVIDIA Corp.</name><cusip>67066G104</cusip>
        <lei>549300S4KLFTLO7GSQ80</lei><pctVal>8.681</pctVal>
      </invstOrSec>
      <invstOrSec>
        <name>Alphabet Inc.</name><cusip>02079K305</cusip>
        <lei>5493006MHB84DD0ZWV18</lei><pctVal>3.430</pctVal>
      </invstOrSec>
      <invstOrSec>
        <name>Alphabet Inc.</name><cusip>02079K107</cusip>
        <lei>5493006MHB84DD0ZWV18</lei><pctVal>3.203</pctVal>
      </invstOrSec>
    </invstOrSecs>
  </formData>
</edgarSubmission>"""


class NormalizeNameTests(unittest.TestCase):
    def test_suffixes_and_articles_drop(self) -> None:
        self.assertEqual(normalize_name("The Kraft Heinz Co"), "KRAFT HEINZ")
        self.assertEqual(normalize_name("KRAFT HEINZ CO"), "KRAFT HEINZ")

    def test_single_letter_legal_tokens_drop(self) -> None:
        # "ASML Holding N.V." must key identically to "ASML HOLDING NV".
        self.assertEqual(normalize_name("ASML Holding N.V."), "ASML")
        self.assertEqual(normalize_name("ASML HOLDING NV"), "ASML")

    def test_share_classes_share_a_key(self) -> None:
        self.assertEqual(
            normalize_name("Alphabet Inc. Class A"), normalize_name("Alphabet Inc.")
        )


class ParserTests(unittest.TestCase):
    def test_fixture_parses_with_period_and_sorted_weights(self) -> None:
        parsed = parse_holdings(FIXTURE_XML)
        self.assertEqual(parsed["report_period"], "2026-03-31")
        self.assertEqual(len(parsed["holdings"]), 3)
        self.assertEqual(parsed["holdings"][0]["name"], "NVIDIA Corp.")
        self.assertEqual(parsed["holdings"][0]["cusip"], "67066G104")
        pcts = [h["pct"] for h in parsed["holdings"]]
        self.assertEqual(pcts, sorted(pcts, reverse=True))


class CrossCheckTests(unittest.TestCase):
    """Against the committed QQQ snapshot + taxonomy - offline."""

    def test_match_rate_and_known_identifications(self) -> None:
        report = cross_check("QQQ")
        self.assertGreaterEqual(report["taxonomy_matched"], 90)
        # ASML matches once single-letter legal tokens normalize away.
        self.assertNotIn("ASML", report["taxonomy_unmatched"])
        # The profile's unresolvable "n/a" holding is identified by the
        # regulator's filing: Ferrovial. The cross-check must keep naming it.
        self.assertTrue(
            any("FERROVIAL" in n.upper() for n in report["nport_only_over_10bps"]),
            report["nport_only_over_10bps"],
        )

    def test_unmatched_names_are_recent_index_adds(self) -> None:
        # Every unmatched taxonomy symbol must be absent from the March
        # N-PORT because it joined the index later - not because matching
        # broke. Pin the current set; growth of this list on a future
        # refresh is a review trigger, not an auto-pass.
        report = cross_check("QQQ")
        self.assertLessEqual(
            set(report["taxonomy_unmatched"]),
            {"ALAB", "CRWV", "HONA", "LITE", "NBIS", "RKLB", "SNDK", "SPCX", "TER"},
            report["taxonomy_unmatched"],
        )

    def test_period_difference_is_declared(self) -> None:
        report = cross_check("QQQ")
        self.assertIn("different dates", report["period_note"])
        self.assertNotEqual(report["nport_period"], report["taxonomy_as_of"])


if __name__ == "__main__":
    unittest.main()
