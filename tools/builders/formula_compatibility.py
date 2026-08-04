"""Normalize formulas for reliable Excel and LibreOffice recalculation.

The OOXML formula dialect accepts legacy Excel statistical names that are
understood by both current Excel and LibreOffice. Newer dotted function names
can be serialized as unknown functions by LibreOffice. This module rewrites
only mathematically equivalent functions and leaves workbook structure intact.
"""
from __future__ import annotations

from collections.abc import Callable


def _replace_calls(formula: str, function_name: str,
                   transform: Callable[[list[str]], str]) -> str:
    search = function_name.upper() + "("
    output = formula
    position = 0
    while True:
        index = output.upper().find(search, position)
        if index < 0:
            break
        open_index = index + len(function_name)
        depth = 0
        close_index = None
        comma_indexes: list[int] = []
        in_string = False
        cursor = open_index
        while cursor < len(output):
            character = output[cursor]
            if character == '"':
                in_string = not in_string
            elif not in_string:
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                    if depth == 0:
                        close_index = cursor
                        break
                elif character == "," and depth == 1:
                    comma_indexes.append(cursor)
            cursor += 1
        if close_index is None:
            raise ValueError(f"unbalanced formula while parsing {function_name}: {formula}")
        boundaries = [open_index + 1, *[item + 1 for item in comma_indexes], close_index + 1]
        args = []
        previous = open_index + 1
        for comma in comma_indexes:
            args.append(output[previous:comma].strip())
            previous = comma + 1
        args.append(output[previous:close_index].strip())
        replacement = transform(args)
        output = output[:index] + replacement + output[close_index + 1:]
        position = index + len(replacement)
    return output


def portable_formula(formula: str) -> str:
    if not isinstance(formula, str) or not formula.startswith("="):
        return formula

    def norm_dist(args: list[str]) -> str:
        if len(args) != 2:
            raise ValueError(f"NORM.S.DIST expected two arguments: {formula}")
        value, cumulative = args
        if cumulative.upper() in {"TRUE", "TRUE()", "1"}:
            return f"NORMSDIST({value})"
        if cumulative.upper() in {"FALSE", "FALSE()", "0"}:
            return f"(EXP(-(({value})^2)/2)/SQRT(2*PI()))"
        raise ValueError(f"unsupported NORM.S.DIST cumulative flag {cumulative}")

    result = _replace_calls(formula, "NORM.S.DIST", norm_dist)
    result = _replace_calls(
        result,
        "NORM.S.INV",
        lambda args: f"NORMSINV({args[0]})" if len(args) == 1 else (_ for _ in ()).throw(ValueError("NORM.S.INV expected one argument")),
    )
    result = result.replace("STDEV.P(", "STDEVP(").replace("stdev.p(", "STDEVP(")
    result = result.replace("PERCENTILE.INC(", "PERCENTILE(").replace("percentile.inc(", "PERCENTILE(")
    return result


def normalize_workbook_formulas(workbook) -> int:
    changed = 0
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    normalized = portable_formula(cell.value)
                    if normalized != cell.value:
                        cell.value = normalized
                        changed += 1
    return changed
