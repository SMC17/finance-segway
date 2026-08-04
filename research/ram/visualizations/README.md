# Real-universe research visualizations

`build_universe_viz.py` renders a reviewed, source-receipted RAM data release.
It has no generated-data fallback and fails closed when the receipt or artifact
hashes do not match.

```bash
python research/ram/fetch_real_universe.py --as-of YYYY-MM-DD
python research/ram/build_universe_viz.py --as-of YYYY-MM-DD
```

Generated workbooks are research tools, not governed decision models, and do
not receive an M0–M4 claim. Review source licensing before committing raw or
derived observations.
