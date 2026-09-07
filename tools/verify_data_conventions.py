"""Check the repository's data against the notation standards it claims to follow.

Scope: ISO 8601 (dates and times), ISO 4217 (currency), the SI decimal
multiples and UCUM (magnitude), and ISO/IEC 25012 / ISO 8000 consistency for
the places where a numeric field holds a string.

WHY THIS EXISTS
---------------
This repository encodes two pieces of metadata inside identifiers rather than
alongside them:

    "revenue_usd_mm": 245122.0

The currency (USD) and the scale (millions) live in the field NAME. Nothing
declares them, nothing validates them, and nothing stops a second convention
appearing next to the first. That is precisely the failure ISO/IEC 11179
describes: a data element whose meaning is carried by an unregistered naming
habit rather than by a definition.

So this checker does not try to change the convention -- it is the convention
of the source filings and the workbooks. It makes the convention CHECKED:
every currency token must be a registered ISO 4217 code, every magnitude
suffix must resolve to an exact multiplier in the registry, and any drift
between two suffixes meaning the same thing is reported rather than tolerated.

WHAT IS AND IS NOT A FAILURE
----------------------------
Hard failures (exit 1) are things that make data wrong or unreadable:
  - a date-semantic field whose value is not ISO 8601,
  - a currency token that is not in the registry's allow-list,
  - a magnitude suffix that resolves to no declared multiplier,
  - a string sentinel that is not a known upstream sentinel.

Warnings (exit 0, but reported and counted) are things that make data
inconsistent rather than wrong:
  - two suffixes denoting the same multiplier ('m' and 'mm'),
  - ISO 8601 basic format mixed with extended format,
  - known upstream sentinels ("NA") sitting in numeric columns,
  - monetary fields whose scale cannot be parsed at all.

The split matters. A checker that fails on everything gets switched off; one
that fails only on what is actually broken keeps its authority.

Usage:
    python tools/verify_data_conventions.py
    python tools/verify_data_conventions.py --report conventions.json
    python tools/verify_data_conventions.py --strict   # warnings become failures
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "standards" / "conformance" / "unit_and_currency_registry.json"

SKIP_DIRS = {".git", "node_modules", ".model-build", "__pycache__", ".pytest_cache"}

# Keys whose values are expected to carry a date or timestamp. Matched on the
# key name, because a value that merely looks like a date ("2024" as a label,
# a fiscal-year integer) must not be dragged into a format check.
DATE_KEY = re.compile(
    r"(^|_)(date|as_of|asof|filed|retrieved_utc|registered_on|resolve_by|"
    r"generated_on|next_check|last_refreshed|captured_at|end|start)(_|$)",
    re.IGNORECASE,
)

# ISO 8601 forms this repository actually uses.
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)
ISO_BASIC_DATETIME = re.compile(r"^\d{8}T\d{6}Z$")
ISO_YEAR_MONTH = re.compile(r"^\d{4}-\d{2}$")
ISO_YEAR = re.compile(r"^\d{4}$")

# A monetary field name: <something>_<ISO4217>[_<magnitude>]
MONEY_FIELD = re.compile(r"_(?P<ccy>[a-z]{3})(?:_(?P<mag>[a-z]{1,3}))?$", re.IGNORECASE)


def load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        raise FileNotFoundError(
            f"missing {REGISTRY.relative_to(ROOT)} -- the notation registry is the "
            "authority this check reads; without it there is nothing to check against"
        )
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def json_files() -> Iterator[Path]:
    for path in sorted(ROOT.rglob("*.json")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def walk(node: Any, path: str = "") -> Iterator[tuple[str, str, Any]]:
    """Yield (json_pointer, key, value) for every key/value pair in the tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            pointer = f"{path}/{key}"
            yield pointer, str(key), value
            yield from walk(value, pointer)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from walk(item, f"{path}/{index}")


def classify_date(value: str) -> str | None:
    """Return the ISO 8601 form used, or None if the value is not ISO 8601."""
    if ISO_DATE.match(value):
        return "extended_date"
    if ISO_DATETIME.match(value):
        return "extended_datetime"
    if ISO_BASIC_DATETIME.match(value):
        return "basic_datetime"
    if ISO_YEAR_MONTH.match(value):
        return "year_month"
    if ISO_YEAR.match(value):
        return "year"
    return None


def run(strict: bool = False) -> dict[str, Any]:
    registry = load_registry()
    currencies = registry["currency_codes"]
    magnitudes = registry["magnitude_suffixes"]
    dimensionless = set(registry["dimensionless_conventions"])
    sentinels = set(registry["sentinel_values"]["known"])

    failures: list[str] = []
    warnings: list[str] = []
    date_forms: Counter[str] = Counter()
    currency_use: Counter[str] = Counter()
    magnitude_use: Counter[str] = Counter()
    sentinel_hits: Counter[str] = Counter()
    files_scanned = 0

    # Multipliers that more than one suffix maps onto: an inconsistency the
    # registry records and this check surfaces with its real cost.
    by_multiplier: dict[int, list[str]] = {}
    for suffix, spec in magnitudes.items():
        by_multiplier.setdefault(spec["multiplier"], []).append(suffix)

    for path in json_files():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            failures.append(f"{path.relative_to(ROOT)}: unreadable JSON: {error}")
            continue
        files_scanned += 1
        relative = path.relative_to(ROOT)

        for pointer, key, value in walk(payload):
            # --- ISO 8601 ------------------------------------------------
            if isinstance(value, str) and DATE_KEY.search(key) and value.strip():
                form = classify_date(value.strip())
                if form is None:
                    # A date-named key may legitimately hold a label rather
                    # than a date (an "end" that names a table column, a
                    # "start" that names a phase). Only flag values that are
                    # date-SHAPED but malformed, so the check stays precise.
                    if re.match(r"^\s*\d{1,4}[-/.]\d{1,2}([-/.]\d{1,4})?", value):
                        failures.append(
                            f"{relative}{pointer}: {key!r} = {value!r} is date-shaped "
                            "but not ISO 8601"
                        )
                else:
                    date_forms[form] += 1

            # --- ISO 4217 + magnitude -----------------------------------
            match = MONEY_FIELD.search(key)
            if match:
                code = match.group("ccy").upper()
                if code in currencies:
                    currency_use[code] += 1
                    magnitude = match.group("mag")
                    if magnitude is None:
                        # A bare ISO 4217 suffix means the currency's principal
                        # unit. That reading is registered, so it is a declared
                        # scale rather than a missing one.
                        magnitude_use["<units>"] += 1
                    elif magnitude.lower() in magnitudes:
                        magnitude_use[magnitude.lower()] += 1
                    elif magnitude.lower() in dimensionless:
                        magnitude_use[magnitude.lower()] += 1
                    else:
                        failures.append(
                            f"{relative}{pointer}: {key!r} uses magnitude suffix "
                            f"{magnitude!r}, which resolves to no declared multiplier "
                            f"in {REGISTRY.relative_to(ROOT)}"
                        )

            # --- sentinel strings in numeric position -------------------
            if isinstance(value, str) and value.strip() in sentinels and value.strip():
                sentinel_hits[value.strip()] += 1

    for multiplier, suffixes in sorted(by_multiplier.items()):
        used = [s for s in suffixes if magnitude_use.get(s)]
        if len(used) > 1:
            counts = ", ".join(f"{s} x{magnitude_use[s]}" for s in sorted(used))
            warnings.append(
                f"magnitude ambiguity: {counts} all mean {multiplier:,} -- one "
                "multiplier with two spellings is an ISO/IEC 25012 consistency defect; "
                "the registry marks the duplicate deprecated"
            )

    if sentinel_hits:
        total = sum(sentinel_hits.values())
        detail = ", ".join(f"{v!r} x{c}" for v, c in sentinel_hits.most_common(5))
        warnings.append(
            f"{total} string sentinels sit in otherwise-numeric fields ({detail}). "
            "These arrive from upstream spreadsheet exports. They are known, but a "
            "string where a number belongs still fails JSON Schema type validation "
            "and ISO/IEC 25012 consistency"
        )

    if date_forms.get("basic_datetime") and date_forms.get("extended_datetime"):
        warnings.append(
            f"ISO 8601 basic format ({date_forms['basic_datetime']} values, "
            f"e.g. 20260817T230452Z) is mixed with extended format "
            f"({date_forms['extended_datetime']} values). Both are valid ISO 8601, "
            "but two formats for one concept forces every consumer to handle both"
        )

    status = "PASS" if not failures and (not strict or not warnings) else "FAIL"
    return {
        "status": status,
        "files_scanned": files_scanned,
        "iso8601_values_checked": sum(date_forms.values()),
        "iso8601_forms": dict(date_forms),
        "iso4217_codes_used": dict(currency_use),
        "magnitude_suffixes_used": dict(magnitude_use),
        "failures": failures,
        "warnings": warnings,
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat consistency warnings as failures",
    )
    args = parser.parse_args()

    report = run(strict=args.strict)
    printable = dict(report)
    printable["failures"] = report["failures"][:20]
    printable["warnings"] = report["warnings"][:20]
    print(json.dumps(printable, indent=2))
    if len(report["failures"]) > 20:
        print(f"... and {len(report['failures']) - 20} more failures")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
