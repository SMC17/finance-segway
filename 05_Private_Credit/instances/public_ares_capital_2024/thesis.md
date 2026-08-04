# Thesis — public_ares_capital_2024

## Classification

**real_public** reference instance (portfolio-level BDC proxy).

## Why this case

Ares Capital Corporation (ARCC, CIK 0001287750) is a large publicly reporting BDC. Its SEC filings provide redistributable portfolio and balance-sheet facts suitable for:

- Exercising the Private Credit archetype engines (debt schedule, interest, leverage context)
- Proving L2 EDGAR → provenance → instance wiring
- Training the `private_credit_underwrite` agent path on real numbers

This is **not** a single-borrower unitranche commitment memo. CFADS and facility pricing for a specific private borrower remain modeler-owned until a discrete credit agreement is sourced.

## Decision outputs expected from the archetype

- Debt / leverage context from public LongTermDebt and Assets
- Interest load from disclosed InterestExpense
- Recovery / LGD and covenant headroom only after underwriter assumptions are explicitly entered and labeled

## Sources

- Domain register: `05_Private_Credit/sources/source_register.csv` (Ares 10-K / 10-Q rows)
- EDGAR companyfacts extract: `tools/data_fabric/out/ARCC_facts_selected.json`
- Instance register: `instances/public_ares_capital_2024/sources/source_register.csv`

## Limitations

- Portfolio aggregate ≠ single-credit underwriting
- Placeholder CFADS / spread must be replaced before any client use
- Checks status starts as NOT_RUN until LibreOffice recalc + domain contracts pass
