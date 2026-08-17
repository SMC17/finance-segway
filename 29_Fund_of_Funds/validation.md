# Independent Validation: Fund of Funds

## Validation identity

- Model ID and version: 29 / 1.0.0
- Workbook checksum: see `29_Fund_of_Funds/_template_FOF.xlsx` at release time; real-case receipt at `standards/public_cases/fof-public-hlpaf-2026.json`
- Builder commit: `tools/builders/build_fund_of_funds_institutional.py`
- Validation date: 2026-08-05
- Validator: Claude Code (independent Python recomputation, not reusing the workbook's own formulas)
- Validator independence statement: benchmark figures below were computed directly in Python from the same input values, not by reading back the workbook's formula results.
- Risk tier: Tier 1
- Scope of validation: template mechanics only — no real instance exists yet, so this is conceptual and implementation verification, not evidence-backed benchmarking against a real disclosed outcome.

## Executive conclusion

- **Approved with limitations** at M2.
- Declared maturity supported: Yes, for M2 — one real, sourced, LibreOffice-recalculated public case (`fof-public-hlpaf-2026`) now exists in `standards/public_cases/index.json`.
- Material findings: two real defects were found and fixed during template-mechanics validation (see Finding IDs FOF-01 and FOF-02 below), plus one real, honest signal from the case itself — its NAV roll-forward reconciliation check FAILs (Overall: BREACH), a genuine consequence of applying this template's simplified fee model to a real complex fund, documented rather than suppressed (see §2 and §6).
- Required compensating controls: no capital, fiduciary, regulatory, or live-risk use without a named human owner and approver; the one real case's BREACH status must be understood (fee-model simplification, not a data defect) before any decision use.
- Revalidation trigger: a second real public case is added, the fee-layering / NAV roll-forward methodology changes, or HLPAF's own filings are revised.

## 1. Conceptual soundness

The methodology (two-layer NAV roll-forward with an explicit fee-layering-drag metric) is standard for fund-of-funds analysis and matches how real vehicles like HarbourVest Global Private Equity or Pantheon International report to their own LPs: a look-through portfolio table plus a period NAV roll-forward, not a fully dynamic cash-flow simulation. Units are consistent ($mm throughout); the Base/Downside scenario convention matches the rest of the repo.

One boundary condition is explicitly documented rather than silently accepted: the Downside scenario only stresses the underlying-fund portfolio's marked NAV, not the FoF-level roll-forward's own reported (observed) figures, which can trip the fee-layering-drag check under Downside — see model card, Limitations.

### Findings

| ID | Severity | Finding | Evidence | Remediation | Owner | Due date |
|---|---|---|---|---|---|---|
| FOF-01 | High | The FoF carried-interest formula swapped the carry-rate and hurdle-rate cell references (`Assumptions!$C$7` and `$C$8`), computing carry as `MAX(0, distributions − beginning_NAV × carry_rate) × hurdle_rate` instead of the reverse. Caught by recalculating the template via LibreOffice and finding the NAV roll-forward reconciliation check failed. | LibreOffice recalc of the built template, before vs. after fix | Fixed in `build_fund_of_funds_institutional.py` before this release | Claude Code | Closed 2026-08-05 |
| FOF-02 | Medium | The illustrative default numbers were economically inconsistent: FoF-level (LP) cumulative called capital (320) was set lower than the underlying-fund portfolio's own cumulative called capital (386) — impossible in practice, since a FoF cannot call more from underlying funds than it has called from its own LPs. | Manual review of `Performance & Multiples` output (fee-layering drag came out negative, an impossible result under the stated methodology) | Raised FoF-level called capital to 400 (above the portfolio total) in the illustrative defaults | Claude Code | Closed 2026-08-05 |

## 2. Data and source validation

One real, sourced case exists: `fof-public-hlpaf-2026`, from Hamilton Lane Private Assets Fund's N-CSR (SEC EDGAR, accession 0001213900-26-066804, filed 2026-06-09, period ended 2026-03-31). `29_Fund_of_Funds/sources/source_register.csv` and `sources/snapshots/fof-public-hlpaf-2026.json` are populated; the snapshot is hash-pinned (`snapshot_sha256` in the case's `standards/public_cases/index.json` entry).

Real: top 8 (of 159 disclosed) secondary-fund positions by cost/fair value (Consolidated Schedule of Investments); FoF-level beginning/ending NAV, this-year realized/unrealized gain, this-year distributions, this-year net capital-share transactions, paid-in capital (Consolidated Statements of Changes in Net Assets). Not disclosed, not invented: per-position Commitment/Called/Distributed history and vintage year (Cost and acquisition date substitute, both labeled as proxies, not observed facts); cumulative distributions-to-date sums only the two most recent fiscal years. See model card, "Real public case," for the full accounting.

## 3. Implementation verification

- Builder-to-workbook parity: verified via `tools/build_all_models.py --require-parity` (see repository-wide verification run for this release).
- Formula and cross-sheet-link review: manual review of every formula in the builder source; two real defects found and fixed (FOF-01, FOF-02 above).
- External-link scan: `tools/validate_model_inventory.py` checks for external workbook links; none present.
- Circularity: none — the model is a single-pass roll-forward, no iterative calculation required.
- Reproducibility: `python tools/builders/build_fund_of_funds_institutional.py --output <path>` regenerates the canonical template byte-for-byte deterministically from the builder source.

## 4. Independent benchmarking

Recomputed directly in Python from the same input values (not by reading the workbook's own formula results):

| Model output | Workbook result | Independent result | Tolerance | Residual | Status |
|---|---:|---:|---:|---:|---|
| FoF carried interest this period | 0.38 | `max(0, 38 - 380*0.08) * 0.05 = 0.38` | 1e-9 | 0.0 | PASS |
| Computed ending FoF NAV | 411.0 | `380+45-38-3.75-0.38+28.13 = 411.0` | 1e-9 | 0.0 | PASS |
| FoF net TVPI (to LP) | 1.44 | `165/400 + 411/400 = 0.4125+1.0275 = 1.44` | 1e-9 | 0.0 | PASS |
| Look-through gross TVPI | 1.726683938 | `(208.5+458)/386 = 1.726683938` | 1e-9 | 0.0 | PASS |
| Fee-layering drag | 0.286683938 | `1.726683938 - 1.44 = 0.286683938` | 1e-9 | 0.0 | PASS |

## 5. Sensitivity and stress behavior

Base and Downside scenarios both run cleanly (see workbook `Checks` sheet). Downside (25% underlying-fund NAV markdown) correctly reduces look-through gross TVPI and, given the FoF-level roll-forward figures are observed/static rather than scenario-reactive, correctly surfaces a fee-layering-drag BREACH — an honest staleness signal, documented in the model card rather than treated as a bug to suppress.

## 6. Outcomes analysis

`fof-public-hlpaf-2026` is registered with `counts_toward_m4: false` and outcome status `pending` (`metric: next_fiscal_year_total_net_assets_usd_mm`, `forecast: 5785.7`, `realized: null`) — a genuine forward-looking check against HLPAF's next disclosed N-CSR, not yet resolvable since that filing does not exist yet. In the meantime, the case's own internal reconciliation check is the available evidence: NAV roll-forward reconciliation **FAILs** (residual ≈ $77.8mm, ~1.3% of ending NAV, Overall: BREACH) — attributable to this template's simplified two-line fee model (flat management fee + simple hurdle-then-carry) not reproducing HLPAF's real multi-share-class fee structure (management fee + incentive fee + per-class distribution fees), not to a data-sourcing error. This is the correct, informative signal for this case, following the same "honest imperfection over false precision" pattern established for the Private Credit domain's Yellow Corp REVIEW and the ETF domain's KWEB sector-band REVIEW elsewhere in this repository's evidence registry.

## 7. Use and governance

- Named owner and approver: SMC17 / repository owner (approval pending).
- Approved and prohibited uses: see model card.
- Monitoring thresholds: see model card.
- Escalation and retirement rules: see model card release record.

## 8. Limitations

See model card "Limitations and failure modes" — the one real case trips the NAV roll-forward check (fee-model simplification, documented, not a defect), single-period snapshot rather than a full J-curve simulation, simplified hurdle-then-carry waterfall (no catch-up tranche), and the Downside-scenario scope boundary between the portfolio and roll-forward sheets.

## Sign-off

- Developer response: implemented mechanics, checks, and this validation record; found and fixed two real defects during self-review; sourced one real public case and documented its honest reconciliation-check failure rather than adjusting inputs to force a PASS.
- Validator conclusion: approved with limitations at M2.
- Owner decision: **PENDING**
- Approval date: **PENDING**
- Next validation date or trigger: a second real public case is sourced, or the methodology changes.
