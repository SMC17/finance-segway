# Agent Tool Contract (L3)

**Status**: Binding — three of four flagship tools on the original implementation order are shipped  
**Depends on**: `docs/AI_NATIVE_GOLDMAN_ROADMAP.md`, domain builders, Checks sheets, source registers

## Principle

An agent may only produce numbers that a governed engine has computed and that a Checks sheet can verify.  
The Excel workbook remains the receipt. The agent’s job is to gather allowed inputs, invoke the tool, and package the receipt + short narrative. It does not invent math.

## Tool shape (stable)

Every flagship tool exposes roughly:

```text
Input
  - domain_id          e.g. "05_Private_Credit"
  - instance_slug      e.g. "acme_unitranche_2026"
  - inputs             structured facts (JSON) with source provenance for each material field
  - scenario           optional (Base / Downside / ...)
  - as_of              date

Process
  1. Validate that every material input has provenance (source, as-of, retrieval date).
  2. Call the domain builder / reference engines (never re-implement formulas in the agent).
  3. Write or update the instance workbook under <domain>/instances/<slug>/.
  4. Run Checks; fail closed if any identity fails.
  5. Append RefreshLog entry.
  6. Return paths + Checks status + headline decision outputs.

Output
  - workbook_path
  - checks_status      PASS | REVIEW | FAIL
  - headline           dict of decision metrics (MOIC, DSCR, recovery, etc.)
  - sources_written    list of source_register rows added
  - refresh_log_entry  summary
```

## Fail-closed rules

- Missing provenance on a material input → reject.  
- Checks FAIL → do not present the workbook as a client deliverable.  
- Agent narrative must not contain numeric claims that are absent from the workbook.  
- No direct write to inventory maturity fields; maturity is owned by validators and evidence packs.

## First tools to implement (order)

1. `private_credit_underwrite` → 05 — shipped, `tools/agents/private_credit_underwrite.py`
2. `lbo_underwrite` → 03 — shipped, `tools/agents/lbo_underwrite.py`
3. `restructuring_screen` → 24 — shipped, `tools/agents/restructuring_screen.py`
4. `dcf_comps` → 01  

Each ships with a golden-path test: fixed public inputs → deterministic workbook hash (or semantic parity) + Checks PASS.

## Relationship to research rails

RAM / kdb / dbt outputs may be registered as *inputs* (regime stats, realized vols, etc.) only through the Sources discipline. They never bypass the domain engine.

## Non-goals

- General chat interface over all 24 domains before flagships are tool-ready.  
- Agent autonomy that mutates frozen public instances without an explicit refresh protocol.  
- Replacing Cover / Checks / RefreshLog with free-form LLM text for external clients.
