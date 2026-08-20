# April 2020 WTI Storyline

One public historical case, as a journalist would open it: an annotated line of
official EIA Cushing spot prices, with cards that cite the hashed Excel cells.

Open `index.html` in a browser. No Excel, pip, LibreOffice, Google Sheet, or
terminal license. Rebuild and check:

```bash
python3 tools/build_wti_storyline.py --check
python3 -m unittest tests.test_wti_storyline -v
```

## What the line is

Pinned extract of EIA series **RWTC** — Cushing, OK WTI Spot Price FOB,
https://www.eia.gov/dnav/pet/hist/RWTCD.htm — captured 2026-08-20, window
2020-01-06 through 2020-07-15. Bytes: `series.csv` / `source_weeks.json`.
SHA-256 values live in `provenance.json`.

Spot is **not** the NYMEX May 2020 futures settlement. On 20 Apr 2020 this
series prints **-$36.98**. The hashed model cell `Hedging!C7` is **-$37.63**
(EIA-cited May contract settlement). EIA prose also records an intradaily low
of **-$40.32**. All three are labeled; only -$36.98 is plotted.

## What the hash is

The public-case receipt at
`15_Commodities/instances/public_wti_april_2020.receipt.json` fingerprints the
workbook and the four sourced cells. Matching bytes are not a correct model,
not a trading signal, and not M4.

## This is not

A live hedge, price target, Bloomberg replacement, or new domain. Classification:
`external_historical_case_visual`. `counts_toward_M4: false`.
