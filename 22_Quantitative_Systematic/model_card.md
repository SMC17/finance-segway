# Model Card: Quantitative & Systematic

## Identity

- Model ID: 22
- Domain: Quantitative & Systematic
- Version: 2.1.0
- As-of date: 2026-08-04
- Owner: SMC17 / repository owner
- Developer: Claude Code and ChatGPT/Codex synthesis
- Independent validator: independent-oracle, workbook-contract, parity, and LibreOffice suites
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: M2
- Intended horizon: trading_daily

## Intended use

### Approved uses

- Point-in-time research backtests
- Cost and capacity analysis
- Walk-forward validation
- Backtest-to-live monitoring

### Prohibited or unsupported uses

- Live trading without execution/risk controls
- Use of revised data without vintage handling
- Performance claims without cost and capacity treatment

## Scope and methodology

- Canonical workbook: `22_Quantitative_Systematic/_template_QUANT.xlsx`
- Reproducible builder: `tools/builders/build_quant_release.py`
- Methodology: domain-specific financial identities and market conventions, independently benchmarked where possible.
- Time-step and timeline: `trading_daily`.
- Public cases: one conventional and one adversarial historical case, both classified as external evidence and not M4 production instances.

## Inputs and sources

- Source register: `22_Quantitative_Systematic/sources/source_register.csv`
- Frozen snapshots: `22_Quantitative_Systematic/sources/snapshots/`
- Input classes: observed, derived, or modeler-owned assumption.
- Source observations are immutable JSON snapshots with SHA-256 digests.
- Modeler-owned assumptions remain visibly labeled and sensitivity-tested.

## Domain engines

| Engine | Workbook sheet / code module | Status | Validation evidence |
|---|---|---|---|
| `point_in_time_backtest` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `walk_forward` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `transaction_costs` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `capacity` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `performance` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `var_es` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `stress_testing` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |
| `backtest_live_controls` | Canonical workbook / builder | Implemented | Builder parity and domain contracts |

## Stakeholder perspectives

| Perspective | Definitions / metrics | Reconciliation |
|---|---|---|
| researcher | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| portfolio_manager | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| risk | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |
| execution | Domain-specific metrics from Institutional Surface | Conflicts resolved through Challenge Log |

## Checks and controls

- Builder-to-workbook semantic parity is required.
- LibreOffice recalculation must produce zero cached formula errors.
- External workbook links and literal Excel errors are prohibited.
- Independent-oracle and domain-contract tests must pass.
- Challenge, source lineage, and release evidence are retained.

## Limitations and failure modes

- Single-strategy workbook
- No portfolio optimizer or borrow model
- Public index series is a research proxy and may have redistribution restrictions

## Monitoring

| Metric | Warning | Breach | Required action |
|---|---:|---:|---|
| live_sharpe_degradation | -0.5 | -1.0 | Reduce risk and revalidate signal |
| cost_slippage_bps | 5 | 10 | Recalibrate implementation shortfall and capacity |
| drawdown | -0.15 | -0.2 | Escalate stop, regime, and retirement review |

## Release record

- Active release: 2.1.0
- Rollback release: flagship-2.1.0
- Validation record: `22_Quantitative_Systematic/validation.md`
- Stakeholder sign-off: `22_Quantitative_Systematic/governance/signoff.json`
- Lifecycle record: `22_Quantitative_Systematic/governance/lifecycle.json`
- Retirement trigger: Signal loses economic rationale, live degradation breaches threshold, or data process is invalidated
