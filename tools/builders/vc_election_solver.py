"""Transparent Excel formulas for holder-by-holder VC conversion elections."""
from __future__ import annotations

from dataclasses import dataclass

try:
    from tools.builders.template_helpers import (
        BLACK,
        BOLD,
        BORDER,
        CUR,
        GRAY_FILL,
        ITALIC_GRAY,
        NUM,
        style_header_row,
    )
except ModuleNotFoundError:
    from template_helpers import (  # type: ignore
        BLACK,
        BOLD,
        BORDER,
        CUR,
        GRAY_FILL,
        ITALIC_GRAY,
        NUM,
        style_header_row,
    )


@dataclass(frozen=True)
class VCElectionLayout:
    support_cell: str
    first_class_row: int
    last_class_row: int
    base_total_cell: str
    adverse_total_cell: str
    base_residual_cell: str
    adverse_residual_cell: str
    base_equilibrium_cell: str
    adverse_equilibrium_cell: str


def _preference_payment(
    exit_ref: str,
    flags: list[str],
    target: int,
    preferred_rows: list[int],
) -> str:
    target_row = preferred_rows[target]
    senior_claims = "+".join(
        f'IF($E${other_row}>$E${target_row},(1-({flags[index]}))*$D${other_row},0)'
        for index, other_row in enumerate(preferred_rows)
    )
    return (
        f'IF(({flags[target]})=1,0,MIN($D${target_row},'
        f'MAX(0,{exit_ref}-({senior_claims}))))'
    )


def add_holder_election_solver(
    sheet,
    *,
    base_exit_ref: str,
    adverse_exit_ref: str,
    start_row: int,
) -> VCElectionLayout:
    """Add an auditable 2^3 election solver to an Exit Waterfall worksheet.

    The cap-table contract is rows 5/6 common, 8/9/10 preferred (Seed/A/B),
    with as-converted shares in M, invested amount in F, preference multiple
    in H, participation type in I, participation cap in J, and seniority in K.
    """

    title_row = start_row
    terms_row = start_row + 1
    note_row = start_row + 2
    header_row = start_row + 4
    first_class_row = header_row + 1
    preferred_rows = [first_class_row, first_class_row + 1, first_class_row + 2]
    common_row = first_class_row + 3
    last_class_row = common_row

    sheet.cell(title_row, 2, "Liquidation Preference Waterfall — Holder Elections")
    sheet.cell(title_row, 2).font = BOLD
    sheet.cell(title_row, 2).fill = GRAY_FILL
    sheet.cell(terms_row, 2, "Terms / solver status")
    support_cell = f"C{terms_row}"
    support_ref = f"$C${terms_row}"
    sheet[support_cell] = (
        f'=IF(AND(COUNT(C{first_class_row}:C{last_class_row})=4,'
        f'MIN(C{first_class_row}:C{last_class_row})>=0,'
        f'COUNT(D{first_class_row}:D{preferred_rows[-1]})=3,'
        f'MIN(D{first_class_row}:D{preferred_rows[-1]})>=0,'
        f'COUNT(E{first_class_row}:E{preferred_rows[-1]})=3,'
        f'MIN(E{first_class_row}:E{preferred_rows[-1]})>0,'
        f'E{preferred_rows[0]}<>E{preferred_rows[1]},'
        f'E{preferred_rows[0]}<>E{preferred_rows[2]},'
        f'E{preferred_rows[1]}<>E{preferred_rows[2]},'
        f'COUNTIF(F{first_class_row}:F{preferred_rows[-1]},"Non-participating")=3,'
        f'COUNT(G{first_class_row}:G{preferred_rows[-1]})=3,'
        f'MIN(G{first_class_row}:G{preferred_rows[-1]})=0,'
        f'MAX(G{first_class_row}:G{preferred_rows[-1]})=0,'
        'COUNTIF(\'Cap Table\'!G8:G10,"Preferred")=3,'
        'MIN(\'Cap Table\'!L8:L10)>0,\'Cap Table\'!M7=0),'
        '"SUPPORTED","UNSUPPORTED / INCOMPLETE")'
    )
    sheet[support_cell].font = BOLD
    sheet.cell(
        note_row,
        2,
        "Each preferred class independently retains its preference or converts. "
        "The selected state conserves proceeds and admits no profitable unilateral "
        "election change. Participating preferred, non-zero participation caps, "
        "duplicate seniority, and unconverted SAFEs fail closed for legal review.",
    )
    sheet.cell(note_row, 2).font = ITALIC_GRAY

    headers = [
        "Class",
        "As-converted shares",
        "Preference claim",
        "Seniority",
        "Participation",
        "Cap (x)",
        "Base election",
        "Base payout",
        "Adverse election",
        "Adverse payout",
    ]
    for column, value in enumerate(headers, start=2):
        sheet.cell(header_row, column, value)
    style_header_row(sheet, header_row, len(headers), start_col=2)

    source_rows = [10, 9, 8]
    labels = ["Series B preferred", "Series A preferred", "Seed preferred"]
    for row, source_row, label in zip(preferred_rows, source_rows, labels):
        sheet.cell(row, 2, label)
        sheet.cell(row, 3, f"=IFERROR('Cap Table'!M{source_row},0)")
        sheet.cell(row, 4, f"=MAX(0,'Cap Table'!F{source_row}*'Cap Table'!H{source_row})")
        sheet.cell(row, 5, f"='Cap Table'!K{source_row}")
        sheet.cell(row, 6, f"='Cap Table'!I{source_row}")
        sheet.cell(row, 7, f"='Cap Table'!J{source_row}")
    sheet.cell(common_row, 2, "Common (founders + option pool)")
    sheet.cell(common_row, 3, "=IFERROR('Cap Table'!M5+'Cap Table'!M6,0)")
    sheet.cell(common_row, 4, 0)
    sheet.cell(common_row, 5, 0)
    sheet.cell(common_row, 6, "N/A")
    sheet.cell(common_row, 7, 0)

    total_row = last_class_row + 2
    residual_row = total_row + 1
    equilibrium_row = total_row + 2
    sheet.cell(total_row, 2, "Total distributed")
    sheet.cell(residual_row, 2, "Conservation residual")
    sheet.cell(equilibrium_row, 2, "Selected stable election mask")

    candidate_headers = [
        "Mask",
        "B converts",
        "A converts",
        "Seed converts",
        "B pref pay",
        "A pref pay",
        "Seed pref pay",
        "Residual",
        "Common-pool shares",
        "B payout",
        "A payout",
        "Seed payout",
        "Common payout",
        "Total",
        "B alt payout",
        "A alt payout",
        "Seed alt payout",
        "B stable",
        "A stable",
        "Seed stable",
        "Stable candidate",
    ]

    def write_candidates(title: str, title_at: int, exit_ref: str) -> tuple[int, int]:
        sheet.cell(title_at, 2, title)
        sheet.cell(title_at, 2).font = BOLD
        candidate_header = title_at + 1
        first = candidate_header + 1
        last = first + 7
        for column, value in enumerate(candidate_headers, start=2):
            sheet.cell(candidate_header, column, value)
        style_header_row(sheet, candidate_header, len(candidate_headers), start_col=2)
        for mask, row in enumerate(range(first, last + 1)):
            flags = [
                f"$C{row}",
                f"$D{row}",
                f"$E{row}",
            ]
            values = [(mask >> 2) & 1, (mask >> 1) & 1, mask & 1]
            sheet.cell(row, 2, mask)
            for column, value in enumerate(values, start=3):
                sheet.cell(row, column, value)
            for index, column in enumerate(range(6, 9)):
                sheet.cell(
                    row,
                    column,
                    "=" + _preference_payment(
                        exit_ref, flags, index, preferred_rows
                    ),
                )
            sheet.cell(row, 9, f"=MAX(0,{exit_ref}-SUM(F{row}:H{row}))")
            sheet.cell(
                row,
                10,
                f"=$C${common_row}+C{row}*$C${preferred_rows[0]}+"
                f"D{row}*$C${preferred_rows[1]}+E{row}*$C${preferred_rows[2]}",
            )
            for index, column in enumerate(range(11, 14)):
                flag_column = chr(ord("C") + index)
                preference_column = chr(ord("F") + index)
                sheet.cell(
                    row,
                    column,
                    f"=IF({flag_column}{row}=1,IFERROR(I{row}*$C${preferred_rows[index]}/J{row},0),"
                    f"{preference_column}{row})",
                )
            sheet.cell(row, 14, f"=IFERROR(I{row}*$C${common_row}/J{row},0)")
            sheet.cell(row, 15, f"=SUM(K{row}:N{row})")
            for index, (actual_column, alternative_column) in enumerate(
                zip(range(11, 14), range(16, 19))
            ):
                flag_column = chr(ord("C") + index)
                bit_value = 4 >> index
                actual_letter = chr(ord("K") + index)
                sheet.cell(
                    row,
                    alternative_column,
                    f"=INDEX(${actual_letter}${first}:${actual_letter}${last},"
                    f"MATCH(IF({flag_column}{row}=1,B{row}-{bit_value},B{row}+{bit_value}),"
                    f"$B${first}:$B${last},0))",
                )
            for actual_column, alternative_column, stable_column in zip(
                range(11, 14), range(16, 19), range(19, 22)
            ):
                sheet.cell(
                    row,
                    stable_column,
                    f"=--({sheet.cell(row, actual_column).coordinate}+0.000001>="
                    f"{sheet.cell(row, alternative_column).coordinate})",
                )
            sheet.cell(
                row,
                22,
                f'=IFERROR(--(AND({support_ref}="SUPPORTED",S{row}=1,T{row}=1,'
                f'U{row}=1,ABS(O{row}-{exit_ref})<=0.01)),0)',
            )
            for column in range(2, 23):
                sheet.cell(row, column).border = BORDER
            for column in range(6, 19):
                sheet.cell(row, column).number_format = CUR
        return first, last

    base_title = equilibrium_row + 2
    base_first, base_last = write_candidates(
        "Base — exhaustive holder-election candidates", base_title, base_exit_ref
    )
    adverse_title = base_last + 2
    adverse_first, adverse_last = write_candidates(
        "Adverse — exhaustive holder-election candidates", adverse_title, adverse_exit_ref
    )

    def selected(range_first: int, range_last: int, column: str) -> str:
        return (
            f"INDEX(${column}${range_first}:${column}${range_last},"
            f"MATCH(1,$V${range_first}:$V${range_last},0))"
        )

    for index, row in enumerate(preferred_rows):
        flag_column = chr(ord("C") + index)
        payout_column = chr(ord("K") + index)
        sheet.cell(
            row,
            8,
            f'=IFERROR(IF({selected(base_first, base_last, flag_column)}=1,'
            '"CONVERT","PREFERENCE"),"NO EQUILIBRIUM")',
        )
        sheet.cell(
            row,
            9,
            f"=IFERROR({selected(base_first, base_last, payout_column)},0)",
        )
        sheet.cell(
            row,
            10,
            f'=IFERROR(IF({selected(adverse_first, adverse_last, flag_column)}=1,'
            '"CONVERT","PREFERENCE"),"NO EQUILIBRIUM")',
        )
        sheet.cell(
            row,
            11,
            f"=IFERROR({selected(adverse_first, adverse_last, payout_column)},0)",
        )
    sheet.cell(common_row, 8, "COMMON")
    sheet.cell(common_row, 9, f"=IFERROR({selected(base_first, base_last, 'N')},0)")
    sheet.cell(common_row, 10, "COMMON")
    sheet.cell(
        common_row,
        11,
        f"=IFERROR({selected(adverse_first, adverse_last, 'N')},0)",
    )

    sheet.cell(total_row, 9, f"=SUM(I{first_class_row}:I{last_class_row})")
    sheet.cell(total_row, 11, f"=SUM(K{first_class_row}:K{last_class_row})")
    sheet.cell(residual_row, 9, f"=I{total_row}-{base_exit_ref}")
    sheet.cell(residual_row, 11, f"=K{total_row}-{adverse_exit_ref}")
    sheet.cell(
        equilibrium_row,
        9,
        f"=IFERROR({selected(base_first, base_last, 'B')},\"NONE\")",
    )
    sheet.cell(
        equilibrium_row,
        11,
        f"=IFERROR({selected(adverse_first, adverse_last, 'B')},\"NONE\")",
    )

    for row in range(first_class_row, last_class_row + 1):
        for column in range(2, 12):
            sheet.cell(row, column).border = BORDER
            sheet.cell(row, column).font = BLACK
        sheet.cell(row, 3).number_format = NUM
        sheet.cell(row, 4).number_format = CUR
        sheet.cell(row, 7).number_format = "0.0x"
        sheet.cell(row, 9).number_format = CUR
        sheet.cell(row, 11).number_format = CUR
    for cell in (
        sheet.cell(total_row, 9),
        sheet.cell(total_row, 11),
        sheet.cell(residual_row, 9),
        sheet.cell(residual_row, 11),
    ):
        cell.number_format = CUR
        cell.font = BOLD
        cell.border = BORDER

    return VCElectionLayout(
        support_cell=support_cell,
        first_class_row=first_class_row,
        last_class_row=last_class_row,
        base_total_cell=f"I{total_row}",
        adverse_total_cell=f"K{total_row}",
        base_residual_cell=f"I{residual_row}",
        adverse_residual_cell=f"K{residual_row}",
        base_equilibrium_cell=f"I{equilibrium_row}",
        adverse_equilibrium_cell=f"K{equilibrium_row}",
    )
