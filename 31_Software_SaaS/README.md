# 31 Software & SaaS

**Archetype:** `_template_SOFTWARE.xlsx` · **Sector group:** TMT · **Subsector:** software

The first *sector* model in the library. ARR cohort roll-forward, subscription/services revenue disaggregation, customer-acquisition efficiency, and Rule of 40.

This exists because a software business and an industrial business are not the same model with different inputs. Revenue here is a consequence of an ARR balance rolling forward, not an independent growth assumption; sales & marketing is an investment with a payback period, not an expense ratio; and stock-based compensation is large enough (routinely 10-25% of revenue) that burying it inside opex makes a model useless for decisions.

Declared maturity: **M2**. Two real, sourced instances:

- `software-public-adobe-fy2025` (Adobe Inc., conventional/Base) — RPO and cost layer sourced from disclosed FY2025 facts; ARR flow rates proxy revenue as ARR scale (no issuer discloses ARR in XBRL).
- `software-public-uipath-fy2023-stress` (UiPath, Inc., adversarial/Downside) — UiPath discloses ARR directly. FY2023, the year its dollar-based net retention rate first cratered (145% -> 123%); the following year's 10-K shows it fell further, to 119% — a real, disclosed, persistent stress, not a one-off. UiPath's real FY2023 sales & marketing ratio (66.3% of revenue) exceeds even this template's own Downside illustrative default (42%).

Instances live in `instances/`. Populate from a real filer's ARR and retention disclosures via a manifest, then run `tools/recalc.py`.
