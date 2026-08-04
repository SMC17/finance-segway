# Finance Model Library Integration Ledger

This ledger records the component-level synthesis of the Claude Code and
ChatGPT/Codex implementation lanes. PR #3 established the engineered 2.1.0
library on `main`. PR #5 is the institutional operating-system tranche.

## Reconciled implementation lanes

| Lane | Retained contribution |
|---|---|
| Claude Code | Complete 24-domain baseline, workbook breadth, original builders, broad formula hardening, and the independent spreadsheet regression suite |
| Earlier ChatGPT/Codex prototypes | Selected financial identities and credit mechanics; obsolete shared workbooks, binaries, and writers rejected |
| Engineered synthesis | Canonical financial engines, domain contracts, semantic parity, recalculation, public instances, receipts, and atomic artifact release |
| Institutional tranche | Domain operating profiles, decision surfaces, challenge logs, lineage maps, control plane, and profile-bound release evidence |

Components are combined according to economic identity and test evidence, not
according to which agent or branch created them.

## Current verified architecture

- Inventory version: **2.1.0**
- **24** core archetypes
- **24 M2 Decision Models** and **0 M1 Correct Skeletons**
- **24** domain-specific institutional profiles
- **24** canonical workbooks with `Institutional Surface`, `Challenge Log`, and `Lineage Map`
- **48** source-addressed public historical/adversarial cases
- **0** synthetic manifests, workbooks, or receipts
- A nine-sheet institutional control plane under `00_Control_Plane/`
- **0 M3** and **0 M4** claims without named human challenge and maintained operation

## Standardized operating envelope

The common layer standardizes how a model is used without forcing different
financial instruments into a generic calculation template. Every domain now
specifies:

- the actual decision arena and committee artifact;
- decision outputs and binding constraints;
- governing and diligence documents;
- practitioner-level questions that expose weak underwriting;
- scenario families and independent challenge tests;
- recurrent implementation and interpretation failures;
- source classes, refresh cadence, controls, and ownership;
- applicable regulatory or methodological anchors.

An LBO cash sweep, a loss-development triangle, a structured-credit waterfall,
a volatility surface, and a sovereign debt sustainability analysis remain
financially distinct.

## Completed component decisions

| Component | Decision | Canonical implementation |
|---|---|---|
| Repository skeleton and domain coverage | Retain | Claude baseline |
| Spreadsheet independent-oracle suite | Retain and update | `tools/verify_reference_calcs.py` |
| Pure-Python financial engines | Combine and extend | `finance_segway/` and reference engines |
| Model inventory and maturity gates | Retain | `standards/model_inventory.json` |
| Whole-library workbook audit | Require | `tools/workbook_engineering.py` |
| Semantic builder parity | Require | `tools/workbook_parity.py` and `tools/build_all_models.py` |
| Model-specific institutional parity | Add | per-model enrichment after each shared builder runs |
| Domain operating profiles | Add | `standards/domain_profiles/*.tsv` |
| Workbook decision surface | Add | `tools/institutional_surface.py` |
| Full-library surface promotion | Add | `tools/promote_institutional_surface.py` |
| Portfolio control plane | Add | `tools/build_institutional_control_plane.py` |
| Release evidence | Extend | profile-registry hash and per-model surface evidence |
| Artifact promotion | Preserve single writer | stale-head-guarded atomic GitHub release |
| Maintained instance plumbing | Preserve and enrich | provenance, RefreshLog, SHA receipts, and enriched templates |
| Weekly refresh | Preserve read-only behavior | report artifact, not an uncontrolled binary writer |

## Institutional release gates

1. Source compiles and all unit tests pass.
2. The profile registry covers exactly the 24 inventory domains.
3. Domain-specific workbook contracts pass before recalculation.
4. LibreOffice recalculation produces zero cached formula errors.
5. Domain contracts still pass after spreadsheet normalization.
6. Every canonical workbook receives and validates its domain-specific operating surface.
7. Each builder reproduces each model-specific committed workbook semantically.
8. External links and literal Excel errors are absent.
9. All 48 public historical/adversarial instances validate and bind to current receipts.
10. Release evidence hashes builders, workbooks, and the institutional profile registry.
11. The institutional control plane rebuilds from inventory, profiles, instances, and evidence.
12. Any source-head movement aborts rather than rebasing stale binaries.

## Explicit maturity boundary

The new decision surfaces make M3 evidence gaps visible; they do not fill them.
M3 still requires public source snapshots, populated model cards, independent
validation, effective challenge, stakeholder sign-off, and externally sourced
cases. M4 additionally requires maintained public instances, repeated refresh
history, realized-outcome comparison, and documented model changes over time.

The next frontier is therefore two-sided:

1. continue promoting M1 domains through deeper financial mechanics and independent oracles;
2. begin a public evidence program that can legitimately move selected M2 models to M3 and eventually M4.
