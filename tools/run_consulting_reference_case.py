"""Run the synthetic consulting operating-system reference case."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Mapping

from finance_segway.consulting import (
    Activity,
    AgentRuntime,
    AgentSpec,
    AutomationCase,
    AutonomyLevel,
    BusinessFunction,
    EvidenceLedger,
    ExecutionContext,
    OperatingModel,
    ProcessRedesign,
    RiskTier,
    Skill,
    SkillRegistry,
    canonical_json,
    evaluate_case,
    select_portfolio,
    simulate_refounding,
)
from finance_segway.consulting.functions.commercial import (
    PricingPolicy,
    Product,
    QuoteRequest,
    build_quote,
)
from finance_segway.consulting.functions.knowledge_data import KnowledgeBase, KnowledgeDocument


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = ROOT / "consulting/reference_cases/synthetic_industrial_services.json"


def _activity(record: Mapping[str, Any]) -> Activity:
    values = dict(record)
    values["function"] = BusinessFunction(values["function"])
    values["predecessors"] = tuple(values.get("predecessors", ()))
    return Activity(**values)


def _automation_case(record: Mapping[str, Any]) -> AutomationCase:
    values = dict(record)
    values["function"] = BusinessFunction(values["function"])
    values["risk_tier"] = RiskTier[values.get("risk_tier", "MODERATE")]
    values["dependencies"] = tuple(values.get("dependencies", ()))
    return AutomationCase(**values)


def _quote_components(record: Mapping[str, Any]):
    products = {
        item["sku"]: Product(
            item["sku"], Decimal(item["list_price"]),
            Decimal(item["unit_cost"]), int(item["available_units"]),
        )
        for item in record["products"]
    }
    request = record["request"]
    quote_request = QuoteRequest(
        request["quote_id"], request["quantities"], request.get("requested_discount", 0),
    )
    policy = record["policy"]
    pricing_policy = PricingPolicy(
        policy["max_discount"], policy["min_gross_margin"],
        Decimal(policy["material_quote_value"]),
    )
    return products, quote_request, pricing_policy


def run_case(path: Path = DEFAULT_CASE) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if not source.get("synthetic"):
        raise ValueError("reference runner accepts synthetic cases only")

    model = OperatingModel(_activity(item) for item in source["activities"])
    activity_economics = {
        activity_id: asdict(model.economics(activity_id))
        for activity_id in model.dependency_order()
    }
    bottlenecks = [asdict(item) for item in model.bottlenecks()]

    cases = [_automation_case(item) for item in source["automation_cases"]]
    policy = source["portfolio_policy"]
    case_economics = {
        item.case_id: asdict(evaluate_case(
            item, hurdle_rate=policy["hurdle_rate"], life_years=policy["life_years"],
        ))
        for item in cases
    }
    portfolio = select_portfolio(
        cases,
        budget=policy["budget"],
        max_high_risk=policy["max_high_risk"],
        hurdle_rate=policy["hurdle_rate"],
        life_years=policy["life_years"],
    )

    products, quote_request, pricing_policy = _quote_components(source["quote"])
    registry = SkillRegistry()
    registry.register(Skill(
        "build_quote",
        lambda request: asdict(build_quote(
            QuoteRequest(request["quote_id"], request["quantities"], request["requested_discount"]),
            products,
            pricing_policy,
        )),
        risk_tier=RiskTier.HIGH,
        required_autonomy=AutonomyLevel.DRAFT,
        required_evidence=frozenset({"price_book"}),
        read_scopes=frozenset({"product_catalog", "price_book"}),
        write_scopes=frozenset({"draft_quotes"}),
    ))
    ledger = EvidenceLedger()
    runtime = AgentRuntime(registry, ledger)
    agent = AgentSpec(
        "reference-quoter",
        BusinessFunction.SALES,
        "Create policy-controlled draft quotes",
        frozenset({"build_quote"}),
        AutonomyLevel.DRAFT,
        frozenset({"product_catalog", "price_book"}),
        frozenset({"draft_quotes"}),
        frozenset({"price_book"}),
        ("gross_margin", "quote_cycle_time"),
        ("Does not send quotes", "Does not override inventory, discount, or margin policy"),
    )
    request_payload = {
        "quote_id": quote_request.quote_id,
        "quantities": quote_request.quantities,
        "requested_discount": quote_request.requested_discount,
    }
    quote_execution = runtime.execute(
        agent,
        "build_quote",
        request_payload,
        ExecutionContext(
            actor="reference-case",
            evidence_ids=frozenset({"price_book"}),
            granted_read_scopes=frozenset({"product_catalog", "price_book"}),
            granted_write_scopes=frozenset({"draft_quotes"}),
            approved=True,
            approval_reference="synthetic-reference-approval",
            timestamp=datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc),
        ),
    )

    knowledge = source["knowledge"]
    knowledge_base = KnowledgeBase(KnowledgeDocument(
        item["document_id"], item["title"], item["text"], item["citation"], item["as_of"],
        frozenset(item.get("allowed_roles", ())),
    ) for item in knowledge["documents"])
    search_results = [asdict(item) for item in knowledge_base.search(
        knowledge["query"], roles=knowledge.get("roles", ()),
    )]

    refounding = source["refounding"]
    redesign = simulate_refounding(
        [ProcessRedesign(**item) for item in refounding["processes"]],
        implementation_cost=refounding["implementation_cost"],
        annual_platform_cost=refounding["annual_platform_cost"],
    )

    payload = {
        "case_id": source["case_id"],
        "synthetic": True,
        "as_of": source["as_of"],
        "company": source["company"],
        "operating_model": {
            "dependency_order": model.dependency_order(),
            "activity_economics": activity_economics,
            "bottlenecks": bottlenecks,
            "function_rollup": model.rollup_by_function(),
        },
        "initiative_portfolio": {
            "case_economics": case_economics,
            "selection": asdict(portfolio),
        },
        "quote_control": {
            "status": quote_execution.status,
            "output": quote_execution.output,
            "receipt_hash": quote_execution.receipt_hash,
        },
        "knowledge": {"query": knowledge["query"], "results": search_results},
        "refounding": asdict(redesign),
        "evidence": {
            "ledger_valid": ledger.verify(),
            "entry_count": len(ledger.entries),
            "head_hash": ledger.entries[-1].entry_hash if ledger.entries else "",
        },
        "limitations": [
            "All company and economic inputs are synthetic.",
            "The benchmark proves local mechanics and controls, not client outcomes.",
            "No external system was read, written, or contacted.",
        ],
    }
    return json.loads(canonical_json(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run_case(args.case)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
