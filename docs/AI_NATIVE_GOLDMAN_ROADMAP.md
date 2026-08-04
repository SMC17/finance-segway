# AI-Native Goldman Roadmap

**Status**: Active operating thesis  
**Date**: 2026-08-04  
**Kernel**: Finance-Segway governed model library

## Thesis (non-negotiable)

Most AI finance products put a chatbot on top of weak or opaque models.  
We invert that: **build governed models first**, then let a fleet of agents use them without hallucinating math.

Goldman is three businesses. The 24 domains map onto them:

| Goldman business | Finance-Segway coverage |
|------------------|-------------------------|
| Deals & Financing | IB, CorpFin, PE, Merchant Banking, Private Credit, Debt Finance, Distressed, Project Finance, Structured |
| Markets | Options, Rates, Commodities, Risk, Quant/Systematic |
| Asset Management / Platform | Asset Management, Real Estate, Insurance, Fintech, Crypto, Microfinance, Trade Finance, Public Finance |

**Excel is not overhead — it is the product and the audit trail.**  
When a founder, lender, or allocator receives a deliverable, they get a workbook with:

- Cover (purpose / owner / limitations)
- Sources (dated provenance)
- Checks (identities tied)
- RefreshLog (what changed and why)

That is the SR-style compliance story. Competitors who only ship Python traces or chat transcripts cannot produce it.

**Operating model**

```text
Agents do the work
Python reference engines do the math
Excel is the receipt the client can audit
```

## Four layers

| Layer | Name | Status today | What “done” looks like |
|-------|------|--------------|------------------------|
| **L1** | Governed Model Library | **M2 across 24 domains** | Deterministic builders, independent oracles, inventory + maturity gates, institutional surfaces |
| **L2** | Data Fabric | Seed only (`db/` + `postgres_etl.py`) | Parsers and connectors that populate model inputs from public filings / market data and log every transformation into Sources |
| **L3** | Agent Analysts | Missing (unlock) | Each flagship archetype exposed as a tool with job description, allowed inputs, required Checks, and Excel receipt |
| **L4** | Trading & Distribution | Research rail only (RAM + kdb contracts) | Quant/Systematic + Risk driven by L2/L3, not by ad-hoc Excel |

Today we are at **L1 M2**. That is the foundational ~20% that almost everyone else skips. Do not dilute it.

## Six flagships (do not push all 24 to M3 at once)

Focus capital and evidence on six domains that cover both **service revenue** and **trading arm**:

### Service-revenue core (monetizable first)

1. **05 Private Credit** — CFADS, covenants, yield/OID, recovery/LGD  
2. **06 Debt Finance** — issuance, refinancing, maturity ladder  
3. **24 Distressed & Restructuring** — 13-week liquidity, recovery waterfall, fulcrum  

These three are the near-term advisory / underwriting product for lower-middle-market companies that cannot get a bulge-bracket team. Target: first paid work in months, not years.

### Sell-side / buy-side flex

4. **01 Investment Banking** — 3-statement, DCF, comps  
5. **03 Private Equity** — full LBO (already has real public instances + Postgres pilot)

### Trading arm (client zero after agents are reliable)

6. **09 Risk Management** + **14 Options & Derivatives** + **22 Quantitative & Systematic**  
   (treat as one flagship cluster for sequencing)

All other domains remain M2 skeletons and improve only when they unblock a flagship or a client engagement.

## M3 / M4 bar for each flagship (from existing standards)

For each flagship:

1. **Real-only evidence** — retire or clearly quarantine synthetic benchmarks (see Public Instance Program).  
2. Run `tools/scaffold_model_evidence.py <domain>` → model card, validation, source register.  
3. One **reference** + one **adversarial** real instance.  
4. At least **three material RefreshLog entries** and one documented outcome comparison → path to M4.  
5. Green CI, named owner, dated release.

PE already has real public instances (Home Depot, Macy’s adversarial). That is the template the other five must follow.

## L2 Data Fabric — contract (next engineering surface)

Current state: ETL only extracts *from* committed workbooks into Postgres.  
Required state: connectors that ETL *into* workbooks (or into a staging layer that builders consume) while writing provenance.

Minimum viable L2 for the service flagships:

- SEC EDGAR (10-K / 10-Q / 8-K) → structured facts for 3-statement / credit inputs  
- Public credit agreements / indentures (where redistributable) → covenant terms  
- Market data (rates, spreads, equities) already partially present via the research rail  

Every automated population must produce a row in `sources/source_register.csv` with as-of date, retrieval date, transformation, and checksum/snapshot pointer. A live URL alone is not evidence.

## L3 Agent Analysts — tool contract (thin, stable)

Agents never become the source of truth. They call tools that:

1. Accept only registered, dated inputs.  
2. Invoke the domain builder / reference engines.  
3. Emit a recalc-clean workbook (Cover, Sources, Checks, RefreshLog).  
4. Fail closed if Checks do not pass or sources are incomplete.

Example agent jobs (illustrative):

| Agent | Primary tools (domains) |
|-------|-------------------------|
| Private Credit Analyst | 05, 06, 20 |
| IB / PE Analyst | 01, 02, 03 |
| Restructuring Analyst | 24, 19 |
| Derivatives / Risk Analyst | 14, 09, 21 |

The Cover + Checks conventions are what make agent output trustworthy relative to generic document AI. That advantage is lost the moment an agent is allowed to invent a number outside a governed engine.

## Sequencing (do not invert)

```text
1. L1 flagships → real evidence → M3 (then M4 on 1–2 instances each)
2. L2 minimal connectors for those flagships only
3. L3 agents on the same six tools
4. One end-to-end demo: ticker / credit name → filings → models → Excel + short memo with every source dated
5. Service revenue on Private Credit / Debt / Distressed
6. L4 trading arm as client zero of the reliable agent layer
```

Trading before reliable agents is the classic inversion. Avoid it.

## Non-goals (explicit)

- Do not claim M3/M4 without the evidence packs and real instances required by the inventory.  
- Do not replace Excel receipts with chat logs for external deliverables.  
- Do not expand the research/RAM/kdb rails into the maturity claims of the core 24 domains.  
- Do not build a general “chat with any model” surface before the six flagships have real evidence and tool contracts.

## Near-term work packages (next 30–90 days)

| Priority | Package | Exit criteria |
|----------|---------|---------------|
| P0 | Real-only evidence push on 03 PE (already strongest) | Synthetic quarantine complete; model card + validation + source register live; RefreshLog discipline on public instances |
| P0 | Scaffold + first real reference instance for 05 Private Credit | Evidence pack + one public or public-derived credit case |
| P1 | Same for 06 Debt Finance and 24 Distressed | Evidence packs + at least one real instance each |
| P1 | Thin L3 tool interface draft for 05 and 03 | JSON/CLI contract: inputs → builder → workbook path + Checks status |
| P2 | Minimal L2: one EDGAR → 3-statement input path with Sources logging | End-to-end for one IB/PE name |
| P2 | Service packaging | One-page “what the client receives” (workbook + memo template) for private credit underwriting |

## Success metric for the next phase

Not “all 24 at M3.”  
**Six flagships with real evidence, one end-to-end agent demo that produces an auditable Excel receipt, and a clear path to first paid private-credit / debt advisory work.**

That is the foundation from which a top-tier raise and a strategic exit to a bank become credible. Everything else is downstream.
