# Model Governance Standard

Finance-Segway is not a folder of spreadsheets. It is a governed model system.

This standard separates four questions that are often conflated:

1. **Does the workbook open and recalculate?**
2. **Are the formulas conceptually correct?**
3. **Is the model complete enough to support a real decision?**
4. **Does the model remain reliable after assumptions, markets, and authors change?**

A model may pass the first two and still be too shallow for underwriting. The repository therefore uses an explicit inventory, maturity scale, model-risk lifecycle, and evidence standard.

## External standards used

The repository is informed by, but does not claim certification or formal compliance with:

- ICAEW Financial Modelling Code and Twenty Principles for Good Spreadsheet Practice
- FAST Standard: Flexible, Appropriate, Structured, Transparent
- U.S. interagency Revised Guidance on Model Risk Management, issued April 17, 2026 and replacing SR 11-7
- IFC / DFI Enhanced Blended Concessional Finance Principles for private-sector projects
- Public-domain finance theory and independently implemented reference calculations

The governing interpretation is:

- **ICAEW / FAST** control how models are designed, structured, reviewed, and handed off.
- **Model-risk guidance** controls inventory, ownership, effective challenge, validation, monitoring, and change management.
- **Domain references** control the financial identities and market conventions inside each archetype.
- **Independent engines and instances** provide evidence that the workbook is not merely internally self-consistent.

## Model maturity

The canonical maturity declarations live in `standards/model_inventory.json`.

### M0 — Placeholder

A concept, folder, or stub. It must not be described as built.

### M1 — Correct Skeleton

A formula-driven archetype with:

- Cover and RefreshLog sheets
- at least one tested core financial identity
- no external workbook links
- no literal Excel errors
- a reproducible builder
- clear inputs, formulas, and outputs

M1 means “correct foundation,” not “institutional model.”

### M2 — Decision Model

M1 plus:

- integrated domain mechanics rather than isolated calculators
- scenario or sensitivity analysis
- decision-useful outputs
- at least one independent reference check
- meaningful downside behavior
- documented limitations

### M3 — Institutional Underwriting

M2 plus:

- the complete domain engine set defined in the inventory
- multiple stakeholder perspectives
- Sources and Checks sheets
- a model card and validation record
- source provenance and assumption ownership
- effective challenge by someone other than the developer
- explicit liquidity, covenant, tail-risk, and failure-mode analysis where relevant
- reproducible release artifacts

### M4 — Maintained Production System

M3 plus:

- at least two populated public instances
- append-only RefreshLog history
- dated source snapshots
- outcome monitoring and backtesting where applicable
- model-performance thresholds and escalation rules
- versioned releases and migration notes
- evidence that the model survives real updates without manual repair

## Risk classification

Each model use receives a risk tier independent of maturity.

### Tier 1 — Capital, fiduciary, or regulatory decision

Examples: acquisition underwriting, credit approval, project financing, reserve adequacy, regulatory capital, or a live trading-risk limit.

Required controls:

- independent validation
- named owner and approver
- documented data lineage
- controlled release
- outcomes analysis
- explicit limitations and compensating controls

### Tier 2 — Material analysis or recommendation

Examples: investment committee support, strategic planning, portfolio construction, pricing analysis, or public research.

Required controls:

- independent reference tests
- peer effective challenge
- source register
- scenario and sensitivity analysis
- dated release

### Tier 3 — Training, exploration, or demonstration

Examples: blank templates and educational instances.

Required controls:

- accurate labeling
- no claims of production readiness
- core formula verification
- documented scope and omissions

## Model lifecycle

### 1. Identification and inventory

Every archetype and material instance must appear in the inventory with:

- domain
- owner
- purpose
- decision/use
- risk tier
- maturity
- horizon
- builder and workbook paths
- required engines
- required stakeholder perspectives
- reference checks
- known limitations

Uninventoried models are unsupported.

### 2. Development

Development must keep assumptions, calculations, outputs, and checks distinct. Complex formulas should be decomposed into inspectable steps. Repeated formulas should be structurally consistent. Hard-coded values inside formulas require an explicit documented exception.

### 3. Conceptual soundness

The developer must explain:

- the economic or financial theory
- the chosen methodology
- conventions and units
- assumptions and proxies
- boundary conditions
- omitted risks
- when the model should not be used

A correct spreadsheet implementation of the wrong concept is still a failed model.

### 4. Independent validation and effective challenge

Validation is performed by someone other than the primary developer and covers:

- conceptual soundness
- process verification
- benchmarking against independent calculations or external references
- sensitivity and stress behavior
- outcomes analysis or backtesting where possible
- data and assumption lineage
- limitations and compensating controls

Review comments are not validation unless they reach a clear conclusion and produce retained evidence.

### 5. Approval and release

A release requires:

- green automated checks
- completed model card
- completed validation record
- reconciled builder and workbook
- version identifier
- owner and approver
- change summary
- limitations
- rollback path

### 6. Ongoing monitoring

Monitoring must distinguish:

- **data drift** — inputs or source definitions changed
- **assumption drift** — business or market relationships changed
- **performance drift** — realized outcomes differ materially from model outputs
- **structural drift** — formulas, sheets, or builders diverged
- **use drift** — the model is being used for a decision it was not designed to support

Each M4 model defines thresholds and escalation actions.

### 7. Change control

Changes are classified as:

- cosmetic
- data refresh
- assumption change
- methodology change
- structural change
- emergency correction

Methodology and structural changes require revalidation. Emergency corrections require a post-mortem and regression test.

### 8. Retirement

Retired models are retained with:

- final version
- retirement reason
- successor model
- unresolved limitations
- date and owner

They are removed from active workflows but not silently deleted.

## Required evidence pack

M3 and M4 models should maintain:

```text
<domain>/
  model_card.md
  validation.md
  sources/
    source_register.csv
    snapshots/
  releases/
    CHANGELOG.md
  instances/
```

The evidence pack must answer:

- What decision is this model designed to support?
- Who owns it?
- What are its material assumptions?
- What are its failure modes?
- What was independently tested?
- What changed since the previous release?
- What evidence supports continued use?

## Stakeholder perspectives

A deep model should not show only the developer’s preferred view. The inventory defines required perspectives by domain. Common lenses include:

- owner / sponsor
- lender
- rating agency
- LP or investment committee
- regulator
- counterparty
- taxpayer / public authority
- servicer / operator
- restructuring or recovery

Where perspectives use different definitions, the model should reconcile rather than obscure the differences.

## Verification hierarchy

From weakest to strongest:

1. workbook opens
2. formulas recalculate without errors
3. accounting or cash-flow identities tie
4. closed-form or independent-code benchmark agrees
5. sensitivities behave monotonically and economically
6. historical outcomes or external observations agree within defined tolerances
7. independent reviewer approves continued use

A model does not receive a high maturity grade from sheet count, file size, or visual polish.

## Current implementation

- `standards/model_inventory.json` defines the model catalog and maturity claims.
- `tools/validate_model_inventory.py` checks repository evidence against those claims.
- `tools/reference_engines.py` contains dependency-free independent calculations.
- `tools/test_reference_engines.py` tests closed forms, monotonicity, and conservation identities.
- `tools/verify_reference_calcs.py` compares selected spreadsheet outputs with independent calculations.
- `tools/weekly_refresh_check.py` detects freshness and structural drift.

The objective is not to make every model equally complex. It is to make every claim about a model precise, testable, and honest.
