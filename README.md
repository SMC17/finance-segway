# Finance-Segway

A governed, multi-domain financial-modeling system: reproducible Excel archetypes, independent reference engines, explicit model-risk controls, and a maintenance pipeline designed to prevent model rot.

## Current state

The repository is broad, formula-driven, and heavily checked. It is not yet a production-grade institutional model library.

The machine-validated baseline is:

- **24** core spreadsheet archetypes
- **7 M2 Decision Models**
- **17 M1 Correct Skeletons**
- **0 M3 Institutional Underwriting Models**
- **0 M4 Maintained Production Systems**
- **0 populated public instances**

That distinction is deliberate. “The workbook opens” and “the core formula is correct” are necessary but not sufficient evidence of underwriting depth.

The canonical inventory is `standards/model_inventory.json`. CI validates every maturity claim with `tools/validate_model_inventory.py` and publishes a governance report on each pull request.

## Maturity scale

| Level | Meaning |
|---|---|
| **M0** | Placeholder or concept only |
| **M1** | Correct Skeleton: formula-driven, reproducible, core identity checked |
| **M2** | Decision Model: integrated mechanics, scenarios/sensitivities, independent reference checks |
| **M3** | Institutional Underwriting: complete domain engine, stakeholder lenses, sources, checks, validation, audit trail |
| **M4** | Maintained Production System: M3 plus populated instances, outcome monitoring, source snapshots, and release discipline |

See `docs/MODEL_GOVERNANCE_STANDARD.md` for the promotion and validation rules.

## Why this exists

Most personal model libraries rot. A DCF or trading worksheet gets built for one event, never refreshed, and becomes untrustworthy. Finance-Segway treats maintenance, verification, source provenance, and change control as part of the model itself.

Every archetype is expected to have:

- a reproducible Python builder
- `Cover` and append-only `RefreshLog` sheets
- consistent input/formula/link conventions
- formula and external-link scans
- independent benchmark tests for material math
- a declared use, horizon, owner, limitations, and maturity
- a path from blank archetype to maintained public instances

## Core conventions

| Convention | Meaning |
|---|---|
| **Blue text** | Hardcoded input |
| **Black text** | Formula |
| **Green text** | Cross-sheet link |
| **Yellow fill** | Material assumption |
| **Cover** | Purpose, thesis, ownership, refresh and next material date |
| **RefreshLog** | Append-only record of what changed and why |
| **Sources** | Dated provenance, units, transformations, and restrictions |
| **Checks** | Visible financial identities, residuals, and status flags |

## Governance and verification

The system separates five levels of evidence:

1. workbook opens
2. formulas recalculate without errors
3. accounting, cash-flow, or waterfall identities tie
4. independent code or closed-form benchmark agrees
5. realized outcomes or external observations support continued use

Current controls include:

- `tools/recalc.py` — headless recalculation and cached-error detection
- `tools/verify_reference_calcs.py` — spreadsheet outputs versus independent calculations
- `tools/reference_engines.py` — dependency-free Black-Scholes, bond, debt-sweep, coverage, and waterfall oracles
- `tools/test_reference_engines.py` — closed-form, monotonicity, and conservation tests
- `tools/weekly_refresh_check.py` — freshness and structural-drift scanner
- `tools/validate_model_inventory.py` — maturity and evidence gate
- `tools/scaffold_model_evidence.py` — creates model cards, validation records, source registers, release logs, and instance structure

The design is informed by—but does not claim certification or formal compliance with—the ICAEW Financial Modelling Code, the FAST Standard, current U.S. interagency model-risk guidance, and IFC/DFI blended-finance principles.

## Domain inventory

| # | Domain | Archetype | Current maturity |
|---|---|---|---|
| 01 | Investment Banking | 3-statement, DCF, comps | **M2** |
| 02 | Corporate Finance | 3-statement and capital structure | **M2** |
| 03 | Private Equity | LBO sources/uses, debt schedule, returns | **M2** |
| 04 | Merchant Banking | Principal-investing LBO variant | **M2** |
| 05 | Private Credit | Lender yield, covenants, debt schedule | **M1** |
| 06 | Debt Finance | Issuer / instrument credit engine | **M1** |
| 07 | Public Finance | Sovereign DSA and coverage | **M1** |
| 08 | Asset Management | NAV, fees, carry, attribution | **M1** |
| 09 | Risk Management | VaR and stress framework | **M1** |
| 10 | Trade Finance | Cash conversion, LC, factoring | **M1** |
| 11 | Microfinance | PAR, loss, OSS/FSS | **M1** |
| 12 | Equity Finance | BASE model with equity lens | **M1** |
| 13 | Venture Capital | Cap table, SAFE, waterfall | **M2** |
| 14 | Options / Derivatives | Black-Scholes, Greeks, payoffs | **M2** |
| 15 | Commodities | Curves, carry, roll yield, hedging | **M1** |
| 16 | Crypto / Digital Assets | Token supply, staking, multiples | **M1** |
| 17 | Real Estate / REIT | Property pro forma and FFO/AFFO | **M1** |
| 18 | Insurance / Actuarial | Loss ratio, triangle, embedded value | **M1** |
| 19 | Structured Finance | Tranche waterfall, CPR, WAL | **M1** |
| 20 | Project Finance | Construction, CFADS, DSCR | **M1** |
| 21 | Fixed Income / Rates | Bond price, duration, curve | **M2** |
| 22 | Quantitative / Systematic | Performance and sizing framework | **M1** |
| 23 | Fintech / Payments | Unit economics and cohorts | **M1** |
| 24 | Distressed / Restructuring | Recovery and fulcrum waterfall | **M1** |

Non-model research frameworks live under `25_Frameworks_NonModel/`.

## Depth program

The next phase is not “add a few tabs to every workbook.” It is to build six reference-grade flagships and reusable shared engines:

1. Private Equity / Merchant Banking
2. Private Credit / Debt Finance
3. Options / Fixed Income / Rates
4. Project Finance / Infrastructure
5. Structured Finance / Insurance
6. Quantitative / Systematic / Risk

The complete target mechanics are defined in `docs/INSTITUTIONAL_DEPTH_BLUEPRINT.md` and machine-readable in `standards/model_inventory.json`.

Cross-domain engines will cover timelines, scenarios, three statements, working capital, tax, debt instruments, covenants, cash waterfalls, curves, valuation, risk, recovery, sources, checks, and release metadata.

## Public instance program

Blank templates cannot prove maintainability. Each flagship must eventually include at least two public, reproducible instances:

- one conventional reference case
- one adversarial or stressed case

An M4 instance requires a source register, frozen as-of date, model card, validation record, at least three material refreshes, and at least one outcome comparison. See `docs/PUBLIC_INSTANCE_PROGRAM.md`.

## Repository layout

```text
<domain>/
  _template_<ARCHETYPE>.xlsx
  README.md
  model_card.md                 # M3+ evidence
  validation.md                 # M3+ evidence
  sources/
    source_register.csv
    snapshots/
  releases/
    CHANGELOG.md
  instances/

standards/
  model_inventory.json
  templates/

tools/
  builders/
  recalc.py
  verify_reference_calcs.py
  reference_engines.py
  test_reference_engines.py
  validate_model_inventory.py
  weekly_refresh_check.py
  scaffold_model_evidence.py
```

## Quickstart

```bash
# Verify pure-Python reference engines
python tools/test_reference_engines.py

# Recalculate and check a workbook
python tools/recalc.py 14_Options_Derivatives/_template_OPTIONS.xlsx

# Validate the complete inventory and maturity claims
python tools/validate_model_inventory.py --report model-governance-report.json

# Scan freshness and structural drift
python tools/weekly_refresh_check.py .

# Create the evidence pack for a domain
python tools/scaffold_model_evidence.py 03_Private_Equity
```

## Collaboration

Claude Code and ChatGPT/Codex work in independent branches. Integration occurs component by component through a draft synthesis PR. A newer branch does not win automatically, and tests are never weakened to make a merge pass.

See:

- `docs/COLLABORATION_PROTOCOL.md`
- `docs/INTEGRATION_LEDGER.md`

## Public references

- ICAEW Financial Modelling Code and spreadsheet-review guidance
- FAST Standard
- U.S. Federal Reserve SR 26-2, Revised Guidance on Model Risk Management, April 17, 2026
- IFC / DFI Enhanced Blended Concessional Finance Principles
- Rosenbaum & Pearl, Damodaran, McKinsey Valuation, Benninga
- Hull and Haug for derivatives
- Tuckman & Serrat and Fabozzi for fixed income and structured finance
- public modeling lectures and open-source examples, used for discipline rather than copied files

All workbook and builder implementations in this repository are original. Do not commit proprietary models, confidential deal data, or restricted datasets.

## License

MIT. Not financial, legal, tax, accounting, actuarial, or investment advice.
