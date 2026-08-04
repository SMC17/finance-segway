"""Thin L3 tool stub: private_credit_underwrite

Fail-closed agent-facing interface for the 05 Private Credit flagship.
Does not invent math. Does not claim M3. Invokes (or simulates invocation of)
the domain builder path and requires provenance on material inputs.

Usage (CLI):
  python tools/agents/private_credit_underwrite.py --demo
  python tools/agents/private_credit_underwrite.py --inputs path/to/inputs.json

Contract: docs/AGENT_TOOL_CONTRACT.md
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ROOT / "05_Private_Credit"


@dataclass
class Provenance:
    source_name: str
    as_of_date: str
    retrieval_date: str
    transformation: str = "none"


@dataclass
class ToolInput:
    instance_slug: str
    as_of: str
    scenario: str = "Base"
    # Material facts must carry provenance
    facts: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Provenance] = field(default_factory=dict)


@dataclass
class ToolOutput:
    ok: bool
    checks_status: str  # PASS | REVIEW | FAIL | NOT_RUN
    workbook_path: str | None
    headline: dict[str, Any]
    sources_written: list[dict[str, str]]
    message: str
    refresh_log_entry: str | None = None


REQUIRED_FACT_KEYS = (
    "borrower_name",
    "facility_size",
    "pricing_spread_bps",
    "cfads_base",
    "senior_debt",
)


def validate_provenance(inp: ToolInput) -> list[str]:
    errors = []
    for key in REQUIRED_FACT_KEYS:
        if key not in inp.facts:
            errors.append(f"missing required fact: {key}")
            continue
        if key not in inp.provenance:
            errors.append(f"missing provenance for material fact: {key}")
    return errors


def run(inp: ToolInput) -> ToolOutput:
    """"Execute the tool. Builder integration is stubbed until instance path is live."""
    errors = validate_provenance(inp)
    if errors:
        return ToolOutput(
            ok=False,
            checks_status="FAIL",
            workbook_path=None,
            headline={},
            sources_written=[],
            message="fail-closed: " + "; ".join(errors),
        )

    # Stub: in production this calls build_private_credit_release / instance writer
    # and runs Checks. Here we only prove the contract surface.
    sources = []
    for key, prov in inp.provenance.items():
        sources.append(
            {
                "field": key,
                "source_name": prov.source_name,
                "as_of_date": prov.as_of_date,
                "retrieval_date": prov.retrieval_date,
                "transformation": prov.transformation,
            }
        )

    instance_dir = DOMAIN / "instances" / inp.instance_slug
    workbook_path = str(instance_dir / "model.xlsx")

    return ToolOutput(
        ok=True,
        checks_status="NOT_RUN",  # becomes PASS/FAIL when builder+Checks wired
        workbook_path=workbook_path,
        headline={
            "borrower": inp.facts.get("borrower_name"),
            "scenario": inp.scenario,
            "facility_size": inp.facts.get("facility_size"),
            "note": "stub — invoke domain builder next",
        },
        sources_written=sources,
        message=(
            "provenance OK; builder/Checks not yet invoked. "
            "Wire tools/builders/build_private_credit_release.py next."
        ),
        refresh_log_entry=f"{inp.as_of} stub underwrite for {inp.instance_slug}",
    )


def demo() -> ToolOutput:
    today = date.today().isoformat()
    inp = ToolInput(
        instance_slug="demo_unitranche_stub",
        as_of=today,
        scenario="Base",
        facts={
            "borrower_name": "Demo Borrower LLC",
            "facility_size": 150_000_000,
            "pricing_spread_bps": 550,
            "cfads_base": 28_000_000,
            "senior_debt": 150_000_000,
        },
        provenance={
            k: Provenance(
                source_name="demo_fixture",
                as_of_date=today,
                retrieval_date=today,
                transformation="demo only — not for client use",
            )
            for k in REQUIRED_FACT_KEYS
        },
    )
    return run(inp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--inputs", type=Path, help="JSON file matching ToolInput shape")
    args = ap.parse_args()

    if args.demo:
        out = demo()
    elif args.inputs:
        raw = json.loads(args.inputs.read_text())
        prov = {
            k: Provenance(**v) if isinstance(v, dict) else v
            for k, v in raw.get("provenance", {}).items()
        }
        inp = ToolInput(
            instance_slug=raw["instance_slug"],
            as_of=raw["as_of"],
            scenario=raw.get("scenario", "Base"),
            facts=raw.get("facts", {}),
            provenance=prov,
        )
        out = run(inp)
    else:
        ap.error("provide --demo or --inputs")
        return 2

    print(json.dumps(asdict(out), indent=2))
    return 0 if out.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
