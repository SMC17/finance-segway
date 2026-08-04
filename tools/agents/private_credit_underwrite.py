"""L3 tool: private_credit_underwrite

Fail-closed agent interface for 05 Private Credit.
- Requires provenance on every material fact
- Invokes tools/builders/build_private_credit_release.py
- Writes instance directory, source_register fragment, receipt, RefreshLog note
- Does not invent math; does not claim Checks PASS until a human/CI recalc verifies

Usage:
  python tools/agents/private_credit_underwrite.py --demo
  python tools/agents/private_credit_underwrite.py --inputs inputs.json
  python tools/agents/private_credit_underwrite.py --instance public_ares_capital_2024 --use-ares-fixture
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ROOT / "05_Private_Credit"
BUILDER = ROOT / "tools" / "builders" / "build_private_credit_release.py"
TEMPLATE = DOMAIN / "_template_CREDIT.xlsx"

sys.path.insert(0, str(ROOT))


@dataclass
class Provenance:
    source_name: str
    as_of_date: str
    retrieval_date: str
    transformation: str = "none"
    snapshot: str = ""


@dataclass
class ToolInput:
    instance_slug: str
    as_of: str
    scenario: str = "Base"
    facts: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Provenance] = field(default_factory=dict)


@dataclass
class ToolOutput:
    ok: bool
    checks_status: str
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


def _write_source_register(instance_dir: Path, inp: ToolInput) -> list[dict[str, str]]:
    reg_path = instance_dir / "sources" / "source_register.csv"
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    lines = [
        "field,source_name,as_of_date,retrieval_date,transformation,snapshot,workbook_destination"
    ]
    for key, prov in inp.provenance.items():
        row = {
            "field": key,
            "source_name": prov.source_name,
            "as_of_date": prov.as_of_date,
            "retrieval_date": prov.retrieval_date,
            "transformation": prov.transformation,
            "snapshot": prov.snapshot,
            "workbook_destination": "Assumptions / operating case",
        }
        rows.append(row)
        lines.append(
            ",".join(
                str(row[c]).replace(",", ";")
                for c in [
                    "field",
                    "source_name",
                    "as_of_date",
                    "retrieval_date",
                    "transformation",
                    "snapshot",
                    "workbook_destination",
                ]
            )
        )
    reg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def _invoke_builder(workbook_path: Path) -> str:
    """Build release-grade credit workbook into workbook_path."""
    try:
        from tools.builders.build_private_credit_release import build as pc_build

        pc_build(workbook_path)
        return "builder_ok"
    except Exception as exc:
        # Fallback: copy canonical template so the instance still has a workbook shell
        if TEMPLATE.exists():
            shutil.copyfile(TEMPLATE, workbook_path)
            return f"builder_failed_fallback_template: {exc}"
        return f"builder_failed: {exc}"


def run(inp: ToolInput) -> ToolOutput:
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

    instance_dir = DOMAIN / "instances" / inp.instance_slug
    instance_dir.mkdir(parents=True, exist_ok=True)
    (instance_dir / "sources" / "snapshots").mkdir(parents=True, exist_ok=True)

    workbook_path = instance_dir / "model.xlsx"
    builder_status = _invoke_builder(workbook_path)

    # Persist inputs for audit
    (instance_dir / "inputs.json").write_text(
        json.dumps(
            {
                "instance_slug": inp.instance_slug,
                "as_of": inp.as_of,
                "scenario": inp.scenario,
                "facts": inp.facts,
                "provenance": {k: asdict(v) for k, v in inp.provenance.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    sources = _write_source_register(instance_dir, inp)

    receipt = {
        "instance_slug": inp.instance_slug,
        "domain": "05_Private_Credit",
        "as_of": inp.as_of,
        "scenario": inp.scenario,
        "builder_status": builder_status,
        "checks_status": "NOT_RUN",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "facts": inp.facts,
        "note": (
            "Workbook produced by builder or template fallback. "
            "LibreOffice recalc + Checks must be run before client use. "
            "Maturity remains M2 until evidence gates in EVIDENCE_STATUS.md are met."
        ),
    }
    (instance_dir / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    refresh = (
        f"{inp.as_of} | underwrite via private_credit_underwrite | "
        f"scenario={inp.scenario} | builder={builder_status} | checks=NOT_RUN"
    )
    log_path = instance_dir / "RefreshLog.md"
    prev = log_path.read_text(encoding="utf-8") if log_path.exists() else "# RefreshLog\n\n"
    log_path.write_text(prev + f"- {refresh}\n", encoding="utf-8")

    return ToolOutput(
        ok=True,
        checks_status="NOT_RUN",
        workbook_path=str(workbook_path.relative_to(ROOT)),
        headline={
            "borrower": inp.facts.get("borrower_name"),
            "scenario": inp.scenario,
            "facility_size": inp.facts.get("facility_size"),
            "senior_debt": inp.facts.get("senior_debt"),
            "cfads_base": inp.facts.get("cfads_base"),
            "builder_status": builder_status,
        },
        sources_written=sources,
        message=(
            f"Instance written under {instance_dir.relative_to(ROOT)}. "
            f"Builder: {builder_status}. Run Checks before any client deliverable."
        ),
        refresh_log_entry=refresh,
    )


def ares_fixture() -> ToolInput:
    """Public BDC reference case using Ares Capital sourced facts (see domain source_register)."""
    today = date.today().isoformat()
    # Portfolio-level proxy metrics from public ARCC disclosures / EDGAR facts —
    # labeled as modeler mapping, not a single-borrower commitment letter.
    return ToolInput(
        instance_slug="public_ares_capital_2024",
        as_of="2026-03-31",
        scenario="Base",
        facts={
            "borrower_name": "Ares Capital Corporation (public BDC portfolio proxy)",
            "facility_size": 15_848_000_000,  # LongTermDebt from companyfacts
            "pricing_spread_bps": 0,  # portfolio blended — modeler assumption, not single facility
            "cfads_base": 0,  # requires portfolio CFADS construction — placeholder 0 forces REVIEW
            "senior_debt": 15_848_000_000,
            "total_assets": 30_679_000_000,
            "stockholders_equity": 14_065_000_000,
            "interest_expense_q": 213_000_000,
            "cash": 505_000_000,
        },
        provenance={
            "borrower_name": Provenance(
                "SEC EDGAR / Ares Capital identity",
                "2026-03-31",
                today,
                "public company name",
                "05_Private_Credit/sources/snapshots/credit-public-ares-2024.json",
            ),
            "facility_size": Provenance(
                "SEC companyfacts LongTermDebt",
                "2026-03-31",
                today,
                "latest USD LongTermDebt from 10-Q",
                "tools/data_fabric/out/ARCC_facts_selected.json",
            ),
            "pricing_spread_bps": Provenance(
                "modeler_assumption",
                "2026-03-31",
                today,
                "portfolio blended spread not a single facility — set 0 pending underwriting",
                "",
            ),
            "cfads_base": Provenance(
                "modeler_assumption",
                "2026-03-31",
                today,
                "placeholder 0 — construct CFADS from portfolio company data before decision use",
                "",
            ),
            "senior_debt": Provenance(
                "SEC companyfacts LongTermDebt",
                "2026-03-31",
                today,
                "latest USD LongTermDebt from 10-Q",
                "tools/data_fabric/out/ARCC_facts_selected.json",
            ),
        },
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
            k: Provenance("demo_fixture", today, today, "demo only — not for client use")
            for k in REQUIRED_FACT_KEYS
        },
    )
    return run(inp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--use-ares-fixture", action="store_true")
    ap.add_argument("--instance", type=str, default="")
    ap.add_argument("--inputs", type=Path, help="JSON file matching ToolInput shape")
    args = ap.parse_args()

    if args.use_ares_fixture:
        inp = ares_fixture()
        if args.instance:
            inp.instance_slug = args.instance
        out = run(inp)
    elif args.demo:
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
        ap.error("provide --demo, --use-ares-fixture, or --inputs")
        return 2

    print(json.dumps(asdict(out), indent=2))
    return 0 if out.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
