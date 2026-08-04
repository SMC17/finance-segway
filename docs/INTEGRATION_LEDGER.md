# Finance Model Library Integration Ledger

This ledger records the component-level synthesis of the Claude Code and
ChatGPT/Codex implementation lanes. The canonical merge target is
`agent/synthesize-finance-model-library-v2` through draft PR #3.

## Reconciled branch state

| Lane | Disposition |
|---|---|
| Claude Code | Retained as the complete 24-domain baseline, workbook history, broad builder hardening, and independent spreadsheet regression suite |
| Earlier ChatGPT/Codex credit prototype | Financial mechanics selectively rebuilt; obsolete binaries and workflows rejected |
| Engineered synthesis lane | Canonical source, artifact, validation, benchmark, and release-evidence system |

No active source branch was overwritten or force-pushed. Components were retained,
combined, superseded, or rejected according to financial identity and test evidence.

## Current verified inventory

- Inventory version: **2.1.0**
- 24 core archetypes
- 15 M2 Decision Models
- 9 M1 Correct Skeletons
- 0 M3 Institutional Underwriting Models
- 0 M4 Maintained Production Systems
- 18 synthetic reference/adversarial benchmark instances
- 0 public maintained instances that count toward M4

## Completed component decisions

| Component | Decision | Canonical implementation |
|---|---|---|
| Repository skeleton and domain coverage | Retain | Claude baseline |
| Spreadsheet independent-oracle suite | Retain | `tools/verify_reference_calcs.py` |
| Pure-Python financial engines | Combine and extend | `finance_segway/` and `tools/reference_engines.py` |
| Model inventory and maturity gates | Retain | `standards/model_inventory.json` and `tools/validate_model_inventory.py` |
| Whole-library workbook audit | Add | `tools/workbook_engineering.py` |
| Semantic builder parity | Add and require | `tools/workbook_parity.py`, `tools/build_all_models.py`, required parity CI |
| Private Credit | Rebuilt and promoted M2 | distinct five-year lender model |
| Debt Finance | Split and promoted M2 | distinct issuance, refinancing, maturity-ladder, and recovery model |
| Public Finance | Rebuilt and promoted M2 | sovereign DSA plus municipal operating, reserve, pension, and coverage model |
| Private Equity / Merchant Banking | Rebuilt and promoted M2 | seven-year operating model, multi-tranche debt, covenants, management equity, exit waterfall |
| Risk Management | Rebuilt and promoted M2 | positions, factor covariance, Euler/component VaR, ES, stress, liquidity, P&L explain, limits |
| Options / Derivatives | Rebuilt and promoted M2 | pricing, IV, American option, Greeks, surface, portfolio and scenario risk |
| Insurance / Actuarial | Rebuilt and promoted M2 | triangle, chain ladder, BF, underwriting, embedded value, capital and stress |
| Structured Finance | Rebuilt and promoted M2 | monthly collateral, CPR/CDR/recoveries, waterfall, shortfalls, triggers, WAL and sensitivity |
| Project Finance | Rebuilt and promoted M2 | construction/IDC, sources and uses, CFADS, sculpting, DSRA, DSCR/LLCR/PLCR |
| Fixed Income / Rates | Rebuilt and promoted M2 | curve, price, duration, convexity, key-rate DV01, carry/roll, scenarios and P&L explain |
| Quantitative / Systematic | Rebuilt and promoted M2 | point-in-time backtest, costs, capacity, walk-forward, VaR/ES and stress |
| Artifact promotion | Supersede ad hoc transfer | GitHub-native, recalculated, stale-head-guarded atomic release |
| Maintained instance plumbing | Add | manifest inputs, provenance, RefreshLog, SHA receipts, 18 benchmark instances |
| Weekly refresh | Supersede commit-writing job | read-only report artifact |

## Rejected implementation patterns

- blanket “Built” labels without maturity evidence;
- a single shared workbook for economically different domains;
- connector-side binary XLSX transport;
- source changes that silently leave committed artifacts stale;
- formula parity based only on raw ZIP or byte equality;
- array formulas that do not recalculate consistently across Excel engines;
- bot commits triggered by shared-helper edits;
- M3/M4 claims based on formula count, visual polish, or synthetic fixtures.

## Permanent acceptance gates

1. Source compiles and unit tests pass.
2. Domain-specific workbook contracts pass.
3. LibreOffice recalculation produces zero cached Excel errors.
4. Contracts still pass after spreadsheet normalization.
5. Inventory claims are internally valid.
6. Every inventory builder reproduces the committed workbook semantically.
7. External links and literal errors are absent.
8. Release artifacts and builders receive SHA-256 evidence.
9. Reference and adversarial benchmark instances recalculate cleanly.
10. Any source-head movement aborts rather than rebasing stale binaries.

## Remaining maturity work

Reconciliation and model-engineering work are complete for the current flagship
release. Remaining work is not another branch merge or cosmetic workbook expansion.
M3 requires external source snapshots, completed model cards, independent validation
and effective challenge, stakeholder sign-off, and externally sourced reference and
adversarial instances. M4 requires repeated maintenance and outcome evidence over time.
