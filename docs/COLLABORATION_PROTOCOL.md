# Parallel-Agent Collaboration Protocol

This repository is developed through multiple independent engineering lanes. The goal is not to choose a winning branch; it is to preserve independent reasoning, compare implementations, and synthesize the strongest component-level result.

## Branch roles

- `main` — reviewed, merge-ready baseline only.
- `claude/<task>` — Claude Code implementation lane.
- `agent/<task>` — ChatGPT/Codex implementation lane.
- `agent/synthesize-<task>` — integration lane created from the strongest current upstream baseline.

No agent force-pushes, rewrites, or deletes another agent's active branch.

## Integration method

1. Freeze a comparison point by recording both branch SHAs.
2. Compare by component, not by total diff or line count.
3. Classify each change as:
   - **Retain** — stronger implementation with no material conflict.
   - **Combine** — complementary mechanics should coexist or be fused.
   - **Supersede** — replacement is demonstrably stronger and passes all prior tests.
   - **Reject** — incorrect, unauditable, duplicative, or below repository standards.
   - **Review** — insufficient evidence; do not merge yet.
4. Preserve independent-oracle tests whenever two implementations model the same result.
5. Merge only through a draft synthesis PR with a visible integration ledger.

## Workbook acceptance gates

A model change is not accepted because the workbook opens. It must pass:

- Formula, external-link, and literal-error scans.
- Required-sheet and formula-anchor contracts.
- Visible `Checks` status and source register.
- Explicit actual/forecast and Base/Downside boundaries where applicable.
- Builder-to-workbook reproducibility or a documented reviewed-release exception.
- Independent benchmark or hand-calculation checks for core mechanics.
- Render-based visual review of the highest-risk sheets.
- Weekly refresh compatibility without false stale-date warnings on blank templates.

## Conflict policy

- Prefer the implementation with the stronger financial identity and audit trail.
- Do not flatten two valid approaches when they answer different questions; expose both as separate lenses or modules.
- Never weaken tests to make a merge pass.
- If a binary workbook cannot be transferred safely, preserve the valid Git object and move the deeper logic into a reproducible builder until the next reviewed release artifact is generated.

## Merge authority

Synthesis PRs remain draft while either upstream implementation is still materially changing. `main` is updated only after CI is green, the integration ledger is complete, and the repository owner explicitly approves the merge.
