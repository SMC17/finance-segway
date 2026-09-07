"""Require the workbook's verdict to be able to see the model it grades.

WHY THIS GATE EXISTS
--------------------
A case can source a hundred values into a sheet, recalculate cleanly, reconcile
its identities, cite every input -- and report `Overall: PASS` from six checks
that read none of it. That is not hypothetical. In this repository's
corporate-finance case, `DCF!`, `BS!`, `CF!` and `Comps!` are referenced by
**zero** formulas anywhere in the workbook, so a DCF publishing $1.13 a share
could not have failed a check: no check could see the DCF.

The naive question -- "does any formula reference this sheet?" -- is the wrong
one, and getting it wrong is instructive. A checks sheet is terminal by design,
so that question calls every reporting sheet an orphan and labels the actually
dead valuation "terminal by design", which is the known case backwards.

The right question starts at the thing that DECIDES. Find the sheets that
produce verdicts, follow every cross-sheet reference transitively, and you have
the set of sheets the verdict can see. Anything outside it cannot change any
verdict, whatever it says.

WHAT MAKES A SHEET REQUIRED, WITHOUT ANYONE DECLARING ANYTHING
--------------------------------------------------------------
Requiring every sheet to be reachable would fail on `Sensitivity` in fifteen
workbooks, and a sensitivity table a human reads is not obviously something a
check should consult. Requiring only sheets a case *declares* load-bearing
would pass vacuously today, because no case declares any.

So the requirement is derived from the repository's own bookkeeping: **a sheet
the case record writes sourced inputs into is a sheet the case asserts is part
of the model.** Sourcing a cell is that assertion. If the case sources 103
values into three sheets and its verdict can reach none of them, the case
contradicts itself, and it does so in data the repository already keeps.

Measured across all 54 case records, this fires on exactly one -- the case
already known to be broken -- and on no others. It is a sharp rule rather than
a noisy one, which is why it carries no exemption mechanism: there is no case
that needs one, and an unused escape hatch on a gate is how gates stop failing.
Add one when a real case earns it.

WHAT THE OUTCOMES MEAN
----------------------
  reachable          every sourced sheet is reachable from a verdict
  stranded           at least one is not                             -> FAIL
  no_verdict_sheet   the workbook produces no verdicts at all        -> FAIL
  no_sourced_inputs  the case sources nothing: the rule has no subject
  unreadable         the workbook could not be read                  -> FAIL

`no_sourced_inputs` is not a pass. A case that asserts nothing and a case whose
assertions are all wired up must not render as the same green.

Usage:
    python tools/verify_verdict_closure.py
    python tools/verify_verdict_closure.py --report closure.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "standards" / "public_cases"

# 'Quoted Sheet'!A1 or Bare!A1. The alternation matters: a sheet name containing
# a space or an ampersand is always quoted, and a pattern that handles only the
# bare form silently finds nothing for exactly the sheets most likely to be
# check sheets ("Decision & Checks", "Treasury & Liquidity").
SHEET_REF = re.compile(r"(?:'([^']+)'|(\b[A-Za-z_][A-Za-z0-9_. ]*))!")

VERDICT_WORDS = ("PASS", "FAIL", "BREACH", "REVIEW")
MIN_VERDICTS_FOR_A_VERDICT_SHEET = 3

FAIL_OUTCOMES = {"stranded", "no_verdict_sheet", "unreadable"}
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOTHING_CHECKED = 3


def scan(book: Any) -> dict[str, Any]:
    """One pass over every formula: the reference graph, and where verdicts are made."""
    names = {sheet.title for sheet in book.worksheets}
    edges: dict[str, set[str]] = collections.defaultdict(set)
    verdicts: collections.Counter[str] = collections.Counter()
    formulas: collections.Counter[str] = collections.Counter()
    referenced: set[str] = set()
    for sheet in book.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                value = cell.value
                if not (isinstance(value, str) and value.startswith("=")):
                    continue
                formulas[sheet.title] += 1
                if any(f'"{word}"' in value for word in VERDICT_WORDS):
                    verdicts[sheet.title] += 1
                for quoted, bare in SHEET_REF.findall(value):
                    target = (quoted or bare).strip()
                    if target in names:
                        referenced.add(target)
                        if target != sheet.title:
                            edges[sheet.title].add(target)
    return {"names": names, "edges": edges, "verdicts": verdicts,
            "formulas": formulas, "referenced": referenced}


def verdict_sheets(scanned: dict[str, Any]) -> list[str]:
    """Sheets that decide, found by what they DO rather than by what they are called.

    A sheet naming three or more verdict outcomes in its formulas is grading
    something. Matching on the name instead would miss a renamed sheet and would
    have to be kept in step with every domain's vocabulary.
    """
    return sorted(name for name, count in scanned["verdicts"].items()
                  if count >= MIN_VERDICTS_FOR_A_VERDICT_SHEET)


def reachable_from(roots: list[str], edges: dict[str, set[str]]) -> set[str]:
    seen, stack = set(roots), list(roots)
    while stack:
        current = stack.pop()
        for nxt in edges.get(current, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def sourced_sheets(record: dict[str, Any]) -> tuple[collections.Counter, collections.Counter]:
    """Sourced inputs per sheet, and the numeric subset of them.

    The numeric subset is what makes a sheet required. Keying on "does it
    compute, or is it referenced" was the first attempt and it was fail-open:
    severing the reference that strands a sheet ALSO removes it from the
    referenced set, so a sheet full of sourced numbers that nothing reads --
    the worst case there is -- exempted itself from the requirement. A test
    fixture that broke the chain exposed it.

    What the case sourced is a fact about the case, and no defect in the
    workbook can change it. A prose title on a cover page is not a claim about
    the model; a number is.
    """
    every: collections.Counter = collections.Counter()
    numeric: collections.Counter = collections.Counter()
    for entry in record.get("inputs", []):
        sheet = entry.get("sheet")
        if not isinstance(sheet, str):
            continue
        every[sheet] += 1
        value = entry.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric[sheet] += 1
    return every, numeric


def check_case(record: dict[str, Any]) -> dict[str, Any]:
    case_id = record.get("id", "<unnamed>")
    output = record.get("output")
    result: dict[str, Any] = {"case": case_id, "workbook": output}
    if not output or not (ROOT / output).is_file():
        return {**result, "outcome": "unreadable",
                "detail": f"the record names no readable workbook ({output!r})"}
    try:
        book = openpyxl.load_workbook(ROOT / output)
    except Exception as error:
        return {**result, "outcome": "unreadable", "detail": str(error)[:200]}

    scanned = scan(book)
    roots = verdict_sheets(scanned)
    if not roots:
        return {**result, "outcome": "no_verdict_sheet",
                "detail": "no sheet names three or more verdict outcomes, so this "
                          "workbook grades nothing and there is no closure to be in"}
    seen = reachable_from(roots, scanned["edges"])
    computing = {name for name, count in scanned["formulas"].items() if count}

    sourced, numeric = sourced_sheets(record)
    # A sheet the case wrote a NUMBER into is a sheet the case says is part of
    # the model. Sourcing a prose title into a cover page is not that claim.
    #
    # A name the workbook does not have is refused rather than dropped. Filtering
    # it out silently would mean a renamed or deleted sheet removes its own
    # requirement -- the record would still claim the model needs it, the gate
    # would stop asking, and nothing would say so. No case does this today, which
    # is exactly when an allowance like that gets written and never revisited.
    unknown = sorted(name for name in numeric if name not in scanned["names"])
    if unknown:
        return {**result, "outcome": "unreadable",
                "detail": "the case sources numbers into sheet(s) this workbook does "
                          f"not have: {', '.join(unknown)}"}
    required = set(numeric)
    stranded = sorted(required - seen)

    result.update({
        "verdict_sheets": roots,
        "closure": sorted(seen),
        "sourced_sheets": {name: sourced[name] for name in sorted(sourced)},
        "numeric_sourced_sheets": {name: numeric[name] for name in sorted(numeric)},
        "required_sheets": sorted(required),
        "stranded_sheets": stranded,
        "stranded_inputs": sum(numeric[name] for name in stranded),
        # reported, never failed on: a sensitivity table nobody sourced into is
        # outside the closure by design, and saying so is not the same as
        # complaining about it.
        "unreached_computing_sheets": sorted(computing - seen),
    })
    if not required:
        result["outcome"] = "no_sourced_inputs"
        result["detail"] = ("this case sources no numeric input into any sheet of this "
                            "workbook, so it asserts nothing for a verdict to see")
    elif stranded:
        result["outcome"] = "stranded"
    else:
        result["outcome"] = "reachable"
    return result


def case_records() -> tuple[list[dict[str, Any]], list[str]]:
    """The case records, and the names of the files skipped as not being cases.

    Discriminated on structure rather than on filename: a case record carries
    both an `id` and a `template`. That keeps `index.json` out without a
    hard-coded exception, and -- the part that matters -- it does NOT let a real
    case record slip through by merely lacking its `output`, which would turn a
    broken case into a silent skip.
    """
    records, skipped = [], []
    for path in sorted(CASE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records.append({"id": path.name, "output": None})
            continue
        if isinstance(payload, dict) and payload.get("id") and payload.get("template"):
            records.append(payload)
        else:
            skipped.append(path.name)
    return records, skipped


def render(results: list[dict[str, Any]], skipped: list[str]) -> None:
    for result in sorted(results, key=lambda r: -r.get("stranded_inputs", 0)):
        if result["outcome"] == "reachable":
            continue
        print(f"\n{result['case']}  [{result['outcome']}]")
        if result.get("detail"):
            print(f"    {result['detail']}")
        if result.get("stranded_sheets"):
            print(f"    verdict sheets   : {', '.join(result['verdict_sheets'])}")
            print(f"    it can see       : {', '.join(result['closure'])}")
            print(f"    STRANDED         : {', '.join(result['stranded_sheets'])}"
                  f"  ({result['stranded_inputs']} sourced inputs)")
            for name in result["stranded_sheets"]:
                print(f"        {name}: {result['numeric_sourced_sheets'][name]} sourced "
                      "number(s) no check can reach")

    counts: collections.Counter[str] = collections.Counter(r["outcome"] for r in results)
    print("\n" + "-" * 74)
    for outcome in sorted(counts):
        print(f"  {outcome:20s} {counts[outcome]}")
    if skipped:
        print(f"  {'not a case record':20s} {len(skipped)}  ({', '.join(skipped)})")

    unreached = sum(len(r.get("unreached_computing_sheets") or []) for r in results)
    print("\nAND HERE IS WHAT THIS DID NOT CHECK")
    print("  - Reachability, not correctness. A sheet inside the closure can still be")
    print("    read by a check that tests nothing about it.")
    print("  - Only sheets the case sources a NUMBER into are required to be reachable.")
    print("    A sheet built entirely from formulas asserts nothing here and is not")
    print("    demanded, so a computed sheet nobody sourced into can still be unreached.")
    print(f"  - {unreached} computing sheet(s) across all cases sit outside their verdict's")
    print("    closure without being required to be inside it -- sensitivity tables,")
    print("    scenario grids and the like. They are listed in --report and are NOT")
    print("    failed on, because a table a human reads is not obviously a check's job.")
    print("  - Cross-sheet references only. A check reading a stale hard-coded number")
    print("    copied from another sheet looks exactly like a check reading nothing.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--report", type=Path, help="write the full result as JSON")
    args = parser.parse_args()

    records, skipped = case_records()
    results = [check_case(record) for record in records]
    render(results, skipped)

    if args.report:
        args.report.write_text(
            json.dumps({"results": results}, indent=2, sort_keys=True, default=sorted) + "\n",
            encoding="utf-8")
        print(f"\nreport: {args.report}")

    failed = [r for r in results if r["outcome"] in FAIL_OUTCOMES]
    checked = [r for r in results if r["outcome"] in {"reachable", "stranded"}]
    if failed:
        for outcome, wording in (
            ("stranded", "grade a model their verdict cannot see"),
            ("no_verdict_sheet", "produce no verdict at all"),
            ("unreadable", "could not be read"),
        ):
            hit = [r for r in failed if r["outcome"] == outcome]
            if hit:
                print(f"\nFAIL: {len(hit)} case(s) {wording}: "
                      f"{', '.join(r['case'] for r in hit)}")
        return EXIT_FAILED
    if not checked:
        print("\nFAIL: no case in this repository sources an input into a sheet that "
              "computes, so this gate had nothing to test. That is a finding.")
        return EXIT_NOTHING_CHECKED
    print(f"\nPASS: {len(checked)} case(s) keep every sourced sheet within reach of "
          "their verdict.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
