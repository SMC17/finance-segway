# Consulting Operating System

Finance-Segway's consulting wing is a governed company operating model, not a
directory of AI vendors and not a collection of prompt wrappers. It connects
functional work to P&L drivers, typed decisions, evidence, controls, and realized
outcomes.

The initial release deliberately hand-rolls the dependency-free core. It does
not integrate with email, calendars, CRM, ERP, HRIS, ticketing systems, model
providers, cloud runtimes, media generators, or external agent platforms.

## Architecture

The system has six layers.

1. **Operating graph** — maps acquisition, pricing, delivery, quality,
   retention, billing, capacity, procurement, and talent dependencies.
2. **Metric and evidence layer** — defines metric ownership, lineage, dated
   observations, diagnostic questions, and hash-chained evidence.
3. **Functional kernels** — deterministic reference implementations for the
   highest-value decisions within each business function.
4. **Agent control plane** — declares skills, autonomy, read/write scopes,
   required evidence, approvals, and limitations before execution.
5. **Value and portfolio layer** — converts operating interventions into
   confidence-adjusted NPV, payback, risk penalties, dependencies, and a
   budget-constrained sequence.
6. **Validation and monitoring** — tests capability claims, runs a synthetic
   integrated benchmark, and preserves receipts without claiming client proof.

## Functional coverage

| Functional surface | Hand-rolled core |
|---|---|
| Engineering | Delegation-risk classification, required controls, assisted-throughput measurement |
| Data and analytics | Semantic metric catalog, aliases, exact evaluation, ownership, and field lineage |
| Knowledge and meetings | Role-scoped BM25 retrieval with citations; structured decisions, actions, risks, and notes |
| Marketing and GEO | Feature-based ICP scoring, prompt-level visibility metrics, share of voice, and brand-policy checks |
| Sales and pricing | Lead response and funnel telemetry; inventory-, discount-, margin-, and value-controlled quote construction |
| Customer service and success | Case priority/SLA/escalation and explainable customer-health/renewal risk |
| Finance and treasury | Rolling base/downside cash forecast, close control, spend decisions, and collections priority |
| Procurement | Policy-controlled requests and contract/PO/invoice leakage audit |
| People and talent | Skills- and evidence-based ranking, internal-mobility support, and hiring-funnel telemetry |
| Operations and delivery | Demand forecast, capacity plan, skills-aware dispatch, and contribution-at-risk |
| Quality and compliance | First-pass yield, defect, rework, and compliance-failure metrics |
| Legal | Structured contract-policy exception detection; no legal interpretation |
| IT and security | Ticket routing/SLA and least-privilege, time-bound access decisions |
| Creative | Brief completeness, production-tier selection, claims/source requirements, and review routing |

`standards/consulting/capability_catalog.json` is the canonical machine-readable
inventory. `tools/validate_consulting_catalog.py` rejects unsupported maturity,
missing functions, missing tests, and broken implementation references.

## Agent control plane

`finance_segway.consulting.runtime.AgentRuntime` is intentionally local and
deterministic. A registered skill declares:

- risk tier and minimum autonomy;
- required evidence;
- allowed read and write scopes;
- whether repeated execution is idempotent;
- the pure handler that performs the calculation.

An agent separately declares its purpose, skills, autonomy, scopes, success
metrics, and limitations. Execution is rejected when the agent, calling context,
or evidence pack lacks authority. High-risk skills require named approval. Each
attempt produces a hash-chained receipt covering request and output hashes,
status, actor, and approval reference.

This is not a security sandbox and does not create external authority. It is the
policy and evidence kernel to place inside a sandbox later.

## P&L and refounding work

`OperatingModel` makes the company value chain explicit and computes:

- activity utilization and bottlenecks;
- annual labor cost and quality loss;
- constrained units and contribution at risk;
- labor, error, and capacity intervention value;
- rollups by business function.

`simulate_refounding` compares baseline and redesigned service economics using
explicit volume, labor minutes, error loss, variable cost, implementation cost,
and ongoing platform cost. It reports contribution margins, FTE equivalents,
capacity multiplier, annual value created, and payback. It does not assume that
automation savings will be realized.

`evaluate_case` and `select_portfolio` then apply feasibility, adoption,
evidence confidence, risk tier, dependencies, delivery time, budget, and hurdle
rate. This prevents an attractive demo from being treated as an investable
business case without evidence.

## Consulting engagement sequence

1. Map the client's activity graph and P&L drivers.
2. Define executive questions, authoritative metrics, owners, and evidence.
3. Establish the baseline before proposing an agent or redesigned process.
4. Build and independently test only the relevant deterministic kernels.
5. Run reference and adversarial cases within declared read/write scopes.
6. Quantify a confidence- and risk-adjusted initiative portfolio.
7. Deliver a decision record, limitations, acceptance record, and monitoring plan.
8. Measure realized outcomes against the frozen baseline and retire failed uses.

Client system integrations and confidential engagement repositories remain
outside this public core.

## Maturity

| Level | Meaning |
|---|---|
| A0 | Decision, owner, metrics, risks, and evidence are specified |
| A1 | Typed deterministic core and unit tests exist |
| A2 | Reproducible multi-step synthetic benchmark and receipts exist |
| A3 | Controlled client use, validation, effective challenge, and sign-off exist |
| A4 | Maintained live use, outcomes, thresholds, rollback, and retirement exist |

The initial functional catalog is A1. The synthetic industrial-services case
integrates the operating graph, initiative portfolio, quote control, scoped
knowledge retrieval, agent runtime, evidence ledger, and refounding economics.
It is engineering evidence only and does not promote any capability to A3 or A4.

## Explicit exclusions

- no copied proprietary workflows, prompts, models, or vendor implementations;
- no autonomous hiring rejection, legal approval, payment, purchasing, access
  grant, customer communication, publication, or production deployment;
- no claims that a deterministic score replaces accountable judgment;
- no healthcare revenue-cycle module in the generic core; it belongs in a
  separately validated vertical pack if pursued;
- no production maturity without external evidence and outcome history.
