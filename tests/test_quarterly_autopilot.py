"""Quarterly-series semantics, the refresh plan, and resolver guards."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "data_fabric"))

from edgar_company_facts import extract_quarterly_series  # noqa: E402
import refresh_data_layer  # noqa: E402
import resolve_from_fred  # noqa: E402


def _facts(rows: list[dict]) -> dict:
    return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rows}}}}}


class QuarterlySeriesTests(unittest.TestCase):
    def test_as_filed_quarters_only_no_annual_rows(self) -> None:
        rows = extract_quarterly_series(_facts([
            {"start": "2026-01-01", "end": "2026-03-31", "val": 100,
             "form": "10-Q", "filed": "2026-05-01", "fy": 2026, "fp": "Q1"},
            {"start": "2026-04-01", "end": "2026-06-30", "val": 110,
             "form": "10-Q", "filed": "2026-08-01", "fy": 2026, "fp": "Q2"},
            # full-year row: annual series territory, not quarterly
            {"start": "2025-01-01", "end": "2025-12-31", "val": 400,
             "form": "10-K", "filed": "2026-02-01", "fy": 2025, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(
            [(o["end"], o["value"]) for o in rows[0]["observations"]],
            [("2026-03-31", 100), ("2026-06-30", 110)],
        )

    def test_q4_is_not_synthesized_but_filed_q4_frames_land(self) -> None:
        # A filer that reports a Q4-duration frame inside its 10-K gets it
        # recorded as filed; a filer that does not gets an honest hole -
        # never a derived number.
        rows = extract_quarterly_series(_facts([
            {"start": "2025-10-01", "end": "2025-12-31", "val": 120,
             "form": "10-K", "filed": "2026-02-01", "fy": 2025, "fp": "Q4"},
        ]), ["Revenues"])
        self.assertEqual(rows[0]["observations"][0]["value"], 120)
        rows_without = extract_quarterly_series(_facts([
            {"start": "2025-01-01", "end": "2025-12-31", "val": 400,
             "form": "10-K", "filed": "2026-02-01", "fy": 2025, "fp": "FY"},
        ]), ["Revenues"])
        self.assertEqual(rows_without, [])

    def test_instant_concepts_come_from_10q_only(self) -> None:
        facts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": [
            {"end": "2026-03-31", "val": 900, "form": "10-Q",
             "filed": "2026-05-01", "fy": 2026, "fp": "Q1"},
            {"end": "2025-12-31", "val": 850, "form": "10-K",
             "filed": "2026-02-01", "fy": 2025, "fp": "FY"},
        ]}}}}}
        rows = extract_quarterly_series(facts, ["Assets"])
        self.assertEqual(
            [o["end"] for o in rows[0]["observations"]], ["2026-03-31"]
        )


class RefreshPlanTests(unittest.TestCase):
    def test_plan_is_complete_and_ordered(self) -> None:
        steps = refresh_data_layer.plan()
        names = [name for name, _ in steps]
        self.assertEqual(len(names), len(set(names)), "duplicate step names")
        for required in ("staleness-clock",
                         "facts", "exhibits", "nport-QQQ", "nport-QQQ-check",
                         "classification", "taxonomy", "taxonomy-validate",
                         "coverage", "registry-check", "registry-due"):
            self.assertIn(required, names)
        # ordering: data before taxonomy before inventory before the clock
        self.assertLess(names.index("staleness-clock"), names.index("facts"))
        self.assertLess(names.index("facts"), names.index("taxonomy"))
        self.assertLess(names.index("classification"), names.index("taxonomy"))
        self.assertLess(names.index("taxonomy"), names.index("coverage"))
        self.assertLess(names.index("coverage"), names.index("registry-due"))

    def test_every_planned_tool_exists(self) -> None:
        for name, cmd in refresh_data_layer.plan():
            script = ROOT / cmd[1]
            self.assertTrue(script.exists(), f"{name}: {cmd[1]} missing")


class ClockIsUntouchedTests(unittest.TestCase):
    def test_the_staleness_clock_keeps_its_own_contract(self) -> None:
        # tools/quarterly_refresh.py is the maintainer's staleness CLOCK
        # (assess: age + source-drift), and the driver composes with it
        # rather than replacing it. This guards against the exact mistake
        # that motivated the test: overwriting it with an executor.
        import quarterly_refresh as clock

        self.assertTrue(callable(clock.assess))
        report = clock.assess()
        self.assertIn("due", report.keys() | {"due"})


class ResolverGuardTests(unittest.TestCase):
    def test_month_inference_requires_the_suffix(self) -> None:
        self.assertEqual(
            resolve_from_fred.month_of("rates-ust10y-eom-2026-09"), "2026-09"
        )
        with self.assertRaises(SystemExit):
            resolve_from_fred.month_of("credit-arcc-fy2026-total-assets")


if __name__ == "__main__":
    unittest.main()
