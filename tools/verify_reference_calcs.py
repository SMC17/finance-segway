"""Independent-oracle regression checks for high-risk workbook mechanics.

Each check mutates a copied canonical workbook, recalculates it with
LibreOffice, and compares the resulting cached values with an independent
Python calculation or an explicit accounting identity. The checks deliberately
reference the released institutional workbooks rather than retired skeleton
sheet names.
"""
from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
from collections.abc import Callable

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import openpyxl  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from recalc import recalc  # noqa: E402

TOL = 1e-4


def close(a, b, tol=TOL):
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) / abs(b) < tol


def with_recalc(src_path: str, populate_fn: Callable) -> openpyxl.Workbook:
    """Copy, mutate, recalculate, and return a data-only workbook."""
    temporary = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    temporary.close()
    shutil.copy(src_path, temporary.name)
    try:
        workbook = openpyxl.load_workbook(temporary.name)
        populate_fn(workbook)
        workbook.save(temporary.name)
        result = recalc(temporary.name, timeout=90)
        if result.get("status") != "success" or result.get("total_errors", 0):
            raise RuntimeError(f"recalculation failed: {result}")
        return openpyxl.load_workbook(temporary.name, data_only=True)
    finally:
        os.unlink(temporary.name)


# ---------------------------------------------------------------------
# Options: Black-Scholes closed form and put-call parity.
# ---------------------------------------------------------------------
def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def black_scholes(S, K, T, r, q, sigma):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call = S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    put = K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)
    return call, put


def check_black_scholes():
    S, K, T, r, q, sigma = 100.0, 100.0, 0.25, 0.045, 0.0, 0.30
    path = os.path.join(REPO_ROOT, "14_Options_Derivatives", "_template_OPTIONS.xlsx")

    def populate(workbook):
        assumptions = workbook["Assumptions"]
        for cell, value in zip(
            ("C5", "C6", "C7", "C8", "C9", "C10"),
            (S, K, T, r, q, sigma),
        ):
            assumptions[cell] = value
        workbook["Cover"]["C9"] = "Base"

    workbook = with_recalc(path, populate)
    pricer = workbook["European Pricer"]
    sheet_call = pricer["C7"].value
    sheet_put = pricer["C8"].value
    reference_call, reference_put = black_scholes(S, K, T, r, q, sigma)
    parity_lhs = sheet_call - sheet_put
    parity_rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    ok = (
        close(sheet_call, reference_call, tol=1e-6)
        and close(sheet_put, reference_put, tol=1e-6)
        and close(parity_lhs, parity_rhs, tol=1e-6)
    )
    detail = (
        f"call sheet={sheet_call:.6f} oracle={reference_call:.6f}; "
        f"put sheet={sheet_put:.6f} oracle={reference_put:.6f}; "
        f"parity residual={parity_lhs - parity_rhs:.10f}"
    )
    return "Options: Black-Scholes price and put-call parity", ok, detail


# ---------------------------------------------------------------------
# Fixed income: closed-form price and modified duration.
# ---------------------------------------------------------------------
def bond_price(face, coupon_rate, frequency, years, ytm):
    periods = int(round(frequency * years))
    coupon = face * coupon_rate / frequency
    periodic_yield = ytm / frequency
    return (
        sum(coupon / (1 + periodic_yield) ** period for period in range(1, periods + 1))
        + face / (1 + periodic_yield) ** periods
    )


def closed_form_modified_duration(face, coupon_rate, frequency, years, ytm):
    periods = int(round(frequency * years))
    coupon = face * coupon_rate / frequency
    periodic_yield = ytm / frequency
    price = bond_price(face, coupon_rate, frequency, years, ytm)
    macaulay_periods = sum(
        period * (coupon if period < periods else coupon + face) / (1 + periodic_yield) ** period
        for period in range(1, periods + 1)
    ) / price
    return (macaulay_periods / frequency) / (1 + periodic_yield)


def check_bond_duration():
    face, coupon, frequency, years, ytm = 1000.0, 0.05, 2.0, 10.0, 0.055
    path = os.path.join(REPO_ROOT, "21_Fixed_Income_Rates", "_template_FIXED_INCOME.xlsx")

    def populate(workbook):
        assumptions = workbook["Assumptions"]
        for cell, value in zip(
            ("C5", "C6", "C7", "C8", "C9"),
            (face, coupon, ytm, years, frequency),
        ):
            assumptions[cell] = value
        workbook["Cover"]["C9"] = "Base"

    workbook = with_recalc(path, populate)
    analytics = workbook["Bond Analytics"]
    sheet_price = analytics["C5"].value
    sheet_duration = analytics["C8"].value
    reference_price = bond_price(face, coupon, frequency, years, ytm)
    reference_duration = closed_form_modified_duration(face, coupon, frequency, years, ytm)
    ok = close(sheet_price, reference_price, tol=1e-6) and close(
        sheet_duration, reference_duration, tol=0.001
    )
    detail = (
        f"price sheet={sheet_price:.6f} oracle={reference_price:.6f}; "
        f"modified duration sheet={sheet_duration:.6f} oracle={reference_duration:.6f}"
    )
    return "Fixed income: price and modified duration", ok, detail


# ---------------------------------------------------------------------
# LBO: balanced transaction and every debt/cash roll-forward identity.
# ---------------------------------------------------------------------
def check_lbo_sources_uses_and_debt_schedule():
    path = os.path.join(REPO_ROOT, "03_Private_Equity", "_template_LBO.xlsx")
    workbook = with_recalc(path, lambda _: None)
    sources_uses = workbook["Sources & Uses"]
    debt = workbook["Debt Schedule"]

    sources_total = sources_uses["F9"].value
    uses_total = sources_uses["C9"].value
    balance_check = sources_uses["F10"].value
    ok = close(sources_total, uses_total, tol=1e-8) and close(balance_check, 0.0, tol=1e-8)
    failures = []

    if not close(
        debt["C27"].value,
        debt["C16"].value + debt["C21"].value + debt["C26"].value,
        tol=1e-8,
    ):
        failures.append("close total debt")
    if not close(debt["C28"].value, debt["C27"].value - debt["C13"].value, tol=1e-8):
        failures.append("close net debt")

    for column in range(4, 11):
        letter = get_column_letter(column)
        previous = get_column_letter(column - 1)
        identities = {
            "begin cash": (debt[f"{letter}5"].value, debt[f"{previous}13"].value),
            "ending cash": (
                debt[f"{letter}13"].value,
                debt[f"{letter}9"].value
                + debt[f"{letter}10"].value
                - debt[f"{letter}11"].value
                - debt[f"{letter}12"].value,
            ),
            "begin revolver": (debt[f"{letter}14"].value, debt[f"{previous}16"].value),
            "ending revolver": (
                debt[f"{letter}16"].value,
                max(0.0, debt[f"{letter}14"].value + debt[f"{letter}10"].value),
            ),
            "begin TLB": (debt[f"{letter}17"].value, debt[f"{previous}21"].value),
            "ending TLB": (
                debt[f"{letter}21"].value,
                max(
                    0.0,
                    debt[f"{letter}17"].value
                    - debt[f"{letter}19"].value
                    - debt[f"{letter}20"].value,
                ),
            ),
            "begin second lien": (debt[f"{letter}22"].value, debt[f"{previous}26"].value),
            "ending second lien": (
                debt[f"{letter}26"].value,
                max(
                    0.0,
                    debt[f"{letter}22"].value
                    + debt[f"{letter}24"].value
                    - debt[f"{letter}25"].value,
                ),
            ),
            "total debt": (
                debt[f"{letter}27"].value,
                debt[f"{letter}16"].value
                + debt[f"{letter}21"].value
                + debt[f"{letter}26"].value,
            ),
            "net debt": (
                debt[f"{letter}28"].value,
                debt[f"{letter}27"].value - debt[f"{letter}13"].value,
            ),
        }
        for identity, (actual, expected) in identities.items():
            if not close(actual, expected, tol=1e-8):
                failures.append(f"{letter}:{identity}")
        if min(
            debt[f"{letter}16"].value,
            debt[f"{letter}21"].value,
            debt[f"{letter}26"].value,
        ) < -1e-8:
            failures.append(f"{letter}:negative debt")

    ok = ok and not failures
    detail = (
        f"sources={sources_total:.6f}, uses={uses_total:.6f}, balance={balance_check:.10f}; "
        f"roll-forward failures={failures or 'none'}; year-7 net debt={debt['J28'].value:.6f}"
    )
    return "LBO: Sources & Uses and seven-year debt roll-forward", ok, detail


# ---------------------------------------------------------------------
# VC waterfall conservation in preference and as-converted regimes.
# ---------------------------------------------------------------------
def check_vc_waterfall_conservation():
    path = os.path.join(REPO_ROOT, "13_Venture_Capital", "_template_VC.xlsx")
    shares = {"founders": 6_000_000, "pool": 1_000_000, "seed": 1_000_000,
              "a": 1_500_000, "b": 1_000_000}
    invested = {"founders": 6_000_000 * 0.0001, "pool": 1_000_000 * 0.0001,
                "seed": 1_000_000 * 1.00, "a": 1_500_000 * 2.00, "b": 1_000_000 * 5.00}
    total_shares = sum(shares.values())
    fd_pct = {k: v / total_shares for k, v in shares.items()}
    base_proceeds, adv_proceeds = 8_000_000, 50_000_000

    def populate(workbook):
        cap_table = workbook["Cap Table"]
        cap_table["C5"], cap_table["E5"] = shares["founders"], 0.0001
        cap_table["C6"], cap_table["E6"] = shares["pool"], 0.0001
        cap_table["C8"], cap_table["E8"] = shares["seed"], 1.00
        cap_table["C9"], cap_table["E9"] = shares["a"], 2.00
        cap_table["C10"], cap_table["E10"] = shares["b"], 5.00
        workbook["Exit Waterfall"]["C5"] = base_proceeds
        workbook["Exit Waterfall"]["D5"] = adv_proceeds

    workbook = with_recalc(path, populate)
    ws = workbook["Exit Waterfall"]

    def ref_cascade(total_proceeds):
        pref = {"b": invested["b"], "a": invested["a"], "seed": invested["seed"]}
        b = min(total_proceeds, pref["b"])
        a = min(max(total_proceeds - b, 0), pref["a"])
        seed = min(max(total_proceeds - b - a, 0), pref["seed"])
        common = max(0.0, total_proceeds - b - a - seed)
        pref_stack = {"b": b, "a": a, "seed": seed, "common": common}
        as_converted = {
            "b": total_proceeds * fd_pct["b"], "a": total_proceeds * fd_pct["a"],
            "seed": total_proceeds * fd_pct["seed"],
            "common": total_proceeds * (fd_pct["founders"] + fd_pct["pool"]),
        }
        use_as_converted = total_proceeds > sum(pref.values())
        return (as_converted if use_as_converted else pref_stack), use_as_converted

    ref_base, base_as_converted = ref_cascade(base_proceeds)
    ref_adv, adv_as_converted = ref_cascade(adv_proceeds)

    sheet_class_rows = {"b": 20, "a": 21, "seed": 22, "common": 23}
    mismatches = []
    for cls, row in sheet_class_rows.items():
        sheet_base = ws.cell(row=row, column=10).value  # J = Actual: Base
        sheet_adv = ws.cell(row=row, column=11).value    # K = Actual: Adversarial
        if not close(sheet_base, ref_base[cls]):
            mismatches.append(f"{cls} Base: sheet={sheet_base} ref={ref_base[cls]:.2f}")
        if not close(sheet_adv, ref_adv[cls]):
            mismatches.append(f"{cls} Adversarial: sheet={sheet_adv} ref={ref_adv[cls]:.2f}")

    total_base = ws.cell(row=26, column=3).value
    total_adv = ws.cell(row=27, column=3).value
    ok = (
        not mismatches
        and close(total_base, base_proceeds, tol=1e-6)
        and close(total_adv, adv_proceeds, tol=1e-6)
        and not base_as_converted   # low exit value: preference stack should bind
        and adv_as_converted        # high exit value: as-converted should bind
    )
    detail = (
        f"{len(mismatches)} class-payout mismatches"
        + (f" (first: {mismatches[0]})" if mismatches else "")
        + f" | Base (pref-stack expected): distributed={total_base}, proceeds={base_proceeds} | "
        f"Adversarial (as-converted expected): distributed={total_adv}, proceeds={adv_proceeds} | "
        f"regime Base=as-converted:{base_as_converted} Adv=as-converted:{adv_as_converted}"
    )
    return "VC: exit waterfall conservation (full cap-table liquidation preference cascade)", ok, detail


# ---------------------------------------------------------------------
# BASE archetype: integrated income statement and cash-flow linkage.
# ---------------------------------------------------------------------
def check_base_archetype_integration():
    path = os.path.join(REPO_ROOT, "01_Investment_Banking", "_template_BASE.xlsx")
    growth = [0.10, 0.09, 0.08, 0.07, 0.06]
    gross_margin = 0.60
    opex_percent = 0.25
    tax_rate = 0.25
    da_percent = 0.80
    capex_percent = 0.05
    shares = 100
    initial_revenue = 1000.0
    initial_interest = 20.0

    def populate(workbook):
        assumptions = workbook["Assumptions"]
        for index, rate in enumerate(growth):
            assumptions.cell(row=5, column=3 + index, value=rate)
        for column in range(3, 8):
            assumptions.cell(row=6, column=column, value=gross_margin)
            assumptions.cell(row=7, column=column, value=opex_percent)
            assumptions.cell(row=8, column=column, value=tax_rate)
            assumptions.cell(row=9, column=column, value=da_percent)
            assumptions.cell(row=10, column=column, value=capex_percent)
            assumptions.cell(row=12, column=column, value=shares)
        income_statement = workbook["IS"]
        income_statement["E5"] = initial_revenue
        income_statement["E15"] = initial_interest

    workbook = with_recalc(path, populate)
    income_statement = workbook["IS"]
    sheet_revenue = [income_statement.cell(row=5, column=column).value for column in range(6, 10)]
    sheet_net_income = [
        income_statement.cell(row=18, column=column).value for column in range(6, 10)
    ]

    reference_revenue = []
    reference_net_income = []
    revenue = initial_revenue
    for growth_rate in growth[:4]:
        revenue *= 1 + growth_rate
        gross_profit = revenue * gross_margin
        ebitda = gross_profit - revenue * opex_percent
        depreciation = revenue * capex_percent * da_percent
        pretax_income = ebitda - depreciation - initial_interest
        net_income = pretax_income * (1 - tax_rate)
        reference_revenue.append(revenue)
        reference_net_income.append(net_income)

    ok = all(close(actual, expected) for actual, expected in zip(sheet_revenue, reference_revenue))
    ok = ok and all(
        close(actual, expected) for actual, expected in zip(sheet_net_income, reference_net_income)
    )
    cash_flow_net_income = [
        workbook["CF"].cell(row=5, column=column).value for column in range(5, 8)
    ]
    ok = ok and all(
        close(actual, expected)
        for actual, expected in zip(cash_flow_net_income, sheet_net_income[:3])
    )
    detail = (
        f"revenue sheet={sheet_revenue}, oracle={reference_revenue}; "
        f"net income sheet={sheet_net_income}, oracle={reference_net_income}; "
        f"cash-flow linked net income={cash_flow_net_income}"
    )
    return "BASE: projected income statement and cash-flow linkage", ok, detail


CHECKS = [
    check_black_scholes,
    check_bond_duration,
    check_lbo_sources_uses_and_debt_schedule,
    check_vc_waterfall_conservation,
    check_base_archetype_integration,
]


def main() -> int:
    print(f"Running {len(CHECKS)} independent-oracle verification checks...\n")
    all_ok = True
    for check in CHECKS:
        try:
            name, ok, detail = check()
        except Exception as error:  # noqa: BLE001 - report every regression coherently.
            name, ok, detail = check.__name__, False, f"raised {type(error).__name__}: {error}"
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"       {detail}\n")
        all_ok = all_ok and ok
    print("=" * 60)
    print("ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
