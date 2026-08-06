# Model Card: Software & SaaS

## Identity

- Model ID: 31
- Domain: Software & SaaS
- Archetype: SOFTWARE
- Sector group: TMT · Subsector: software
- Version: 1.0.0
- As-of date: 2026-08-06
- Owner: SMC17 / repository owner
- Developer: Claude Code
- Independent validator: `tools/verify_reference_calcs.py::check_software_arr_rollforward` (pure-Python oracle, recalculated via LibreOffice)
- Approver: **PENDING STAKEHOLDER SIGN-OFF**
- Risk tier: Tier 1
- Declared maturity: **M1** — engine complete and oracle-verified; no real public instance yet
- Intended horizon: corporate_5y

## Why this is a separate model, not a BASE instance

The generic three-statement archetype takes revenue growth as an input. For a
subscription business that inverts the causality: revenue is a *consequence* of
an ARR balance rolling forward through new bookings, expansion, contraction and
churn. Modeling it the generic way hides the only thing that matters — whether
the installed base is growing or shrinking before new logos are counted.

Three further drivers the BASE archetype does not represent:

- **Revenue mix.** Subscription and services carry very different gross margins.
  Blended margin moves with mix even when neither component changes.
- **S&M as investment.** CAC payback and magic number express whether
  acquisition spend returns within a contract life. A company can be
  GAAP-unprofitable while compounding well, and the model must be able to show
  that rather than obscure it.
- **Stock-based compensation.** Routinely 10-25% of revenue for listed software
  companies. It is added back to cash flow but kept on its own line, because it
  is real dilution even when it is not a cash cost.

## Intended use

### Approved uses
- ARR and retention analysis for a subscription business
- Customer-acquisition efficiency and payback assessment
- Rule of 40 growth-versus-profitability framing
- Sector-appropriate operating forecast for TMT/software targets in the universe

### Prohibited or unsupported uses
- Live capital, fiduciary, regulatory, or tax use without named human approval
- Representing template driver defaults as any specific company's disclosed figures
- Applying this archetype to non-subscription businesses, where ARR mechanics do not hold

## Domain engines

| Engine | Sheet | Status | Validation |
|---|---|---|---|
| `arr_rollforward` | `ARR Rollforward` | Implemented | Oracle-recomputed cohort balance; NRR/GRR ordering |
| `revenue_disaggregation` | `Operating Model` | Implemented | Total = subscription + services; blended margin bounded by components |
| `operating_model` | `Operating Model` | Implemented | SBC add-back ordering check |
| `unit_economics` | `Unit Economics` | Implemented | Magic number, gross-profit-weighted CAC payback |
| `rule_of_40` | `Rule of 40` | Implemented | Computed from model outputs, not quoted |

## Stakeholder perspectives

| Perspective | Surface | What it reads |
|---|---|---|
| management | `Unit Economics` | Whether acquisition spend is returning; where to add or cut |
| public_investor | `Rule of 40` | Growth-versus-profitability trade-off on FCF, not just operating margin |
| growth_equity_investor | `ARR Rollforward` | Installed-base durability: NRR excluding new logos, and GRR beneath it |

## Material drivers

All drivers ship as template defaults and are explicitly **not** any company's
figures. Under the repository modeling standard, a real instance either sources
each one from disclosure or grounds its range in published industry statistics
(see `standards/universe/source_stack.json`, Damodaran entry). A hardcoded
number with no traceable basis is not permitted.

| Driver | Base | Downside | Grounding route |
|---|---:|---:|---|
| New / expansion / contraction / churn rates | 22% / 14% / 4% / 8% | 12% / 8% / 7% / 13% | Issuer ARR and retention disclosure |
| Subscription / services gross margin | 80% / 15% | 76% / 5% | Revenue disaggregation note |
| S&M, R&D, G&A (% revenue) | 38% / 22% / 12% | 42% / 24% / 13% | Income statement; industry ranges |
| Stock-based compensation (% revenue) | 18% | 20% | Equity compensation note |

## Checks

Nine visible checks, including the two that catch the sector's classic errors:
net revenue retention must exceed gross revenue retention (an NRR that silently
includes new logos breaks this), and blended gross margin must sit between its
subscription and services components (a mix or margin error breaks this).

## Limitations

- No real public instance yet — the reason this is M1 and not M2.
- Single ARR cohort, not a per-vintage cohort table; vintage-level retention
  decay is not modeled.
- Services revenue is modeled as a ratio to subscription rather than
  independently contracted.
- No deferred revenue or billings-versus-revenue bridge; RPO is not represented.
- Annual periods only. Quarterly seasonality in bookings is not captured.

## Monitoring

| Metric | Warning | Breach | Action |
|---|---:|---:|---|
| net_revenue_retention | 1.05 | 1.00 | Investigate contraction and churn; below 100% the installed base shrinks before new logos |
| gross_profit_cac_payback_months | 24 | 36 | Review sales efficiency against contract life |
| rule_of_40 | 0.30 | 0.20 | Escalate growth-versus-margin trade-off to owner |

## Release record

- Active release: 1.0.0 · Rollback: none (initial)
- Validation record: `31_Software_SaaS/validation.md`
- Stakeholder sign-off: pending
