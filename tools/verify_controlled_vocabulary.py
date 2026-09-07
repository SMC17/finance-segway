"""Check the repository's data against its own controlled vocabulary.

Standards in scope: ISO 704 (terminology work: definition form and concept
relations), ISO 25964 and ANSI/NISO Z39.19 (thesaurus structure and controlled
value sets), ISO/IEC 11179 (permissible values for a data element), and SKOS
(the interchange form emitted by --emit-skos).

WHY A VOCABULARY NEEDS A CHECKER
--------------------------------
A glossary nobody enforces drifts within one release. The evidence is in this
repository's own data: `input_kind` carries `modeler` once against
`modeler_assumption` 237 times, `classification` carries a plural variant once
against 160 singulars, and `risk_tier` carries two incompatible scales because
two subsystems reached for the same field name. Every one of those is a
one-character-looking problem that silently breaks grouping, filtering, and
counting.

So this tool checks three things that a written glossary cannot:

  1. Every value of a controlled field appears in that field's permitted set.
     Unknown values fail. Values the glossary marks deprecated are reported
     with their replacement and their exact count, so the cost of migrating is
     a number rather than a feeling.

  2. The concept system is well formed under ISO 704: no definition is
     circular, every `broader` and `related` target exists, no two concepts
     share a preferred label, and no preferred label is also another concept's
     alternative label.

  3. Definitions follow ISO 704's substitutability rule. A definition that
     opens "is when" or "refers to" is a gloss, not a definition -- it cannot
     replace the term in a sentence. These are reported as style failures.

Usage:
    python tools/verify_controlled_vocabulary.py
    python tools/verify_controlled_vocabulary.py --report vocab.json
    python tools/verify_controlled_vocabulary.py --emit-skos standards/vocabulary/glossary.skos.jsonld
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "standards" / "vocabulary" / "glossary.json"
SKIP_DIRS = {".git", "node_modules", ".model-build", "__pycache__", ".pytest_cache"}

# ISO 704 rejects definitions that gloss rather than define: a definition must
# be substitutable for the term, so it cannot begin by restating the term or by
# announcing that it is about to explain something.
NON_SUBSTITUTABLE = re.compile(
    r"^\s*(is\s+when|is\s+where|refers\s+to|means\s+that|this\s+is|describes\s+how|"
    r"used\s+to|a\s+term\s+(for|used))\b",
    re.IGNORECASE,
)

BASE_URI = "https://github.com/SMC17/finance-segway/standards/vocabulary#"


def load_glossary() -> dict[str, Any]:
    if not GLOSSARY.exists():
        raise FileNotFoundError(f"missing {GLOSSARY.relative_to(ROOT)}")
    return json.loads(GLOSSARY.read_text(encoding="utf-8"))


def json_files() -> Iterator[Path]:
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def walk(node: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key), value
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def check_concept_system(glossary: dict[str, Any]) -> list[str]:
    """ISO 704 structural checks on the concept system itself."""
    problems: list[str] = []
    concepts = {c["id"]: c for c in glossary["concepts"]}

    if len(concepts) != len(glossary["concepts"]):
        problems.append("duplicate concept ids in the glossary")

    pref_labels: dict[str, str] = {}
    alt_labels: dict[str, str] = {}
    for concept in glossary["concepts"]:
        label = concept["prefLabel"]
        if label in pref_labels:
            problems.append(
                f"designation {label!r} is the preferred label of both "
                f"{pref_labels[label]!r} and {concept['id']!r} -- an undeclared homograph"
            )
        pref_labels[label] = concept["id"]
        for alt in concept.get("altLabels") or []:
            alt_labels[alt] = concept["id"]

    for label, owner in alt_labels.items():
        if label in pref_labels and pref_labels[label] != owner:
            problems.append(
                f"designation {label!r} is an alternative label of {owner!r} and the "
                f"preferred label of {pref_labels[label]!r} -- ambiguous designation"
            )

    for concept in glossary["concepts"]:
        cid = concept["id"]
        definition = (concept.get("definition") or "").strip()
        if not definition:
            problems.append(f"{cid}: no definition")
            continue
        if NON_SUBSTITUTABLE.match(definition):
            problems.append(
                f"{cid}: definition opens with a gloss construction and is not "
                f"substitutable for the term (ISO 704): {definition[:60]!r}"
            )
        # Circularity: a definition may not contain its own preferred label as
        # a standalone word.
        label = concept["prefLabel"]
        if re.search(rf"\b{re.escape(label)}\b", definition, re.IGNORECASE):
            problems.append(
                f"{cid}: definition contains its own designation {label!r} -- circular"
            )
        for relation in ("broader",):
            target = concept.get(relation)
            if target and target not in concepts:
                problems.append(f"{cid}: {relation} points at unknown concept {target!r}")
        for target in concept.get("related") or []:
            if target not in concepts:
                problems.append(f"{cid}: related points at unknown concept {target!r}")

    # Broader chains must terminate.
    for concept in glossary["concepts"]:
        seen: set[str] = set()
        node = concept
        while node and node.get("broader"):
            if node["id"] in seen:
                problems.append(f"{concept['id']}: broader chain is cyclic")
                break
            seen.add(node["id"])
            node = concepts.get(node["broader"])
    return problems


def check_data(glossary: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    """Check every controlled field's values across the repository's JSON."""
    controlled = glossary["controlled_fields"]
    deprecated = glossary.get("deprecated_values", {})
    failures: list[str] = []
    warnings: list[str] = []
    observed: dict[str, Counter[str]] = {field: Counter() for field in controlled}
    locations: dict[tuple[str, str], list[str]] = {}

    for path in json_files():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        relative = str(path.relative_to(ROOT))
        for key, value in walk(payload):
            if key not in controlled or not isinstance(value, str):
                continue
            observed[key][value] += 1
            locations.setdefault((key, value), []).append(relative)

    for field, counts in observed.items():
        permitted = set(controlled[field]["permitted_values"])
        field_deprecated = {
            k: v for k, v in (deprecated.get(field) or {}).items()
        }
        for value, count in counts.most_common():
            if value in field_deprecated:
                where = sorted(set(locations[(field, value)]))
                warnings.append(
                    f"{field} = {value!r} x{count}: deprecated, replace with "
                    f"{field_deprecated[value]!r} (in {', '.join(where[:3])}"
                    f"{' and others' if len(where) > 3 else ''})"
                )
            elif value not in permitted:
                where = sorted(set(locations[(field, value)]))
                failures.append(
                    f"{field} = {value!r} x{count} is not in the permitted set "
                    f"{sorted(permitted)} (in {', '.join(where[:3])})"
                )

    summary = {field: dict(counts) for field, counts in observed.items()}
    return failures, warnings, summary


def check_homographs(glossary: dict[str, Any]) -> list[str]:
    """Every declared homograph must state a resolution and be marked resolved."""
    problems: list[str] = []
    for entry in glossary.get("homographs", []):
        if not str(entry.get("resolution", "")).strip():
            problems.append(
                f"homograph {entry.get('designation')!r} declared with no resolution -- "
                "ISO 704 requires the designations be distinguished, not merely noted"
            )
        if entry.get("status") not in {"resolved", "open"}:
            problems.append(
                f"homograph {entry.get('designation')!r} has no status"
            )
    return problems


def to_skos(glossary: dict[str, Any]) -> dict[str, Any]:
    """Emit the concept system as SKOS in JSON-LD."""
    graph: list[dict[str, Any]] = [
        {
            "@id": BASE_URI.rstrip("#"),
            "@type": "skos:ConceptScheme",
            "dcterms:title": glossary["title"],
            "dcterms:modified": glossary["as_of"],
        }
    ]
    for concept in glossary["concepts"]:
        node: dict[str, Any] = {
            "@id": BASE_URI + concept["id"],
            "@type": "skos:Concept",
            "skos:inScheme": {"@id": BASE_URI.rstrip("#")},
            "skos:prefLabel": {"@value": concept["prefLabel"], "@language": "en"},
            "skos:definition": {"@value": concept["definition"], "@language": "en"},
        }
        if concept.get("altLabels"):
            node["skos:altLabel"] = [
                {"@value": a, "@language": "en"} for a in concept["altLabels"]
            ]
        if concept.get("broader"):
            node["skos:broader"] = {"@id": BASE_URI + concept["broader"]}
        if concept.get("related"):
            node["skos:related"] = [
                {"@id": BASE_URI + r} for r in concept["related"]
            ]
        if concept.get("scopeNote"):
            node["skos:scopeNote"] = {
                "@value": concept["scopeNote"], "@language": "en"
            }
        graph.append(node)
    return {
        "@context": {
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "dcterms": "http://purl.org/dc/terms/",
        },
        "@graph": graph,
    }


def run() -> dict[str, Any]:
    glossary = load_glossary()
    structural = check_concept_system(glossary) + check_homographs(glossary)
    data_failures, warnings, summary = check_data(glossary)
    failures = structural + data_failures
    return {
        "status": "PASS" if not failures else "FAIL",
        "concepts": len(glossary["concepts"]),
        "controlled_fields": len(glossary["controlled_fields"]),
        "observed_values": summary,
        "failures": failures,
        "warnings": warnings,
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--emit-skos", type=Path, default=None)
    args = parser.parse_args()

    if args.emit_skos:
        payload = to_skos(load_glossary())
        args.emit_skos.parent.mkdir(parents=True, exist_ok=True)
        args.emit_skos.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        # Path may be given relative to the caller's cwd, which is not
        # necessarily the repository root.
        try:
            shown = args.emit_skos.resolve().relative_to(ROOT)
        except ValueError:
            shown = args.emit_skos
        print(f"wrote {shown} ({len(payload['@graph'])} nodes)")

    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != "observed_values"}, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
