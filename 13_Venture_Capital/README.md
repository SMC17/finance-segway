# 13 Venture Capital

**Canonical model:** `_template_VC.xlsx`

Cap table, round modeling, SAFE conversion, reserves, and an exhaustive
holder-by-holder liquidation-preference/conversion waterfall.

The waterfall enumerates all eight elections for Series B, Series A, and Seed,
selects a state with no profitable unilateral conversion change, and requires
every state to conserve exit proceeds. It supports unique-seniority,
non-participating preferred terms. Participating preferred, caps, and
unconverted SAFEs fail closed for a transaction-specific legal waterfall.

Source-addressed historical instances live in `instances/`; their receipts do
not confer M3/M4 status. Refresh selected cases with
`python tools/refresh_public_case.py <case-id>` after a governed builder change.
