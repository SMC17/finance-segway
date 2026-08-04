"""Portable scalar rewrites for hardened legacy workbook checks.

Legacy templates often return the text placeholder ``-`` when inputs are
missing. Excel may tolerate some downstream expressions involving those cells,
but LibreOffice correctly exposes them as type errors. These rewrites keep the
blank-template state explicit while ensuring that decision checks never emit a
cached spreadsheet error.
"""
from __future__ import annotations


def normalize_hardened_formulas(workbook) -> None:
    if {
        "Decision & Checks",
        "5-Year Hold & IRR",
        "Cap Rate & Valuation",
    }.issubset(workbook.sheetnames):
        checks = workbook["Decision & Checks"]
        checks["C12"] = (
            "=IF(AND(ISNUMBER('5-Year Hold & IRR'!C6),"
            "ISNUMBER('Cap Rate & Valuation'!C9)),"
            "'5-Year Hold & IRR'!C6-'Cap Rate & Valuation'!C9,0)"
        )
        checks["D12"] = (
            "=IF(AND(ISNUMBER('5-Year Hold & IRR'!C6),"
            "ISNUMBER('Cap Rate & Valuation'!C9)),"
            "IF(C12>=0,\"PASS\",\"REVIEW\"),\"REVIEW\")"
        )

    if {"Decision & Checks", "Recovery Waterfall"}.issubset(workbook.sheetnames):
        checks = workbook["Decision & Checks"]
        recovery = "'Recovery Waterfall'!"
        pairs = []
        for senior, junior in ((5, 6), (6, 7), (7, 8), (8, 9)):
            pairs.append(
                f"IF(AND(ISNUMBER({recovery}F{senior}),"
                f"ISNUMBER({recovery}F{junior})),"
                f"{recovery}F{senior}-{recovery}F{junior},0)"
            )
        checks["C6"] = "=MIN(" + ",".join(pairs) + ")"
        checks["D6"] = '=IF(C6>=-0.000001,"PASS","FAIL")'

    if {"Decision & Checks", "Fund Performance"}.issubset(workbook.sheetnames):
        checks = workbook["Decision & Checks"]
        numeric_test = (
            "AND(ISNUMBER('Fund Performance'!C18),"
            "ISNUMBER('Fund Performance'!C16),"
            "ISNUMBER('Fund Performance'!C17))"
        )
        checks["C6"] = (
            f"=IF({numeric_test},'Fund Performance'!C18-"
            "'Fund Performance'!C16-'Fund Performance'!C17,0)"
        )
        checks["D6"] = (
            f'=IF({numeric_test},IF(ABS(C6)<0.000001,"PASS","FAIL"),"REVIEW")'
        )

    if {"Decision & Checks", "Working Capital Cycle"}.issubset(
        workbook.sheetnames
    ):
        checks = workbook["Decision & Checks"]
        numeric_test = (
            "AND(ISNUMBER('Working Capital Cycle'!C15),"
            "ISNUMBER('Working Capital Cycle'!C12),"
            "ISNUMBER('Working Capital Cycle'!C13),"
            "ISNUMBER('Working Capital Cycle'!C14))"
        )
        checks["C5"] = (
            f"=IF({numeric_test},'Working Capital Cycle'!C15-("
            "'Working Capital Cycle'!C12+'Working Capital Cycle'!C13-"
            "'Working Capital Cycle'!C14),0)"
        )
        checks["D5"] = (
            f'=IF({numeric_test},IF(ABS(C5)<0.000001,"PASS","FAIL"),"REVIEW")'
        )
