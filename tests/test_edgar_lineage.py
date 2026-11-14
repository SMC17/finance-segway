"""Rules that turn EDGAR filing records into lineage events.

Fixtures are hand-built filing histories, not financial values: they test the
derivation rules in edgar_corporate_events.py, which decide every derived edge.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "data_fabric"))
sys.path.insert(0, str(ROOT / "tools"))

import edgar_corporate_events as ev  # noqa: E402
import sec_daily_ingest as daily  # noqa: E402

AS_OF = date(2026, 11, 14)


def entity(cik, *, first="2000-03-01", last="2026-08-01", events=(), shared=()):
    return {
        "cik": cik, "has_periodic": True, "shared": list(shared), "name": f"Entity {cik}",
        "sic": "2834", "sic_description": "Pharmaceutical Preparations", "entity_type": "operating",
        "tickers": [], "exchanges": [], "state_of_incorporation": "DE", "former_names": [],
        "first_filed": first, "last_filed": last, "first_periodic": first, "last_periodic": last,
        "periodic_years": [str(y) for y in range(int(first[:4]), int(last[:4]) + 1)],
        "events": list(events),
    }


def merged(events):
    return {(e["cik"], e["counterparty"]) for e in events if e["event"] == "merged_into"}


class MergerDirection(unittest.TestCase):
    def test_target_that_deregisters_merges_into_the_survivor(self):
        target = entity("A", last="2019-08-01", events=[("deregistered", "2019-11-20", "acc-15", "15-12B")],
                        shared=[("acc-1", "425", "2019-02-01")])
        survivor = entity("B", shared=[("acc-1", "425", "2019-02-01")])
        _, events = ev.derive([target, survivor], AS_OF)
        self.assertEqual({("A", "B")}, merged(events))
        self.assertEqual("ceased:merged_into", target["status"])

    def test_no_direction_when_both_parties_stop_reporting(self):
        a = entity("A", last="2019-08-01", events=[("deregistered", "2019-11-20", "x", "15-12B")], shared=[("acc", "425", "2019-02-01")])
        b = entity("B", last="2019-08-01", events=[("deregistered", "2019-11-21", "y", "15-12B")], shared=[("acc", "425", "2019-02-01")])
        _, events = ev.derive([a, b], AS_OF)
        self.assertEqual(set(), merged(events))
        self.assertEqual(2, sum(e["event"] == "combination_filing" for e in events))

    def test_termination_outside_the_window_is_not_a_merger(self):
        target = entity("A", last="2016-01-01", events=[("deregistered", "2016-02-01", "x", "15-12B")],
                        shared=[("acc", "425", "2010-01-01")])
        _, events = ev.derive([target, entity("B", shared=[("acc", "425", "2010-01-01")])], AS_OF)
        self.assertEqual(set(), merged(events))

    def test_latest_shared_filing_picks_the_survivor_among_co_filers(self):
        target = entity("A", last="2015-04-28", events=[("deregistered", "2015-07-02", "x", "15-12B")],
                        shared=[("early", "425", "2015-03-25"), ("late", "425", "2015-06-29")])
        investor = entity("B", shared=[("early", "425", "2015-03-25")])
        combined = entity("C", shared=[("late", "425", "2015-06-29")])
        _, events = ev.derive([target, investor, combined], AS_OF)
        self.assertEqual({("A", "C")}, merged(events))

    def test_fund_family_filings_with_many_parties_are_ignored(self):
        shared = [("acc", "425", "2019-02-01")]
        ents = [entity(c, last="2019-08-01", events=[("deregistered", "2019-11-20", "x", "15-12B")], shared=shared) for c in "ABCD"]
        _, events = ev.derive(ents, AS_OF)
        self.assertFalse([e for e in events if e["event"] in ("combination_filing", "merged_into")])


class ExitReason(unittest.TestCase):
    def test_bankruptcy_is_the_reason_when_reporting_stops_after_it(self):
        e = entity("A", last="2023-06-14", events=[("bankruptcy_filed", "2023-04-24", "x", "8-K")])
        ev.derive([e], AS_OF)
        self.assertEqual("ceased:bankruptcy_filed", e["status"])

    def test_silence_without_a_filing_is_undisclosed(self):
        e = entity("A", last="2012-03-01")
        ev.derive([e], AS_OF)
        self.assertEqual("ceased:undisclosed", e["status"])

    def test_recent_filer_is_reporting(self):
        e = entity("A", last="2026-10-01", events=[("bankruptcy_filed", "2020-05-26", "x", "8-K")])
        ev.derive([e], AS_OF)
        self.assertEqual("reporting", e["status"])


class SicDivision(unittest.TestCase):
    def test_divisions_follow_the_major_group_ranges(self):
        self.assertEqual("D", ev.sic_division("2834")[0])
        self.assertEqual("H", ev.sic_division("6211")[0])
        self.assertEqual("", ev.sic_division("")[0])


class DailyIngest(unittest.TestCase):
    def test_previous_business_day_skips_the_weekend(self):
        self.assertEqual(date(2026, 11, 13), daily.previous_business_day(date(2026, 11, 16)))
        self.assertEqual(date(2026, 11, 13), daily.previous_business_day(date(2026, 11, 14)))

    def test_daily_index_url_uses_the_calendar_quarter(self):
        self.assertTrue(daily.daily_index_url(date(2026, 11, 13)).endswith("/2026/QTR4/master.20261113.idx"))


if __name__ == "__main__":
    unittest.main()
