# Independent Validation: ETF Construction & Management

## Validation identity

- Model ID and version: 30 / 1.0.0
- Workbook checksum: see `30_ETF_Construction_Management/instances/public_qqq_2026.receipt.json` for the released instance's `workbook_sha256`
- Builder commit: `tools/builders/build_etf_construction_institutional.py`
- Validation date: 2026-08-06
- Validator: Claude Code (independent Python recomputation, not reusing the workbook's own formulas)
- Validator independence statement: benchmark figures below were computed directly in Python from the same real, sourced input values, not by reading back the workbook's formula results.
- Risk tier: Tier 1
- Scope of validation: template mechanics plus one real, sourced public instance (`etf-public-qqq-2026`, Invesco QQQ Trust).

## Executive conclusion

- **Approved with limitations** at M2.
- Declared maturity supported: Yes -- integrated mechanics, a real sourced public instance with LibreOffice-recalculated checks, and independent reference checks against genuinely disclosed data (not tautological pass-throughs). Not yet supported for M3 (requires multiple stakeholder perspectives evidenced in practice, a second public instance, and human effective challenge).
- Required compensating controls: no capital, fiduciary, regulatory, or live-risk use without a named human owner and approver; the illustrative creation-unit-size, securities-lending, cash-drag, and sampling-error assumptions must not be represented as QQQ's own disclosed figures.
- Revalidation trigger: a second (adversarial/stress) public case is added, prospectus/SAI access becomes available to source the creation-unit size and realized tracking-difference statistics for real, or the methodology changes.

## 1. Conceptual soundness

The methodology (look-through portfolio construction, creation-unit/AP arbitrage economics, and a tracking-difference bridge) matches standard open-end ETF mechanics as described in fund issuers' own prospectuses and academic/practitioner literature on ETF arbitrage. Units are consistent ($mm for AUM, $/share for price, % for rates); the Base/Downside scenario convention matches the rest of the repo.

One boundary condition is explicitly documented rather than silently accepted: market price is used as a proxy for the fund's own officially calculated NAV, since this session's data sources provide market quotes but not the fund's own daily NAV series -- see model card, Limitations.

## 2. Data and source validation

- Real source: Invesco QQQ Trust's own disclosed ETF profile (AUM, net expense ratio, dividend yield, 105 holdings with weights, 11 sector weights), retrieved via Alpha Vantage `ETF_PROFILE`, and last close market price via `GLOBAL_QUOTE` -- both recorded raw in `tools/data_fabric/out/` and registered in `30_ETF_Construction_Management/sources/source_register.csv` with SHA-256 checksums.
- Frozen snapshot: `30_ETF_Construction_Management/sources/snapshots/etf-public-qqq-2026.json`, self-referentially hashed (`snapshot_sha256`) and cross-checked against `standards/public_cases/index.json`.
- Illustrative (non-real) inputs are explicitly flagged in the model card's "What's illustrative" section and were never asserted as observed/derived in the manifest.

## 3. Implementation verification

- Builder-to-workbook parity: verified via `tools/build_all_models.py --require-parity`.
- Formula and cross-sheet-link review: manual review of every formula in the builder source. Two real defects were found and fixed during this pass, before release (see Findings below).
- External-link scan: `tools/validate_model_inventory.py` checks for external workbook links; none present.
- Circularity: none -- single-pass computation, no iterative calculation required.
- Reproducibility: `python tools/builders/build_etf_construction_institutional.py --output <path>` regenerates the canonical template deterministically; `python tools/model_instances.py standards/public_cases/etf-public-qqq-2026.json` regenerates the real instance from the frozen manifest.

### Findings

| ID | Severity | Finding | Evidence | Remediation | Owner | Due date |
|---|---|---|---|---|---|---|
| ETF-01 | High | The AP-arbitrage-profit formula on `Creation & Redemption` multiplied two dollar-denominated cells (`C7*C6`, both creation-unit basket values) instead of premium/discount (a percentage) times basket value, producing a nonsensical dollar-squared result. Caught by manual review of the formula list against the stated methodology before this release. | Formula review during initial build | Corrected to `=C9*C7` (premium/discount times market-price-basis basket value) | Claude Code | Closed 2026-08-06 |
| ETF-02 | Medium | The "AP action threshold breached?" formula referenced the wrong Assumptions cell (`$E$13`, sampling/optimization tracking error) instead of `$E$14` (the actual AP arbitrage action threshold), and compared against the wrong metric cell (`C8`, implied AUM share, instead of `C9`, premium/discount). Caught by the same formula review. | Formula review during initial build | Corrected to reference `C9` and `Assumptions!$E$14` | Claude Code | Closed 2026-08-06 |

## 4. Independent benchmarking

Recomputed directly in Python from the same real input values (not by reading the workbook's own formula results):

| Model output | Workbook result | Independent result | Tolerance | Residual | Status |
|---|---:|---:|---:|---:|---|
| Implied shares outstanding (mm) | 683.2566569 | `490100/717.30 = 683.2566569` | 1e-4 | 0.0 | PASS |
| Creation unit basket value ($) | 35,865,000 | `717.30*50000 = 35,865,000` | 1e-6 | 0.0 | PASS |
| Creation unit implied share of AUM | 0.0000731789 | `35865000/(490100*1e6) = 0.0000731789` | 1e-9 | 0.0 | PASS |
| Estimated net tracking difference | -0.0028 | `-0.0018+0.0002-0.0002-0.0010 = -0.0028` | 1e-9 | 0.0 | PASS |
| Top 30 holdings weight sum | 0.7495 | Sum of the 30 real disclosed weights | 1e-4 | 0.0 | PASS |
| Sector weight sum (all 11 disclosed sectors) | 0.967 | Sum of the 11 real disclosed sector weights | 1e-4 | 0.0 | PASS |

## 5. Sensitivity and stress behavior

Base and Downside scenarios both run cleanly (see workbook `Checks` sheet, `Overall: PASS` for the real QQQ instance). Downside widens the premium/discount to NAV, raises cash-drag and sampling-error assumptions, and lowers the securities-lending offset -- all illustrative levers, since the real, sourced inputs (AUM, expense ratio, dividend yield, holdings, sector weights) are static observed facts, not scenario-reactive.

## 6. Outcomes analysis

No realized outcome exists yet. The `etf-public-qqq-2026` case's outcome is registered as `status: "pending"` (metric: next-quarter net assets, forecast = current AUM as a naive carry-forward, not a claimed prediction) in `standards/public_cases/index.json`, following the same "pending" convention already used for the BlackRock AUM and WTI price cases elsewhere in this repository's evidence registry -- honestly labeled as unresolved, not backdated or hindsight-fit.

## 7. Use and governance

- Named owner and approver: SMC17 / repository owner (approval pending).
- Approved and prohibited uses: see model card.
- Monitoring thresholds: see model card.
- Escalation and retirement rules: see model card release record.

## 8. Limitations

See model card "Limitations and failure modes" -- single real instance (no adversarial/stress case yet), market price used as a NAV proxy rather than the fund's own officially calculated NAV, and several illustrative (not yet sourced) cost-bridge assumptions.

## Sign-off

- Developer response: implemented mechanics, one real sourced instance, checks, and this validation record; found and fixed two real defects during self-review before release.
- Validator conclusion: approved with limitations at M2; M3 not yet supported pending a second public case and human effective challenge.
- Owner decision: **PENDING**
- Approval date: **PENDING**
- Next validation date or trigger: a second public case is sourced, prospectus/SAI data becomes available, or the methodology changes.
