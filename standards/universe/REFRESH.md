# The quarterly refresh — one command, every layer

Once a quarter (after 10-Q/10-K season settles, and any week the index
reconstitutes), the whole data layer refreshes with:

```bash
python tools/quarterly_refresh.py            # network side; --dry-run to preview
```

What it runs, in order, and why the order matters:

| step | what | why this order |
|---|---|---|
| facts | full `--all-sectors` re-fetch (annual series, all concepts) | refresh means overwrite; `--skip-existing` is the RESUME primitive, not refresh |
| exhibits | earnings materials, `--skip-existing` | frozen filings never change; only new quarters add |
| nport + check | the regulator's portfolio + cross-check vs taxonomy | a new N-PORT lands each quarter - the second source keeps the vendor honest |
| classification | SIC re-harvest | constituents may have churned; new names need codes |
| taxonomy + validate | regenerate + gate | generator-first: hand-edits die on regeneration by design |
| coverage | the dispatch manifest, written to `standards/universe/coverage_report.json` | the swarm's work queue reflects the fresh state |
| registry check + due | content and time gates | `--due` turns red the week a forecast window expires |

Any step failing **stops the run with the step named** - a half-refreshed
depot must not look finished.

## Resolving the fast windows

When `--due` lists a UST-10Y window, resolution is deliberate and evidenced:

```bash
python tools/resolve_from_fred.py --forecast-id rates-ust10y-eom-2026-09          # read-only: shows realized value + source
python tools/resolve_from_fred.py --forecast-id rates-ust10y-eom-2026-09 --commit # records it via the registry's own --resolve
```

The helper refuses months that haven't closed and forecasts already
resolved; the registry re-validates everything it writes.

## After the refresh

Review the diff like any PR: the cross-check report names constituent
churn and weight moves; the coverage report names new gaps; the taxonomy
validator fails loudly if classification drifted from the issuer's
disclosed partition. Commit when green.
