# Forecast registry — the M4 clock

Every outcome row elsewhere in this repository was written knowing the answer.
That is honest evidence of model *mechanics* (and is labeled as such), but it
can never demonstrate forward accuracy: M4 requires evidence generated over
time, and hindsight cannot be backfilled. This directory is where forward
evidence accumulates.

## The contract

One JSON file per forecast, managed exclusively by
`tools/forecast_registration.py`:

1. **Register before the outcome exists.** A record is registered by stamping
   `registration_sha256` — a content hash of the registration payload
   (forecast id, case, metric, point, interval, basis, baseline, dates).
   Git history dates the commit; the hash makes any later edit to a
   registered field detectable. Registrations are immutable; resolutions are
   final.
2. **Declare the baseline you claim to beat.** Every registration freezes a
   naive baseline value (last recorded value or random walk) taken from data
   already in this repository, with its source named. At resolution the
   headline score is Murphy skill: `1 − |forecast − realized| / |baseline −
   realized|`. Positive skill beats naive; a model that cannot beat the
   last-known value has no demonstrated forward edge, however small its raw
   error looks.
3. **Only out-of-sample forecasts live here.** `outcome_class` must be
   `out_of_sample_forecast`. Same-period reproduction checks and
   retrospective reconstructions belong in the domain outcome logs, where
   they are already labeled.

`--check` (wired into CI) validates every record: schema, date ordering
(no registration with an already-closed window, no future `registered_on`,
no same-day resolution), hash integrity, and — for resolved records — that
the committed scores equal what deterministic re-scoring of the registered
payload produces.

## Current registrations

The initial registrations are deliberately **baseline-only** (`basis:
naive_last_recorded` / `naive_random_walk`): mechanical forecasts derived
entirely from values already recorded in this repository, with no invented
intelligence. They start the clock and define the bar — every modeled
forecast registered after them has a skill target to beat, and the naive
records themselves resolve into the calibration record that M4 needs.

To register a modeled forecast: write the draft JSON with `basis: modeled`,
a declared baseline, and a future `resolve_by`, then run
`python tools/forecast_registration.py --register standards/forecasts/<f>.json`
and commit the stamped file. To resolve when the source publishes:
`python tools/forecast_registration.py --resolve <forecast_id> --realized <x>
--source "<document>"`.

## Agent workflow (the bridge)

An agent tool that has produced a forward number registers it in four lines -
the naive baseline is frozen automatically from the history it supplies, so
no forecast can enter unfalsifiable:

```python
from tools.forecast_registration import draft_registration, register

record = draft_registration(
    forecast_id="pc-acme-fy2027-revenue",
    case_id="acme_unitranche_2026", model_id="05", metric="revenue_usd_mm",
    point=112.0,                          # e.g. parsed from a statistician-protocol reply
    history=[("FY2025", 101.0), ("FY2026", 104.0)],   # from the instance workbook
    interval=[102.0, 121.0],              # optional: the Base/Downside scenario range
    resolve_by="2027-09-30",
    resolution_source_expected="Issuer FY2027 audited financials",
)
path = FORECAST_DIR / f"{record['forecast_id']}.json"
path.write_text(json.dumps(record, indent=2) + "\n")
register(path)                            # stamps the immutable content hash
```

On `interval`: the honest producer here is a scenario range already in the
workbook (Base/Downside), not LLM elicitation - elicited intervals are
unbenchmarked and must not be recorded as if they carried measured coverage.
