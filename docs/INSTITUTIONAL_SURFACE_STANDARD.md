# Institutional Decision Surface Standard

Every workbook in finance-segway now carries the same **operational envelope**
while retaining domain-specific financial mechanics.

The standard is implemented by:

- `standards/domain_profiles/*.tsv`
- `tools/institutional_surface.py`
- `tools/promote_institutional_surface.py`
- `tools/build_institutional_control_plane.py`
- `tests/test_institutional_surface.py`

## What is standardized

Each workbook receives three idempotent sheets:

1. **Institutional Surface** — decision arena, committee artifact, key outputs,
   insider questions, scenario families, primary diligence documents,
   independent challenge tests, known failure modes, and regulatory anchors.
2. **Challenge Log** — append-only independent challenge, override, evidence,
   remediation, accepted-risk, and closure workflow.
3. **Lineage Map** — source class, cadence, control, system/provider, as-of
   vintage, owner, transformation, downstream use, and status.

Workbook-level defined names expose `FS_MODEL_ID`, `FS_DOMAIN`, and
`FS_MATURITY` for automated cataloging and cross-model tooling.

## What is not standardized

Financial mechanics are **not** forced into a generic template. An LBO cash
sweep, an insurance development triangle, a structured-credit waterfall, a
volatility surface, and a sovereign DSA remain economically distinct. The
common layer governs decision use, evidence, challenge, lineage, refresh, and
release discipline.

## Evidence boundary

The surface is necessary for M3 but not sufficient. It does not create public
source snapshots, independent validation, effective challenge, sign-off, or
outcome-monitoring history. Blank operational fields are deliberate evidence
gaps, not implied completion.

## Institutional control plane

`00_Control_Plane/Finance_Model_Control_Plane.xlsx` is generated from the
inventory, profile registry, public-case index, and release evidence. It exposes:

- maturity and release coverage;
- engine, perspective, and reference-check saturation;
- decision arenas and insider questions;
- source and refresh requirements;
- cross-domain scenario and challenge libraries;
- public instances and cryptographic receipts;
- evidence-gated M1→M2→M3→M4 roadmap.

## Model-risk baseline

The repository uses the Federal Reserve's April 17, 2026 revised model-risk
guidance as the global governance baseline and maps domain-specific anchors
where useful. Applicability must always be documented rather than assumed.
