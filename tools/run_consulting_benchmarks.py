"""Run committed A2 synthetic benchmarks for the consulting control plane."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from finance_segway.consulting import (
    AgentRuntime,
    AgentSpec,
    ApprovalGrant,
    AssertionOperator,
    AutonomyLevel,
    BenchmarkCase,
    BusinessFunction,
    ConditionOperator,
    ExecutionContext,
    InitiativeImpact,
    InitiativeSimulation,
    InvestmentBaseline,
    MetamorphicRelation,
    OutputAssertion,
    PolicyCondition,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    ProcessEvent,
    ProcessMiner,
    PromotionGate,
    QueueStage,
    RelationOperator,
    RiskTier,
    Skill,
    SkillRegistry,
    TriangularDistribution,
    WorkflowDefinition,
    WorkflowExecutor,
    WorkflowStep,
    Workstream,
    assess_a2_promotion,
    build_value_creation_bridge,
    canonical_json,
    evaluate_suite,
    replay_matches,
    schedule_100_day_plan,
    sha256_payload,
    simulate_initiative,
    simulate_service_pipeline,
)
from finance_segway.consulting.functions.commercial import (
    PricingPolicy,
    Product,
    QuoteRequest,
    build_quote,
)
from finance_segway.consulting.functions.finance_ops import (
    Invoice,
    PurchaseOrder,
    SpendPolicy,
    SpendRequest,
    SupplierContract,
    audit_invoice,
    decide_spend,
)


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "standards/consulting/benchmarks"


def _instant(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("benchmark timestamps must be timezone-aware")
    return instant


def _triangular(values: list[float]) -> TriangularDistribution:
    if len(values) != 3:
        raise ValueError("triangular benchmark inputs require [low, mode, high]")
    return TriangularDistribution(*values)


def _process_output(source: Mapping[str, Any]) -> dict[str, Any]:
    events = [
        ProcessEvent(
            item["case_id"], item["activity_id"], _instant(item["occurred_at"]),
            item.get("actor", ""), item.get("event_id", ""), item.get("attributes", {}),
        )
        for item in source["events"]
    ]
    assessment = ProcessMiner(events).assess(
        allowed_transitions=tuple(tuple(item) for item in source["allowed_transitions"]),
        required_activities=source.get("required_activities", ()),
        allowed_starts=source.get("allowed_starts", ()),
        allowed_ends=source.get("allowed_ends", ()),
    )
    return asdict(assessment)


def _approvals(
    source: Mapping[str, Any],
    scenario: Mapping[str, Any],
    request_hash: str,
    action: str,
    at: datetime,
) -> tuple[ApprovalGrant, ...]:
    approvers = source["policy"]["approvers"]
    return tuple(
        ApprovalGrant(
            f"{scenario['scenario_id']}:{role}",
            approvers[role],
            role,
            action,
            request_hash,
            at - timedelta(minutes=5),
            at + timedelta(hours=2),
        )
        for role in scenario.get("approval_roles", ())
    )


def _policy(source: Mapping[str, Any], action: str, status_field: str) -> PolicyEngine:
    policy = source["policy"]
    return PolicyEngine((
        PolicyRule(
            "blocked-counterparty", action, PolicyEffect.DENY,
            (PolicyCondition(f"attributes.{status_field}", ConditionOperator.EQ, "blocked"),),
            obligations=("retain_denial",), priority=100,
        ),
        PolicyRule(
            "material-decision", action, PolicyEffect.REQUIRE_APPROVAL,
            (PolicyCondition("attributes.request.amount", ConditionOperator.GTE, Decimal(str(policy["material_threshold"]))),),
            obligations=("retain_inputs", "retain_approvals", "retain_decision"),
            approval_roles=tuple(policy["required_roles"]), priority=50,
        ),
        PolicyRule(
            "ordinary-decision", action, PolicyEffect.ALLOW,
            obligations=("retain_decision",),
        ),
    ))


def _quote_runner(source: Mapping[str, Any]) -> Callable[[BenchmarkCase], Mapping[str, Any]]:
    quote_source = source["quote"]
    products = {
        item["sku"]: Product(
            item["sku"], Decimal(item["list_price"]),
            Decimal(item["unit_cost"]), int(item["available_units"]),
        )
        for item in quote_source["products"]
    }
    pricing = quote_source["policy"]
    pricing_policy = PricingPolicy(
        pricing["max_discount"], pricing["min_gross_margin"],
        Decimal(pricing["material_quote_value"]),
    )
    action = "stage_material_quote"
    policy_engine = _policy(source, action, "customer_status")
    at = _instant(source["as_of"])

    def runner(case: BenchmarkCase) -> Mapping[str, Any]:
        scenario = case.payload
        request_source = quote_source["request"]
        quote_request = QuoteRequest(
            request_source["quote_id"], request_source["quantities"],
            scenario.get("requested_discount", request_source["requested_discount"]),
        )
        expected_quote = build_quote(quote_request, products, pricing_policy)
        stage_request = {
            "quote_id": expected_quote.quote_id,
            "amount": expected_quote.total,
            "approval_required": expected_quote.approval_required,
        }
        grants = _approvals(source, scenario, sha256_payload(stage_request), action, at)
        registry = SkillRegistry()
        registry.register(Skill(
            "draft_quote",
            lambda request: asdict(build_quote(
                QuoteRequest(request["quote_id"], request["quantities"], request["requested_discount"]),
                products, pricing_policy,
            )),
            risk_tier=RiskTier.HIGH,
            required_autonomy=AutonomyLevel.DRAFT,
            required_evidence=frozenset({"price_book"}),
            read_scopes=frozenset({"catalog", "price_book"}),
            write_scopes=frozenset({"draft_quotes"}),
        ))
        registry.register(Skill(
            "stage_delivery",
            lambda request: {
                "quote_id": request["quote_id"], "amount": request["amount"],
                "status": "staged_not_dispatched",
            },
            risk_tier=RiskTier.MODERATE,
            required_autonomy=AutonomyLevel.DRAFT,
            write_scopes=frozenset({"draft_schedules"}),
        ))
        registry.register(Skill(
            "project_receivable",
            lambda request: {
                "quote_id": request["quote_id"],
                "projected_receivable": request["amount"],
                "status": "projection_only",
            },
            read_scopes=frozenset({"draft_quotes"}),
        ))
        runtime = AgentRuntime(registry)
        agent = AgentSpec(
            "quote-to-cash-controller", BusinessFunction.SALES,
            "Draft, authorize, and project a synthetic quote without external action",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT,
            frozenset({"catalog", "price_book", "draft_quotes"}),
            frozenset({"draft_quotes", "draft_schedules"}),
            frozenset({"price_book"}),
            limitations=("Does not dispatch, send, invoice, or collect",),
        )
        definition = WorkflowDefinition("quote-to-cash", "1", (
            WorkflowStep(
                "quote", "draft_quote",
                constants={
                    "quote_id": quote_request.quote_id,
                    "quantities": quote_request.quantities,
                    "requested_discount": quote_request.requested_discount,
                },
            ),
            WorkflowStep(
                "stage", "stage_delivery", dependencies=("quote",),
                bindings={
                    "quote_id": "steps.quote.output.quote_id",
                    "amount": "steps.quote.output.total",
                    "approval_required": "steps.quote.output.approval_required",
                },
                policy_action=action,
            ),
            WorkflowStep(
                "cash", "project_receivable", dependencies=("stage",),
                bindings={
                    "quote_id": "steps.stage.output.quote_id",
                    "amount": "steps.stage.output.amount",
                },
            ),
        ))
        context = ExecutionContext(
            actor="synthetic-consultant",
            evidence_ids=frozenset({"price_book"}),
            granted_read_scopes=frozenset({"catalog", "price_book", "draft_quotes"}),
            granted_write_scopes=frozenset({"draft_quotes", "draft_schedules"}),
            approved=True,
            approval_reference="synthetic-draft-approval",
            timestamp=at,
        )
        executor = WorkflowExecutor(runtime, policy_engine)
        first = executor.run(
            definition, agent, {}, context,
            run_id=f"{scenario['scenario_id']}:1", approvals=grants,
            policy_attributes={"customer_status": scenario.get("customer_status", "active")},
        )
        replay = first
        replay_ok = False
        if scenario.get("replay", False):
            replay = executor.run(
                definition, agent, {}, context,
                run_id=f"{scenario['scenario_id']}:2", approvals=grants,
                policy_attributes={"customer_status": scenario.get("customer_status", "active")},
            )
            replay_ok = replay_matches(first, replay)
        return {
            "workflow_status": first.status,
            "step_statuses": {step.step_id: step.status for step in first.steps},
            "completed_step_count": sum(step.status == "completed" for step in first.steps),
            "replay_match": replay_ok,
            "ledger_valid": runtime.ledger.verify(),
            "ledger_entries": len(runtime.ledger.entries),
            "workflow": asdict(first),
        }

    return runner


def _procurement_runner(source: Mapping[str, Any]) -> Callable[[BenchmarkCase], Mapping[str, Any]]:
    spend_source = source["spend"]
    spend_request = SpendRequest(
        spend_source["request_id"], spend_source["category"], Decimal(spend_source["amount"]),
        spend_source["requester"], spend_source["vendor_id"],
        Decimal(spend_source["budget_remaining"]), spend_source["contract_id"],
    )
    spend_policy = SpendPolicy(
        {key: Decimal(value) for key, value in spend_source["policy"]["category_limits"].items()},
        Decimal(spend_source["policy"]["approval_threshold"]),
        Decimal(spend_source["policy"]["contract_required_threshold"]),
        frozenset(spend_source["policy"].get("blocked_vendors", ())),
    )
    invoice_source = source["invoice"]
    contract = SupplierContract(
        invoice_source["contract_id"],
        {key: Decimal(value) for key, value in invoice_source["contract_prices"].items()},
        invoice_source.get("quantity_tolerance", 0), invoice_source.get("tax_rate", 0),
        invoice_source.get("early_payment_discount", 0),
    )
    purchase_order = PurchaseOrder(
        invoice_source["po_id"], invoice_source["contract_id"], invoice_source["ordered_quantities"],
    )
    invoice = Invoice(
        invoice_source["invoice_id"], invoice_source["po_id"], invoice_source["invoiced_quantities"],
        {key: Decimal(value) for key, value in invoice_source["invoice_prices"].items()},
        Decimal(invoice_source["subtotal"]), Decimal(invoice_source["tax"]),
        Decimal(invoice_source.get("discount_taken", "0")),
    )
    action = "stage_invoice_review"
    policy_engine = _policy(source, action, "vendor_status")
    at = _instant(source["as_of"])

    def runner(case: BenchmarkCase) -> Mapping[str, Any]:
        scenario = case.payload
        expected_spend = decide_spend(spend_request, spend_policy)
        audit_request = {
            "request_id": spend_request.request_id,
            "amount": spend_request.amount,
            "spend_status": expected_spend.status,
        }
        grants = _approvals(source, scenario, sha256_payload(audit_request), action, at)
        registry = SkillRegistry()
        registry.register(Skill(
            "screen_spend", lambda _request: asdict(decide_spend(spend_request, spend_policy)),
            risk_tier=RiskTier.HIGH, required_autonomy=AutonomyLevel.DRAFT,
            required_evidence=frozenset({"spend_policy"}), read_scopes=frozenset({"spend_policy"}),
        ))
        registry.register(Skill(
            "audit_invoice", lambda _request: asdict(audit_invoice(invoice, purchase_order, contract)),
            read_scopes=frozenset({"contract", "purchase_order", "invoice"}),
        ))
        registry.register(Skill(
            "project_cash", lambda request: {
                "invoice_id": request["invoice_id"],
                "projected_cash_requirement": request["expected_total"],
                "status": "projection_only",
            },
            read_scopes=frozenset({"invoice"}),
        ))
        runtime = AgentRuntime(registry)
        agent = AgentSpec(
            "procure-to-pay-controller", BusinessFunction.PROCUREMENT,
            "Screen and audit synthetic spend without issuing a purchase or payment",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT,
            frozenset({"spend_policy", "contract", "purchase_order", "invoice"}),
            frozenset(), frozenset({"spend_policy"}),
            limitations=("Does not create a purchase order or release payment",),
        )
        definition = WorkflowDefinition("procure-to-pay", "1", (
            WorkflowStep("screen", "screen_spend", constants={"request_id": spend_request.request_id}),
            WorkflowStep(
                "audit", "audit_invoice", dependencies=("screen",),
                constants={"request_id": spend_request.request_id, "amount": spend_request.amount},
                bindings={"spend_status": "steps.screen.output.status"}, policy_action=action,
            ),
            WorkflowStep(
                "cash", "project_cash", dependencies=("audit",),
                bindings={
                    "invoice_id": "steps.audit.output.invoice_id",
                    "expected_total": "steps.audit.output.expected_total",
                },
            ),
        ))
        context = ExecutionContext(
            actor="synthetic-consultant",
            evidence_ids=frozenset({"spend_policy"}),
            granted_read_scopes=frozenset({"spend_policy", "contract", "purchase_order", "invoice"}),
            approved=True, approval_reference="synthetic-screen-approval", timestamp=at,
        )
        executor = WorkflowExecutor(runtime, policy_engine)
        first = executor.run(
            definition, agent, {}, context,
            run_id=f"{scenario['scenario_id']}:1", approvals=grants,
            policy_attributes={"vendor_status": scenario.get("vendor_status", "active")},
        )
        replay_ok = False
        if scenario.get("replay", False):
            second = executor.run(
                definition, agent, {}, context,
                run_id=f"{scenario['scenario_id']}:2", approvals=grants,
                policy_attributes={"vendor_status": scenario.get("vendor_status", "active")},
            )
            replay_ok = replay_matches(first, second)
        return {
            "workflow_status": first.status,
            "step_statuses": {step.step_id: step.status for step in first.steps},
            "completed_step_count": sum(step.status == "completed" for step in first.steps),
            "replay_match": replay_ok,
            "ledger_valid": runtime.ledger.verify(),
            "ledger_entries": len(runtime.ledger.entries),
            "workflow": asdict(first),
        }

    return runner


def _case(source: Mapping[str, Any], scenario: Mapping[str, Any]) -> BenchmarkCase:
    expected = scenario["expected"]
    assertions = [
        OutputAssertion("workflow_status", AssertionOperator.EQ, expected["workflow_status"]),
        OutputAssertion("completed_step_count", AssertionOperator.EQ, expected["completed_step_count"]),
        OutputAssertion("ledger_valid", AssertionOperator.EQ, True),
    ]
    for step_id, status in expected.get("step_statuses", {}).items():
        assertions.append(OutputAssertion(f"step_statuses.{step_id}", AssertionOperator.EQ, status))
    if scenario.get("replay", False):
        assertions.append(OutputAssertion("replay_match", AssertionOperator.EQ, True))
    return BenchmarkCase(
        scenario["scenario_id"], scenario, tuple(assertions),
        scenario.get("category", "reference"), scenario.get("severity", 2),
        evidence_ids=(f"fixture:{source['benchmark_id']}:{scenario['scenario_id']}",),
    )


def _value_creation_output(source: Mapping[str, Any]) -> dict[str, Any]:
    if "value_creation" not in source:
        return {}
    values = source["value_creation"]
    baseline = InvestmentBaseline(**values["baseline"])
    initiatives = [
        InitiativeImpact(
            **{
                **item,
                "dependencies": tuple(item.get("dependencies", ())),
                "evidence_ids": tuple(item["evidence_ids"]),
            },
        )
        for item in values["initiatives"]
    ]
    result = {"bridge": asdict(build_value_creation_bridge(baseline, initiatives))}
    if values.get("workstreams"):
        workstreams = [
            Workstream(
                **{
                    **item,
                    "dependencies": tuple(item.get("dependencies", ())),
                    "required_evidence": tuple(item.get("required_evidence", ())),
                },
            )
            for item in values["workstreams"]
        ]
        result["hundred_day_plan"] = asdict(schedule_100_day_plan(
            workstreams,
            available_evidence_ids=values.get("available_evidence_ids", ()),
        ))
    return result


def _simulation_output(source: Mapping[str, Any]) -> dict[str, Any]:
    if "simulation" not in source:
        return {}
    values = source["simulation"]
    case = InitiativeSimulation(
        values["simulation_id"],
        _triangular(values["implementation_cost"]),
        _triangular(values["annual_gross_value"]),
        _triangular(values["annual_recurring_cost"]),
        _triangular(values["adoption_fraction"]),
        _triangular(values["delivery_months"]),
        _triangular(values.get("working_capital_release", [0, 0, 0])),
        values.get("feasibility_probability", 1),
        values.get("life_years", 3), values.get("discount_rate", 0.12),
        values.get("ramp_months", 6),
    )
    return asdict(simulate_initiative(
        case, iterations=values.get("iterations", 1000), seed=values.get("seed", 17),
    ))


def _capacity_output(source: Mapping[str, Any]) -> dict[str, Any]:
    if "capacity_simulation" not in source:
        return {}
    values = source["capacity_simulation"]
    stages = tuple(
        QueueStage(
            item["stage_id"], item["servers"], _triangular(item["service_minutes"]),
            item.get("rework_probability", 0),
        )
        for item in values["stages"]
    )
    return asdict(simulate_service_pipeline(
        stages,
        item_count=values["item_count"],
        interarrival_minutes=values["interarrival_minutes"],
        seed=values.get("seed", 17),
    ))


def run_manifest(path: Path) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if not source.get("synthetic"):
        raise ValueError("consulting benchmark runner accepts synthetic manifests only")
    if source["flow"] == "quote_to_cash":
        runner = _quote_runner(source)
    elif source["flow"] == "procure_to_pay":
        runner = _procurement_runner(source)
    else:
        raise ValueError(f"unsupported benchmark flow: {source['flow']}")
    cases = tuple(_case(source, item) for item in source["scenarios"])
    relations = tuple(
        MetamorphicRelation(
            item["relation_id"], item["base_case_id"], item["variant_case_id"],
            item["path"], RelationOperator(item["operator"]), item.get("tolerance", 1e-9),
        )
        for item in source.get("relations", ())
    )
    scorecard = evaluate_suite(source["benchmark_id"], cases, runner, relations=relations)
    outputs = {item.case_id: item.output for item in scorecard.case_results}
    reference_id = source["reference_scenario_id"]
    reference = outputs[reference_id]
    promotion = assess_a2_promotion(
        scorecard,
        PromotionGate(),
        integrated_workflow=reference["workflow_status"] == "completed",
        ledger_valid=all(output["ledger_valid"] for output in outputs.values()),
        deterministic_replay=reference["replay_match"],
    )
    result = {
        "benchmark_id": source["benchmark_id"],
        "flow": source["flow"],
        "synthetic": True,
        "as_of": source["as_of"],
        "process_assessment": _process_output(source["process_log"]),
        "evaluation": asdict(scorecard),
        "promotion": asdict(promotion),
        "simulation": _simulation_output(source),
        "capacity_simulation": _capacity_output(source),
        "value_creation": _value_creation_output(source),
        "limitations": [
            "All identities, events, economics, approvals, and source references are synthetic.",
            "A2 proves reproducible local integration and controls, not client or production maturity.",
            "No external system was read, written, messaged, or mutated.",
        ],
    }
    return json.loads(canonical_json(result))


def run_all(directory: Path = BENCHMARK_DIR) -> dict[str, Any]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("no consulting benchmark manifests found")
    benchmarks = [run_manifest(path) for path in paths]
    return {
        "suite": "consulting-control-plane-a2",
        "synthetic": True,
        "benchmark_count": len(benchmarks),
        "all_eligible_for_a2": all(item["promotion"]["eligible"] for item in benchmarks),
        "benchmarks": benchmarks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--directory", type=Path, default=BENCHMARK_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run_manifest(args.manifest) if args.manifest else run_all(args.directory)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return int(not (
        result.get("promotion", {}).get("eligible", result.get("all_eligible_for_a2", False))
    ))


if __name__ == "__main__":
    raise SystemExit(main())
