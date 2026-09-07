"""Refuse any standards-conformance claim that no passing check supports.

This is the meta-check. The register at standards/conformance/register.json says
what this project claims about roughly sixty external standards; this tool's job
is to make those claims cost something.

THE PROBLEM IT SOLVES
---------------------
Conformance registers rot in one direction. Nobody ever downgrades a row. A
status set to "conformant" when a check existed stays "conformant" after the
check is deleted, renamed, or quietly starts failing, and the register becomes a
list of things that used to be true. Since the whole point of this repository is
that claims must be checkable, a register nobody checks would be the most
embarrassing artefact in it.

So the rules are mechanical and they fail closed:

  1. Every standard the project has been asked to address must appear. A
     standard cannot be made to go away by deleting its row.
  2. "conformant" and "partial" require evidence.check to name a file that
     exists, and (with --run-checks) that file must exit zero.
  3. "conformant" and "partial" additionally require a requirement_basis of
     verified_by_check or well_established. A standard we only know the scope of
     cannot be one we claim to conform to -- that is the honest constraint, and
     it is why several rows here sit at not_yet despite real work behind them.
  4. "partial" requires at least one stated gap. A partial with no gaps is a
     conformant that lost its nerve, or a conformant that is overclaiming.
  5. "not_applicable" requires a reason, and "not_yet" requires a plan.
  6. Any row whose requirement_basis is "unverified" is surfaced in the report
     regardless of status, because those are the rows a human still has to
     resolve.

It also checks the two machine-readable entry points, llms.txt and AGENTS.md,
since the register claims conformance for them and something has to verify it.

Usage:
    python tools/verify_standards_conformance.py
    python tools/verify_standards_conformance.py --run-checks
    python tools/verify_standards_conformance.py --report conformance.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "standards" / "conformance" / "register.json"
LLMS_TXT = ROOT / "llms.txt"
AGENTS_MD = ROOT / "AGENTS.md"

VALID_STATUS = {"conformant", "partial", "not_applicable", "not_yet"}
VALID_BASIS = {"verified_by_check", "well_established", "summary_only", "unverified"}
CLAIMING = {"conformant", "partial"}
BASIS_PERMITTING_CLAIM = {"verified_by_check", "well_established"}

# The standards this project has been asked to address. A row may change status,
# but it may not disappear: the register must stay a complete answer to the
# question that was asked.
REQUIRED_STANDARD_IDS = {
    "iso-24495-1", "iso-24495-2", "iso-24495-3", "iso-24495-4", "asd-ste100",
    "easy-to-read", "iso-704", "iso-25964", "ansi-niso-z39-19", "wcag-2-2",
    "iso-iec-40500", "en-301-549", "iso-9241-210", "dita", "s1000d", "iirds",
    "docbook", "information-mapping", "doclang", "iso-15836-dublin-core", "dcat",
    "schema-org", "json-ld", "iso-iec-11179", "iso-19115", "fair", "iso-iec-8183",
    "llms-txt", "agents-md", "iso-8000", "iso-iec-25012", "iso-iec-25024",
    "iso-iec-5259", "skos", "rdf", "owl", "iso-24613-lmf", "iso-24611-maf",
    "iso-iec-22989", "iso-30401", "iso-15489", "iso-10013", "iso-9001",
    "iso-iec-42001", "iso-iec-23894", "iso-iec-23053", "iso-iec-5338",
    "iso-iec-25059", "iso-iec-12792", "iso-iec-42005", "iso-iec-38507",
    "clear-framework", "nist-ai-rmf", "model-cards", "datasheets-for-datasets",
    "factsheets", "iso-8601", "iso-3166", "iso-4217", "si-units", "ucum",
    "openapi", "json-schema", "iso-24896",
}

REPO_LINK = re.compile(r"\]\(([^)#][^)]*)\)")


def load_register() -> dict[str, Any]:
    if not REGISTER.exists():
        raise FileNotFoundError(f"missing {REGISTER.relative_to(ROOT)}")
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def check_entry_points() -> list[str]:
    """llms.txt and AGENTS.md: the register claims these, so verify them."""
    problems: list[str] = []

    if not LLMS_TXT.exists():
        problems.append("llms.txt is absent from the repository root")
    else:
        text = LLMS_TXT.read_text(encoding="utf-8")
        if not re.match(r"^#\s+\S", text):
            problems.append("llms.txt does not open with an H1 title")
        if "\n>" not in text:
            problems.append("llms.txt has no blockquote summary")
        for target in REPO_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (ROOT / target).exists():
                problems.append(f"llms.txt links {target}, which does not exist")

    if not AGENTS_MD.exists():
        problems.append("AGENTS.md is absent from the repository root")
    else:
        text = AGENTS_MD.read_text(encoding="utf-8")
        required_ideas = {
            "the data-fabrication prohibition": r"never (write|fabricate).{0,40}(number|data)",
            "the verification commands": r"python -m unittest",
            "the gates no agent may pass": r"sign-?off",
        }
        for label, pattern in required_ideas.items():
            if not re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                problems.append(f"AGENTS.md does not state {label}")
        for target in REPO_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (ROOT / target).exists():
                problems.append(f"AGENTS.md links {target}, which does not exist")

    return problems


def run_check(relative: str) -> tuple[bool, str]:
    path = ROOT / relative
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if result.returncode == 0:
        return True, "exit 0"
    tail = (result.stdout or result.stderr).strip().splitlines()
    return False, f"exit {result.returncode}: {tail[-1] if tail else 'no output'}"


def run(execute_checks: bool = False) -> dict[str, Any]:
    register = load_register()
    rows = register["standards"]
    failures: list[str] = []
    warnings: list[str] = []

    seen = [row["id"] for row in rows]
    duplicates = [item for item, count in Counter(seen).items() if count > 1]
    for duplicate in duplicates:
        failures.append(f"standard {duplicate!r} appears more than once")

    missing = sorted(REQUIRED_STANDARD_IDS - set(seen))
    for item in missing:
        failures.append(
            f"standard {item!r} was asked for but has no row -- a standard cannot be "
            "removed from the register, only re-assessed"
        )
    extra = sorted(set(seen) - REQUIRED_STANDARD_IDS)
    for item in extra:
        warnings.append(f"register carries {item!r}, which is not in the required set")

    checks_to_run: dict[str, list[str]] = {}

    for row in rows:
        name = row["id"]
        status = row.get("status")
        basis = row.get("requirement_basis")

        if status not in VALID_STATUS:
            failures.append(f"{name}: status {status!r} is not one of {sorted(VALID_STATUS)}")
            continue
        if basis not in VALID_BASIS:
            failures.append(f"{name}: requirement_basis {basis!r} is not recognised")
            continue

        evidence = row.get("evidence") or {}
        check = evidence.get("check")

        if status in CLAIMING:
            if basis not in BASIS_PERMITTING_CLAIM:
                failures.append(
                    f"{name}: claims {status!r} on a {basis!r} basis. A standard whose "
                    "requirements we have not confirmed cannot be one we claim to meet"
                )
            if not check:
                failures.append(
                    f"{name}: claims {status!r} but names no check. Conformance without "
                    "evidence is the thing this register exists to prevent"
                )
            elif not (ROOT / check).exists():
                failures.append(
                    f"{name}: names check {check!r}, which does not exist"
                )
            else:
                checks_to_run.setdefault(check, []).append(name)
            if not str(evidence.get("asserts", "")).strip():
                failures.append(
                    f"{name}: names a check but does not say what it asserts, so a "
                    "reader cannot tell what was actually proved"
                )

        if status == "partial" and not (row.get("gaps") or []):
            failures.append(
                f"{name}: is 'partial' with no gaps listed. Either the gaps are "
                "unstated or the status should be 'conformant'"
            )
        if status == "conformant" and (row.get("gaps") or []):
            failures.append(
                f"{name}: is 'conformant' but lists gaps. A standard with known gaps "
                "is 'partial'"
            )
        if status == "not_applicable" and not str(row.get("reason", "")).strip():
            failures.append(f"{name}: is 'not_applicable' with no reason")
        if status == "not_yet" and not str(row.get("plan", "")).strip():
            failures.append(f"{name}: is 'not_yet' with no plan")

        if basis == "unverified":
            warnings.append(
                f"{name}: requirement_basis is 'unverified' -- a human must confirm what "
                "this standard requires before any claim is made about it"
            )

    failures.extend(check_entry_points())

    executed: dict[str, str] = {}
    if execute_checks:
        self_path = str(Path(__file__).resolve().relative_to(ROOT))
        for check, claimants in sorted(checks_to_run.items()):
            if check == self_path:
                # This tool backs the llms.txt and AGENTS.md rows itself. Running
                # it from inside its own run would recurse without adding
                # evidence -- those entry-point checks have already executed
                # above.
                executed[check] = "checked inline; not re-executed"
                continue
            passed, detail = run_check(check)
            executed[check] = detail
            if not passed:
                failures.append(
                    f"check {check} FAILED ({detail}), so the claims it backs are not "
                    f"supported: {sorted(claimants)}"
                )

    tally = Counter(row["status"] for row in rows)
    return {
        "status": "PASS" if not failures else "FAIL",
        "standards_registered": len(rows),
        "by_status": dict(tally),
        "by_basis": dict(Counter(row["requirement_basis"] for row in rows)),
        "checks_backing_claims": sorted(checks_to_run),
        "checks_executed": executed,
        "failures": failures,
        "warnings": warnings,
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument(
        "--run-checks",
        action="store_true",
        help="execute every check the register cites and require it to pass",
    )
    args = parser.parse_args()
    report = run(execute_checks=args.run_checks)
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
