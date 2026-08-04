"""Generate and validate cryptographic release evidence for model artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tools.institutional_surface import (
        profiles_by_id,
        validate_profiles,
        validate_workbook_surface,
    )
    from tools.workbook_engineering import audit_workbook
except ModuleNotFoundError:
    from institutional_surface import profiles_by_id, validate_profiles, validate_workbook_surface
    from workbook_engineering import audit_workbook


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_registry_sha256(root: Path) -> str | None:
    paths = sorted((root / "standards/domain_profiles").glob("*.tsv"))
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def profile_sha256(profile: dict[str, Any]) -> str:
    encoded = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def build_evidence(
    root: Path,
    release_id: str,
    model_ids: list[str],
    require_institutional_surface: bool = False,
) -> dict[str, Any]:
    inventory = json.loads((root / "standards/model_inventory.json").read_text(encoding="utf-8"))
    by_id = {model["id"]: model for model in inventory["models"]}
    missing = sorted(set(model_ids) - set(by_id))
    if missing:
        raise ValueError(f"release references missing inventory models: {missing}")
    profiles = profiles_by_id(root) if (root / "standards/domain_profiles").exists() else {}
    errors = validate_profiles(root) if profiles else []
    if require_institutional_surface and not profiles:
        errors.append("institutional profile registry is missing")
    artifacts = []
    for model_id in model_ids:
        model = by_id[model_id]
        workbook = root / model["workbook"]
        builder = root / model["builder"]
        if not workbook.exists():
            errors.append(f"missing workbook: {workbook}")
            continue
        if not builder.exists():
            errors.append(f"missing builder: {builder}")
            continue
        summary, findings = audit_workbook(workbook)
        artifact_errors = [finding.__dict__ for finding in findings if finding.severity == "error"]
        if artifact_errors:
            errors.append(f"workbook audit failed: {model['workbook']}")
        profile = profiles.get(model_id)
        surface_errors: list[str] = []
        if profile:
            surface_errors = validate_workbook_surface(workbook, model, profile)
            errors.extend(surface_errors)
        elif require_institutional_surface:
            errors.append(f"missing institutional profile: {model_id}")
        artifacts.append({
            "model_id": model_id,
            "domain": model["domain"],
            "maturity": model["declared_maturity"],
            "workbook": model["workbook"],
            "workbook_sha256": sha256(workbook),
            "builder": model["builder"],
            "builder_sha256": sha256(builder),
            "formula_count": summary["formulas"],
            "sheet_count": summary["sheets"],
            "sheet_names": summary["sheet_names"],
            "external_links": summary["external_links"],
            "literal_errors": summary["literal_errors"],
            "audit_findings": summary["findings"],
            "required_engines": model["required_engines"],
            "required_perspectives": model["required_perspectives"],
            "reference_checks": model["reference_checks"],
            "institutional_surface": {
                "required": require_institutional_surface,
                "status": "PASS" if profile and not surface_errors else ("NOT REQUIRED" if not require_institutional_surface else "FAIL"),
                "profile_sha256": profile_sha256(profile) if profile else None,
                "decision_arena": profile.get("decision_arena") if profile else None,
                "committee_artifact": profile.get("committee_artifact") if profile else None,
                "surface_errors": surface_errors,
            },
        })
    evidence = {
        "schema_version": "1.1",
        "release_id": release_id,
        "inventory_version": inventory["version"],
        "profile_registry_sha256": profile_registry_sha256(root),
        "git_commit": git_head(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "models": artifacts,
        "errors": sorted(set(errors)),
        "status": "PASS" if not errors else "FAIL",
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--release-id", default="flagship-2.1.0")
    parser.add_argument("--model-ids", default="03,04,09,14,18,19,20,21,22", help="comma-separated inventory model IDs")
    parser.add_argument("--output", type=Path, default=Path("standards/releases/flagship-2.1.0.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    model_ids = [item.strip() for item in args.model_ids.split(",") if item.strip()]
    evidence = build_evidence(root, args.release_id, model_ids, require_institutional_surface=True)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "release_id": evidence["release_id"],
        "status": evidence["status"],
        "artifacts": len(evidence["models"]),
        "profile_registry_sha256": evidence["profile_registry_sha256"],
        "errors": evidence["errors"],
    }, indent=2))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
