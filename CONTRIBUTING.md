# Contributing

## Standards checklist (every model, every domain)

A model isn't done until it passes all of these:

1. **Recalculates with zero formula errors.** Run:
   `python3 tools/recalc.py <file.xlsx>` — must return `"status": "success"`.
2. **Every input is blue, every formula is black, every cross-sheet link is
   green.** See the Cover tab legend in `_template.xlsx` for the canonical
   definitions. No exceptions — this is what makes a model auditable by
   someone who didn't build it.
3. **Key assumptions are yellow-filled.** If reviewing this model in 90
   seconds, yellow cells should be the only things you need to sanity-check.
4. **Div/0 and blank-input guards.** Every formula that can divide by a
   blank/zero input must be wrapped in `IFERROR(...)`. Ship blank templates
   with zero cached errors, not just populated ones.
5. **Cover tab is complete**, including `Last refreshed` and (where
   applicable) `Next earnings/expiry/distribution date` — this is what the
   weekly refresh checker reads.
6. **RefreshLog tab exists and gets an entry on every material update** —
   date, trigger (earnings, rate move, manual review), what changed.
7. **Sanity-checked against a known reference before merging.** Hand-calc it,
   check put-call parity, cross-check against a published example — whatever
   applies to the archetype. State the check in the PR description.

## Adding a new archetype (a genuinely new type of model)

1. Confirm it doesn't already exist — check `README.md`'s domain table first.
2. Build it as `<DOMAIN>_template.py` using `tools/template_helpers.py` for
   consistent styling.
3. Add the domain to `tools/scaffold_repo.py`'s `DOMAINS` dict.
4. Run `tools/recalc.py` and fix every error before opening a PR.
5. Add the archetype's required tabs to `tools/weekly_refresh_check.py`'s
   `ARCHETYPE_REQUIRED_TABS` so the weekly job can detect structural drift.

## Adding a company/deal/instance to an existing domain

1. Copy the domain's `_template_<archetype>.xlsx` into its `instances`
   subfolder (e.g. `03_Private_Equity/deals/`).
2. Rename to the ticker/deal code.
3. Fill in the Cover tab completely, including refresh dates.
4. Fill in all blue (input) cells. Never overwrite black (formula) or green
   (link) cells directly — if a formula is wrong, fix it at the source.
5. Run the recalculator before committing.

## Weekly maintenance

`tools/weekly_refresh_check.py <path>` runs against the whole repo or a
single domain folder. It's wired into `.github/workflows/weekly-refresh.yml`
to run automatically and commit the report — see that file for schedule.
Treat a non-empty report as a to-do list, not a formality.

## PR review bar

Reviewers should reject (not just comment on) PRs that:
- Introduce formula errors on a clean recalc
- Break the color convention
- Skip the sanity-check step for a new archetype
- Leave the Cover tab's refresh dates blank on a populated (non-template)
  instance
