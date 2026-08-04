"""Create the governance evidence pack for a model domain.

Usage:
    python tools/scaffold_model_evidence.py 03_Private_Equity
    python tools/scaffold_model_evidence.py 20_Project_Finance --force

The command never modifies workbook files. Existing evidence files are preserved
unless --force is explicitly supplied.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "standards" / "templates"


def copy_template(source_name: str, destination: Path, force: bool) -> str:
    source = TEMPLATES / source_name
    if not source.is_file():
        raise FileNotFoundError(f"missing evidence template: {source}")
    if destination.exists() and not force:
        return f"SKIP {destination.relative_to(ROOT)} (already exists)"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return f"WRITE {destination.relative_to(ROOT)}"


def ensure_text(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"SKIP {path.relative_to(ROOT)} (already exists)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"WRITE {path.relative_to(ROOT)}"


def scaffold(domain: Path, force: bool = False) -> list[str]:
    if not domain.is_absolute():
        domain = ROOT / domain
    domain = domain.resolve()
    try:
        domain.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("domain must be inside the repository") from exc
    if not domain.is_dir():
        raise FileNotFoundError(f"domain folder does not exist: {domain}")

    actions = [
        copy_template("model_card.md", domain / "model_card.md", force),
        copy_template("validation.md", domain / "validation.md", force),
        copy_template(
            "source_register.csv",
            domain / "sources" / "source_register.csv",
            force,
        ),
        ensure_text(
            domain / "releases" / "CHANGELOG.md",
            "# Model Release Changelog\n\n## Unreleased\n\n- Initial evidence pack created.\n",
            force,
        ),
        ensure_text(domain / "sources" / "snapshots" / ".gitkeep", "", force),
        ensure_text(domain / "instances" / ".gitkeep", "", force),
    ]
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", type=Path, help="Domain folder relative to repository root")
    parser.add_argument("--force", action="store_true", help="Overwrite existing evidence files")
    args = parser.parse_args()

    try:
        actions = scaffold(args.domain, args.force)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    for action in actions:
        print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
