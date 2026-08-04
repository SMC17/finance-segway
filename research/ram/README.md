# RAM risk rail

RAM means Risk & Asset Management: hand-rolled in-memory covariance, factor,
stress, and allocation engines. Scaling is allowed only after explicit gates in
`STAGE_GATES.md`.

## Current state

- `simple_covariance.py` is a Stage-0 numerical engine skeleton capped at ten
  names.
- `test_simple_covariance.py` uses small deterministic mathematical vectors to
  test identities and failure modes.
- No empirical universe, dataset, benchmark result, or visualization is claimed.
- No RAM artifact has M-maturity or operational evidence status.

The next step is not generated data. It is a source-addressed public historical
sample with a frozen snapshot, checksum, methodology, and reviewable outcome.

## Boundaries

- Numerical test vectors are tests only, never business evidence.
- No replacement of `09_Risk_Management`.
- No S&P 100/500 or performance claim before the corresponding gate passes.
- No external acceleration dependency until the pure implementation is the
  verified reference.
