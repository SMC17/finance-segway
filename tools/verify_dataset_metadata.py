"""Check the dataset catalogue against the repository it claims to describe.

Standards in scope: ISO 15836 (Dublin Core), W3C DCAT, schema.org, JSON-LD,
FAIR, and ISO/IEC 11179 (data element definitions).

The catalogue at standards/metadata/catalog.jsonld is generated, not written.
This tool exists so that being generated actually means something: it
re-derives every computed field from the filesystem and fails where the
catalogue and the repository disagree. Without it, "generated" degrades to
"generated once, a while ago".

Four families of check:

  Freshness   - declared paths exist; record counts, byte sizes, and SHA-256
                digests match what the filesystem holds right now.
  Dublin Core - every dataset carries the elements a consumer needs to cite and
                reuse it: identifier, title, description, publisher, licence,
                modification date, rights.
  DCAT        - the catalogue links to its datasets, each dataset carries at
                least one distribution, and each distribution declares a media
                type and an access URL.
  ISO/IEC 11179 + FAIR
              - every dataset defines its key data elements with a name, a
                definition, and a datatype, and states concretely what each FAIR
                letter means for it rather than asserting the acronym.

Usage:
    python tools/verify_dataset_metadata.py
    python tools/verify_dataset_metadata.py --report metadata.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "standards" / "metadata" / "catalog.jsonld"

DUBLIN_CORE_REQUIRED = (
    "dcterms:identifier",
    "dcterms:title",
    "dcterms:description",
    "dcterms:publisher",
    "dcterms:license",
    "dcterms:modified",
    "dcterms:rights",
)
FAIR_LETTERS = ("findable", "accessible", "interoperable", "reusable")
ELEMENT_REQUIRED = ("name", "definition", "datatype")


def load() -> dict[str, Any]:
    if not CATALOG.exists():
        raise FileNotFoundError(
            f"missing {CATALOG.relative_to(ROOT)} -- run "
            "tools/build_dataset_metadata.py"
        )
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def recount(path: Path, unit: str) -> int | None:
    """Re-derive a dataset's record count the same way the generator does."""
    if path.is_dir():
        return len(list(path.glob("*.json")))
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in ("cases", "models", "concepts", "companies"):
        if key in payload and isinstance(payload[key], list):
            return len(payload[key])
    return None


def run() -> dict[str, Any]:
    catalog = load()
    graph = catalog["@graph"]
    failures: list[str] = []
    warnings: list[str] = []

    catalogs = [n for n in graph if "dcat:Catalog" in n.get("@type", [])]
    datasets = [n for n in graph if "dcat:Dataset" in n.get("@type", [])]

    if len(catalogs) != 1:
        failures.append(f"expected exactly one dcat:Catalog node, found {len(catalogs)}")
    if not datasets:
        failures.append("catalogue declares no datasets")

    if catalogs:
        declared = set(catalogs[0].get("dcat:dataset", []))
        actual = {n["@id"] for n in datasets}
        for missing in sorted(actual - declared):
            failures.append(f"dataset {missing} is not linked from the catalogue node")
        for dangling in sorted(declared - actual):
            failures.append(f"catalogue links {dangling}, which is not in the graph")

    if "@context" not in catalog:
        failures.append("no JSON-LD @context: the document is not interpretable as linked data")
    else:
        for prefix in ("dcat", "dcterms", "schema"):
            if prefix not in catalog["@context"]:
                failures.append(f"@context does not bind the {prefix!r} prefix")

    for node in datasets:
        name = node.get("dcterms:identifier", node.get("@id", "<unnamed>"))

        for element in DUBLIN_CORE_REQUIRED:
            if not node.get(element):
                failures.append(f"{name}: missing Dublin Core element {element}")

        # --- freshness ---------------------------------------------------
        relative = node.get("repo:path")
        if not relative:
            failures.append(f"{name}: no repo:path, so nothing can be verified")
            continue
        path = ROOT / relative
        if not path.exists():
            failures.append(f"{name}: declared path {relative} does not exist")
            continue

        declared_count = node.get("repo:recordCount")
        actual_count = recount(path, node.get("repo:recordUnit", ""))
        if actual_count is not None and declared_count != actual_count:
            failures.append(
                f"{name}: catalogue says {declared_count} "
                f"{node.get('repo:recordUnit', 'record')}s, repository holds "
                f"{actual_count} -- the catalogue is stale"
            )

        distributions = node.get("dcat:distribution") or []
        if not distributions:
            failures.append(f"{name}: no dcat:distribution")
        for distribution in distributions:
            if not distribution.get("dcat:mediaType"):
                failures.append(f"{name}: distribution declares no media type")
            if not distribution.get("dcat:accessURL"):
                failures.append(f"{name}: distribution declares no access URL")
            extent = (distribution.get("dcterms:extent") or {}).get("rdf:value")
            actual_size = (
                sum(f.stat().st_size for f in path.glob("*.json"))
                if path.is_dir()
                else path.stat().st_size
            )
            if extent is not None and extent != actual_size:
                failures.append(
                    f"{name}: catalogue says {extent} bytes, repository holds "
                    f"{actual_size} -- the catalogue is stale"
                )
            checksum = distribution.get("spdx:checksum")
            if checksum and not path.is_dir():
                actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if checksum.get("spdx:checksumValue") != actual_digest:
                    failures.append(
                        f"{name}: recorded SHA-256 does not match the file on disk"
                    )
            if checksum and path.is_dir():
                failures.append(
                    f"{name}: a digest is recorded for a directory, which cannot be "
                    "stable as its contents change"
                )

        # --- ISO/IEC 11179 ------------------------------------------------
        elements = node.get("repo:dataElements") or []
        if not elements:
            failures.append(
                f"{name}: defines no data elements, so a consumer cannot know what its "
                "fields mean (ISO/IEC 11179)"
            )
        for element in elements:
            for field in ELEMENT_REQUIRED:
                if not element.get(field):
                    failures.append(
                        f"{name}: data element {element.get('name', '<unnamed>')!r} "
                        f"has no {field}"
                    )
            source = element.get("permitted_values_source")
            if source:
                target = ROOT / source.split("#", 1)[0]
                if not target.exists():
                    failures.append(
                        f"{name}: data element {element.get('name')!r} cites permitted "
                        f"values in {source}, which does not exist"
                    )

        # --- FAIR ----------------------------------------------------------
        fair = node.get("repo:fair") or {}
        for letter in FAIR_LETTERS:
            if not str(fair.get(letter, "")).strip():
                failures.append(
                    f"{name}: FAIR '{letter}' is unstated. Asserting FAIR without "
                    "saying what it means for this dataset is the failure mode the "
                    "principles were written against"
                )

    return {
        "status": "PASS" if not failures else "FAIL",
        "datasets": len(datasets),
        "failures": failures,
        "warnings": warnings,
        "failure_count": len(failures),
        "warning_count": len(warnings),
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
