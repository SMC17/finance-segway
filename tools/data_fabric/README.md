# Data Fabric (L2 seed)

Connectors that pull **public** data and emit structured facts plus
`source_register`-compatible provenance rows for governed workbooks.

| Script | Purpose |
|--------|--------|
| `edgar_company_facts.py` | SEC companyfacts → selected US-GAAP values + provenance CSV |

## Rules

- Every automated fact must land with as-of, retrieval date, transformation, and snapshot pointer.
- Do not commit paywalled or confidential data.
- Domain builders remain the calculation engine; this layer only supplies inputs.

## Example

```bash
python tools/data_fabric/edgar_company_facts.py --ticker AAPL --cik 320193
```

Attach the generated `*_source_register.csv` rows into the relevant domain or instance source register.
