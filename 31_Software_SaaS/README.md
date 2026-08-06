# 31 Software & SaaS

**Archetype:** `_template_SOFTWARE.xlsx` · **Sector group:** TMT · **Subsector:** software

The first *sector* model in the library. ARR cohort roll-forward, subscription/services revenue disaggregation, customer-acquisition efficiency, and Rule of 40.

This exists because a software business and an industrial business are not the same model with different inputs. Revenue here is a consequence of an ARR balance rolling forward, not an independent growth assumption; sales & marketing is an investment with a payback period, not an expense ratio; and stock-based compensation is large enough (routinely 10-25% of revenue) that burying it inside opex makes a model useless for decisions.

Declared maturity: **M1**. The engine is built, oracle-verified, and internally consistent, but no real public instance exists yet — see `model_card.md`.

Instances live in `instances/`. Populate from a real filer's ARR and retention disclosures via a manifest, then run `tools/recalc.py`.
