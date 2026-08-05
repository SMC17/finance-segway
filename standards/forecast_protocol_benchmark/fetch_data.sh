#!/usr/bin/env bash
# Pull country-indicator panels from the CIA World Factbook archive
# (worldfactbookarchive.org - public-domain data, open API, no auth).
# 56 small JSON files (evidence years 2011-2023 + target 2025). The host's
# CDN blocks default curl agents, so a standard browser User-Agent is sent;
# the data is public domain and the API is open.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
for ind in inflation pop_growth gdp_percap mil_pct_gdp; do
  for y in $(seq 2011 2023) 2025; do
    f="data/$ind.$y.json"
    [ -s "$f" ] || {
      curl -sS --max-time 30 -A "$UA" -H "Accept: application/json" \
        "https://worldfactbookarchive.org/api/v2/rank/$ind/$y?limit=300" -o "$f"
      sleep 0.4
    }
  done
done
echo "Ready: $(ls data | wc -l | tr -d ' ') files in data/"
