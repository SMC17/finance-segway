"""Regenerate every workbook builder and enforce semantic parity.

Builders can serve more than one economic domain. Each unique builder runs once,
then its output is copied and enriched with the model-specific institutional
surface before comparison with that model's committed artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from tools.institutional_surface import (
        apply_surface,
        profiles_by_id,
        validate_profiles,
        validate_workbook_surface,
    )
    from tools.workbook_engineering import audit_workbook
    from tools.workbook_parity import compare_workbooks
except ModuleNotFoundError:
    from institutional_surface import (
        apply_surface,
        profiles_by_id,
        validate_profiles,
        validate_workbook_surface,
    )
    from workbook_engineering import audit_workbook
    from workbook_parity import compare_workbooks


def load_inventory(root: Path) -> dict[str, Any]:
    return json.loads((root / "standards/model_inventory.json").read_text(encoding="utf-8"))


def run_builder(root: Path, builder_rel: str, output_name: str, workdir: Path) -> Path:
    builder = root / builder_rel
    if not builder.exists():
        raise FileNotFoundError(builder)
    env = os.environ.copy()
    pythonpath = [str(root), str(root / "tools"), str(root / "tools/builders")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    requested = workdir / output_name
    modern = subprocess.run(
        [sys.executable, str(builder), "--output", str(requested)],
        cwd=workdir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if modern.returncode == 0 and requested.exists():
        return requested
    for artifact in workdir.glob("*.xlsx"):
        artifact.unlink()
    legacy = subprocess.run(
        [sys.executable, str(builder)],
        cwd=workdir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    artifacts = sorted(workdir.glob("*.xlsx"))
    if legacy.returncode != 0 or len(artifacts) != 1:
        output = "\n--- modern attempt ---\n" + modern.stdout + "\n--- legacy attempt ---\n" + legacy.stdout
        raise RuntimeError(f"builder {builder_rel} failed or produced {len(artifacts)} artifacts:{output}")
    return artifacts[0]


def build_and_compare(root: Path, build_root: Path) -> dict[str, Any]:
    inventory = load_inventory(root)
    models = inventory["models"]
    profiles = profiles_by_id(root)
    errors: list[dict[str, Any]] = [
        {"error": error} for error in validate_profiles(root)
    ]
    by_builder: dict[str, list[dict[str, Any]]] = {}
    for model in models:
        by_builder.setdefault(model["builder"], []).append(model)
    results = []
    for builder_rel, builder_models in sorted(by_builder.items()):
        with tempfile.TemporaryDirectory(prefix="finance-segway-builder-") as temp_name:
            temp = Path(temp_name)
            output_name = Path(builder_models[0]["workbook"]).name
            try:
                base_artifact = run_builder(root, builder_rel, output_name, temp)
            except Exception as exc:
                errors.append({"builder": builder_rel, "error": str(exc)})
                continue
            for model in builder_models:
                model_artifact = build_root / f"{model['id']}__{builder_rel.replace('/', '__').replace('.py', '.xlsx')}"
                model_artifact.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(base_artifact, model_artifact)
                try:
                    apply_surface(model_artifact, model, profiles[model["id"]])
                    surface_errors = validate_workbook_surface(
                        model_artifact, model, profiles[model["id"]]
                    )
                    if surface_errors:
                        errors.append({
                            "model": model["id"],
                            "error": "generated institutional surface failed validation",
                            "findings": surface_errors,
                        })
                except Exception as exc:
                    errors.append({
                        "model": model["id"],
                        "builder": builder_rel,
                        "error": f"institutional surface failed: {exc}",
                    })
                    continue
                generated_summary, generated_findings = audit_workbook(model_artifact)
                generated_errors = [
                    item.__dict__ for item in generated_findings if item.severity == "error"
                ]
                if generated_errors:
                    errors.append({
                        "model": model["id"],
                        "builder": builder_rel,
                        "error": "generated workbook failed audit",
                        "findings": generated_errors,
                    })
                committed = root / model["workbook"]
                if not committed.exists():
                    errors.append({
                        "model": model["id"],
                        "error": f"missing committed workbook {committed}",
                    })
                    continue
                parity = compare_workbooks(model_artifact, committed)
                results.append({
                    "model_id": model["id"],
                    "domain": model["domain"],
                    "builder": builder_rel,
                    "generated": str(model_artifact),
                    "committed": model["workbook"],
                    "generated_formulas": generated_summary["formulas"],
                    "institutional_surface": True,
                    **parity,
                })
    return {
        "models": len(models),
        "unique_builders": len(by_builder),
        "institutional_profiles": len(profiles),
        "parity_passed": sum(1 for item in results if item["semantic_parity"]),
        "parity_failed": sum(1 for item in results if not item["semantic_parity"]),
        "presentation_parity_passed": sum(1 for item in results if item["presentation_parity"]),
        "presentation_parity_failed": sum(1 for item in results if not item["presentation_parity"]),
        "builder_errors": errors,
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--build-dir", type=Path, default=Path(".model-build"))
    parser.add_argument("--report", type=Path, default=Path("builder-parity-report.json"))
    parser.add_argument("--require-parity", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    build_root = (root / args.build_dir).resolve() if not args.build_dir.is_absolute() else args.build_dir
    build_root.mkdir(parents=True, exist_ok=True)
    report = build_and_compare(root, build_root)
    report_path = args.report if args.report.is_absolute() else root / args.report
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "models", "unique_builders", "institutional_profiles", "parity_passed",
        "parity_failed", "presentation_parity_passed", "presentation_parity_failed",
    )}, indent=2))
    if report["builder_errors"]:
        return 1
    if args.require_parity and report["parity_failed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
