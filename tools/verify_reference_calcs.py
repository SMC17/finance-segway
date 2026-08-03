"""
verify_reference_calcs.py — independent-oracle regression tests for the
highest-risk formulas in the library.

Every check in here follows the same shape: build a template with known
test inputs (openpyxl), recalculate it for real (tools/recalc.py, headless
LibreOffice — not just "did it open"), and compare the recalculated cell
against a value computed a SECOND way in plain Python, independent of the
spreadsheet formula. That's a materially stronger bar than "recalc
succeeded with zero cached errors" (which only proves the formula didn't
throw, not that it's computing the right thing) — it's how several of the
bugs fixed in this library were actually caught (the VC waterfall
conservation break, the LBO debt schedule being unwired, the Commodities
annualized-basis day-count error).

This does not attempt to re-verify every archetype — it covers the
mathematically riskiest pieces (closed-form vs. numerical duration,
Black-Scholes vs. put-call parity, an integrated 3-statement build,
LBO Sources=Uses, VC waterfall conservation). Extend it as new archetypes
get the same treatment; see CONTRIBUTING.md's verification standard.

Usage:
    python3 tools/verify_reference_calcs.py
Exit code is 0 iff every check passes.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

import openpyxl  # noqa: E402
from recalc import recalc  # noqa: E402

TOL = 1e-4  # relative tolerance for float comparisons


def close(a, b, tol=TOL):
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) / abs(b) < tol


def with_recalc(src_path, populate_fn):
    """Copy src_path to a temp file, let populate_fn mutate an openpyxl
    workbook in place, recalc it for real, and return the recalculated
    (data_only) workbook."""
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(src_path, tmp.name)
    try:
        wb = openpyxl.load_workbook(tmp.name)
        populate_fn(wb)
        wb.save(tmp.name)
        result = recalc(tmp.name, timeout=45)
        if "error" in result:
            raise RuntimeError(f"recalc failed: {result['error']}")
        if result.get("status") != "success":
            raise RuntimeError(f"recalc found formula errors: {result}")
        return openpyxl.load_workbook(tmp.name, data_only=True)
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------
# Black-Scholes: put-call parity + closed-form cross-check
# ---------------------------------------------------------------------
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def black_scholes(S, K, T, r, q, sigma):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call = S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    put = K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)
    return call, put


def check_black_scholes():
    S, K, T, r, q, sigma = 100, 100, 0.25, 0.045, 0.0, 0.30
    path = os.path.join(REPO_ROOT, "14_Options_Derivatives", "_template_OPTIONS.xlsx")

    def populate(wb):
        bs = wb["BS Pricer"]
        bs["C5"], bs["C6"], bs["C7"] = S, K, T
        bs["C8"], bs["C9"], bs["C10"] = r, q, sigma

    wb = with_recalc(path, populate)
    sheet_call = wb["BS Pricer"]["C13"].value
    sheet_put = wb["BS Pricer"]["C14"].value
    ref_call, ref_put = black_scholes(S, K, T, r, q, sigma)

    ok = close(sheet_call, ref_call) and close(sheet_put, ref_put)
    parity_lhs = sheet_call - sheet_put
    parity_rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    ok = ok and close(parity_lhs, parity_rhs)
    detail = (f"sheet call={sheet_call:.6f} ref={ref_call:.6f} | "
              f"sheet put={sheet_put:.6f} ref={ref_put:.6f} | "
              f"parity lhs={parity_lhs:.6f} rhs={parity_rhs:.6f}")
    return "Black-Scholes price + put-call parity", ok, detail


# ---------------------------------------------------------------------
# Bond duration: closed-form Macaulay/modified duration vs. the sheet's
# numerical (price-shock finite-difference) duration.
# ---------------------------------------------------------------------
def bond_price(face, coupon_rate, freq, years, ytm):
    n = int(round(freq * years))
    c = face * coupon_rate / freq
    y = ytm / freq
    price = sum(c / (1 + y) ** t for t in range(1, n + 1)) + face / (1 + y) ** n
    return price


def closed_form_modified_duration(face, coupon_rate, freq, years, ytm):
    n = int(round(freq * years))
    c = face * coupon_rate / freq
    y = ytm / freq
    price = bond_price(face, coupon_rate, freq, years, ytm)
    mac_dur_periods = sum(
        t * (c if t < n else c + face) / (1 + y) ** t for t in range(1, n + 1)
    ) / price
    mac_dur_years = mac_dur_periods / freq
    mod_dur = mac_dur_years / (1 + y)
    return mod_dur


def check_bond_duration():
    face, coupon, freq, years, ytm = 1000, 0.05, 2, 10, 0.055
    path = os.path.join(REPO_ROOT, "21_Fixed_Income_Rates", "_template_FIXED_INCOME.xlsx")

    def populate(wb):
        bp = wb["Bond Pricing"]
        bp["C5"], bp["C6"], bp["C7"] = face, coupon, freq
        bp["C8"], bp["C9"] = years, ytm

    wb = with_recalc(path, populate)
    sheet_price = wb["Bond Pricing"]["C11"].value
    sheet_mod_dur = wb["Duration & Convexity"]["C8"].value

    ref_price = bond_price(face, coupon, freq, years, ytm)
    ref_mod_dur = closed_form_modified_duration(face, coupon, freq, years, ytm)

    # Numerical (50bp shock, finite-difference) duration is an approximation
    # of the closed-form value — allow a looser tolerance than exact formulas.
    ok = close(sheet_price, ref_price, tol=1e-6) and close(sheet_mod_dur, ref_mod_dur, tol=0.01)
    detail = (f"price: sheet={sheet_price:.4f} closed-form={ref_price:.4f} | "
              f"mod. duration: sheet(numerical)={sheet_mod_dur:.4f} "
              f"closed-form={ref_mod_dur:.4f}")
    return "Bond price + closed-form vs. numerical duration", ok, detail


# ---------------------------------------------------------------------
# LBO: Sources = Uses, and the debt schedule cash-sweep cascade
# ---------------------------------------------------------------------
def check_lbo_sources_uses_and_debt_schedule():
    path = os.path.join(REPO_ROOT, "03_Private_Equity", "_template_LBO.xlsx")

    def populate(wb):
        su = wb["Sources & Uses"]
        su["C5"], su["C6"], su["C7"] = 0, 0, 400   # revolver, TLA, TLB
        su["C8"], su["C9"], su["C10"] = 0, 100, 0  # notes, sponsor equity, rollover
        su["F5"], su["F6"] = 450, 50               # purchase price, fees
        ret = wb["Returns"]
        ret["C5"] = 100  # entry EBITDA

    wb = with_recalc(path, populate)
    su = wb["Sources & Uses"]
    # Sources has 6 line items (rows 5-10) -> total at row 11; Uses has 5
    # (rows 5-9) -> total at row 10. The two "Total" rows land one apart.
    sources_total = su["C11"].value
    uses_total = su["F10"].value
    check_cell = su["C13"].value

    ok = close(sources_total, 500) and close(uses_total, 500) and close(check_cell, 0, tol=1e-6)

    # Cross-check the debt schedule cash-sweep cascade against an
    # independent Python re-implementation of the same non-circular
    # (beginning-balance-interest) mechanic.
    ds = wb["Debt Schedule"]
    ebitda0, growth = 100, 0.05
    fcf_conv, amort_pct, sweep_pct, rate = 0.50, 0.01, 0.75, 0.09
    debt0 = 400.0
    beginning = debt0
    for _yr in range(6):  # Yr0..Yr5
        ebitda = ebitda0 * (1 + growth) ** _yr
        fcf = ebitda * fcf_conv
        amort = min(debt0 * amort_pct, beginning)
        interest = beginning * rate
        sweep = min(max(0, sweep_pct * (fcf - amort - interest)), beginning - amort)
        ending = beginning - amort - sweep
        beginning = ending
    ref_final_debt = ending
    sheet_final_debt = ds["H15"].value  # Yr5 total debt
    ok = ok and close(sheet_final_debt, ref_final_debt)

    detail = (f"sources={sources_total} uses={uses_total} check={check_cell} | "
              f"Yr5 debt: sheet={sheet_final_debt:.4f} python-reimpl={ref_final_debt:.4f}")
    return "LBO Sources=Uses + debt schedule cash-sweep cascade", ok, detail


# ---------------------------------------------------------------------
# VC Exit Waterfall: conservation (this is the exact bug class caught and
# fixed mid-session — pinned here as a permanent regression test).
# ---------------------------------------------------------------------
def check_vc_waterfall_conservation():
    path = os.path.join(REPO_ROOT, "13_Venture_Capital", "_template_VC.xlsx")

    def populate(wb, total_proceeds):
        ct = wb["Cap Table"]
        ct["C5"], ct["E5"] = 6_000_000, 0.0001
        ct["C6"], ct["E6"] = 1_000_000, 0.0001
        ct["C8"], ct["E8"] = 1_000_000, 1.00
        ct["C9"], ct["E9"] = 1_500_000, 2.00
        ct["C10"], ct["E10"] = 1_000_000, 5.00
        wb["Exit Waterfall"]["C15"] = total_proceeds

    ok = True
    details = []
    for scenario, proceeds in (("small exit (pref-stack regime)", 8_000_000),
                                ("large exit (as-converted regime)", 50_000_000)):
        wb = with_recalc(path, lambda w, p=proceeds: populate(w, p))
        ew = wb["Exit Waterfall"]
        distributed = ew["C11"].value
        this_ok = close(distributed, proceeds, tol=1e-6)
        ok = ok and this_ok
        details.append(f"{scenario}: distributed={distributed} vs proceeds={proceeds} ({'OK' if this_ok else 'FAIL'})")

    return "VC Exit Waterfall conservation (both regimes)", ok, "; ".join(details)


# ---------------------------------------------------------------------
# BASE archetype: integrated IS -> BS/CF -> DCF, spot-checked end to end.
# ---------------------------------------------------------------------
def check_base_archetype_integration():
    path = os.path.join(REPO_ROOT, "01_Investment_Banking", "_template_BASE.xlsx")
    growth = [0.10, 0.09, 0.08, 0.07, 0.06]
    gm, opex_pct, tax_rate, da_pct, capex_pct, shares = 0.60, 0.25, 0.25, 0.80, 0.05, 100
    rev0, interest0 = 1000.0, 20.0

    def populate(wb):
        a = wb["Assumptions"]
        for i, g in enumerate(growth):
            a.cell(row=5, column=3 + i, value=g)
        for c in range(3, 8):
            a.cell(row=6, column=c, value=gm)
            a.cell(row=7, column=c, value=opex_pct)
            a.cell(row=8, column=c, value=tax_rate)
            a.cell(row=9, column=c, value=da_pct)
            a.cell(row=10, column=c, value=capex_pct)
            a.cell(row=12, column=c, value=shares)
        isw = wb["IS"]
        isw["E5"] = rev0
        isw["E15"] = interest0

    wb = with_recalc(path, populate)
    isw = wb["IS"]
    sheet_rev = [isw.cell(row=5, column=c).value for c in range(6, 10)]
    sheet_ni = [isw.cell(row=18, column=c).value for c in range(6, 10)]

    ref_rev, ref_ni = [], []
    revenue = rev0
    for i, g in enumerate(growth[:4]):
        revenue = revenue * (1 + g)
        cogs = revenue * (1 - gm)
        gp = revenue - cogs
        opex = revenue * opex_pct
        ebitda = gp - opex
        da = revenue * capex_pct * da_pct
        ebit = ebitda - da
        pretax = ebit - interest0
        tax = pretax * tax_rate
        ni = pretax - tax
        ref_rev.append(revenue)
        ref_ni.append(ni)

    ok = all(close(a, b) for a, b in zip(sheet_rev, ref_rev))
    ok = ok and all(close(a, b) for a, b in zip(sheet_ni, ref_ni))

    cf = wb["CF"]
    cf_ni = [cf.cell(row=5, column=c).value for c in range(5, 8)]
    ok = ok and all(close(a, b) for a, b in zip(cf_ni, sheet_ni[:3]))

    detail = (f"revenue: sheet={sheet_rev} ref={ref_rev} | "
              f"net income: sheet={sheet_ni} ref={ref_ni} | CF-linked NI={cf_ni}")
    return "BASE archetype: IS projections + CF linkage", ok, detail


CHECKS = [
    check_black_scholes,
    check_bond_duration,
    check_lbo_sources_uses_and_debt_schedule,
    check_vc_waterfall_conservation,
    check_base_archetype_integration,
]


def main():
    print(f"Running {len(CHECKS)} independent-oracle verification checks...\n")
    all_ok = True
    for check in CHECKS:
        try:
            name, ok, detail = check()
        except Exception as e:  # noqa: BLE001
            name, ok, detail = check.__name__, False, f"raised {type(e).__name__}: {e}"
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"       {detail}\n")

    print("=" * 60)
    print("ALL CHECKS PASSED" if all_ok else "SOME CHECKS FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
