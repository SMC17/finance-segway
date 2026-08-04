# Institutional Control Plane

The generated `Finance_Model_Control_Plane.xlsx` is the portfolio-level operating
system for the model library. It is rebuilt from repository sources and committed
only by the atomic release workflow.

Do not edit the binary as a source of truth. Update:

- `standards/model_inventory.json`
- `standards/domain_profiles/*.tsv`
- benchmark manifests and receipts
- release evidence

Then run the complete engineered release.
