# kdb+/q ↔ Finance-Segway Integration Contracts

## Contract 1 — Scenario / Regime Export

**Direction**: kdb+ → Governance rail  
**Purpose**: Supply empirical scenario sets and regime statistics that become inputs or stress cases inside governed archetypes.

Required fields for a compliant export:

| Field | Type | Notes |
|-------|------|-------|
| as_of_date | date | Freeze date of the statistics |
| universe | symbol | e.g. `sp500_liquid`, `hy_credit` |
| metric | symbol | e.g. `realized_vol_1y`, `recovery_multiple_p50` |
| value | float | |
| methodology | symbol | Short description or code reference |
| source_checksum | symbol | Optional but preferred |

The export must be registered in the consuming domain’s `sources/source_register.csv` and (where redistribution permits) accompanied by a snapshot under `sources/snapshots/`.

## Contract 2 — Outcome Monitoring Feed

**Direction**: kdb+ (or other realized-data store) → Governance rail  
**Purpose**: Provide realized outcomes that can be compared with prior model predictions for M3/M4 evidence.

Minimum fields:

- instrument / deal identifier
- prediction_date
- outcome_date
- predicted_value / metric
- realized_value / metric
- error or residual
- notes

These records land in the domain’s `outcomes/` tree or are summarized into the model card / validation record.

## Non-goals

- kdb+ will not become the calculation engine for any M-maturity model.
- Live tick streams will not be written directly into frozen public instances.
