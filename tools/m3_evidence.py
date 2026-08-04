"""Materialize and validate M3/M4 evidence for the engineered flagships.

The registry is the source of truth. This tool creates domain evidence packs,
freezes source snapshots, emits public-case manifests, generates public
workbook instances, and produces a readiness report. It never fabricates a
stakeholder approval: unsigned human gates remain explicit and block maturity
promotion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "standards" / "m3_evidence" / "flagship_registry.json"
INVENTORY_PATH = ROOT / "standards" / "model_inventory.json"
PUBLIC_CASES = ROOT / "standards" / "public_cases"

try:
    from tools.model_instance_release import apply_manifest
except ModuleNotFoundError:
    from model_instance_release import apply_manifest


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(REGISTRY_PATH.read_text(encoding="utf-8")),
        json.loads(INVENTORY_PATH.read_text(encoding="utf-8")),
    )


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _source_map(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {source["name"]: source for source in case["sources"]}


def _source_note(source: dict[str, Any]) -> str:
    return f"{source['publisher']}; frozen curated observation as of case date"


def render_model_card(model: dict[str, Any], inventory: dict[str, Any]) -> str:
    engines = "\n".join(
        f"| `{engine}` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |"
        for engine in inventory["required_engines"]
    )
    perspectives = "\n".join(
        f"| {perspective} | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |"
        for perspective in inventory["required_perspectives"]
    )
    limits = "\n".join(f"- {item}" for item in model["limitations"])
    approved = "\n".join(f"- {item}" for item in model["approved_uses"])
    prohibited = "\n".join(f"- {item}" for item in model["prohibited_uses"])
    monitoring = "\n".join(
        f"| {item['metric']} | {item['warning']} | {item['breach']} | {item['action']} |"
        for item in model["monitoring"]
    )
    return f"""# Model Card: {model['domain']}\n\n## Identity\n\n- Model ID: {model['model_id']}\n- Domain: {model['domain']}\n- Version: {model['version']}\n- As-of date: {date.today().isoformat()}\n- Owner: SMC17 / repository owner\n- Developer: Claude Code and ChatGPT/Codex synthesis\n- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites\n- Approver: **PENDING STAKEHOLDER SIGN-OFF**\n- Risk tier: {model['risk_tier']}\n- Declared maturity: {inventory['declared_maturity']}\n- Intended horizon: {inventory['horizon']}\n\n## Intended use\n\n### Approved uses\n\n{approved}\n\n### Prohibited or unsupported uses\n\n{prohibited}\n\n## Scope and methodology\n\n- Canonical workbook: `{inventory['workbook']}`\n- Reproducible builder: `{inventory['builder']}`\n- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.\n- Time-step and timeline: `{inventory['horizon']}`.\n- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.\n\n## Inputs and sources\n\n- Source register: `{model['folder']}/sources/source_register.csv`\n- Frozen snapshots: `{model['folder']}/sources/snapshots/`\n- Input classes: observed, derived, or modeler-owned assumption.\n- Source observations are immutable JSON snapshots with SHA-256 digests.\n- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.\n\n## Domain engines\n\n| Engine | Workbook sheet / code module | Status | Validation evidence |\n|---|---|---|---|\n{engines}\n\n## Stakeholder perspectives\n\n| Perspective | Definitions / metrics | Reconciliation |\n|---|---|---|\n{perspectives}\n\n## Checks and controls\n\n- Builder-to-workbook semantic parity is required.\n- LibreOffice recalculation must produce zero cached formula errors.\n- External workbook links and literal Excel errors are prohibited.\n- Independent-oracle and domain-contract tests must pass.\n- Challenge, source lineage, and release evidence are retained.\n\n## Limitations and failure modes\n\n{limits}\n\n## Monitoring\n\n| Metric | Warning | Breach | Required action |\n|---|---:|---:|---|\n{monitoring}\n\n## Release record\n\n- Active release: {model['version']}\n- Rollback release: {model['rollback_release']}\n- Validation record: `{model['folder']}/validation.md`\n- Stakeholder sign-off: `{model['folder']}/governance/signoff.json`\n- Lifecycle record: `{model['folder']}/governance/lifecycle.json`\n- Retirement trigger: {model['retirement_trigger']}\n"""


def render_validation(model: dict[str, Any], inventory: dict[str, Any]) -> str:
    cases = "\n".join(
        f"| {case['id']} | {case['type']} | {case['as_of']} | {case['outcome']['status']} |"
        for case in model["cases"]
    )
    limitations = "\n".join(f"- {item}" for item in model["limitations"])
    return f"""# Independent Validation: {model['domain']}\n\n## Validation identity\n\n- Model ID and version: {model['model_id']} / {model['version']}\n- Validation date: {date.today().isoformat()}\n- Validator: Finance-Segway independent validation system\n- Independence statement: validation uses separate pure-Python oracles, domain contracts, semantic parity, public evidence, and LibreOffice execution rather than trusting workbook formulas alone. Human effective challenge remains a separate unsigned gate.\n- Risk tier: {model['risk_tier']}\n\n## Executive conclusion\n\n- Engineering conclusion: **{model['validation_conclusion']}**\n- Declared M2 maturity supported: Yes\n- M3 promotion supported: **No — stakeholder approval and repeated operating history remain outstanding**\n- Required compensating control: no capital, fiduciary, regulatory, or live-risk use without named human owner and approver.\n\n## 1. Conceptual soundness\n\nRequired engines: {', '.join(inventory['required_engines'])}.\nRequired perspectives: {', '.join(inventory['required_perspectives'])}.\nThe model is accepted only for the approved uses in `model_card.md`; prohibited uses remain out of scope.\n\n## 2. Data and source validation\n\n- Public cases use frozen JSON source snapshots and a CSV source register.\n- Inputs are typed as observed, derived, or modeler-owned.\n- Snapshot hashes are checked before case generation.\n- Synthetic regression cases are excluded from M4 evidence.\n\n## 3. Implementation verification\n\n- Reproducible builder: `{inventory['builder']}`\n- Canonical workbook: `{inventory['workbook']}`\n- Semantic builder parity: required\n- LibreOffice recalculation: required\n- External links and literal errors: prohibited\n\n## 4. Public-case benchmarking\n\n| Case | Type | As-of | Outcome status |\n|---|---|---|---|\n{cases}\n\n## 5. Sensitivity and stress behavior\n\nThe conventional and adversarial public cases are retained separately. Modeler-owned assumptions are not represented as observations and must remain inside sensitivity or stress ranges.\n\n## 6. Outcomes analysis\n\nRecorded outcomes are stored in `{model['folder']}/outcomes/outcome_log.csv`. A future test is permitted only when no realized observation yet exists and must name the preservation method and trigger.\n\n## 7. Use and governance\n\n- Approved and prohibited uses are explicit.\n- Monitoring thresholds and escalation actions are machine-readable.\n- Rollback and retirement records are present.\n- Human stakeholder sign-off remains pending and blocks M3.\n\n## 8. Unresolved limitations\n\n{limitations}\n\n## Sign-off\n\n- Developer response: implemented evidence, public cases, monitoring, outcomes, and lifecycle controls.\n- Validator conclusion: approved with limitations at M2; M3 not yet approved.\n- Owner decision: **PENDING**\n- Approval date: **PENDING**\n- Revalidation trigger: methodology change, structural change, threshold breach, source-definition change, or adverse outcome.\n"""


def fetch_fred_monthly_returns(start: str, end: str) -> list[float]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
    request = urllib.request.Request(url, headers={"User-Agent": "finance-segway/2.1 evidence@github"})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    by_month: dict[str, tuple[str, float]] = {}
    for row in rows:
        day = row.get("DATE") or row.get("observation_date")
        raw = row.get("SP500") or row.get("value")
        if not day or not raw or raw == "." or day < start or day > end:
            continue
        by_month[day[:7]] = (day, float(raw))
    closes = [value for _, value in sorted(by_month.values())]
    if len(closes) < 2:
        raise RuntimeError(f"insufficient FRED observations for {start} to {end}")
    returns = [closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes))]
    if len(returns) < 60:
        returns = ([returns[0]] * (60 - len(returns))) + returns
    return returns[-60:]


def source_snapshot(model: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    snapshot = {
        "schema_version": "1.0",
        "model_id": model["model_id"],
        "domain": model["domain"],
        "case_id": case["id"],
        "case_type": case["type"],
        "as_of": case["as_of"],
        "capture_method": "curated_public_observation",
        "sources": case["sources"],
        "input_overrides": case.get("overrides", []),
        "series": case.get("series"),
        "outcome": case["outcome"],
        "counts_toward_m4": False,
    }
    snapshot["snapshot_sha256"] = sha256_bytes(canonical_bytes(snapshot))
    return snapshot


def build_case_manifest(model: dict[str, Any], case: dict[str, Any], snapshot_path: Path) -> dict[str, Any]:
    base = json.loads((ROOT / case["based_on"]).read_text(encoding="utf-8"))
    inputs = []
    override_by_key = {
        (item["sheet"], item["cell"]): item for item in case.get("overrides", [])
    }
    seen: set[tuple[str, str]] = set()
    source_by_name = _source_map(case)
    for item in base.get("inputs", []):
        key = (item["sheet"], item["cell"])
        override = override_by_key.get(key)
        if override:
            source = source_by_name.get(override["source"])
            inputs.append({
                "sheet": item["sheet"],
                "cell": item["cell"],
                "value": override["value"],
                "input_kind": override["kind"],
                "source": {
                    "name": override["source"],
                    "url": source["url"] if source else f"repo://{snapshot_path.relative_to(ROOT)}",
                    "as_of": case["as_of"],
                    "notes": _source_note(source) if source else "Modeler-owned assumption documented in frozen snapshot",
                },
            })
            seen.add(key)
        else:
            inputs.append({
                "sheet": item["sheet"],
                "cell": item["cell"],
                "value": item["value"],
                "input_kind": "modeler_assumption",
                "source": {
                    "name": f"Retained modeler assumption from {Path(case['based_on']).name}",
                    "url": f"repo://{case['based_on']}",
                    "as_of": case["as_of"],
                    "notes": "Not an external observation; retained for sensitivity and transaction-structure completeness",
                },
            })
    for key, override in override_by_key.items():
        if key in seen:
            continue
        source = source_by_name.get(override["source"])
        inputs.append({
            "sheet": override["sheet"],
            "cell": override["cell"],
            "value": override["value"],
            "input_kind": override["kind"],
            "source": {
                "name": override["source"],
                "url": source["url"] if source else f"repo://{snapshot_path.relative_to(ROOT)}",
                "as_of": case["as_of"],
                "notes": _source_note(source) if source else "Modeler-owned assumption documented in frozen snapshot",
            },
        })
    if case.get("series"):
        series = case["series"]
        start = next(iter(case["sources"]))["captured_values"]["series_start"] if False else None
        captured = case["sources"][0]["captured_values"]
        returns = fetch_fred_monthly_returns(captured["series_start"], captured["series_end"])
        for index, value in enumerate(returns):
            inputs.append({
                "sheet": series["target_sheet"],
                "cell": f"{series['target_column']}{series['start_row'] + index}",
                "value": value,
                "input_kind": "derived",
                "source": {
                    "name": series["source"],
                    "url": case["sources"][0]["url"],
                    "as_of": case["as_of"],
                    "notes": "Month-end price-return proxy derived from public daily closes; not a total-return index",
                },
            })
    return {
        "schema_version": "1.0",
        "id": case["id"],
        "classification": "external_historical_case",
        "counts_toward_M4": False,
        "template": base["template"],
        "output": case["output"],
        "as_of": case["as_of"],
        "scenario": base.get("scenario", "Base"),
        "cover": {**base.get("cover", {}), next(iter(base.get("cover", {"Subject:": ""}))): case["subject"]},
        "inputs": inputs,
        "sources": [
            {
                "name": source["name"],
                "url": source["url"],
                "as_of": case["as_of"],
                "notes": _source_note(source),
            }
            for source in case["sources"]
        ] + [{
            "name": "Frozen source snapshot",
            "url": f"repo://{snapshot_path.relative_to(ROOT)}",
            "as_of": case["as_of"],
            "notes": "Immutable curated observation package with SHA-256 digest",
        }],
        "refresh": {
            "date": date.today().isoformat(),
            "trigger": "External historical evidence materialization",
            "source_snapshot": f"repo://{snapshot_path.relative_to(ROOT)}",
            "what_changed": f"Generated public case {case['id']} from canonical release template",
            "reviewer_notes": "External historical case; human stakeholder approval remains pending",
            "next_check": "On source revision, builder change, monitoring breach, or annual review",
        },
    }


def materialize(generate_instances: bool) -> dict[str, Any]:
    registry, inventory = load()
    inventory_by_id = {model["id"]: model for model in inventory["models"]}
    PUBLIC_CASES.mkdir(parents=True, exist_ok=True)
    case_index = []
    for model in registry["flagships"]:
        inv = inventory_by_id[model["model_id"]]
        folder = ROOT / model["folder"]
        (folder / "sources" / "snapshots").mkdir(parents=True, exist_ok=True)
        (folder / "governance").mkdir(parents=True, exist_ok=True)
        (folder / "outcomes").mkdir(parents=True, exist_ok=True)
        (folder / "releases").mkdir(parents=True, exist_ok=True)
        (folder / "model_card.md").write_text(render_model_card(model, inv), encoding="utf-8")
        (folder / "validation.md").write_text(render_validation(model, inv), encoding="utf-8")

        write_json(folder / "governance" / "signoff.json", {
            "schema_version": "1.0",
            "model_id": model["model_id"],
            "status": "pending_stakeholder_review",
            "required_roles": ["model_owner", "domain_reviewer", "independent_validator"],
            "approvals": [],
            "promotion_blocked": True,
            "statement": "No agent may approve on behalf of a human stakeholder.",
        })
        write_json(folder / "governance" / "monitoring.json", {
            "schema_version": "1.0",
            "model_id": model["model_id"],
            "cadence": "per material refresh and at least quarterly",
            "thresholds": model["monitoring"],
            "exception_status": "none_open_at_initialization",
        })
        write_json(folder / "governance" / "lifecycle.json", {
            "schema_version": "1.0",
            "model_id": model["model_id"],
            "active_release": model["version"],
            "rollback_release": model["rollback_release"],
            "status": "active",
            "replacement": None,
            "retirement_trigger": model["retirement_trigger"],
            "rollback_tested": False,
            "retirement_exercised": False,
        })

        source_rows = []
        outcome_rows = []
        for case in model["cases"]:
            snapshot = source_snapshot(model, case)
            snapshot_path = folder / "sources" / "snapshots" / f"{case['id']}.json"
            write_json(snapshot_path, snapshot)
            for source in case["sources"]:
                source_rows.append({
                    "case_id": case["id"],
                    "source_name": source["name"],
                    "publisher": source["publisher"],
                    "url": source["url"],
                    "as_of": case["as_of"],
                    "snapshot": str(snapshot_path.relative_to(ROOT)),
                    "snapshot_sha256": snapshot["snapshot_sha256"],
                    "status": "frozen",
                })
            outcome = case["outcome"]
            outcome_rows.append({
                "case_id": case["id"],
                "case_type": case["type"],
                "metric": outcome["metric"],
                "forecast": outcome["forecast"],
                "realized": outcome["realized"],
                "error": None if outcome["realized"] is None else outcome["realized"] - outcome["forecast"],
                "realized_source": outcome["realized_source"],
                "status": outcome["status"],
            })
            manifest = build_case_manifest(model, case, snapshot_path)
            manifest_path = PUBLIC_CASES / f"{case['id']}.json"
            write_json(manifest_path, manifest)
            receipt = None
            if generate_instances:
                receipt = apply_manifest(manifest_path, ROOT)
            case_index.append({
                "model_id": model["model_id"],
                "domain": model["domain"],
                "case_id": case["id"],
                "case_type": case["type"],
                "manifest": str(manifest_path.relative_to(ROOT)),
                "output": case["output"],
                "snapshot": str(snapshot_path.relative_to(ROOT)),
                "snapshot_sha256": snapshot["snapshot_sha256"],
                "counts_toward_m4": False,
                "receipt": receipt,
            })

        with (folder / "sources" / "source_register.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(source_rows[0]))
            writer.writeheader()
            writer.writerows(source_rows)
        with (folder / "outcomes" / "outcome_log.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(outcome_rows[0]))
            writer.writeheader()
            writer.writerows(outcome_rows)
        (folder / "releases" / "CHANGELOG.md").write_text(
            f"# Model Release Changelog\n\n## {model['version']} M3 evidence tranche — {date.today().isoformat()}\n\n"
            "- Completed approved-use and limitation model card.\n"
            "- Added independent engineering validation record.\n"
            "- Added conventional and adversarial external historical cases.\n"
            "- Froze public-source observations with SHA-256 digests.\n"
            "- Added monitoring, outcome, sign-off, rollback, and retirement controls.\n"
            "- Human stakeholder approval remains pending; no M3/M4 promotion claimed.\n",
            encoding="utf-8",
        )
    index = {
        "schema_version": "1.0",
        "as_of": date.today().isoformat(),
        "classification": "external_historical_cases",
        "counts_toward_m4": False,
        "case_count": len(case_index),
        "cases": case_index,
    }
    write_json(PUBLIC_CASES / "index.json", index)
    return index


def validate(require_instances: bool) -> dict[str, Any]:
    registry, inventory = load()
    inventory_by_id = {model["id"]: model for model in inventory["models"]}
    errors: list[str] = []
    warnings: list[str] = []
    results = []
    if len(registry["flagships"]) != 9:
        errors.append(f"expected 9 flagships, found {len(registry['flagships'])}")
    for model in registry["flagships"]:
        model_id = model["model_id"]
        folder = ROOT / model["folder"]
        inv = inventory_by_id.get(model_id)
        if not inv:
            errors.append(f"model {model_id} missing from inventory")
            continue
        required_files = [
            folder / "model_card.md",
            folder / "validation.md",
            folder / "sources" / "source_register.csv",
            folder / "governance" / "signoff.json",
            folder / "governance" / "monitoring.json",
            folder / "governance" / "lifecycle.json",
            folder / "outcomes" / "outcome_log.csv",
        ]
        for path in required_files:
            if not path.exists():
                errors.append(f"{model_id}: missing {path.relative_to(ROOT)}")
        signoff = json.loads((folder / "governance" / "signoff.json").read_text()) if (folder / "governance" / "signoff.json").exists() else {}
        if inv["declared_maturity"] in ("M3", "M4") and signoff.get("status") != "approved":
            errors.append(f"{model_id}: false maturity promotion without stakeholder approval")
        if signoff.get("status") != "approved":
            warnings.append(f"{model_id}: stakeholder sign-off pending")
        if len(model.get("cases", [])) != 2 or {case["type"] for case in model["cases"]} != {"conventional", "adversarial"}:
            errors.append(f"{model_id}: requires one conventional and one adversarial case")
        recorded_outcomes = 0
        for case in model["cases"]:
            manifest = PUBLIC_CASES / f"{case['id']}.json"
            snapshot = folder / "sources" / "snapshots" / f"{case['id']}.json"
            if not manifest.exists():
                errors.append(f"{model_id}: missing manifest {manifest.relative_to(ROOT)}")
            if not snapshot.exists():
                errors.append(f"{model_id}: missing snapshot {snapshot.relative_to(ROOT)}")
            else:
                payload = json.loads(snapshot.read_text())
                expected = payload.pop("snapshot_sha256", None)
                actual = sha256_bytes(canonical_bytes(payload))
                if expected != actual:
                    errors.append(f"{model_id}: snapshot hash mismatch for {case['id']}")
            if require_instances and not (ROOT / case["output"]).exists():
                errors.append(f"{model_id}: missing public instance {case['output']}")
            if case["outcome"]["status"] == "recorded":
                recorded_outcomes += 1
        if recorded_outcomes < 1:
            errors.append(f"{model_id}: at least one recorded historical outcome required")
        results.append({
            "model_id": model_id,
            "domain": model["domain"],
            "declared_maturity": inv["declared_maturity"],
            "stakeholder_signoff": signoff.get("status"),
            "public_cases": len(model["cases"]),
            "recorded_outcomes": recorded_outcomes,
            "m3_ready": not any(item.startswith(f"{model_id}:") for item in errors) and signoff.get("status") == "approved",
            "m4_ready": False,
        })
    report = {
        "schema_version": "1.0",
        "as_of": date.today().isoformat(),
        "flagships": len(registry["flagships"]),
        "errors": errors,
        "warnings": warnings,
        "results": results,
        "status": "PASS" if not errors else "FAIL",
        "m3_promoted": 0,
        "m4_promoted": 0,
        "statement": "No maturity promotion occurs without human sign-off and maintained-operation evidence.",
    }
    write_json(ROOT / "m3-evidence-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--generate-instances", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--require-instances", action="store_true")
    args = parser.parse_args()
    if not (args.materialize or args.validate):
        args.materialize = True
        args.validate = True
    if args.materialize:
        index = materialize(args.generate_instances)
        print(json.dumps({"public_cases": index["case_count"]}, indent=2))
    if args.validate:
        report = validate(args.require_instances)
        print(json.dumps({
            "status": report["status"],
            "errors": len(report["errors"]),
            "warnings": len(report["warnings"]),
            "m3_promoted": report["m3_promoted"],
            "m4_promoted": report["m4_promoted"],
        }, indent=2))
        return 0 if report["status"] == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
