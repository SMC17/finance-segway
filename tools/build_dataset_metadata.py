"""Generate the repository's dataset catalogue as DCAT + Dublin Core JSON-LD.

Standards in scope: ISO 15836 (Dublin Core metadata element set), W3C DCAT
(data catalogue vocabulary), schema.org, JSON-LD, the FAIR principles, and
ISO/IEC 11179 (data element definitions).

WHY THIS IS GENERATED AND NOT WRITTEN
-------------------------------------
A hand-written catalogue describes the repository as it was on the day someone
wrote it. Within a release it is describing a repository that no longer exists:
record counts drift, files move, digests go stale. So every factual field here
is computed from the filesystem at generation time -- path, byte size, record
count, SHA-256 -- and only the editorial fields (title, description, the data
element definitions) are authored.

That split is the point. `tools/verify_dataset_metadata.py` then re-derives the
computed fields and fails if the catalogue disagrees with the repository, which
makes a stale catalogue a build failure rather than a quiet lie.

WHAT FAIR MEANS HERE, CONCRETELY
--------------------------------
FAIR is often cited and rarely operationalised, so each dataset records what it
actually satisfies rather than asserting the acronym:

  Findable     - a persistent identifier, and rich metadata in this catalogue.
  Accessible   - a repository-relative path that resolves, under a stated licence.
  Interoperable- vocabulary terms resolve into the SKOS concept scheme, and units
                 and currencies resolve into the notation registry.
  Reusable     - provenance (where each fact came from) plus an explicit licence
                 plus the usage limits, which for this repository are severe and
                 stated.

Usage:
    python tools/build_dataset_metadata.py
    python tools/build_dataset_metadata.py --output standards/metadata/catalog.jsonld
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "standards" / "metadata" / "catalog.jsonld"

BASE = "https://github.com/SMC17/finance-segway"
VOCAB = f"{BASE}/standards/vocabulary#"
LICENSE_URI = "https://spdx.org/licenses/MIT.html"
PUBLISHER = "SMC17 / finance-segway"

# Irregular plurals, so the summary line reads like English.
PLURALS = {"company": "companies"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count_cases(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8"))["cases"])


def count_models(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8"))["models"])


def count_concepts(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8"))["concepts"])


def count_companies(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8"))["companies"])


def count_dir(pattern: str) -> Callable[[Path], int]:
    def counter(path: Path) -> int:
        return len(list(path.glob(pattern)))

    return counter


# Authored editorial metadata. Everything factual is computed below.
#
# `data_elements` is the ISO/IEC 11179 layer: for each dataset, the fields a
# consumer must understand, each with a name, a definition, and a datatype. A
# dataset whose fields are undefined is not reusable no matter how well it is
# licensed.
DATASETS: list[dict[str, Any]] = [
    {
        "id": "public-cases",
        "path": "standards/public_cases/index.json",
        "title": "Public case index",
        "description": (
            "Every dated, sourced case study in the repository, with its manifest, "
            "frozen source snapshot, snapshot digest, generated instance, and recorded "
            "outcome. Each case applies one domain model to one real subject at one "
            "stated date."
        ),
        "keywords": ["financial modelling", "public filings", "evidence", "provenance"],
        "record_unit": "case",
        "counter": count_cases,
        "theme": "model evidence",
        "data_elements": [
            {"name": "case_id", "definition": "The case's persistent identifier within this repository.", "datatype": "string"},
            {"name": "model_id", "definition": "The two-digit identifier of the domain model the case exercises.", "datatype": "string"},
            {"name": "case_type", "definition": "Whether the case exercises the model on a subject in its normal operating range (conventional) or under stress (adversarial).", "datatype": "string", "permitted_values_source": "standards/vocabulary/glossary.json#controlled_fields/case_type"},
            {"name": "snapshot_sha256", "definition": "SHA-256 digest of the frozen source snapshot the case rests on.", "datatype": "string", "format": "hex-64"},
            {"name": "outcome", "definition": "The recorded metric, forecast value, realised value, and resolution status for the case.", "datatype": "object"},
        ],
    },
    {
        "id": "model-inventory",
        "path": "standards/model_inventory.json",
        "title": "Model inventory",
        "description": (
            "The governed register of domain models: builder, canonical workbook, "
            "required engines and stakeholder perspectives, declared maturity, and the "
            "reference checks each model claims."
        ),
        "keywords": ["model risk", "governance", "inventory"],
        "record_unit": "model",
        "counter": count_models,
        "theme": "model governance",
        "data_elements": [
            {"name": "id", "definition": "The model's two-digit identifier, matching its domain folder prefix.", "datatype": "string"},
            {"name": "declared_maturity", "definition": "The evidence stage the model claims on this repository's ladder.", "datatype": "string", "permitted_values_source": "standards/vocabulary/glossary.json#controlled_fields/declared_maturity"},
            {"name": "builder", "definition": "Repository path of the module that deterministically generates the model's workbook.", "datatype": "string"},
            {"name": "workbook", "definition": "Repository path of the committed canonical workbook.", "datatype": "string"},
            {"name": "reference_checks", "definition": "Named identities the model claims an independent oracle verifies.", "datatype": "array of string"},
        ],
    },
    {
        "id": "forecast-registry",
        "path": "standards/forecasts",
        "title": "Out-of-sample forecast registry",
        "description": (
            "Predictions registered and content-hashed before their outcome was "
            "reportable, each declaring the naive baseline it must beat. Registration "
            "precedes resolution by construction: editing a registered forecast breaks "
            "its hash."
        ),
        "keywords": ["forecasting", "out-of-sample", "skill scoring", "pre-registration"],
        "record_unit": "forecast",
        "counter": count_dir("*.json"),
        "theme": "forward evidence",
        "data_elements": [
            {"name": "forecast_id", "definition": "The forecast's persistent identifier.", "datatype": "string"},
            {"name": "point", "definition": "The predicted value of the metric.", "datatype": "number"},
            {"name": "interval", "definition": "The predicted range, as a two-element low/high pair, or null where none was declared.", "datatype": "array of number or null"},
            {"name": "baseline", "definition": "The unskilled prediction the forecast must beat, frozen at registration with its source.", "datatype": "object"},
            {"name": "resolve_by", "definition": "The date by which the resolving disclosure is expected.", "datatype": "string", "format": "ISO 8601 date"},
            {"name": "registration_sha256", "definition": "Digest pinning the registered payload, so post-hoc edits are detectable.", "datatype": "string", "format": "hex-64"},
        ],
    },
    {
        "id": "vocabulary",
        "path": "standards/vocabulary/glossary.json",
        "title": "Concept system and controlled vocabulary",
        "description": (
            "The repository's terminology: concepts with ISO 704 definitions and SKOS "
            "relations, plus the permitted value set for every enumerated field."
        ),
        "keywords": ["terminology", "SKOS", "controlled vocabulary", "ISO 704"],
        "record_unit": "concept",
        "counter": count_concepts,
        "theme": "terminology",
        "data_elements": [
            {"name": "id", "definition": "The concept's identifier, used as the SKOS URI fragment.", "datatype": "string"},
            {"name": "prefLabel", "definition": "The preferred designation for the concept.", "datatype": "string"},
            {"name": "definition", "definition": "A substitutable noun phrase naming the superordinate concept and the characteristics delimiting this one.", "datatype": "string"},
            {"name": "broader", "definition": "Identifier of the superordinate concept, or null at the top of a hierarchy.", "datatype": "string or null"},
        ],
    },
    {
        "id": "universe-taxonomy",
        "path": "standards/universe/taxonomy.json",
        "title": "Index universe taxonomy",
        "description": (
            "The domain-to-sector-to-company backlog, built only from recorded index "
            "disclosures. A company carries no sector unless a classification source is "
            "cited for it."
        ),
        "keywords": ["index constituents", "sector classification", "SIC"],
        "record_unit": "company",
        "counter": count_companies,
        "theme": "coverage universe",
        "data_elements": [
            {"name": "symbol", "definition": "The constituent's exchange ticker, or null where the issuer disclosure does not resolve to one.", "datatype": "string or null"},
            {"name": "cik", "definition": "The issuer's SEC Central Index Key.", "datatype": "string or null"},
            {"name": "sector_id", "definition": "Identifier of the assigned sector bucket, null until a classification source exists.", "datatype": "string or null"},
            {"name": "sector_source", "definition": "The citation justifying the sector assignment; required whenever sector_id is set.", "datatype": "string or null"},
        ],
    },
    {
        "id": "data-fabric",
        "path": "tools/data_fabric/out",
        "title": "Recorded public-fact corpus",
        "description": (
            "Structured facts recorded from public sources with provenance: SEC EDGAR "
            "XBRL company facts, U.S. Treasury par yield and bill curves, and Damodaran "
            "Online industry data. Each file is accompanied by a source-register row "
            "naming publisher, URL, retrieval time, and digest."
        ),
        "keywords": ["SEC EDGAR", "XBRL", "US Treasury", "Damodaran", "provenance"],
        "record_unit": "file",
        "counter": count_dir("*.json"),
        "theme": "source data",
        "data_elements": [
            {"name": "retrieved_utc", "definition": "The instant the fetch was performed, in ISO 8601 basic format.", "datatype": "string", "format": "ISO 8601 basic datetime"},
            {"name": "concept", "definition": "The us-gaap or source-defined element name the observations belong to.", "datatype": "string"},
            {"name": "end", "definition": "The period-end date an observation reports.", "datatype": "string", "format": "ISO 8601 date"},
            {"name": "value", "definition": "The reported figure, in the source's own units before any scaling.", "datatype": "number"},
            {"name": "filed", "definition": "The date the filing supplying the observation was submitted.", "datatype": "string", "format": "ISO 8601 date"},
        ],
    },
]


def describe(dataset: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / dataset["path"]
    if not path.exists():
        raise FileNotFoundError(
            f"catalogue names {dataset['path']}, which does not exist -- the catalogue "
            "must describe the repository as it is"
        )
    is_dir = path.is_dir()
    record_count = dataset["counter"](path)

    distribution: dict[str, Any] = {
        "@type": "dcat:Distribution",
        "dcterms:title": f"{dataset['title']} (JSON)",
        "dcat:mediaType": "application/json",
        "dcat:accessURL": f"{BASE}/blob/main/{dataset['path']}",
        "dcterms:extent": {
            "@type": "dcterms:SizeOrDuration",
            "rdf:value": (
                sum(f.stat().st_size for f in path.glob("*.json"))
                if is_dir
                else path.stat().st_size
            ),
            "unitText": "bytes (UCUM: By)",
        },
    }
    if not is_dir:
        # A digest is only meaningful for a single artifact; a directory's
        # contents change file by file, so claiming one digest for it would be
        # a fact that quietly stops being true.
        distribution["spdx:checksum"] = {
            "@type": "spdx:Checksum",
            "spdx:algorithm": "spdx:checksumAlgorithm_sha256",
            "spdx:checksumValue": sha256_file(path),
        }

    return {
        "@id": f"{BASE}#dataset-{dataset['id']}",
        "@type": ["dcat:Dataset", "schema:Dataset"],
        "dcterms:identifier": dataset["id"],
        "dcterms:title": dataset["title"],
        "dcterms:description": dataset["description"],
        "dcterms:publisher": PUBLISHER,
        "dcterms:license": {"@id": LICENSE_URI},
        "dcterms:rights": (
            "MIT licensed. Not investment advice and not validated for capital, "
            "fiduciary, or regulatory use."
        ),
        "dcterms:modified": date.today().isoformat(),
        "dcterms:conformsTo": [
            {"@id": f"{BASE}/standards/vocabulary"},
            {"@id": f"{BASE}/standards/conformance/unit_and_currency_registry.json"},
        ],
        "dcat:theme": dataset["theme"],
        "dcat:keyword": dataset["keywords"],
        "dcat:distribution": [distribution],
        "repo:path": dataset["path"],
        "repo:recordUnit": dataset["record_unit"],
        "repo:recordCount": record_count,
        "repo:dataElements": dataset["data_elements"],
        "repo:fair": {
            "findable": f"Persistent identifier {dataset['id']!r} and full metadata in this catalogue.",
            "accessible": f"Repository-relative path {dataset['path']} under the MIT licence.",
            "interoperable": (
                "Enumerated values resolve into the SKOS concept scheme at "
                "standards/vocabulary/glossary.skos.jsonld; units and currencies resolve "
                "into standards/conformance/unit_and_currency_registry.json."
            ),
            "reusable": (
                "Every record carries provenance to a named public source, and the "
                "stated usage limits are part of the metadata rather than a footnote."
            ),
        },
    }


def build() -> dict[str, Any]:
    datasets = [describe(d) for d in DATASETS]
    catalog = {
        "@id": f"{BASE}#catalog",
        "@type": ["dcat:Catalog", "schema:DataCatalog"],
        "dcterms:title": "Finance-Segway data catalogue",
        "dcterms:description": (
            "Machine-readable description of every dataset this repository publishes. "
            "Factual fields are computed from the filesystem at generation time and "
            "re-derived by tools/verify_dataset_metadata.py, so a stale catalogue fails "
            "the build instead of misleading a reader."
        ),
        "dcterms:publisher": PUBLISHER,
        "dcterms:license": {"@id": LICENSE_URI},
        "dcterms:modified": date.today().isoformat(),
        "dcat:dataset": [d["@id"] for d in datasets],
    }
    return {
        "@context": {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dcterms": "http://purl.org/dc/terms/",
            "schema": "https://schema.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "spdx": "http://spdx.org/rdf/terms#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "repo": f"{BASE}/standards/metadata#",
        },
        "@graph": [catalog, *datasets],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    catalog = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    datasets = [n for n in catalog["@graph"] if "dcat:Dataset" in n.get("@type", [])]
    print(f"wrote {args.output} with {len(datasets)} datasets")
    for node in datasets:
        unit = node["repo:recordUnit"]
        count = node["repo:recordCount"]
        plural = unit if count == 1 else PLURALS.get(unit, unit + "s")
        print(f"  {node['dcterms:identifier']:<20} {count:>6} {plural:<10} {node['repo:path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
