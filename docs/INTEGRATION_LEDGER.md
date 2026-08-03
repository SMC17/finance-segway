# Finance Model Library Integration Ledger

This ledger tracks the synthesis of the active Claude Code and ChatGPT/Codex lanes. It is intentionally component-specific: a branch can contain the best implementation of one model and a weaker implementation of another.

## Comparison point

| Lane | Branch | Role |
|---|---|---|
| Claude Code | `claude/excel-models-templates-opensource-26937n` | Broad archetype construction, model-specific hardening, independent regression tests |
| ChatGPT/Codex | `agent/integrate-finance-model-library` | Institutional credit/public-finance depth, governance, structural validation, refresh hardening |
| Synthesis | `agent/synthesize-finance-model-library-v2` | Current integration lane; based on Claude's latest validated tree |

## Current component decisions

| Component | Decision | Current source of truth | Remaining gate |
|---|---|---|---|
| Repository skeleton and 24-domain coverage | Retain | Claude lane | Confirm all templates and builders remain paired |
| Cross-model regression suite | Retain | Claude lane | Keep independent-oracle checks green |
| Private credit lender yield / OID analysis | Combine | Claude workbook + institutional extension design | Fuse with five-year CFADS, debt/cash schedule, covenant headroom, recovery/LGD |
| Debt finance | Combine | Shared credit archetype | Add instrument-specific issuance/refinancing lens without duplicating private credit |
| Public finance sovereign DSA | Retain and extend | Claude lane | Preserve primary-balance debt dynamics while adding operating forecast and liquidity schedules |
| Revenue-bond coverage | Combine | Claude lane + institutional extension design | Integrate DSCR, reserves, debt burden, pension burden, and scenarios |
| Weekly refresh workflow | Supersede | Synthesis lane | Read-only workflow; upload report artifact rather than commit generated CSVs |
| Parallel-agent governance | Retain | Synthesis lane | Keep ledger current on every integration PR |
| Binary workbook publication | Review | Valid Claude Git objects | Generate deeper release artifacts only through reproducible, validated build path |

## Claude upgrades queued for component review

The latest Claude lane includes broad changes across specialized archetypes. Review in this order:

1. Insurance and actuarial
2. Structured finance / securitization
3. Project finance
4. Quantitative / systematic
5. Private equity / merchant banking
6. Options / derivatives and fixed income
7. Commodities and crypto
8. Asset management, venture capital, fintech, microfinance, trade finance, real estate, restructuring, and risk

For each component, record:

- Financial identities added or corrected
- Independent benchmark tests
- Source and audit improvements
- Scenario or sensitivity improvements
- Builder/workbook parity
- Any regression versus the previous baseline

## Merge blockers

- Synthesis CI must pass.
- No workbook may contain external links or literal Excel errors.
- Active Claude changes must be triaged through this ledger rather than merged wholesale without review.
- Credit and public-finance institutional builders must be reconciled with the reviewed binary release artifacts.
- The owner must explicitly approve promotion from draft to merge-ready.
