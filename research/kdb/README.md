# kdb+/q research rail

This optional rail is reserved for public, licensed, source-addressed market
observations and controlled empirical exports. It does not underwrite deals,
replace Excel archetypes, or inherit an M-maturity claim.

## Rules

1. Repository examples must use real public observations with dated provenance.
2. Vendor-restricted data stays outside the repository.
3. No generated or synthetic market dataset is an acceptable fallback.
4. Every export that influences a governed model must satisfy
   `INTEGRATION_CONTRACTS.md` and enter the consuming domain's source register.
5. The schema may exist before data does; an empty, honest rail is preferable to
   fabricated empirical evidence.

`schema/market.q` defines the initial empty table shapes. The next admissible
implementation is a loader for a named public source with a frozen snapshot,
checksum, usage terms, and an independently checked transformation.
