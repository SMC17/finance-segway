# Correctness integration: reviewer packet

PR: https://github.com/SMC17/finance-segway/pull/125

This packet supports independent challenge. It is prepared by the contributor,
not an independent approval. No human sign-off or M3/use validation is asserted.
The code/artifact revision freshly checked is
`aacbebdcddd47e779040d601360f215d1db02409`; this packet adds documentation only.
Approve the current PR head, not an earlier revision, after your review.

## What changed for a model reader

The integration preserves the six source proposals (#114, #116, #119, #121,
#123, #124) and their authorship. It reconciles their overlapping changes:

- Reported operating costs already include depreciation/amortization. Charge
  those costs once in EBIT and add D&A back once for EBITDA. The case emitters,
  template formulas and reference calculation now use the same contract.
- Historical actuals explicitly overlay the base year. Forward assumptions
  remain distinct from observed and arithmetically derived inputs.
- Input-cell discovery includes previously missed positions; coverage must
  reflect those inputs rather than silently treating them as sourced.
- Corporate/equity checks read their relevant decisions. Source-sheet
  reachability detects disconnected verdicts, but does not prove the checks
  themselves are economically sufficient.

## Fresh reproducibility record

Checks ran from an archive of the exact revision above. Logs and reports were
kept outside the source tree so they could not contaminate vocabulary scans.
Python 3.12.13; LibreOffice Calc 26.8.2; macOS ARM64.

| Gate | Result |
| --- | --- |
| Whole suite with ResourceWarning treated as error | 596 tests pass |
| Regenerate templates; semantic and presentation parity | 27/27 each |
| Workbook reference calculations | All nine checks pass after actual recalculation |
| Data conventions and controlled vocabulary | Pass |
| Share-series integrity | Gate passes with existing warnings retained |
| Standards conformance | Gate passes with unverified standards disclosed |
| Forecast registration | Pass |

Run from a clean source tree with dependencies and Calc available:

```sh
python -W error::ResourceWarning -m unittest discover -s tests -q
python tools/build_all_models.py
python tools/verify_reference_calcs.py
python tools/verify_data_conventions.py
python tools/verify_controlled_vocabulary.py
python tools/verify_share_series_integrity.py
python tools/verify_standards_conformance.py
python tools/forecast_registration.py --check
```

Never recalculate a committed template in place. The reference tool copies
before recalculating. Existing source-reachability, base-year reproduction,
receipt and committed-result evidence is additional context, not a substitute
for the review questions below.

## Independent challenge requested

1. Trace a reported-cost case from its filing/fact record through its manifest
   into COGS/operating costs, EBIT, EBITDA and cash flow. Confirm D&A is neither
   double charged nor silently excluded. Assess the declared Tesla
   impairment-inclusive EBITDA proxy as a limitation, not pure reported D&A.
2. Inspect a historical overlay and a forward driver side by side. Check the
   as-of cutoff, units, periods, source digest and observed/derived/assumption
   classification. A plausible unsourced value must remain a declared driver
   with no coverage credit.
3. Challenge coverage discovery with an input outside the old scanned area.
   Confirm the lower honest coverage is retained rather than hidden.
4. Mutate a sourced assumption in a scratch copy, recalculate, and verify the
   relevant corporate/equity decision changes or fails as intended. Reachable
   sheets alone do not establish an effective decision gate.
5. Review BASE historical reproduction exceptions, forward tax/share
   assumptions and split-basis warnings. Do not infer a coherent per-share
   series from adjacent restated observations.
6. Inspect the difference between a committed cached result and a recalculated
   scratch result. Verify exact-byte receipts against the intended artifact;
   cached nonempty values alone do not establish correctness.

## Residuals to accept, narrow or reject explicitly

- The declared Tesla impairment-inclusive proxy remains an analytical scope
  choice requiring review; passing arithmetic does not make it reported EBITDA.
- Share-series warnings and unverified standards remain visible. A passing
  gate is not certification of every historical observation or external standard.
- Synthetic oracle scenarios check mechanics. They do not establish source
  completeness, forecast accuracy, suitability for financial use or external
  validation.
- Formula source reachability cannot detect a stale hard-coded copy, prove
  an economic criterion is adequate, or validate every sensitivity table.
- Hosted execution is outside this packet's evidence. Human review remains
  required independently of any build-job availability.

## How to record a real review

Submit APPROVED or CHANGES_REQUESTED against the current head with findings,
sources checked and accepted limitations. The workflow requires a reviewer
other than the PR author and an approval of that exact head. Do not write
`governance/signoff.json`, mark a model M3, or describe it as validated for use
as part of this engineering PR. The separate named-person sign-off is retained.
