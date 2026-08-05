"""Pre-registration discipline for the forecast registry."""
from __future__ import annotations

import copy
import json
import unittest
from datetime import date
from pathlib import Path

from tools.forecast_registration import (
    FORECAST_DIR,
    check_all,
    draft_registration,
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
            resolve_by="2027-09-30",
            resolution_source_expected="Issuer FY2027 audited financials",
            interval=[102.0, 121.0],
            registered_on="2026-08-05",
        )
        self.assertEqual(validate_record(record, today=TODAY), [])
        self.assertEqual(record["baseline"]["kind"], "naive_last_recorded")
        self.assertEqual(record["baseline"]["value"], 104.0)
        self.assertIn("FY2026", record["baseline"]["source"])
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
                resolve_by="2027-01-01",
                resolution_source_expected="src",
            )
        with self.assertRaises(ValueError) as ctx:
            draft_registration(
                forecast_id="closed-window",
                case_id="c",
                model_id="05",
                metric="m",
                point=1.0,
                history=[("FY2025", 1.0)],
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


if __name__ == "__main__":
    unittest.main()
