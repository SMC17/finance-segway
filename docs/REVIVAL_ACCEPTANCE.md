# Correctness integration — 11 November 2026

This branch integrates the existing work in PRs #114, #116, #119, #121, #123
and #124, preserving their commits and credit to Alex Roessner. It resolves the
conflicts between historical-cell derivation, sourced actuals, input detection,
computed verdicts, the forecast registry and dataset metadata.

The integration also fixes a shared cost-basis defect: reported costs already
include D&A, so subtracting D&A again understated EBIT. Both case generators now
use reported operating expense, and EBITDA adds D&A back once. The independent
reference oracle uses the same explicit accounting contract and separately
checks the addback. See BASE_COST_CONTRACT.md. Tesla's vendor cash-flow addback
includes impairment, so its EBITDA line is explicitly described as a proxy.

## Executed checks

With Python dependencies from requirements.txt and LibreOffice Calc 26.8.2:

- 596 unit/integration tests pass, including real recalculations.
- All 27 models match generated semantic and presentation fingerprints.
- All nine independent-oracle checks pass after correcting the old oracle's
  duplicate D&A charge and adding an explicit EBITDA comparison.
- Microsoft and Tesla pass the base-year probe with recorded forward-design
  exceptions. Four BASE cases have no actuals and one has only its revenue
  anchor; they are reported as such and are not counted as reproductions.
- 54 public cases keep all sourced sheets within reach of the verdict.
  Reachability does not establish that every formula is correct.
- Computability, data conventions, controlled vocabulary, standards conformance,
  share-series integrity and forecast-registration checks pass their gates.
- The share-series report still warns about 153 recorded comparability breaks;
  conformance still lists five unverified standards requirements. These are
  visible limitations, not new certifications or invented data corrections.
- The Microsoft and Tesla generators reproduce their owned manifests and source
  snapshots byte-for-byte when repeated. Six BASE instances were regenerated
  and recalculated, and their receipts bind their exact workbook bytes.

The new fault tests show that a discount rate below terminal growth changes
both corporate and equity overall decisions to BREACH. Historical formula
overrides are restricted by the generator to sourced historical subtotals and
count in both sides of case coverage. Unknown-sheet and unsourced flags do not
silently gain coverage.

## Review boundary

Independent approval remains required under AGENTS.md. No model is promoted to
M3, no human sign-off is written, and this branch is not merged over a red
independent-approval check. The tests establish the stated engineering checks;
they do not approve the models for a financial decision. Hosted CI also remains
subject to the account billing restriction.
