# Thesis — public_ares_capital_2024 (refreshed FY2025)

## Classification

**real_public** reference instance (portfolio-level BDC proxy). Written by
`tools/agents/private_credit_underwrite.py --use-ares-fixture` against the
FY2025 10-K companyfacts extract; classified `agent_tool_draft` /
`counts_toward_M4: false` in its manifest until human review (Issue #7).

## Why this case

Ares Capital Corporation (ARCC, CIK 0001287750) is a large publicly
reporting BDC. Its SEC filings provide redistributable portfolio and
balance-sheet facts suitable for:

- exercising the Private Credit archetype engines (debt schedule, interest,
  leverage context) against real numbers;
- proving the L2 EDGAR → provenance → governed-instance wiring end to end;
- training the `private_credit_underwrite` agent path on a real filer
  before it is pointed at a discrete single-borrower credit agreement.

This is **not** a single-borrower unitranche commitment memo. CFADS and
facility pricing for a specific private borrower remain modeler-owned
until a discrete credit agreement is sourced. Only two Assumptions rows
are overridden with real EDGAR facts (`Opening gross debt`, `Opening
cash`); every covenant-driving assumption (revenue, EBITDA margin, spread,
leverage/DSCR limits) is left at the template default because ARCC's
public filings report portfolio-level investment income, not a
single-credit CFADS build, and this tool refuses to invent an unsourced
mapping.

## Refresh (2026-08-05)

- Source: SEC companyfacts prefer-annual → FY2025 10-K (ended 2025-12-31).
- Opening gross debt (proxy) = **$15,991 m** (LongTermDebt).
- Opening cash = **$638 m**.
- Checks Overall remains **REVIEW** (5 covenant breaches vs template default
  revenue/EBITDA) — expected and documented for a portfolio-proxy instance.

## Sources

- Domain register: `05_Private_Credit/sources/source_register.csv`
  (`credit-public-ares-capital-2025-companyfacts` row)
- EDGAR companyfacts extract: `tools/data_fabric/out/ARCC_facts_selected.json`
- Instance manifest / receipt:
  `instances/public_ares_capital_2024.manifest.json`,
  `instances/public_ares_capital_2024.receipt.json`

## Limitations

- Portfolio aggregate ≠ single-credit underwriting.
- Revenue, EBITDA margin, and all covenant thresholds remain template
  defaults, not ARCC-specific — do not read Checks status as a comment on
  ARCC's actual creditworthiness.
- Not decision-grade and not counted toward M4 evidence until an
  independent human reviewer promotes it past `agent_tool_draft`
  (Issue #7).

## Regenerate

```bash
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --prefer-annual
PYTHONPATH=. python tools/agents/private_credit_underwrite.py --use-ares-fixture
```
