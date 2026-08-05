"""The maturity gate's reference_checks tokens must bind to real oracles."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import reference_check_registry, validate_model_inventory
from tools.reference_check_registry import (
    WORKBOOK_VERIFIED_MODELS,
    coverage_summary,
    resolve_reference_checks,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "standards" / "model_inventory.json"


def _models() -> list[dict]:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))["models"]


class ReferenceCheckBindingTests(unittest.TestCase):
    def test_every_declared_token_is_classified(self) -> None:
        models = _models()
        bindings = resolve_reference_checks(models)
        self.assertEqual(set(bindings), {str(m["id"]) for m in models})
        for model in models:
            binding = bindings[str(model["id"])]
            self.assertEqual(
                sorted(binding["tokens"]),
                sorted(str(t) for t in model.get("reference_checks") or []),
            )
            for status in binding["tokens"].values():
                self.assertIn(status, {"identity", "identity_failed", "flag", "unbound"})

    def test_all_bound_identity_checks_pass_on_committed_registries(self) -> None:
        # The core assertion the gate now enforces: every reference-check
        # token that IS bound to an oracle identity passes it on the
        # committed case registries.
        bindings = resolve_reference_checks(_models())
        failures = {
            model_id: binding["identity_failures"]
            for model_id, binding in bindings.items()
            if binding["identity_failures"]
        }
        self.assertEqual(failures, {})

    def test_oracle_backed_models_have_executable_coverage(self) -> None:
        bindings = resolve_reference_checks(_models())
        for model_id, binding in bindings.items():
            if binding["oracle"] is not None:
                self.assertGreater(binding["cases_run"], 0, model_id)
                self.assertTrue(
                    any(s == "identity" for s in binding["tokens"].values()),
                    f"model {model_id} has an oracle but no identity-bound token",
                )

    def test_coverage_summary_partitions_declared_tokens(self) -> None:
        bindings = resolve_reference_checks(_models())
        coverage = coverage_summary(bindings)
        self.assertEqual(
            coverage["declared"],
            coverage["identity"]
            + coverage["identity_failed"]
            + coverage["flag"]
            + coverage["unbound"],
        )
        self.assertGreaterEqual(coverage["identity"], 1)
        self.assertEqual(coverage["models_with_oracle"], 15)

    def test_workbook_verified_constant_matches_verify_reference_calcs(self) -> None:
        # Pin the constant to the actual check functions so it cannot rot
        # silently when workbook checks are added or removed.
        from tools import verify_reference_calcs

        names = " ".join(check.__name__ for check in verify_reference_calcs.CHECKS)
        expectations = {
            "01": "check_base_archetype_integration",
            "03": "check_lbo_sources_uses_and_debt_schedule",
            "13": "check_vc_",
            "14": "check_black_scholes",
            "21": "check_bond_duration",
        }
        self.assertEqual(set(expectations), WORKBOOK_VERIFIED_MODELS)
        for model_id, fragment in expectations.items():
            self.assertIn(fragment, names, f"model {model_id}: {fragment} missing")

    def test_failing_identity_blocks_an_m2_model(self) -> None:
        # A wrong reference calculation must fail the maturity gate itself,
        # not just the oracle suite: patch the binding pass to report one
        # failing identity for model 01 and assert validate_inventory turns
        # it into a blocking model error (and that unbound tokens surface as
        # warnings, not errors).
        from unittest.mock import patch

        models = _models()
        real = resolve_reference_checks(models)
        doctored = {model_id: dict(binding) for model_id, binding in real.items()}
        doctored["01"] = dict(
            doctored["01"],
            tokens=dict(doctored["01"]["tokens"], per_share_identity="identity_failed"),
            identity_failures=["per_share_identity"],
        )
        with patch.object(
            validate_model_inventory.reference_check_registry,
            "resolve_reference_checks",
            return_value=doctored,
        ):
            results, _ = validate_model_inventory.validate_inventory({"models": models})
        by_id = {result.model_id: result for result in results}
        self.assertTrue(
            any("per_share_identity" in e and "FAILED" in e for e in by_id["01"].errors),
            by_id["01"].errors,
        )
        # Unbound tokens stay warnings on every model, never errors.
        for result in results:
            for warning in result.warnings:
                if "bound to no oracle" in warning:
                    break
            self.assertFalse(
                any("bound to no oracle" in e for e in result.errors)
            )


if __name__ == "__main__":
    unittest.main()
