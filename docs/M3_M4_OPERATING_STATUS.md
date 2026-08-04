# M3/M4 Operating Evidence Status

As of August 4, 2026, the nine engineered flagships have completed the automatable M3 evidence tranche without being falsely promoted.

## Implemented across all nine flagships

- Completed approved-use, prohibited-use, and limitation model cards
- Independent engineering validation records
- One conventional external historical case
- One adversarial external historical case
- Frozen source snapshots with SHA-256 digests
- Source registers and source-addressed workbook receipts
- LibreOffice recalculation of all 18 public case workbooks
- Recorded historical outcome evidence for at least one case per flagship
- Monitoring warning and breach thresholds with escalation actions
- Active release and rollback release records
- Replacement and retirement triggers
- Revalidation triggers and release changelogs

## Deliberately not completed by automation

Human stakeholder approval is pending for every flagship. The repository refuses to promote a model to M3 until named individuals fill the model-owner, domain-reviewer, and independent-validator roles and commit an approval conclusion.

Issue #7 is the effective-challenge and sign-off gate.

## Current maturity state

- M3 promoted: **0**
- M4 promoted: **0**

All flagship inventory records remain at M2.

## M3 remaining gate

Each flagship requires:

1. Named model owner
2. Named domain reviewer
3. Named independent validator
4. Review of approved and prohibited uses
5. Review of conventional and adversarial public cases
6. Acceptance or remediation of limitations
7. Approval of monitoring and escalation thresholds
8. Explicit conclusion: Approved, Approved with limitations, Remediation required, or Rejected
9. Additional material RefreshLog history from subsequent operating reviews

## M4 remaining gate

M4 requires evidence generated over time rather than documents generated in one release:

- At least two maintained public instances per flagship across releases
- Monitoring observations and exception escalation
- Outcome evidence accumulated over multiple releases
- Demonstrated rollback or replacement test
- Demonstrated retirement discipline when a model is no longer fit for use

One-time external historical cases and mathematical unit vectors never count as maintained M4 instances.

## Canonical evidence

- `standards/m3_evidence/flagship_registry.json`
- `standards/public_cases/index.json`
- Domain `model_card.md` and `validation.md` files
- Domain `sources/`, `governance/`, `outcomes/`, and `releases/` directories
- `m3-evidence-report.json`
- `.github/workflows/m3-evidence-operations.yml`
- GitHub issue #7
