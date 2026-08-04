# Consulting Control-Plane Standard

## Purpose

The control plane makes a consulting recommendation executable as a governed
local decision system without granting it external authority. Every material
step must be explainable from observed process evidence, declared policy,
request-scoped approvals, deterministic skills, and a verifiable receipt chain.

## Required control sequence

1. Normalize event records with a case, activity, timezone-aware timestamp, and
   optional actor and event identity.
2. Compare observed traces with an explicitly declared transition model. Record
   variants, missing activities, unexpected transitions, cycle tails, rework,
   actor handoffs, and delay concentration.
3. Hash the exact proposed request before seeking approval. An approval is valid
   only for its action and request hash, inside its validity window.
4. Apply policy with deny overrides. A general allow cannot neutralize a matched
   deny. Approval rules remain gates even when a general allow also matches.
5. Enforce segregation of duties. The requester and executor cannot satisfy a
   segregated approval, and one actor cannot fill multiple required roles in the
   same decision.
6. Execute only a registered skill allowed by the agent, autonomy level,
   evidence pack, read/write scopes, calling context, and named approval.
7. Resolve workflow bindings from initial input or completed predecessor output.
   Unknown paths, dependency cycles, and self-dependencies are invalid.
8. Enforce maximum steps, attempts, and cost units before a step starts. Retry
   only a failed handler; approval and policy blocks are not retry conditions.
9. On a rollback policy, execute only declared compensating skills in reverse
   completion order. Compensation is itself governed and receipted.
10. Compare replay fingerprints over definition, input, status, reason, and
    output semantics. Timing, latency, and new ledger hashes are excluded.

## Evaluation evidence

An A2 control-plane claim requires all of the following:

- at least one frozen, source-addressed real operational case;
- a completed multi-step reference path;
- critical reference and adversarial cases with no failures;
- metamorphic relations where expected behavior should be monotonic or stable;
- evidence identity on every real case and deterministic test vector;
- a valid hash-chained ledger;
- deterministic replay of the reference path;
- independent review of lineage, controls, results, and limitations;
- explicit limitations stating that no external system was mutated.

A2 is not client approval, production security, live monitoring, or realized
outcome evidence. Those belong to A3 and A4.

## Threat and failure boundaries

The current core detects missing authority, missing evidence, scope mismatch,
expired or mis-scoped approval, self-approval conflicts, deny overrides, cycles,
unresolved bindings, step failure, budget exhaustion, failed compensation,
evaluation regression, and ledger tampering.

It is not a process-isolation sandbox, credential vault, network boundary,
identity provider, database transaction manager, or production scheduler. It
contains no connector or autonomous external action.
