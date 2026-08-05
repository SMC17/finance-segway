from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

from finance_segway.consulting.functions.assurance import (
    AccessRequest,
    ContractPolicy,
    ContractRecord,
    CreativeBrief,
    EngineeringTask,
    ServiceTicket,
    audit_contract,
    decide_access,
    delegate_engineering_task,
    engineering_productivity,
    route_creative_brief,
    route_it_ticket,
)
from finance_segway.consulting.functions.commercial import (
    Account,
    BrandPolicy,
    IdealCustomerProfile,
    Lead,
    PricingPolicy,
    Product,
    QuoteRequest,
    VisibilityObservation,
    build_quote,
    check_brand,
    geo_visibility,
    sales_metrics,
    score_accounts,
)
from finance_segway.consulting.functions.finance_ops import (
    CashPeriod,
    CloseTask,
    Invoice,
    PurchaseOrder,
    Receivable,
    SpendPolicy,
    SpendRequest,
    SupplierContract,
    audit_invoice,
    close_control,
    decide_spend,
    prioritize_collections,
    rolling_cash_forecast,
)
from finance_segway.consulting.functions.knowledge_data import (
    KnowledgeBase,
    KnowledgeDocument,
    MetricCatalog,
    SemanticMetric,
    parse_tagged_minutes,
)
from finance_segway.consulting.functions.operations import (
    CapacityPeriod,
    QualityBatch,
    WorkOrder,
    Worker,
    capacity_plan,
    demand_forecast,
    dispatch_work,
    quality_metrics,
)
from finance_segway.consulting.functions.people_service import (
    CandidateProfile,
    CustomerHealth,
    HiringEvent,
    RoleProfile,
    ServiceCase,
    hiring_funnel,
    prioritize_service_cases,
    rank_candidates,
    score_customer_health,
)
from finance_segway.consulting.schema import RiskTier


NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)


class CommercialTests(unittest.TestCase):
    def test_icp_sales_geo_and_brand(self):
        profile = IdealCustomerProfile({"fit": 2, "intent": 1}, frozenset({"us"}), 60)
        scores = score_accounts([
            Account("a", {"fit": 1, "intent": 0.5}, frozenset({"us"})),
            Account("b", {"fit": 0.5, "intent": 1}, frozenset()),
        ], profile)
        self.assertEqual(scores[0].account_id, "a")
        self.assertTrue(scores[0].eligible)
        self.assertFalse(scores[1].eligible)

        leads = [
            Lead("1", NOW, NOW + timedelta(minutes=10), True, True, 2),
            Lead("2", NOW, NOW + timedelta(minutes=120), True, False, 1),
        ]
        metrics = sales_metrics(leads, response_sla_minutes=60)
        self.assertEqual(metrics["qualification_rate"], 1)
        self.assertEqual(metrics["response_sla_attainment"], 0.5)

        visibility = geo_visibility([
            VisibilityObservation("p1", "engine-a", True, True, 1, 0.5),
            VisibilityObservation("p2", "engine-b", False, False, 2, -0.5),
        ])
        self.assertEqual(visibility["mention_rate"], 0.5)
        self.assertIn("missing_required:auditable", check_brand(
            "Fast results without hype", BrandPolicy(("auditable",), ("guaranteed",)),
        ))

    def test_quote_guardrails(self):
        products = {
            "A": Product("A", Decimal("100"), Decimal("70"), 10),
        }
        quote = build_quote(
            QuoteRequest("q1", {"A": 12}, 0.20),
            products,
            PricingPolicy(0.10, 0.25, Decimal("1000")),
        )
        self.assertTrue(quote.approval_required)
        self.assertIn("discount_above_policy", quote.approval_reasons)
        self.assertIn("insufficient_inventory:A", quote.approval_reasons)
        self.assertEqual(quote.total, Decimal("1080.00"))


class FinanceProcurementTests(unittest.TestCase):
    def test_cash_close_spend_and_collections(self):
        forecast = rolling_cash_forecast(Decimal("100"), [
            CashPeriod("w1", Decimal("30"), Decimal("50"), 0.5, 1.1),
        ])
        self.assertEqual(forecast[0].ending_cash, Decimal("80"))
        self.assertLess(forecast[0].downside_ending_cash, forecast[0].ending_cash)

        close = close_control([
            CloseTask("bank", "A", "complete", NOW, NOW, control_id="ctrl-1"),
            CloseTask("rev", "B", "blocked", NOW - timedelta(days=1), blocker="data", control_id="ctrl-2"),
        ], as_of=NOW)
        self.assertFalse(close["ready_to_close"])
        self.assertEqual(close["overdue_task_ids"], ("rev",))

        decision = decide_spend(
            SpendRequest("r1", "software", Decimal("100"), "A", "v1", Decimal("500")),
            SpendPolicy({"software": Decimal("200")}, Decimal("75"), Decimal("150")),
        )
        self.assertEqual(decision.status, "approval_required")

        ranked = prioritize_collections([
            Receivable("i1", "c1", Decimal("100"), date(2026, 7, 1), customer_risk=0.2),
            Receivable("i2", "c2", Decimal("500"), date(2026, 8, 10), customer_risk=0.0),
        ], as_of=date(2026, 8, 4))
        self.assertEqual(ranked[0][0], "i2")

    def test_three_way_invoice_audit_detects_leakage(self):
        contract = SupplierContract("c1", {"sku": Decimal("10")}, 0.0, 0.05, 0.02)
        po = PurchaseOrder("po1", "c1", {"sku": 10})
        invoice = Invoice(
            "inv1", "po1", {"sku": 10}, {"sku": Decimal("11")},
            Decimal("110"), Decimal("5.50"), Decimal("0"),
        )
        audit = audit_invoice(invoice, po, contract)
        self.assertIn("price_exception:sku", audit.exceptions)
        self.assertIn("missed_discount", audit.exceptions)
        self.assertGreater(audit.leakage, 0)


class PeopleCustomerTests(unittest.TestCase):
    def test_skills_first_ranking_and_hiring_funnel(self):
        role = RoleProfile("analyst", {"sql": 2, "finance": 1}, {"sql": 0.7, "finance": 0.5})
        ranked = rank_candidates(role, [
            CandidateProfile("internal", {"sql": 0.9, "finance": 0.8}, {"sql": 2, "finance": 1}, internal=True),
            CandidateProfile("external", {"sql": 1, "finance": 0.2}, {"sql": 3, "finance": 1}),
        ])
        self.assertEqual(ranked[0].candidate_id, "internal")
        self.assertTrue(ranked[0].eligible)
        self.assertFalse(ranked[1].eligible)

        funnel = hiring_funnel([
            HiringEvent("a", NOW, NOW + timedelta(hours=2), True, True),
            HiringEvent("b", NOW, None, False, False),
        ])
        self.assertEqual(funnel["human_contact_coverage"], 0.5)

    def test_service_and_customer_health(self):
        cases = prioritize_service_cases([
            ServiceCase("critical", 4, 1, 0.5, True),
            ServiceCase("routine", 1, 0.1, 1),
        ])
        self.assertEqual(cases[0].case_id, "critical")
        self.assertTrue(cases[0].escalation_required)
        health = score_customer_health([
            CustomerHealth("risk", 0.1, 0.8, 0.8, 0.1, 10),
            CustomerHealth("healthy", 1, 0, 0, 1, 180),
        ])
        self.assertEqual(health[0].customer_id, "risk")
        self.assertTrue(health[0].intervention_required)


class OperationsTests(unittest.TestCase):
    def test_forecast_capacity_dispatch_and_quality(self):
        self.assertEqual(demand_forecast([10, 20, 30], horizon=2, window=2), (25, 27.5))
        plan = capacity_plan([CapacityPeriod("w1", 120, 100, 10)])
        self.assertEqual(plan[0]["contribution_at_risk"], 200)
        dispatched = dispatch_work(
            [Worker("w1", frozenset({"electrical", "general"}), 8)],
            [
                WorkOrder("high", frozenset({"electrical"}), 6, 10, 500),
                WorkOrder("low", frozenset({"general"}), 4, 1, 100),
            ],
        )
        self.assertEqual(dispatched.assignments, {"high": "w1"})
        self.assertEqual(dispatched.unassigned_order_ids, ("low",))
        quality = quality_metrics([QualityBatch("b1", 100, 5, 2, 1)])
        self.assertEqual(quality["first_pass_yield"], 0.95)


class KnowledgeDataTests(unittest.TestCase):
    def test_scoped_retrieval_and_meeting_records(self):
        base = KnowledgeBase([
            KnowledgeDocument("public", "Pricing", "Discounts require margin review.", "policy-1", "2026-08-01"),
            KnowledgeDocument("restricted", "Payroll", "Salary bands are confidential.", "hr-1", "2026-08-01", frozenset({"hr"})),
        ])
        self.assertEqual(base.search("margin review")[0].document_id, "public")
        self.assertEqual(base.search("salary bands"), ())
        self.assertEqual(base.search("salary bands", roles={"hr"})[0].document_id, "restricted")
        record = parse_tagged_minutes(
            "[DECISION] Pilot quoting control\n[ACTION owner=Sean due=2026-08-10] Build benchmark\n[RISK] Price book may be stale"
        )
        self.assertEqual(record.decisions, ("Pilot quoting control",))
        self.assertEqual(record.actions[0].owner, "Sean")

    def test_semantic_metric_catalog(self):
        catalog = MetricCatalog()
        catalog.register(SemanticMetric(
            "conversion", "Conversion", "ratio", "wins", "qualified",
            owner="CRO", source_fields=("crm.wins", "crm.qualified"), aliases=("win rate",),
        ))
        result = catalog.evaluate("win rate", [{"wins": 2, "qualified": 4}, {"wins": 1, "qualified": 2}])
        self.assertEqual(result["value"], 0.5)
        self.assertEqual(result["lineage"], ("crm.wins", "crm.qualified"))


class AssuranceTests(unittest.TestCase):
    def test_engineering_legal_it_access_and_creative(self):
        delegation = delegate_engineering_task(EngineeringTask(
            "deps", True, True, False, False, True, RiskTier.LOW,
        ))
        self.assertEqual(delegation.mode, "autonomous_reversible")
        productivity = engineering_productivity(
            baseline_completed=10, current_completed=20,
            baseline_engineer_hours=10, current_engineer_hours=10, assisted_tasks=10,
        )
        self.assertEqual(productivity["throughput_change"], 1)

        exceptions = audit_contract(
            ContractRecord("c", frozenset({"confidentiality"}), 36, True, 0.5, "NY"),
            ContractPolicy(frozenset({"confidentiality", "audit"}), frozenset(), 24, False, 1.0, frozenset({"DE"})),
        )
        self.assertIn("missing_clause:audit", exceptions)
        self.assertIn("governing_law_exception", exceptions)

        route = route_it_ticket(ServiceTicket("t", "laptop", 2, 2, security_related=True), {"laptop": "endpoint"})
        self.assertEqual(route.queue, "security")
        self.assertTrue(route.human_required)
        access = decide_access(
            AccessRequest("a", "analyst", frozenset({"read", "admin"}), 30),
            {"analyst": frozenset({"read"})},
        )
        self.assertEqual(access.status, "rejected")

        production = route_creative_brief(CreativeBrief(
            "brief", "buyers", "explain", "web", ("saves time",), ("study-1",), True, RiskTier.HIGH,
        ))
        self.assertEqual(production.production_tier, "human_origin")
        self.assertEqual(production.readiness_score, 100)


if __name__ == "__main__":
    unittest.main()
