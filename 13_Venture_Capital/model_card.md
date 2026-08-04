# Model Card: Venture Capital

## Identity

- Model ID: 13
- Domain: Venture Capital
- Version: 3.0.0-evidence
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: corporate_10y

## Intended use

### Approved uses

- Round pricing, ownership and dilution diagnostics
- Follow-on reserve and exit-return stress
- Historical up-round and down-round comparison

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence

## Scope and methodology

- Canonical workbook: `13_Venture_Capital/_template_VC.xlsx`
- Reproducible builder: `tools/builders/build_venture_capital_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `corporate_10y`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `13_Venture_Capital/sources/source_register.csv`
- Frozen snapshots: `13_Venture_Capital/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `cap_table` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `safe_conversion` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `round_modeling` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `liquidation_preferences` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `pro_rata` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `exit_waterfall` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `portfolio_reserves` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| founder | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| investor | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| board | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| lp_ic | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- IPO offerings are used as observable financing and valuation events
- Preferred terms, liquidation preferences, pro rata rights and option-pool treatment require executed documents
- Exit values and follow-on requirements remain modeler assumptions unless explicitly sourced

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| reserve_gap | 0.0 | 1.0 | Escalate reserve allocation and ownership-defense plan |
| round_price_change | 0.0 | -0.25 | Re-underwrite dilution, anti-dilution and portfolio marks |

## Release record

- Active release: 3.0.0-evidence
- Rollback release: m2-frontier-release-3.0.0
- Validation record: `13_Venture_Capital/validation.md`
- Stakeholder sign-off: `13_Venture_Capital/governance/signoff.json`
- Lifecycle record: `13_Venture_Capital/governance/lifecycle.json`
- Retirement trigger: Financing terms, ownership, reserve policy or exit assumptions are superseded
