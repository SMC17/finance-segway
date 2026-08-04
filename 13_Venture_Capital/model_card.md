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
- Holder-by-holder conversion analysis for explicitly entered, unique-seniority, non-participating preferred terms

### Prohibited or unsupported uses

- Live capital, fiduciary, regulatory, legal, or tax use without named human approval
- Representing retained modeler assumptions as external observations
- Treating historical public cases as transaction-specific diligence
- Treating participating preferred, capped participation, or unconverted SAFEs as supported waterfall terms

## Scope and methodology

- Canonical workbook: `13_Venture_Capital/_template_VC.xlsx`
- Reproducible builder: `tools/builders/build_venture_capital_release.py`
- Methodology: domain-specific financial identities plus exhaustive preferred-class election enumeration. Each candidate pays retained preferences in seniority order, allocates residual value across common and converted shares, conserves proceeds, and is eligible for selection only when no holder can improve by changing its election unilaterally.
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
| `liquidation_preferences` | `Exit Waterfall`; `finance_segway/venture_capital.py` | Implemented for non-participating preferred | Exhaustive elections, conservation, seniority, monotonicity, and boundary tests |
| `pro_rata` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `exit_waterfall` | `Exit Waterfall`; `tools/builders/vc_election_solver.py` | Implemented | Independent Python re-derivation plus LibreOffice execution |
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
- Every selected waterfall state must reconcile to total exit proceeds and admit no profitable unilateral conversion change.
- Participating preferred, non-zero participation caps, duplicate seniority ranks, incomplete terms, and unconverted SAFE claims fail closed.

## Limitations and failure modes

- IPO offerings are used as observable financing and valuation events; they do not establish private preferred terms.
- Preferred terms, conversion ratios, liquidation preferences, pro rata rights and option-pool treatment require executed documents.
- The current exact solver supports non-participating preferred only. Participating preferred and caps require a dedicated residual-sharing engine and legal review.
- SAFE claims are excluded until transaction-specific conversion mechanics are entered.
- Exit values and follow-on requirements remain modeler assumptions unless explicitly sourced.

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
