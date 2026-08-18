"""Pre-registration discipline for the forecast registry."""
from __future__ import annotations

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from tools import forecast_registration
from tools.forecast_registration import (
    FORECAST_DIR,
    check_all,
    draft_registration,
    due_report,
    register,
    registration_sha256,
    resolve,
    score,
    validate_record,
)

TODAY = date(2026, 8, 5)


def _valid_record() -> dict:
    record = {
        "forecast_id": "test-forecast",
        "case_id": "some-case",
        "model_id": "03",
        "metric": "revenue_usd_mm",
        "outcome_class": "out_of_sample_forecast",
        "point": 100.0,
        "interval": [90.0, 110.0],
        "basis": "naive_last_recorded",
        "baseline": {
            "kind": "naive_last_recorded",
            "value": 100.0,
            "source": "outcome log",
        },
        "registered_on": "2026-08-01",
        "resolve_by": "2027-08-01",
        "resolution_source_expected": "Issuer Form 10-K",
        "resolution": None,
    }
    record["registration_sha256"] = registration_sha256(record)
    return record


class ForecastRegistrationTests(unittest.TestCase):
    def test_valid_record_passes(self) -> None:
        self.assertEqual(validate_record(_valid_record(), today=TODAY), [])

    def test_editing_a_registered_field_breaks_the_hash(self) -> None:
        record = _valid_record()
        record["point"] = 120.0
        errors = validate_record(record, today=TODAY)
        self.assertTrue(any("registration_sha256" in e for e in errors), errors)

    def test_hindsight_registration_is_rejected(self) -> None:
        closed_window = _valid_record()
        closed_window["resolve_by"] = "2026-07-01"
        closed_window["registration_sha256"] = registration_sha256(closed_window)
        errors = validate_record(closed_window, today=TODAY)
        self.assertTrue(any("hindsight" in e for e in errors), errors)

        future_dated = _valid_record()
        future_dated["registered_on"] = "2026-09-01"
        future_dated["registration_sha256"] = registration_sha256(future_dated)
        errors = validate_record(future_dated, today=TODAY)
        self.assertTrue(any("in the future" in e for e in errors), errors)

    def test_baseline_is_mandatory(self) -> None:
        record = _valid_record()
        del record["baseline"]
        record["registration_sha256"] = registration_sha256(record)
        errors = validate_record(record, today=TODAY)
        self.assertTrue(any("unfalsifiable" in e for e in errors), errors)

    def test_only_out_of_sample_forecasts_are_accepted(self) -> None:
        record = _valid_record()
        record["outcome_class"] = "retrospective_reconstruction"
        record["registration_sha256"] = registration_sha256(record)
        errors = validate_record(record, today=TODAY)
        self.assertTrue(any("outcome_class" in e for e in errors), errors)

    def test_skill_scoring(self) -> None:
        record = _valid_record()
        # Forecast 100 vs baseline 100: identical, realized 104 -> skill 0.
        self.assertAlmostEqual(score(record, 104.0)["skill_vs_baseline"], 0.0)
        # A better forecast: point 103 vs baseline 100, realized 104.
        record["point"] = 103.0
        result = score(record, 104.0)
        self.assertAlmostEqual(result["skill_vs_baseline"], 0.75)
        self.assertTrue(result["interval_hit"])
        # A worse forecast than naive has negative skill.
        record["point"] = 90.0
        self.assertLess(score(record, 104.0)["skill_vs_baseline"], 0.0)
        # Baseline exactly right, forecast wrong: skill is None (reported,
        # not divided by zero).
        record["point"] = 90.0
        self.assertIsNone(score(record, 100.0)["skill_vs_baseline"])
        # Interval miss is recorded.
        record["point"] = 100.0
        self.assertFalse(score(record, 120.0)["interval_hit"])

    def test_resolution_scores_must_match_recomputation(self) -> None:
        record = _valid_record()
        record["resolution"] = {
            "realized": 104.0,
            "realized_source": "Issuer FY Form 10-K",
            "resolved_on": "2026-08-04",
            **score(record, 104.0),
        }
        self.assertEqual(validate_record(record, today=TODAY), [])
        tampered = copy.deepcopy(record)
        tampered["resolution"]["skill_vs_baseline"] = 0.99
        errors = validate_record(tampered, today=TODAY)
        self.assertTrue(any("skill_vs_baseline" in e for e in errors), errors)

    def test_same_day_resolution_is_rejected(self) -> None:
        record = _valid_record()
        record["resolution"] = {
            "realized": 104.0,
            "realized_source": "Issuer FY Form 10-K",
            "resolved_on": "2026-08-01",
            **score(record, 104.0),
        }
        errors = validate_record(record, today=TODAY)
        self.assertTrue(any("not out-of-sample" in e for e in errors), errors)

    def test_draft_registration_freezes_the_carry_forward_baseline(self) -> None:
        record = draft_registration(
            forecast_id="pc-acme-fy2027-revenue",
            case_id="acme_unitranche_2026",
            model_id="05",
            metric="revenue_usd_mm",
            point=112.0,
            history=[("FY2024", 96.0), ("FY2025", 101.0), ("FY2026", 104.0)],
            history_source="05_Private_Credit/instances/acme_unitranche_2026 workbook",
            resolve_by="2027-09-30",
            resolution_source_expected="Issuer FY2027 audited financials",
            interval=[102.0, 121.0],
            registered_on="2026-08-05",
        )
        self.assertEqual(validate_record(record, today=TODAY), [])
        self.assertEqual(record["baseline"]["kind"], "naive_last_recorded")
        self.assertEqual(record["baseline"]["value"], 104.0)
        self.assertIn("FY2026", record["baseline"]["source"])
        self.assertIn("acme_unitranche_2026 workbook", record["baseline"]["source"])
        self.assertEqual(record["outcome_class"], "out_of_sample_forecast")
        self.assertEqual(record["basis"], "modeled")

    def test_draft_registration_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            draft_registration(
                forecast_id="no-history",
                case_id="c",
                model_id="05",
                metric="m",
                point=1.0,
                history=[],
                history_source="src",
                resolve_by="2027-01-01",
                resolution_source_expected="src",
            )
        with self.assertRaises(ValueError) as ctx:
            draft_registration(
                forecast_id="no-history-source",
                case_id="c",
                model_id="05",
                metric="m",
                point=1.0,
                history=[("FY2025", 1.0)],
                history_source="  ",
                resolve_by="2027-01-01",
                resolution_source_expected="src",
            )
        self.assertIn("gameable", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            draft_registration(
                forecast_id="closed-window",
                case_id="c",
                model_id="05",
                metric="m",
                point=1.0,
                history=[("FY2025", 1.0)],
                history_source="src",
                resolve_by="2020-01-01",
                resolution_source_expected="src",
                registered_on="2026-08-05",
            )
        self.assertIn("hindsight", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            draft_registration(
                forecast_id="bad-interval",
                case_id="c",
                model_id="05",
                metric="m",
                point=1.0,
                history=[("FY2025", 1.0)],
                history_source="src",
                resolve_by="2027-01-01",
                resolution_source_expected="src",
                interval=[5.0, 2.0],
            )
        self.assertIn("interval", str(ctx.exception))

    def test_draft_to_register_to_resolve_round_trip(self) -> None:
        # The full agent path: protocol estimate -> draft -> register (hash
        # stamped) -> resolve (skill + interval coverage computed) -> check.
        import tempfile
        from unittest.mock import patch

        estimates = {"acme": 112.0}  # parsed from a statistician-protocol reply
        record = draft_registration(
            forecast_id="e2e-acme-fy2027-revenue",
            case_id="acme_unitranche_2026",
            model_id="05",
            metric="revenue_usd_mm",
            point=estimates["acme"],
            history=[("FY2025", 101.0), ("FY2026", 104.0)],
            history_source="05_Private_Credit/instances/acme_unitranche_2026 workbook",
            resolve_by="2027-09-30",
            resolution_source_expected="Issuer FY2027 audited financials",
            interval=[102.0, 121.0],
            registered_on="2026-08-01",
        )
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "e2e-acme-fy2027-revenue.json"
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            registered = register(path)
            self.assertEqual(
                registered["registration_sha256"], registration_sha256(registered)
            )
            with patch("tools.forecast_registration.FORECAST_DIR", directory), patch(
                "tools.forecast_registration.load_all",
                lambda d=directory: {path: json.loads(path.read_text())},
            ):
                resolved = resolve(
                    "e2e-acme-fy2027-revenue", 110.0, "FY2027 10-K"
                )
            resolution = resolved["resolution"]
            # |112-110| / |104-110| = 2/6 -> skill 2/3; realized inside interval
            self.assertAlmostEqual(resolution["skill_vs_baseline"], 1 - 2 / 6, places=12)
            self.assertTrue(resolution["interval_hit"])
            report = check_all(directory)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["resolved"], 1)

    def test_expired_window_without_resolution_fails_check(self) -> None:
        # Selective resolution - resolving hits while letting misses expire
        # silently - must be impossible: an unresolved forecast past its
        # resolve_by fails the registry check.
        import tempfile

        record = draft_registration(
            forecast_id="overdue-forecast",
            case_id="c",
            model_id="05",
            metric="m",
            point=2.0,
            history=[("FY2024", 1.0)],
            history_source="outcome log",
            resolve_by="2026-01-01",
            resolution_source_expected="src",
            registered_on="2025-06-01",
        )
        record["registration_sha256"] = registration_sha256(record)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "overdue-forecast.json").write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
            report = check_all(directory)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["overdue"], 1)
            self.assertTrue(
                any("overdue" in e for e in report["problems"]["overdue-forecast.json"])
            )

    def test_due_report_separates_overdue_from_upcoming(self) -> None:
        import tempfile
        from datetime import timedelta

        def make(fid: str, resolve_by: str) -> dict:
            record = draft_registration(
                forecast_id=fid, case_id="c", model_id="05", metric="m",
                point=2.0, history=[("FY2024", 1.0)], history_source="log",
                resolve_by=resolve_by, resolution_source_expected="src",
                registered_on="2025-06-01",
            )
            record["registration_sha256"] = registration_sha256(record)
            return record

        today = date.today()
        soon = (today + timedelta(days=10)).isoformat()
        far = (today + timedelta(days=400)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for fid, rb in (("overdue-1", "2026-01-01"), ("soon-1", soon), ("far-1", far)):
                (directory / f"{fid}.json").write_text(
                    json.dumps(make(fid, rb), indent=2) + "\n", encoding="utf-8"
                )
            report = due_report(directory, within_days=45)
            self.assertEqual(report["status"], "OVERDUE")
            self.assertEqual([r["forecast_id"] for r in report["overdue"]], ["overdue-1"])
            self.assertEqual([r["forecast_id"] for r in report["upcoming"]], ["soon-1"])
            self.assertLess(report["overdue"][0]["days"], 0)

    def test_due_report_ok_when_nothing_expired(self) -> None:
        report = due_report()  # committed registry: everything resolves 2027
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["overdue"], [])

    def test_committed_registry_is_clean(self) -> None:
        report = check_all(FORECAST_DIR)
        self.assertEqual(report["problems"], {})
        self.assertEqual(report["duplicate_forecast_ids"], [])
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["forecasts"], 3)

    def test_committed_registrations_are_hash_pinned_and_dated(self) -> None:
        for path in sorted(Path(FORECAST_DIR).glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                record["registration_sha256"], registration_sha256(record), path.name
            )
            self.assertLess(
                date.fromisoformat(record["registered_on"]),
                date.fromisoformat(record["resolve_by"]),
                path.name,
            )


class RestatesBaselineTests(unittest.TestCase):
    """A forecast identical to its baseline scores 0.0 for every outcome.

    Four of the registry's nine live registrations are in exactly that
    shape. They cannot demonstrate skill, and averaging them in would
    report a mean of 0.0 that looks like a measurement of forecasting
    ability rather than an artefact of how they were written.
    """

    def record(self, point: float, baseline: float, **extra) -> dict:
        base = {
            "forecast_id": "t", "case_id": "c", "model_id": "21", "metric": "m",
            "outcome_class": "out_of_sample_forecast", "point": point,
            "interval": None, "basis": "modeled",
            "baseline": {"kind": "naive_last_recorded", "value": baseline, "source": "s"},
            "registered_on": "2026-01-05", "resolve_by": "2026-06-01",
            "resolution_source_expected": "FRED DGS10", "resolution": None,
        }
        base.update(extra)
        return base

    def test_skill_is_zero_for_every_outcome(self) -> None:
        record = self.record(0.0463, 0.0463)
        for realized in (0.03, 0.0463, 0.08):
            self.assertEqual(
                0.0, forecast_registration.score(record, realized)["skill_vs_baseline"]
            )

    def test_detected_only_when_point_equals_baseline(self) -> None:
        self.assertTrue(forecast_registration.restates_baseline(self.record(0.0463, 0.0463)))
        self.assertFalse(forecast_registration.restates_baseline(self.record(0.0466, 0.0463)))

    def test_a_new_registration_is_blocked(self) -> None:
        errors = forecast_registration.validate_record(self.record(0.0463, 0.0463))
        self.assertTrue(
            any("can never demonstrate skill" in e for e in errors), errors
        )

    def test_an_already_registered_record_is_not_retroactively_invalidated(self) -> None:
        # Registrations are immutable by design -- the whole point of the
        # content hash. The rule blocks new ones; it does not rewrite history.
        record = self.record(0.0463, 0.0463)
        record["registration_sha256"] = forecast_registration.registration_sha256(record)
        errors = forecast_registration.validate_record(record)
        self.assertEqual([], [e for e in errors if "demonstrate skill" in e])

    def test_a_forecast_with_an_edge_is_accepted(self) -> None:
        errors = forecast_registration.validate_record(self.record(0.0466, 0.0463))
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
