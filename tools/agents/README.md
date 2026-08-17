# Agent tools (L3)

Fail-closed, provenance-required interfaces over flagship domain builders.

See `docs/AGENT_TOOL_CONTRACT.md` and `docs/AI_NATIVE_GOLDMAN_ROADMAP.md`.

| Tool | Domain | Status |
|------|--------|--------|
| `private_credit_underwrite.py` | 05 Private Credit | **Wired** — provenance validated against live Assumptions-sheet labels; writes via the governed manifest path (`tools/model_instance_release.py`); recalculates for real via LibreOffice; reads Checks back |
| `lbo_underwrite.py` | 03 Private Equity | **Wired** — same shape; real fixture reuses the already-sourced `pe-public-home-depot-2023` public case as a real-operating-profile proxy (not a real LBO -- Home Depot was never taken private, so deal-structure terms stay illustrative) |
| `restructuring_screen.py` | 24 Distressed & Restructuring | **Wired** — input surface is genuinely sheet-scoped (no single Assumptions sheet); real fixture reuses the already-sourced `distressed-public-hertz-2021-reorganization` public case |
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

## Private Equity (LBO)

```bash
# Real operating-profile proxy, reused from the existing public case (no new fetch needed)
PYTHONPATH=. python tools/agents/lbo_underwrite.py --use-home-depot-fixture

# Demo path (fictional facts, writes to .agent-tool-scratch/ -- never a real instance)
PYTHONPATH=. python tools/agents/lbo_underwrite.py --demo
```

Headline output reads Sponsor MOIC/IRR off `Returns Waterfall` at whichever
year column `Assumptions!Exit year` selects (columns C:I = years 1-7),
plus covenant-breach count and sponsor equity from `Sources & Uses` — all
read back from the LibreOffice-recalculated workbook, never computed in
this file.

## Distressed & Restructuring

```bash
# Real Chapter 11 exit-financing fact, reused from the existing public case
PYTHONPATH=. python tools/agents/restructuring_screen.py --use-hertz-fixture

# Demo path (fictional situation, writes to .agent-tool-scratch/)
PYTHONPATH=. python tools/agents/restructuring_screen.py --demo
```

`_template_RESTRUCTURING.xlsx` has no single Assumptions sheet — real
inputs live across four sheets (Recovery Waterfall, 13-Week Liquidity,
New Money, Liquidation vs Reorg), so this tool's `facts`/`provenance` are
sheet-scoped (`{sheet_name: {label: value}}`) rather than flat. Checks
also differ from the other two tools: status lives in column D of
"Decision & Checks" (not C), the overall verdict cell is `C14` labeled
"Overall model status" (not a row labeled "Overall"), and the vocabulary
is PASS / REVIEW / BREACH rather than PASS / REVIEW / FAIL. A BREACH
verdict from real submitted facts is a valid, honest reading (see
`distressed-public-bbby-2022-liquidity`, which correctly shows distress)
— only a literal recalculation failure is treated as a tool failure.
