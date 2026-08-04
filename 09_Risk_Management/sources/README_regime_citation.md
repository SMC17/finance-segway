# Citing the research regime export from a governed domain

This folder contains an **example** of how a governed archetype (here Risk Management) can cite the real regime summary produced by the kdb/research rail.

## Rules

1. The regime CSV is **not** a substitute for the domain’s own engines. It is an empirical prior / scenario input.
2. Every material use must appear as a row in a source register (see `source_register_regime_example.csv`).
3. Prefer the snapshot path (`research/kdb/exports/regime_summary_YYYYMMDD.csv`) over a live URL.
4. RefreshLog must record when regime inputs change and whether decision outputs moved.
5. Research-rail numbers never write maturity claims into `standards/model_inventory.json`.

## How to use in an instance

- Copy the pattern into the instance’s own `sources/source_register.csv`.
- Point `checksum_or_snapshot` at the exact export file used.
- On the model’s Sources or Assumptions sheet, reference the metric names (`realized_vol_1y_avg`, etc.) and the as-of date.

This is the L1↔research integration pattern required by `docs/MULTI_RAIL_ARCHITECTURE.md` and `docs/AI_NATIVE_GOLDMAN_ROADMAP.md`.
