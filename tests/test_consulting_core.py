from datetime import datetime, timezone
import unittest

from finance_segway.consulting import (
    Activity,
    AgentRuntime,
    AgentSpec,
    AutomationCase,
    AutonomyLevel,
    BusinessFunction,
    DiagnosticEngine,
    DiagnosticQuestion,
    Direction,
    EvidenceLedger,
    ExecutionContext,
    MetricDefinition,
    MetricObservation,
    OperatingModel,
    ProcessRedesign,
    RiskTier,
    Skill,
    SkillRegistry,
    evaluate_case,
    select_portfolio,
    simulate_refounding,
)


NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)


class EvidenceLedgerTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self):
        ledger = EvidenceLedger()
        first = ledger.append("evidence_added", {"value": 1}, actor="analyst", timestamp=NOW)
        second = ledger.append("decision_made", {"result": "hold"}, actor="reviewer", timestamp=NOW)
        self.assertEqual(second.previous_hash, first.entry_hash)
        self.assertTrue(ledger.verify())
        records = ledger.export()
        records[0]["payload"]["value"] = 2
        with self.assertRaises(ValueError):
            EvidenceLedger.from_export(records)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        registry = SkillRegistry()
        registry.register(Skill(
            "quote",
            lambda request: {"quote_total": request["units"] * request["price"]},
            risk_tier=RiskTier.HIGH,
            required_autonomy=AutonomyLevel.DRAFT,
            required_evidence=frozenset({"price_book"}),
            read_scopes=frozenset({"catalog"}),
            write_scopes=frozenset({"draft_quotes"}),
        ))
        self.runtime = AgentRuntime(registry)
        self.agent = AgentSpec(
            "quoter",
            BusinessFunction.SALES,
            "Create policy-controlled draft quotes",
            frozenset({"quote"}),
            AutonomyLevel.DRAFT,
            frozenset({"catalog"}),
            frozenset({"draft_quotes"}),
            frozenset({"price_book"}),
        )

    def context(self, approved=False):
        return ExecutionContext(
            actor="consultant",
            evidence_ids=frozenset({"price_book"}),
            granted_read_scopes=frozenset({"catalog"}),
            granted_write_scopes=frozenset({"draft_quotes"}),
            approved=approved,
            approval_reference="approval-1" if approved else "",
            timestamp=NOW,
        )

    def test_high_risk_skill_requires_approval_and_receipts_execution(self):
        pending = self.runtime.execute(self.agent, "quote", {"units": 2, "price": 50}, self.context())
        self.assertEqual(pending.status, "approval_required")
        completed = self.runtime.execute(self.agent, "quote", {"units": 2, "price": 50}, self.context(True))
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.output["quote_total"], 100)
        cached = self.runtime.execute(self.agent, "quote", {"units": 2, "price": 50}, self.context(True))
        self.assertTrue(cached.cached)
        self.assertTrue(self.runtime.ledger.verify())
        self.assertEqual(len(self.runtime.ledger.entries), 3)

    def test_scope_violation_is_rejected(self):
        context = ExecutionContext(
            actor="consultant",
            evidence_ids=frozenset({"price_book"}),
            granted_read_scopes=frozenset(),
            granted_write_scopes=frozenset({"draft_quotes"}),
            timestamp=NOW,
        )
        result = self.runtime.execute(self.agent, "quote", {"units": 1, "price": 5}, context)
        self.assertEqual(result.status, "rejected")
        self.assertIn("context_read_scope_violation", result.reasons)


class OperatingModelTests(unittest.TestCase):
    def test_bottleneck_and_intervention_economics(self):
        model = OperatingModel([
            Activity(
                "quote", "Quote", BusinessFunction.SALES, "gross_margin",
                annual_volume=1200, capacity_units=1000, minutes_per_unit=30,
                loaded_cost_per_hour=60, contribution_per_unit=100,
                error_rate=0.05, cost_per_error=200,
            ),
            Activity("deliver", "Deliver", BusinessFunction.OPERATIONS, "revenue", ("quote",)),
        ])
        economics = model.economics("quote")
        self.assertAlmostEqual(economics.utilization, 1.2)
        self.assertEqual(economics.constrained_contribution, 20_000)
        estimate = model.estimate_intervention(
            "quote", labor_automation=0.5, error_reduction=0.4, capacity_increase=0.25,
        )
        self.assertGreater(estimate.gross_annual_value, 0)
        self.assertEqual(model.dependency_order(), ("quote", "deliver"))
        self.assertEqual(model.bottlenecks()[0].activity_id, "quote")

    def test_dependency_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            OperatingModel([
                Activity("a", "A", BusinessFunction.SALES, "revenue", ("b",)),
                Activity("b", "B", BusinessFunction.SALES, "revenue", ("a",)),
            ])


class PortfolioTests(unittest.TestCase):
    def test_case_economics_and_exact_selection(self):
        foundation = AutomationCase(
            "foundation", "data", BusinessFunction.DATA,
            50, 5, annual_labor_savings=40, evidence_confidence=0.9,
        )
        quoting = AutomationCase(
            "quoting", "quote", BusinessFunction.SALES,
            70, 10, annual_labor_savings=50, annual_revenue_gain=50,
            dependencies=("foundation",), evidence_confidence=0.9,
        )
        risky = AutomationCase(
            "risky", "payment", BusinessFunction.FINANCE,
            100, 0, annual_labor_savings=500, risk_tier=RiskTier.CRITICAL,
        )
        self.assertGreater(evaluate_case(quoting).npv, 0)
        selection = select_portfolio([foundation, quoting, risky], budget=120, max_high_risk=0)
        self.assertEqual(selection.selected_case_ids, ("foundation", "quoting"))
        self.assertEqual(selection.implementation_cost, 120)

    def test_refounding_simulation_exposes_unit_economics(self):
        result = simulate_refounding([
            ProcessRedesign(
                "quote", 1000, 200, 50, 60, 15, 60,
                baseline_error_rate=0.05, redesigned_error_rate=0.01,
                loss_per_error=100,
            ),
        ], implementation_cost=50_000, annual_platform_cost=10_000)
        self.assertGreater(result.annual_value_created, 0)
        self.assertGreater(result.capacity_multiplier_at_fixed_labor, 1)
        self.assertLess(result.redesigned_fte, result.baseline_fte)
        self.assertLess(result.payback_months, 24)


class DiagnosticTests(unittest.TestCase):
    def test_missing_evidence_reduces_score(self):
        metric = MetricDefinition(
            "response_sla", BusinessFunction.SALES, "Response SLA", "%", "CRO",
            Direction.HIGHER, 0.9,
        )
        question = DiagnosticQuestion(
            "sales-speed", BusinessFunction.SALES, "CRO",
            "Are qualified leads handled quickly?", ("response_sla",), ("crm_extract",),
        )
        engine = DiagnosticEngine([metric], [question])
        observation = MetricObservation("response_sla", 0.9, "2026-08-04", ("crm_extract",))
        verified = engine.score_question("sales-speed", [observation], ["crm_extract"])
        unverified = engine.score_question("sales-speed", [observation], [])
        self.assertEqual(verified.score, 100)
        self.assertLess(unverified.score, verified.score)


if __name__ == "__main__":
    unittest.main()
