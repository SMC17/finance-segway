# Agent tools (L3)

Fail-closed, provenance-required interfaces over flagship domain builders.

See `docs/AGENT_TOOL_CONTRACT.md` and `docs/AI_NATIVE_GOLDMAN_ROADMAP.md`.

| Tool | Domain | Status |
|------|--------|--------|
| `private_credit_underwrite.py` | 05 Private Credit | **Wired** — provenance validated against live Assumptions-sheet labels; writes via the governed manifest path (`tools/model_instance_release.py`); recalculates for real via LibreOffice; reads Checks back |
| `lbo_underwrite` | 03 PE | Planned |
| `restructuring_screen` | 24 Distressed | Planned |
| `dcf_comps` | 01 IB | Planned |

## Private Credit

```bash
# Refresh EDGAR facts
python tools/data_fabric/edgar_company_facts.py --ticker ARCC --cik 1287750

# Materialize / refresh the public BDC reference instance (real EDGAR facts)
PYTHONPATH=. python tools/agents/private_credit_underwrite.py --use-ares-fixture

# Demo path (fictional facts, writes to .agent-tool-scratch/ -- never a real instance)
PYTHONPATH=. python tools/agents/private_credit_underwrite.py --demo
```

Every instance in `05_Private_Credit/instances/` uses the same flat
`<slug>.xlsx` + `<slug>.manifest.json` + `<slug>.receipt.json` convention
(no per-instance subdirectory) — this matches every other domain in the
repo, so a builder or governance script never has to special-case Private
Credit's layout.

- `instances/public_ares_2024.xlsx` — real reference instance, Checks PASS
- `instances/public_yellow_2022_stress.xlsx` — real adversarial instance, Checks REVIEW (correctly: Yellow breached covenants and filed Chapter 11)
- `instances/public_ares_capital_2024.xlsx` — real, agent-tool-drafted portfolio proxy, Checks REVIEW (see its `.thesis.md` sibling for why)

Agents must not invent numbers. Excel remains the receipt: `run()` always
recalculates via LibreOffice and reads the actual Checks sheet back before
returning a status — it never hardcodes `NOT_RUN` or reports a status it
hasn't verified. Every manifest this tool writes is tagged
`classification: "agent_tool_draft"`, `counts_toward_M4: false`
unconditionally, so nothing it produces is silently counted as reviewed
evidence ahead of the Issue #7 human gate — regardless of whether the
underlying facts are real (EDGAR-sourced) or a demo fixture.
