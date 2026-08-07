"""Earnings-exhibit freezing: header-typed selection, hash-pinned artifacts."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "data_fabric"))

from edgar_earnings_exhibits import exhibit_documents, results_8ks  # noqa: E402

EXHIBITS_DIR = ROOT / "tools" / "data_fabric" / "exhibits"

# The -index-headers.html page HTML-escapes the SGML, and filenames are
# issuer-arbitrary - both real failure modes this fixture reproduces.
HEADER_FIXTURE = """
<html><body><pre>
&lt;DOCUMENT&gt;
&lt;TYPE&gt;8-K
&lt;FILENAME&gt;adsk-20260528.htm
&lt;/DOCUMENT&gt;
&lt;DOCUMENT&gt;
&lt;TYPE&gt;EX-99.1
&lt;FILENAME&gt;q127pressrelease.htm
&lt;/DOCUMENT&gt;
&lt;DOCUMENT&gt;
&lt;TYPE&gt;GRAPHIC
&lt;FILENAME&gt;logo.jpg
&lt;/DOCUMENT&gt;
</pre></body></html>
"""


class ExhibitSelectionTests(unittest.TestCase):
    def test_header_typed_selection_ignores_filenames(self) -> None:
        documents = exhibit_documents(HEADER_FIXTURE)
        self.assertEqual(documents, [("EX-99.1", "q127pressrelease.htm")])

    def test_results_8ks_filters_on_item_202(self) -> None:
        submissions = {"filings": {"recent": {
            "form": ["8-K", "10-Q", "8-K", "8-K"],
            "accessionNumber": ["a1", "a2", "a3", "a4"],
            "filingDate": ["2026-08-06", "2026-08-01", "2026-06-11", "2026-05-07"],
            "items": ["2.02,9.01", "", "7.01", "2.02,2.05,9.01"],
            "reportDate": ["2026-06-30", "", "", "2026-03-31"],
        }}}
        picked = results_8ks(submissions, limit=2)
        self.assertEqual([f["accession"] for f in picked], ["a1", "a4"])
        self.assertEqual(picked[0]["report_date"], "2026-06-30")


class CommittedExhibitsTests(unittest.TestCase):
    """The frozen software-sector exhibits: every claim in the index true."""

    SOFTWARE = ["MSFT", "PLTR", "CRWD", "SHOP", "CDNS", "ADBE", "DDOG",
                "INTU", "SNPS", "ADSK", "CRWV"]

    def test_every_software_name_has_frozen_materials(self) -> None:
        for ticker in self.SOFTWARE:
            index_path = EXHIBITS_DIR / ticker / "index.json"
            self.assertTrue(index_path.exists(), ticker)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(index["filings"]), 1, ticker)
            for filing in index["filings"]:
                self.assertIn("2.02", filing["items"], ticker)
                self.assertGreaterEqual(len(filing["files"]), 1, ticker)

    def test_committed_bytes_match_recorded_hashes(self) -> None:
        # The citation surface: path + sha256. If the bytes drift from the
        # index, every downstream citation is broken - verify all of them.
        checked = 0
        for ticker in self.SOFTWARE:
            index = json.loads(
                (EXHIBITS_DIR / ticker / "index.json").read_text(encoding="utf-8")
            )
            for filing in index["filings"]:
                acc = filing["accession"].replace("-", "")
                for record in filing["files"]:
                    blob = (EXHIBITS_DIR / ticker / acc / record["name"]).read_bytes()
                    self.assertEqual(
                        hashlib.sha256(blob).hexdigest(), record["sha256"],
                        f"{ticker}/{record['name']}",
                    )
                    self.assertEqual(len(blob), record["bytes"])
                    checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_no_extraction_happened(self) -> None:
        # The contract: raw documents only, zero interpreted numbers. The
        # index must carry no value-like fields.
        for ticker in self.SOFTWARE:
            index = json.loads(
                (EXHIBITS_DIR / ticker / "index.json").read_text(encoding="utf-8")
            )
            for filing in index["filings"]:
                for record in filing["files"]:
                    self.assertEqual(
                        set(record),
                        {"name", "exhibit_type", "url", "sha256", "bytes"},
                    )


if __name__ == "__main__":
    unittest.main()
