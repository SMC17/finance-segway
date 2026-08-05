# Data Fabric (L2)

Connectors and provenance helpers that pull **public** data and emit structured
facts plus `source_register`-compatible rows for governed workbooks.

| Script | Purpose | Status |
|--------|---------|--------|
| `edgar_company_facts.py` | SEC companyfacts (XBRL) → selected US-GAAP + DEI values + provenance CSV. Ticker→CIK resolution via company_tickers.json. Prefer-annual option. | Production-ready seed (expanded concepts) |
| `hvpe_public_facts.py` | HarbourVest Global Private Equity (HVPE) public NAV / portfolio disclosures. Provenance recorder for monthly factsheets & annual reports. | Skeleton + recorder |
| `fca_open_data.py` | FCA published datasets (Product Sales Data, FIRDS, STS, ratings, NSM pointers). Provenance recorder for aggregates and reference extracts. | Skeleton + recorder |

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
