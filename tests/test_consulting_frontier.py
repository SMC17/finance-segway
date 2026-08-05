from datetime import datetime, timedelta, timezone
import unittest

from finance_segway.consulting import (
    AgentRuntime,
    AgentSpec,
    ApprovalGrant,
    AssertionOperator,
    AutonomyLevel,
    BenchmarkCase,
    BusinessFunction,
    ConditionOperator,
    FailurePolicy,
    Guardrail,
    GuardrailOperator,
    InitiativeImpact,
    InitiativeSimulation,
    InvestmentBaseline,
    MetamorphicRelation,
    OutcomeObservation,
    OutcomePeriod,
    OutputAssertion,
    PolicyCondition,
    PolicyEffect,
    PolicyEngine,
    PolicyRequest,
    PolicyRule,
    ProcessEvent,
    ProcessMiner,
    PromotionGate,
    QueueStage,
    RealizationPlan,
    RelationOperator,
    RiskTier,
    Skill,
    SkillRegistry,
    TriangularDistribution,
    WorkflowBudget,
    WorkflowDefinition,
    WorkflowExecutor,
    WorkflowStep,
    Workstream,
    assess_a2_promotion,
    build_value_creation_bridge,
    difference_in_differences,
    evaluate_suite,
    measure_realization,
    replay_matches,
    schedule_100_day_plan,
    simulate_initiative,
    simulate_service_pipeline,
)
from finance_segway.consulting.runtime import ExecutionContext


NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)


class ProcessMiningTests(unittest.TestCase):
    def test_discovers_variants_rework_handoffs_and_conformance(self):
        events = [
            ProcessEvent("C1", "quote", NOW, "sales", "1"),
            ProcessEvent("C1", "approve", NOW + timedelta(hours=2), "finance", "2"),
            ProcessEvent("C1", "deliver", NOW + timedelta(hours=8), "ops", "3"),
            ProcessEvent("C2", "quote", NOW, "sales", "4"),
            ProcessEvent("C2", "approve", NOW + timedelta(hours=4), "finance", "5"),
            ProcessEvent("C2", "quote", NOW + timedelta(hours=6), "sales", "6"),
            ProcessEvent("C2", "deliver", NOW + timedelta(hours=12), "ops", "7"),
        ]
        miner = ProcessMiner(events)
        assessment = miner.assess(
            allowed_transitions=(("quote", "approve"), ("approve", "deliver")),
            required_activities=("quote", "approve", "deliver"),
            allowed_starts=("quote",),
            allowed_ends=("deliver",),
        )
        self.assertEqual(assessment.case_count, 2)
        self.assertEqual(assessment.variant_count, 2)
        self.assertEqual(assessment.conformance_rate, 0.5)
        self.assertGreater(assessment.rework_event_rate, 0)
        self.assertGreater(assessment.average_handoffs_per_case, 1)
        self.assertTrue(any(item.violation_type == "unexpected_transition" for item in assessment.violations))
        delay = miner.cost_of_delay(assessment, value_per_case_hour=100)
        self.assertGreater(delay["approve->deliver"], 0)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = PolicyEngine([
            PolicyRule(
                "blocked-vendor",
                "purchase",
                PolicyEffect.DENY,
                (PolicyCondition("attributes.blocked", ConditionOperator.EQ, True),),
                priority=100,
            ),
            PolicyRule(
                "material-purchase",
                "purchase",
                PolicyEffect.REQUIRE_APPROVAL,
                (PolicyCondition("attributes.amount", ConditionOperator.GTE, 100),),
                obligations=("retain_quote", "retain_approval"),
                approval_roles=("finance", "procurement"),
                priority=50,
            ),
            PolicyRule("ordinary-purchase", "purchase", PolicyEffect.ALLOW),
        ])

    def request(self, **payload):
        return PolicyRequest.from_payload(
            "purchase", "analyst", payload,
            requester="analyst", executor="buyer-agent", at=NOW,
        )

    @staticmethod
    def grant(request, approval_id, actor, role):
        return ApprovalGrant(
            approval_id, actor, role, "purchase", request.request_hash,
            NOW - timedelta(minutes=5), NOW + timedelta(hours=1),
        )

    def test_expiring_scoped_approvals_and_segregation_of_duties(self):
        request = self.request(amount=500, blocked=False)
        one = self.grant(request, "A1", "cfo", "finance")
        pending = self.engine.evaluate(request, (one,))
        self.assertEqual(pending.status, "approval_required")
        self.assertEqual(pending.missing_approval_roles, ("procurement",))
        two = self.grant(request, "A2", "cpo", "procurement")
        allowed = self.engine.evaluate(request, (one, two))
        self.assertTrue(allowed.allowed)
        self.assertEqual(set(allowed.obligations), {"retain_quote", "retain_approval"})

        conflicted = self.grant(request, "A3", "analyst", "procurement")
        decision = self.engine.evaluate(request, (one, conflicted))
        self.assertIn("segregation_of_duties:procurement", decision.reasons)

    def test_deny_overrides_valid_approvals(self):
        request = self.request(amount=500, blocked=True)
        grants = (
            self.grant(request, "A1", "cfo", "finance"),
            self.grant(request, "A2", "cpo", "procurement"),
        )
        decision = self.engine.evaluate(request, grants)
        self.assertEqual(decision.status, "denied")
        self.assertFalse(decision.allowed)

    def test_expired_approval_is_not_authority(self):
        request = self.request(amount=500, blocked=False)
        expired = ApprovalGrant(
            "expired", "cfo", "finance", "purchase", request.request_hash,
            NOW - timedelta(hours=2), NOW - timedelta(hours=1),
        )
        procurement = self.grant(request, "A2", "cpo", "procurement")
        decision = self.engine.evaluate(request, (expired, procurement))
        self.assertEqual(decision.status, "approval_required")
        self.assertIn("finance", decision.missing_approval_roles)

    def test_decision_hash_binds_request_actor_and_evaluation_time(self):
        base = self.request(amount=10, blocked=False)
        changed_request = self.request(amount=11, blocked=False)
        changed_actor = PolicyRequest.from_payload(
            "purchase", "different-actor", {"amount": 10, "blocked": False},
            requester="analyst", executor="buyer-agent", at=NOW,
        )
        changed_time = PolicyRequest.from_payload(
            "purchase", "analyst", {"amount": 10, "blocked": False},
            requester="analyst", executor="buyer-agent", at=NOW + timedelta(seconds=1),
        )
        decisions = [
            self.engine.evaluate(request)
            for request in (base, changed_request, changed_actor, changed_time)
        ]
        self.assertEqual(len({decision.decision_hash for decision in decisions}), 4)
        self.assertEqual(decisions[0].request_hash, base.request_hash)
        self.assertEqual(decisions[0].evaluated_at, NOW.isoformat())


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        registry = SkillRegistry()
        registry.register(Skill("double", lambda request: {"value": request["amount"] * 2}))
        registry.register(Skill("label", lambda request: {"label": f"V-{request['value']}"}))
        registry.register(Skill("reserve", lambda request: {"reservation_id": request["reservation_id"]}))
        registry.register(Skill("release", lambda request: {"released": request["reservation_id"]}))

        def fail(_request):
            raise RuntimeError("simulated handler failure")

        registry.register(Skill("fail", fail, idempotent=False))
        self.runtime = AgentRuntime(registry)
        self.agent = AgentSpec(
            "workflow-agent", BusinessFunction.OPERATIONS, "Run controlled local workflow",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT, frozenset(), frozenset(),
        )
        self.context = ExecutionContext(actor="consultant", timestamp=NOW)

    def test_dag_bindings_receipts_and_replay(self):
        definition = WorkflowDefinition("value-flow", "1", (
            WorkflowStep("calculate", "double", bindings={"amount": "input.amount"}),
            WorkflowStep(
                "render", "label", dependencies=("calculate",),
                bindings={"value": "steps.calculate.output.value"},
            ),
        ))
        executor = WorkflowExecutor(self.runtime)
        first = executor.run(definition, self.agent, {"amount": 4}, self.context, run_id="R1")
        second = executor.run(definition, self.agent, {"amount": 4}, self.context, run_id="R2")
        self.assertEqual(first.status, "completed")
        self.assertEqual(first.steps[-1].output["label"], "V-8")
        self.assertTrue(replay_matches(first, second))
        self.assertTrue(self.runtime.ledger.verify())

    def test_failure_compensates_completed_steps(self):
        definition = WorkflowDefinition("rollback-flow", "1", (
            WorkflowStep(
                "reserve", "reserve", constants={"reservation_id": "RES-1"},
                compensation_skill_id="release",
                compensation_bindings={"reservation_id": "steps.reserve.output.reservation_id"},
            ),
            WorkflowStep(
                "materialize", "fail", dependencies=("reserve",),
                failure_policy=FailurePolicy.ROLLBACK,
            ),
        ))
        result = WorkflowExecutor(self.runtime).run(
            definition, self.agent, {}, self.context, run_id="ROLLBACK-1",
        )
        self.assertEqual(result.status, "rolled_back")
        self.assertEqual(result.steps[0].compensation_status, "completed")
        self.assertEqual(result.steps[1].status, "failed")

    def test_budget_prevents_unbounded_attempts(self):
        definition = WorkflowDefinition("budget-flow", "1", (
            WorkflowStep("expensive", "double", constants={"amount": 2}, max_attempts=3, cost_units=5),
        ))
        result = WorkflowExecutor(self.runtime).run(
            definition, self.agent, {}, self.context, run_id="BUDGET-1",
            budget=WorkflowBudget(max_steps=1, max_attempts=2, max_cost_units=10),
        )
        self.assertEqual(result.status, "budget_exceeded")
        self.assertEqual(result.attempts_used, 0)

    def test_policy_grant_authorizes_high_risk_runtime_execution(self):
        registry = SkillRegistry()
        registry.register(Skill(
            "controlled-write",
            lambda request: {"written": request["value"]},
            risk_tier=RiskTier.HIGH,
        ))
        runtime = AgentRuntime(registry)
        agent = AgentSpec(
            "controlled-agent", BusinessFunction.OPERATIONS, "Controlled execution",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT, frozenset(), frozenset(),
        )
        policy = PolicyEngine((
            PolicyRule(
                "write-approval", "write", PolicyEffect.REQUIRE_APPROVAL,
                approval_roles=("controller",),
            ),
        ))
        definition = WorkflowDefinition("controlled", "1", (
            WorkflowStep(
                "write", "controlled-write", constants={"value": 7},
                policy_action="write",
            ),
        ))
        request = PolicyRequest.from_payload(
            "write", "consultant", {"value": 7},
            attributes={
                "request": {"value": 7},
                "step_id": "write",
                "agent_id": "controlled-agent",
                "phase": "forward",
            },
            requester="consultant", executor="controlled-agent", at=NOW,
        )
        grant = ApprovalGrant(
            "write-1", "controller-user", "controller", "write", request.request_hash,
            NOW - timedelta(minutes=1), NOW + timedelta(hours=1),
        )
        result = WorkflowExecutor(runtime, policy).run(
            definition,
            agent,
            {},
            ExecutionContext(actor="consultant", timestamp=NOW),
            run_id="CONTROLLED-1",
            approvals=(grant,),
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.steps[0].output, {"written": 7})
        completed = [entry for entry in runtime.ledger.entries if entry.event_type == "execution_completed"]
        self.assertEqual(len(completed), 1)
        self.assertTrue(completed[0].payload["approval_reference"].startswith("policy:"))

    def test_denied_compensation_is_not_executed(self):
        calls = []
        registry = SkillRegistry()
        registry.register(Skill("reserve-controlled", lambda request: {"id": request["id"]}))
        registry.register(Skill("release-controlled", lambda request: calls.append(request) or {"released": True}))

        def fail(_request):
            raise RuntimeError("failure")

        registry.register(Skill("fail-controlled", fail, idempotent=False))
        runtime = AgentRuntime(registry)
        agent = AgentSpec(
            "rollback-agent", BusinessFunction.OPERATIONS, "Controlled rollback",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT, frozenset(), frozenset(),
        )
        policy = PolicyEngine((
            PolicyRule("deny-release", "release", PolicyEffect.DENY),
        ))
        definition = WorkflowDefinition("rollback-controlled", "1", (
            WorkflowStep(
                "reserve", "reserve-controlled", constants={"id": "R-1"},
                compensation_skill_id="release-controlled",
                compensation_policy_action="release",
            ),
            WorkflowStep(
                "fail", "fail-controlled", dependencies=("reserve",),
                failure_policy=FailurePolicy.ROLLBACK,
            ),
        ))
        result = WorkflowExecutor(runtime, policy).run(
            definition,
            agent,
            {},
            self.context,
            run_id="ROLLBACK-DENIED",
        )
        self.assertEqual(result.status, "rollback_failed")
        self.assertEqual(result.steps[0].compensation_status, "policy_denied")
        self.assertEqual(calls, [])

    def test_retry_attempt_count_changes_replay_fingerprint(self):
        calls = 0

        def flaky(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("transient")
            return {"value": request["value"]}

        registry = SkillRegistry()
        registry.register(Skill("flaky", flaky, idempotent=False))
        runtime = AgentRuntime(registry)
        agent = AgentSpec(
            "retry-agent", BusinessFunction.OPERATIONS, "Retry test",
            frozenset(registry.skill_ids), AutonomyLevel.DRAFT, frozenset(), frozenset(),
        )
        definition = WorkflowDefinition("retry", "1", (
            WorkflowStep("flaky", "flaky", constants={"value": 3}, max_attempts=2),
        ))
        executor = WorkflowExecutor(runtime)
        first = executor.run(definition, agent, {}, self.context, run_id="RETRY-1")
        second = executor.run(definition, agent, {}, self.context, run_id="RETRY-2")
        self.assertEqual(first.steps[0].attempts, 2)
        self.assertEqual(second.steps[0].attempts, 1)
        self.assertFalse(replay_matches(first, second))


class EvaluationTests(unittest.TestCase):
    def test_adversarial_suite_cannot_promote_without_reviewed_real_case(self):
        cases = (
            BenchmarkCase(
                "base", {"amount": 10},
                (OutputAssertion("score", AssertionOperator.EQ, 20),),
                evidence_ids=("fixture:base",),
            ),
            BenchmarkCase(
                "larger", {"amount": 20},
                (OutputAssertion("score", AssertionOperator.EQ, 40),),
                category="adversarial", severity=4, evidence_ids=("fixture:larger",),
            ),
        )
        scorecard = evaluate_suite(
            "scoring-suite", cases, lambda case: {"score": case.payload["amount"] * 2},
            relations=(MetamorphicRelation(
                "monotonic", "base", "larger", "score", RelationOperator.INCREASES,
            ),),
        )
        self.assertEqual(scorecard.pass_rate, 1)
        self.assertEqual(scorecard.adversarial_pass_rate, 1)
        decision = assess_a2_promotion(
            scorecard, PromotionGate(), integrated_workflow=True,
            ledger_valid=True, deterministic_replay=True,
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.target_maturity, "A2")
        self.assertIn("source_addressed_real_case_required", decision.reasons)
        self.assertIn("independent_review_required", decision.reasons)

        reviewed = assess_a2_promotion(
            scorecard,
            PromotionGate(),
            integrated_workflow=True,
            ledger_valid=True,
            deterministic_replay=True,
            real_case_evidence_ids=("public-case:reviewed-001",),
            independent_reviewed=True,
        )
        self.assertTrue(reviewed.eligible)
        self.assertIn("source-addressed real-case", reviewed.limitations[0])


class ValueRealizationTests(unittest.TestCase):
    def test_difference_in_differences_separates_market_movement(self):
        observations = []
        for unit, treated, baseline, outcome in (
            ("T1", True, 10, 16), ("T2", True, 12, 18),
            ("C1", False, 10, 12), ("C2", False, 12, 14),
        ):
            observations.extend((
                OutcomeObservation(unit, OutcomePeriod.BASELINE, treated, baseline, f"{unit}:base"),
                OutcomeObservation(unit, OutcomePeriod.OUTCOME, treated, outcome, f"{unit}:outcome"),
            ))
        result = difference_in_differences(
            observations,
            design_validated=True,
            identification_assumptions=("parallel trends reviewed", "no concurrent differential intervention"),
        )
        self.assertEqual(result.difference_in_differences, 4)
        self.assertEqual(result.interpretation, "controlled_estimate_subject_to_documented_assumptions")
        self.assertEqual(len(result.evidence_ids), 8)

    def test_realization_plan_enforces_guardrails_and_frozen_evidence(self):
        plan = RealizationPlan(
            "close-cycle", "close_days", "CFO", 10, 5, False,
            NOW, NOW + timedelta(days=90), ("baseline:close",),
            (Guardrail("error_rate", GuardrailOperator.LTE, 0.02),),
        )
        result = measure_realization(
            plan, actual=6, as_of=NOW + timedelta(days=60),
            evidence_ids=("outcome:close",), guardrail_values={"error_rate": 0.01},
        )
        self.assertEqual(result.status, "in_progress")
        self.assertAlmostEqual(result.realization_rate, 0.8)
        breached = measure_realization(
            plan, actual=5, as_of=NOW + timedelta(days=90),
            evidence_ids=("outcome:close-2",), guardrail_values={"error_rate": 0.03},
        )
        self.assertEqual(breached.status, "guardrail_breached")


class SimulationTests(unittest.TestCase):
    def test_seeded_monte_carlo_is_reproducible_and_exposes_sensitivity(self):
        case = InitiativeSimulation(
            "quote-control",
            TriangularDistribution(90_000, 100_000, 120_000),
            TriangularDistribution(100_000, 130_000, 160_000),
            TriangularDistribution(8_000, 12_000, 18_000),
            TriangularDistribution(0.65, 0.8, 0.95),
            TriangularDistribution(2, 3, 5),
            TriangularDistribution(20_000, 30_000, 40_000),
            feasibility_probability=0.9,
        )
        first = simulate_initiative(case, iterations=500, seed=41)
        second = simulate_initiative(case, iterations=500, seed=41)
        self.assertEqual(first.sample_checksum, second.sample_checksum)
        self.assertGreater(first.probability_positive_npv, 0.5)
        self.assertIn("annual_gross_value", first.sensitivity)
        self.assertLess(first.downside_p05_npv, first.upside_p95_npv)

    def test_service_pipeline_quantifies_queue_and_rework(self):
        result = simulate_service_pipeline((
            QueueStage("triage", 1, TriangularDistribution(4, 5, 7), 0.1),
            QueueStage("resolve", 2, TriangularDistribution(10, 15, 25), 0.05),
        ), item_count=100, interarrival_minutes=4, seed=7)
        self.assertGreater(result.throughput_per_hour, 0)
        self.assertGreaterEqual(result.p90_cycle_minutes, result.average_cycle_minutes)
        self.assertEqual(set(result.utilization_by_stage), {"triage", "resolve"})


class ValueCreationTests(unittest.TestCase):
    def test_initiatives_bridge_to_exit_equity_moic_and_irr(self):
        baseline = InvestmentBaseline(
            entry_equity=100_000_000,
            exit_years=5,
            baseline_exit_ebitda=30_000_000,
            baseline_exit_net_debt=50_000_000,
            exit_multiple=10,
        )
        bridge = build_value_creation_bridge(baseline, (
            InitiativeImpact(
                "pricing", "CRO", annual_revenue_uplift=10_000_000,
                incremental_gross_margin=0.6, annual_recurring_cost=500_000,
                one_time_cost=1_000_000, realization_fraction_at_exit=0.8,
                evidence_ids=("case:pricing",),
            ),
            InitiativeImpact(
                "working-capital", "CFO", annual_other_savings=1_000_000,
                working_capital_release=8_000_000, one_time_cost=500_000,
                dependencies=("pricing",), evidence_ids=("case:wc",),
            ),
        ))
        self.assertGreater(bridge.value_plan_exit_equity_value, bridge.baseline_exit_equity_value)
        self.assertGreater(bridge.moic_uplift, 0)
        self.assertGreater(bridge.irr_uplift, 0)
        self.assertEqual(len(bridge.contributions), 2)

    def test_100_day_plan_exposes_critical_path_and_unresolved_gates(self):
        plan = schedule_100_day_plan((
            Workstream("baseline", "pricing", "CFO", 15),
            Workstream(
                "pilot", "pricing", "CRO", 30, ("baseline",),
                decision_gate="pilot acceptance", required_evidence=("pilot-scorecard",),
            ),
            Workstream("scale", "pricing", "COO", 40, ("pilot",)),
        ))
        self.assertTrue(plan.within_100_days)
        self.assertEqual(plan.critical_path, ("baseline", "pilot", "scale"))
        self.assertEqual(plan.unresolved_gate_ids, ("pilot",))


if __name__ == "__main__":
    unittest.main()
