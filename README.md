# Finance-Segway

A governed, multi-domain financial-modeling system: reproducible Excel archetypes, independent reference engines, explicit model-risk controls, and a maintenance pipeline designed to prevent model rot.

## Current state

The repository is broad, formula-driven, and heavily checked. It is not yet a production-grade institutional model library.

The machine-validated baseline on `main` is:

- **24** core spreadsheet archetypes
- **15 M2 Decision Models**
- **9 M1 Correct Skeletons**
- **0 M3 Institutional Underwriting Models**
- **0 M4 Maintained Production Systems**
- **18 source-addressed public historical cases** across 9 domains

That distinction is deliberate. “The workbook opens” and “the core formula is correct” are necessary but not sufficient evidence of underwriting depth.

The canonical inventory is `standards/model_inventory.json`. CI validates every maturity claim with `tools/validate_model_inventory.py`, validates the three reconciled builders with `tools/validate_reconciled_models.py`, and publishes governance evidence on each pull request.

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

- a reproducible Python builder;
- `Cover` and append-only `RefreshLog` sheets;
- consistent input, formula, and cross-sheet-link conventions;
- formula and external-link scans;
- independent benchmark tests for material math;
- a declared use, horizon, owner, limitations, and maturity;
- a path from blank archetype to maintained public instances.

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

1. workbook opens;
2. formulas recalculate without errors;
3. accounting, cash-flow, coverage, or waterfall identities tie;
4. independent code or a closed-form benchmark agrees;
5. realized outcomes or external observations support continued use.

Current controls include:

- `tools/recalc.py` — headless recalculation and cached-error detection;
- `tools/verify_reference_calcs.py` — spreadsheet outputs versus independent calculations;
- `tools/reference_engines.py` — Black-Scholes, bond, debt-sweep, coverage, and waterfall oracles;
- `tools/reconciled_reference_engines.py` — yield, recovery/LGD, debt-sustainability, refinancing, and maturity-concentration oracles;
- `tools/test_reference_engines.py` and `tools/test_reconciled_reference_engines.py` — closed-form, monotonicity, conservation, and identity tests;
- `tools/validate_reconciled_models.py` — builder and workbook contracts for Private Credit, Debt Finance, and Public Finance;
- `tools/weekly_refresh_check.py` — freshness and structural-drift scanner;
- `tools/validate_model_inventory.py` — maturity and evidence gate;
- `tools/scaffold_model_evidence.py` — model cards, validation records, source registers, release logs, and instance structure.

The design is informed by—but does not claim certification or formal compliance with—the ICAEW Financial Modelling Code, the FAST Standard, current U.S. interagency model-risk guidance, and IFC/DFI blended-finance principles.

## Domain inventory

| # | Domain | Archetype | Current maturity |
|---|---|---|---|
| 01 | Investment Banking | 3-statement, DCF, comps | **M2** |
| 02 | Corporate Finance | 3-statement and capital structure | **M2** |
| 03 | Private Equity | LBO sources/uses, debt schedule, returns | **M2** |
| 04 | Merchant Banking | Principal-investing LBO variant | **M2** |
| 05 | Private Credit | Five-year CFADS, debt/cash schedule, covenants, yield/OID, recovery/LGD | **M2** |
| 06 | Debt Finance | Capital structure, maturity ladder, refinancing, rate risk, recovery | **M2** |
| 07 | Public Finance | Sovereign DSA, operating forecast, debt service, reserves and coverage | **M2** |
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

## Reconciled credit and public-finance systems

Three domains now have distinct canonical decisions, builders, workbooks, tests, and inventory records:

- **Private Credit** asks whether and on what terms a lender should underwrite, hold, amend, or restructure an exposure.
- **Debt Finance** asks how an issuer or arranger should size, structure, price, sequence, and refinance debt instruments.
- **Public Finance** combines sovereign debt sustainability with municipal operating, reserve, liquidity, pension, and revenue-bond coverage analysis without collapsing the two lenses.

The exact XLSX release artifacts are generated inside GitHub from their canonical builders by `.github/workflows/reconcile-model-artifacts.yml`. Promotion is atomic: generated workbooks, structural contracts, independent tests, and inventory changes must pass together.

## Depth program

The next phase is not “add a few tabs to every workbook.” It is to build reference-grade flagships and reusable shared engines:

1. Private Equity / Merchant Banking;
2. Options / Fixed Income / Rates;
3. Project Finance / Infrastructure;
4. Structured Finance / Insurance;
5. Quantitative / Systematic / Risk;
6. Investment Banking / Corporate Finance.

Private Credit, Debt Finance, and Public Finance have completed M2 reconciliation. Their next gate is M3 evidence and stakeholder depth: model cards, independent validation, source snapshots, effective challenge, and maintained reference/adversarial instances.

The complete target mechanics are defined in `docs/INSTITUTIONAL_DEPTH_BLUEPRINT.md` and machine-readable in `standards/model_inventory.json`.

## Public instance program

Blank templates cannot prove maintainability. Each flagship must eventually include at least two public, reproducible instances:

- one conventional reference case;
- one adversarial or stressed case.

An M4 instance requires a source register, frozen as-of date, model card, validation record, at least three material refreshes, and at least one outcome comparison. See `docs/PUBLIC_INSTANCE_PROGRAM.md`.

## Repository layout

```text
<domain>/
  _template_<ARCHETYPE>.xlsx
  README.md
  model_card.md
  validation.md
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
  reconciled_reference_engines.py
  test_reference_engines.py
  test_reconciled_reference_engines.py
  validate_model_inventory.py
  validate_reconciled_models.py
  reconcile_model_inventory.py
  weekly_refresh_check.py
  scaffold_model_evidence.py
```

## Quickstart

```bash
# Verify independent code engines
python tools/test_reference_engines.py
PYTHONPATH=tools python tools/test_reconciled_reference_engines.py

# Rebuild and validate the reconciled decision models in a temporary directory
python tools/validate_reconciled_models.py --report reconciled-model-report.json

# Recalculate and check a workbook
python tools/recalc.py 14_Options_Derivatives/_template_OPTIONS.xlsx

# Validate the complete inventory and maturity claims
python tools/validate_model_inventory.py --report model-governance-report.json

# Scan freshness and structural drift
python tools/weekly_refresh_check.py .

# Create the evidence pack for a domain
python tools/scaffold_model_evidence.py 05_Private_Credit
```

## Collaboration

Claude Code and ChatGPT/Codex work in independent branches. Integration occurs component by component through a draft synthesis PR. A newer branch does not win automatically, and tests are never weakened to make a merge pass.

The Claude branch is fully retained in the synthesis history. The earlier institutional prototype branch has been reconciled: stronger mechanics were rebuilt and promoted, while obsolete binaries and workflows were rejected.

See:

- `docs/COLLABORATION_PROTOCOL.md`;
- `docs/INTEGRATION_LEDGER.md`;
- Issue #4, the institutional-depth implementation program.

## Public references

- ICAEW Financial Modelling Code and spreadsheet-review guidance;
- FAST Standard;
- U.S. Federal Reserve SR 26-2, Revised Guidance on Model Risk Management, April 17, 2026;
- IFC / DFI Enhanced Blended Concessional Finance Principles;
- Rosenbaum & Pearl, Damodaran, McKinsey Valuation, and Benninga;
- Hull and Haug for derivatives;
- Tuckman & Serrat and Fabozzi for fixed income and structured finance;
- public modeling lectures and open-source examples, used for discipline rather than copied files.

All workbook and builder implementations in this repository are original. Do not commit proprietary models, confidential deal data, or restricted datasets.

## License

MIT. Not financial, legal, tax, accounting, actuarial, or investment advice.
