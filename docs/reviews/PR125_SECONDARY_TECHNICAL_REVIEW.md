# PR #125: secondary technical review and owner acceptance

**Decision:** accepted for engineering integration by the repository owner on
12 November 2026. The owner identified the original project as their
Claude-assisted implementation, accepted ChatGPT as a second model reviewer,
and instructed finalization.

**Reviewer:** ChatGPT, operating through Codex. This review is a second-model
technical challenge of the project. ChatGPT also performed the integration
repairs and documentation in this session; it is not presented as a reviewer
with no contribution to the integration. The owner explicitly accepts that
review arrangement for this PR.

**GitHub identity:** the authenticated account is SMC17, which is also the PR
author. No non-author APPROVED review is fabricated. This is an owner-directed
engineering acceptance with a disclosed AI review, not a passed non-author
GitHub approval or an independent human sign-off.

## Reviewed scope and evidence

The freshly checked revision is
`19dd9ca97c40be5723537a45f26cdfefa0494220`. The final acceptance commit adds
review documentation and this PR's policy exception only. It does not change
model formulas, financial values, manifests, templates or maturity declarations.

Checks ran again from an archive of that exact revision, with logs outside the
source tree. Python 3.12.13 and LibreOffice Calc 26.8.2 on macOS ARM64:

| Check | Result |
| --- | --- |
| Whole suite, ResourceWarning treated as error | 596 tests pass |
| Template regeneration and semantic parity | 27/27 |
| Presentation parity | 27/27 |
| Recalculated workbook reference checks | All nine pass |
| Data conventions and controlled vocabulary | Pass |
| Share-series integrity and standards conformance | Pass with existing warnings/limitations retained |
| Forecast registration | Pass |

Technical challenge covered the reported-cost EBIT/EBITDA contract and
depreciation bridge, explicit historical overlays, input-cell detection,
corporate/equity verdict dependencies, source/assumption classifications,
and the tests that distinguish a dead forecast base from a populated one.
The emitters preserve existing sourced cells and identify their own generated
entries for repeatability. Historical forward-driver selection excludes later
fiscal periods. No unresolved regression in this engineering scope was found
in the rerun or focused review.

The [challenge packet](CORRECTNESS_PR125.md) retains the review questions and
the broader reproduction commands. Automated reference checks and this review
do not constitute validation for financial use.

## Limits retained with acceptance

- The annual-series corpus deduplicates observations by latest filing. Period
  cutoffs do not prove that each fact was publicly available on the case date.
  These are retrospective historical cases, not demonstrated point-in-time
  forecasting backtests. Filing-time availability needs its own reconstruction.
- The Tesla impairment-inclusive EBITDA proxy remains explicitly scoped; it is
  not relabeled as pure reported EBITDA. Forward tax/share choices and BASE
  reproduction exceptions remain declared.
- Share-series warnings and five unverified standards requirements remain
  visible. Owner authority does not turn an unverified external standard into
  a verified one.
- Source reachability is a dependency check. It cannot establish the economic
  adequacy of a verdict, detect every hard-coded copy or validate every
  sensitivity table.

## Authority and maturity

This owner decision authorizes merging PR #125. The existing external-review
workflow is retained for other changes; it is not rewritten to create a general
self-approval route. Repository hosting protections are not disabled.

No entry is written to `governance/signoff.json`, no model is promoted to M3,
and no model is described as validated for use. Those are separate decisions
from accepting this engineering integration.
