"""Resolve model-inventory reference_checks tokens against executable oracles.

The inventory declares each model's reference_checks as token strings. Two
oracle suites already execute per-model identity checks keyed by those token
names — legacy_engine_oracles (01/02/05/06/07/13) and domain_hardening_oracles
(08/10/11/12/15/16/17/23/24) — against case inputs frozen in their registries.
Until now nothing connected the inventory's tokens to those callables: the
maturity gate counted strings.

This module runs every oracle over its registry cases and classifies each
declared token:

  identity        produced as a pass/fail identity check by the model's
                  oracle and passing across every registry case
  identity_failed produced as an identity check and failing in at least one
                  case — a broken reference check, which must block the gate
  flag            exercised by the oracle as a scenario risk flag in at least
                  one registry case (a real diagnostic, but not a provable
                  pass/fail identity)
  unbound         declared by the inventory but produced by no oracle — a
                  claim with no executable check behind it

The pass is pure Python over JSON case inputs; it does not open workbooks and
needs no LibreOffice, so it is cheap enough to run inside the inventory gate.
Workbook-level verification (LibreOffice recalc vs independent Python in
verify_reference_calcs.py) is reported alongside as workbook_verified.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from tools import domain_hardening_oracles, legacy_engine_oracles
except (ImportError, ModuleNotFoundError):  # script-style execution
    import domain_hardening_oracles
    import legacy_engine_oracles

ROOT = Path(__file__).resolve().parents[1]
LEGACY_REGISTRY = ROOT / "standards" / "frontier" / "legacy_engine_registry.json"
HARDENING_REGISTRY = ROOT / "standards" / "domain_hardening" / "m1_registry.json"

# Models whose workbooks are additionally verified end-to-end (LibreOffice
# recalculation compared to independent Python) by verify_reference_calcs.py.
# Pinned by tests against that module's actual check functions so this
# constant cannot rot silently when checks are added or removed.
WORKBOOK_VERIFIED_MODELS = {"01", "03", "05", "13", "14", "21", "31"}


def _case_sources() -> dict[str, tuple[str, Callable[..., dict[str, Any]], list[dict[str, Any]]]]:
    sources: dict[str, tuple[str, Callable[..., dict[str, Any]], list[dict[str, Any]]]] = {}
    legacy = json.loads(LEGACY_REGISTRY.read_text(encoding="utf-8"))
    for model in legacy.get("models", []):
        sources[str(model["model_id"])] = (
            "legacy",
            legacy_engine_oracles.validate_case,
            model.get("cases", []),
        )
    hardening = json.loads(HARDENING_REGISTRY.read_text(encoding="utf-8"))
    for domain in hardening.get("domains", []):
        sources[str(domain["model_id"])] = (
            "hardening",
            domain_hardening_oracles.validate_case,
            domain.get("cases", []),
        )
    return sources


def resolve_reference_checks(models: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Classify every declared reference_checks token for every model.

    Returns {model_id: {oracle, cases_run, tokens: {token: status},
    identity_failures: [...], workbook_verified}}.
    """
    sources = _case_sources()
    bindings: dict[str, dict[str, Any]] = {}
    for model in models:
        model_id = str(model.get("id", ""))
        declared = [str(token) for token in model.get("reference_checks") or []]
        binding: dict[str, Any] = {
            "oracle": None,
            "cases_run": 0,
            "tokens": {},
            "identity_failures": [],
            "workbook_verified": model_id in WORKBOOK_VERIFIED_MODELS,
        }
        identities: dict[str, bool] = {}
        flags: set[str] = set()
        source = sources.get(model_id)
        if source is not None:
            kind, validate_case, cases = source
            binding["oracle"] = kind
            for case in cases:
                result = validate_case(model_id, case["inputs"])
                for token, passed in result.get("identity_checks", {}).items():
                    identities[token] = identities.get(token, True) and bool(passed)
                flags.update(result.get("active_risk_flags") or [])
                binding["cases_run"] += 1
        for token in declared:
            if token in identities:
                if identities[token]:
                    status = "identity"
                else:
                    status = "identity_failed"
                    binding["identity_failures"].append(token)
            elif token in flags:
                status = "flag"
            else:
                status = "unbound"
            binding["tokens"][token] = status
        bindings[model_id] = binding
    return bindings


def coverage_summary(bindings: dict[str, dict[str, Any]]) -> dict[str, int]:
    summary = {
        "identity": 0,
        "identity_failed": 0,
        "flag": 0,
        "unbound": 0,
        "declared": 0,
        "models_with_oracle": 0,
        "models_workbook_verified": 0,
    }
    for binding in bindings.values():
        for status in binding["tokens"].values():
            summary[status] += 1
            summary["declared"] += 1
        if binding["oracle"]:
            summary["models_with_oracle"] += 1
        if binding["workbook_verified"]:
            summary["models_workbook_verified"] += 1
    return summary
