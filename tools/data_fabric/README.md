# Data Fabric (L2)

Connectors and provenance helpers that pull **public** data and emit structured
facts plus `source_register`-compatible rows for governed workbooks.

| Script | Purpose | Status |
|--------|---------|--------|
| `edgar_company_facts.py` | SEC companyfacts (XBRL) → selected US-GAAP + DEI values + provenance CSV. Ticker→CIK resolution via company_tickers.json. Prefer-annual option. | Production-ready seed (expanded concepts) |
| `treasury_public_facts.py` | U.S. Treasury daily par yield curve / bill / long-term / real (TIPS) rates → dated CSV export (home.treasury.gov; not on the FiscalData REST API) + provenance CSV. | Production-ready |
| `damodaran_public_facts.py` | Aswath Damodaran (NYU Stern) industry cost-of-capital/beta/margin/multiples datasets + global country equity risk premiums. `.xls` via `xlrd`, `.xlsx` via `openpyxl`. | Production-ready |
| `hvpe_public_facts.py` | HarbourVest Global Private Equity (HVPE) public NAV / portfolio disclosures. Provenance recorder for monthly factsheets & annual reports. | Skeleton + recorder |
| `fca_open_data.py` | FCA published datasets (Product Sales Data, FIRDS, STS, ratings, NSM pointers). Provenance recorder for aggregates and reference extracts. | Skeleton + recorder |
| `edgar_bulk_export.py` | Every EDGAR quarterly master index from 1993 Q1, plus the `submissions.zip` and `companyfacts.zip` bulk archives, to `.sec-export/` (git-ignored, ~3.4 GB). The committed manifest `out/edgar_export/manifest.json` records each file's SHA-256. | Production-ready |
| `edgar_corporate_events.py` | Corporate lineage for every company that ever filed a periodic report: renames, 8-K Item 1.03 bankruptcies, Form 15/25 exits, business-combination pairings (observed), and merger direction and exit reasons (derived, by stated rules). Writes `out/edgar_lineage/`. | Production-ready |
| `edgar_lineage_page_data.py` | Packs `out/edgar_lineage/` into the single JSON the interactive lineage page loads. Adds no values. | Production-ready |

## Daily ingest

`tools/sec_daily_ingest.py` reads one business day's EDGAR master index, logs
it to `out/edgar_daily/<year>/<date>.json`, re-pulls company facts for every
tracked company that filed a periodic report, and lists the public cases whose
subject appeared on a material filing. It never rewrites a case: every case is
pinned to a historical as-of date. `.github/workflows/sec-daily-ingest.yml`
runs it Tuesday to Saturday, rebuilds the lineage dataset on Sundays, and opens
a pull request for review instead of pushing to `main`. It needs the
`SEC_USER_AGENT` repository secret.

## Rules

- Every automated or recorded fact must land with as-of, retrieval date, transformation, and snapshot pointer.
- Do not commit paywalled, confidential, or proprietary LP/deal data.
- Domain builders remain the calculation engine; this layer only supplies inputs and provenance.
- Prefer official publisher pages (SEC, hvpe.com / LSE RNS, fca.org.uk / data.fca.org.uk).

## Quick examples

```bash
# SEC – resolve CIK automatically and prefer annual facts
python tools/data_fabric/edgar_company_facts.py --ticker AAPL --prefer-annual
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750

# Treasury – daily par yield curve, one dated row or the full year
python tools/data_fabric/treasury_public_facts.py --year 2026 --as-of 2026-08-17
python tools/data_fabric/treasury_public_facts.py --year 2026 --type daily_treasury_bill_rates

# Damodaran – industry cost of capital / multiples, and country risk premiums
python tools/data_fabric/damodaran_public_facts.py --dataset wacc --industry "Software (Internet)"
python tools/data_fabric/damodaran_public_facts.py --dataset pedata
python tools/data_fabric/damodaran_public_facts.py --dataset ctryprem --country "United States"

# HVPE – emit demo provenance template (then replace with real extracted numbers)
python tools/data_fabric/hvpe_public_facts.py --demo

# FCA – emit demo PSD-style provenance template
python tools/data_fabric/fca_open_data.py --demo
```

Attach the generated `*_source_register.csv` rows into the relevant domain or
instance `sources/source_register.csv`. Keep the JSON snapshot under
`tools/data_fabric/out/` or promote a copy into the domain `sources/snapshots/`
tree when promoting an instance.

## Sector mapping

See `standards/data_sources_sector_map.md` for the domain-by-domain mapping of
SEC/EDGAR, HVPE, FCA and selected academic / research-group resources.
