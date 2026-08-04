# kdb+/q integration contracts

## Empirical scenario export

Required fields:

| Field | Requirement |
|---|---|
| `as_of_date` | Observation freeze date |
| `universe` | Unambiguous public universe identifier |
| `metric` | Versioned metric name |
| `value` | Empirical value |
| `methodology` | Code or documented transformation reference |
| `source_url` | Public or licensed source locator |
| `source_as_of` | Source publication/observation date |
| `source_checksum` | SHA-256 of the frozen admissible input |
| `license_note` | Redistribution and use constraint |

Missing provenance is a hard failure. A compliant export must also be recorded
in the consuming domain's `sources/source_register.csv` and, where permitted,
under `sources/snapshots/`.

## Outcome monitoring feed

An outcome record must identify the instrument or deal, prediction date,
outcome date, predicted metric/value, realized metric/value, residual, source,
and reviewer note. Records land under the governed domain's `outcomes/` tree;
the research rail never edits frozen workbooks directly.

## Prohibitions

- No generated or synthetic business observations.
- No silent substitution when a public source is unavailable.
- No M-maturity claims for the research rail.
- No direct write from a live stream into a committed public instance.
