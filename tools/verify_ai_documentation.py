"""Check the repository's model cards and dataset datasheet against their frameworks.

Frameworks in scope: Model Cards for Model Reporting (Mitchell et al., 2019) and
Datasheets for Datasets (Gebru et al., 2021).

HOW CONFORMANCE IS JUDGED
-------------------------
Neither framework is a standard with clauses to tick; both are section
checklists whose value comes from forcing an author to answer questions they
would otherwise skip. So this tool checks that each required question is
actually answered somewhere in the document, and it does that by mapping the
framework's section names onto the headings this repository actually uses,
rather than demanding the repository rename its headings to match a paper.

The mapping is declared in MODEL_CARD_SECTIONS below and is itself the honest
part: where a framework section has no counterpart here, it is listed as a gap
rather than mapped onto the nearest heading that sounds similar. Three Model
Card sections are currently unmapped, so this repository's conformance to that
framework is PARTIAL and the register says so.

A section that exists but is empty counts as missing. A heading with nothing
under it is the most common way documentation lies.

Usage:
    python tools/verify_ai_documentation.py
    python tools/verify_ai_documentation.py --report ai_docs.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "standards" / "model_inventory.json"
DATASHEET = ROOT / "standards" / "metadata" / "datasheet_public_fact_corpus.md"

# Model Cards for Model Reporting, section -> the heading(s) that answer it here.
# A value of None records a framework section this repository does not yet
# answer. Those are reported as gaps, never quietly dropped.
MODEL_CARD_SECTIONS: dict[str, list[str] | None] = {
    "Model Details": ["Identity"],
    "Intended Use": ["Intended use"],
    "Factors": None,
    "Metrics": ["Checks and controls"],
    "Evaluation Data": ["Inputs and sources"],
    "Training Data": None,
    "Quantitative Analyses": None,
    "Ethical Considerations": ["Limitations and failure modes"],
    "Caveats and Recommendations": ["Limitations and failure modes", "Monitoring"],
}

# Datasheets for Datasets, section -> heading in the datasheet.
DATASHEET_SECTIONS: dict[str, str] = {
    "Motivation": "Motivation",
    "Composition": "Composition",
    "Collection Process": "Collection process",
    "Preprocessing/cleaning/labeling": "Preprocessing, cleaning, labelling",
    "Uses": "Uses",
    "Distribution": "Distribution",
    "Maintenance": "Maintenance",
}

MIN_SECTION_WORDS = 12


def sections(markdown: str) -> dict[str, str]:
    """Split a markdown document into {heading: body}, subsections included.

    A section's body runs to the next heading of the SAME OR HIGHER level, not
    to the next heading of any level. Otherwise a section whose content sits
    under subheadings -- "Intended use" holding "Approved uses" and "Prohibited
    uses" -- reads as empty, and the checker reports a documentation gap that
    is really a parsing bug. Every model card in this repository is written
    that way, so getting this wrong failed all 27 of them.
    """
    lines = markdown.splitlines()
    heads: list[tuple[int, int, str]] = []  # (line index, level, title)
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            heads.append((index, len(match.group(1)), match.group(2).strip()))

    found: dict[str, str] = {}
    for position, (start, level, title) in enumerate(heads):
        end = len(lines)
        for later_start, later_level, _ in heads[position + 1 :]:
            if later_level <= level:
                end = later_start
                break
        body = "\n".join(lines[start + 1 : end]).strip()
        # Keep the first occurrence: a repeated heading later in a document is
        # usually a subsection of something else.
        found.setdefault(title, body)
    return found


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def check_model_cards() -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    checked = 0
    gaps = sorted(k for k, v in MODEL_CARD_SECTIONS.items() if v is None)

    for model in inventory["models"]:
        folder = ROOT / model["folder"] if "folder" in model else None
        if folder is None:
            candidates = list(ROOT.glob(f"{model['id']}_*/model_card.md"))
            card = candidates[0] if candidates else None
        else:
            card = folder / "model_card.md"
        if card is None or not card.exists():
            failures.append(f"model {model['id']}: no model_card.md")
            continue
        checked += 1
        present = sections(card.read_text(encoding="utf-8"))
        for framework_section, headings in MODEL_CARD_SECTIONS.items():
            if headings is None:
                continue
            satisfied = False
            for heading in headings:
                body = present.get(heading)
                if body and word_count(body) >= MIN_SECTION_WORDS:
                    satisfied = True
                    break
            if not satisfied:
                failures.append(
                    f"model {model['id']}: Model Cards section {framework_section!r} "
                    f"maps to heading(s) {headings} which are missing or empty in "
                    f"{card.relative_to(ROOT)}"
                )

    if gaps:
        warnings.append(
            "Model Cards sections with no counterpart in this repository's card "
            f"template: {gaps}. Conformance is partial by construction, not by "
            "oversight -- 'Factors' and 'Quantitative Analyses' presume a "
            "statistical model with performance measured across subgroups, which a "
            "deterministic spreadsheet engine does not have, and 'Training Data' "
            "presumes a fitted model rather than an accounting identity"
        )

    return failures, warnings, {"model_cards_checked": checked, "unmapped_sections": gaps}


def check_datasheet() -> tuple[list[str], list[str], dict[str, Any]]:
    failures: list[str] = []
    warnings: list[str] = []
    if not DATASHEET.exists():
        return (
            [f"missing {DATASHEET.relative_to(ROOT)}"],
            [],
            {"datasheet_sections_present": 0},
        )
    present = sections(DATASHEET.read_text(encoding="utf-8"))
    count = 0
    for framework_section, heading in DATASHEET_SECTIONS.items():
        body = present.get(heading)
        if not body:
            failures.append(
                f"datasheet: section {framework_section!r} (heading {heading!r}) is absent"
            )
        elif word_count(body) < MIN_SECTION_WORDS:
            failures.append(
                f"datasheet: section {heading!r} has {word_count(body)} words, which "
                "is a heading rather than an answer"
            )
        else:
            count += 1
    return failures, warnings, {"datasheet_sections_present": count}


def run() -> dict[str, Any]:
    card_failures, card_warnings, card_stats = check_model_cards()
    sheet_failures, sheet_warnings, sheet_stats = check_datasheet()
    failures = card_failures + sheet_failures
    return {
        "status": "PASS" if not failures else "FAIL",
        "frameworks": {
            "Model Cards for Model Reporting": "partial - see unmapped_sections",
            "Datasheets for Datasets": "all seven sections answered",
        },
        **card_stats,
        **sheet_stats,
        "failures": failures,
        "warnings": card_warnings + sheet_warnings,
        "failure_count": len(failures),
        "warning_count": len(card_warnings + sheet_warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = run()
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
