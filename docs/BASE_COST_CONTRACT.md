# BASE model cost and historical-input contract

The BASE income statement accepts reported cost of revenue and reported
operating expense. Both may already contain depreciation. EBIT is gross profit
less reported operating expense. EBITDA adds total D&A back once. The model
makes no invented allocation of D&A between cost of revenue and operating
expense. Tesla's vendor addback includes impairment, so its EBITDA is a proxy
rather than pure EBITDA; this scope limitation remains explicit. The Tesla generator now uses the same reported-cost basis as Microsoft.

Historical template cells derive subtotals by default. Microsoft's source
manifest explicitly replaces selected historical subtotals with disclosed
actuals using `allow_formula_override`. These observations retain provenance
and remain literal values that the base-year probe can independently compare
with the forecast chain. No forecast cell receives this override. The coverage
scanner counts a valid sourced formula replacement in both the case-specific
input denominator and numerator; it still reports unknown sheets and arbitrary
non-input coordinates as anomalies.

The forward model remains simplified. Microsoft's pre-tax chain omits other
income and expense. Its pre-tax, tax and net-income differences remain explicitly
declared; forward shares model repurchases. EPS inherits those assumptions.
Tesla uses a declared forward tax rate rather than its negative historical
effective rate, and forward shares include the offering and contingent
securities. The base-year manifests record these design differences. EBIT is
not exempt from reproduction. These declarations do not excuse an uncomputable
line, certify a forecast or provide human model validation.

Corporate and equity dashboards now include real forecast-base, discount/growth
and DCF computability checks. A discount rate below terminal growth causes an
overall BREACH. The corporate dashboard also marks absent peer multiples for
review. The new tests recalculate scratch workbooks and check those failures,
not just the presence of a reference in the dependency graph.

The seven raw historical input rows yield 21 entry cells across C:E. C6 states
that prior-year growth is unavailable, rather than presenting another empty
source input. Formula cells keep their formula styling. The earlier expectation
of at least 40 historical raw inputs belonged to a different template schema.

Regenerate templates from builders. Recalculate instances or scratch copies,
then update their receipts to bind the exact bytes. Do not recalculate the
committed templates. Known share-series defects and unverified standards
requirements remain visible in their respective reports. M3 and human sign-off
remain unchanged.
