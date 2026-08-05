# Consulting Operating System

Finance-Segway's consulting wing is a governed company operating model, not a
directory of AI vendors and not a collection of prompt wrappers. It connects
functional work to P&L drivers, typed decisions, evidence, controls, and realized
outcomes.

The initial release deliberately hand-rolls the dependency-free core. It does
not integrate with email, calendars, CRM, ERP, HRIS, ticketing systems, model
providers, cloud runtimes, media generators, or external agent platforms.

## Architecture

The system has nine layers.

1. **Operating and observed-process graph** — maps the expected value chain and
   discovers actual variants, handoffs, rework, cycle time, conformance, and
   delay from normalized event logs.
2. **Metric and evidence layer** — defines metric ownership, lineage, dated
   observations, diagnostic questions, and hash-chained evidence.
3. **Functional kernels** — deterministic reference implementations for the
   highest-value decisions within each business function.
4. **Decision-authority layer** — evaluates default-deny policy, deny
   overrides, obligations, expiring request-scoped approvals, and segregation
   of duties.
5. **Agent and workflow control plane** — declares skills, autonomy,
   read/write scopes, required evidence, typed DAG bindings, budgets, retries,
   failure policy, compensation, and replay semantics before execution.
6. **Value and portfolio layer** — converts operating interventions into
   confidence-adjusted NPV, payback, risk penalties, dependencies, and a
   budget-constrained sequence.
7. **Uncertainty and capacity layer** — runs seeded initiative Monte Carlo and
   service-stage queue simulations with explicit distribution assumptions.
8. **Evaluation and promotion layer** — runs reference, boundary, adversarial,
   regression, and metamorphic tests and enforces a real-case A2 evidence gate.
9. **Outcome and value-creation layer** — freezes baselines, guards outcome
   measurement, labels attribution limits, and bridges EBITDA and net debt into
   enterprise value, equity value, MOIC, IRR, and a 100-day plan.

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

## Cross-functional platform depth

| Platform component | Hand-rolled core | Current evidence |
|---|---|---|
| Observed process intelligence | Trace discovery, variants, transitions, cycle tails, rework, handoffs, conformance, cost of delay | A1 deterministic |
| Decision authority | Attribute conditions, default deny, deny override, obligations, scoped expiry, distinct approvers, segregation of duties | A1 deterministic |
| Workflow control | Typed DAG, bindings, budgets, retries, halt/continue/rollback, compensation, receipts, replay fingerprint | A1 deterministic |
| Evaluation | Weighted assertions, critical cases, adversarial cases, metamorphic relations, evidence coverage, promotion gate | A1 deterministic |
| Uncertainty and capacity | Triangular Monte Carlo, feasibility/adoption/ramp, NPV distribution, payback, sensitivity, queue and rework simulation | A1 deterministic |
| Value realization | Frozen baseline, guardrails, forecast-to-actual bridge, descriptive versus controlled difference-in-differences | A1 deterministic |
| Portfolio-company value creation | EBITDA, net debt, EV, equity value, MOIC, IRR, dependencies, critical path, 100-day gates | A1 deterministic |

See `docs/CONSULTING_CONTROL_PLANE_STANDARD.md` and
`docs/CONSULTING_VALUE_CREATION_STANDARD.md` for the execution and financial
standards behind these claims.

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

`WorkflowExecutor` sits above that kernel. It resolves declared bindings only
after dependencies complete, evaluates step policy against the exact request
hash, enforces step/attempt/cost budgets, retries only failed handlers, and can
run declared compensating skills in reverse completion order. Replay compares
the definition, input, statuses, reasons, and outputs while deliberately
ignoring timing and receipt hashes.

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

`simulate_initiative` exposes the distribution hidden behind point estimates:
downside and upside NPV, probability of positive NPV, payback probability,
expected shortfall, and rank sensitivity to each assumption. The seeded sample
checksum makes the run reproducible. `simulate_service_pipeline` separately
tests whether redesigned capacity can handle the proposed flow without simply
moving the queue downstream.

`build_value_creation_bridge` connects initiatives to exit EBITDA, net debt,
enterprise value, equity value, MOIC, and IRR. One-time cost and capex consume
cash; working-capital release reduces net debt; recurring cost reduces EBITDA.
This explicit bridge makes double counting challengeable. `schedule_100_day_plan`
then computes dependency timing, the critical path, unresolved evidence gates,
and whether the sequence fits the first 100 days.

Outcome evidence remains deliberately more conservative. `RealizationPlan`
freezes a baseline and guardrails before measurement. Difference-in-differences
is labeled descriptive unless the caller records a reviewed design and its
identification assumptions; even then the result remains subject to those
assumptions.

## Consulting engagement sequence

1. Map the client's activity graph and P&L drivers.
2. Define executive questions, authoritative metrics, owners, and evidence.
3. Establish the baseline before proposing an agent or redesigned process.
4. Build and independently test only the relevant deterministic kernels.
5. Run reference and adversarial cases within declared read/write scopes.
6. Encode decision rights, obligations, approval scope, and segregation of duties.
7. Reproduce the controlled workflow, compensation, and replay evidence locally.
8. Quantify a confidence-, risk-, and uncertainty-adjusted initiative portfolio.
9. Bridge the sequence into EBITDA, cash, enterprise value, and a 100-day plan.
10. Deliver decision records, limitations, acceptance criteria, and monitoring plan.
11. Measure realized outcomes against the frozen baseline and retire failed uses.

Client system integrations and confidential engagement repositories remain
outside this public core.

## Maturity

| Level | Meaning |
|---|---|
| A0 | Decision, owner, metrics, risks, and evidence are specified |
| A1 | Typed deterministic core and unit tests exist |
| A2 | A source-addressed real operational case, reproducible receipts, and independent review exist |
| A3 | Controlled client use, validation, effective challenge, and sign-off exist |
| A4 | Maintained live use, outcomes, thresholds, rollback, and retirement exist |

The 14-function catalog and all seven platform components remain A1. The Python
suite integrates the operating graph, initiative portfolio, quote control,
scoped knowledge retrieval, agent runtime, evidence ledger, workflow controls,
uncertainty, and refounding economics using deterministic test vectors only.
Those vectors prove mechanics; they are not business evidence. A2 remains
unclaimed until governed real-case evidence and independent review are added.

## Explicit exclusions

- no copied proprietary workflows, prompts, models, or vendor implementations;
- no autonomous hiring rejection, legal approval, payment, purchasing, access
  grant, customer communication, publication, or production deployment;
- no claims that a deterministic score replaces accountable judgment;
- no healthcare revenue-cycle module in the generic core; it belongs in a
  separately validated vertical pack if pursued;
- no production maturity without external evidence and outcome history.
