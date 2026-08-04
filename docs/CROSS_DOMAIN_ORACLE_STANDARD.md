# Cross-Domain Oracle Standard

The cross-domain engines are independent reference calculations. They do not reuse workbook formulas and they do not make M3 or M4 claims.

## Capital allocation

Capital allocation is a continuous linear program, not a one-dimensional ranking. It maximizes total risk-adjusted value subject to group capital, group liquidity, and per-unit request bounds. The implementation uses a hand-rolled primal simplex solver from a zero-feasible slack basis with Bland's pivot rule. A release must retain a case where ranking by value per capital is suboptimal because liquidity is also scarce.

Required controls:

- every unit name is nonempty and unique;
- all resource limits and request bounds are finite and nonnegative;
- expected return is finite;
- capital and liquidity conserve within tolerance;
- allocations remain within request bounds;
- the committed adversarial optimum is asserted by the frontier validator.

## Liquidity contagion

Contagion is defined by membership: a propagated default is any defaulted entity that was not below its minimum-liquidity threshold immediately after the initial outflows. It is not inferred by comparing the number of defaults with the number of shocked entities; a shocked entity may remain solvent.

Required controls:

- initial and propagated default sets are reported separately;
- transmitted losses and ending liquidity reconcile to initial liquidity and outflows;
- the propagation flag is raised whenever the propagated-default set is nonempty;
- the committed adversarial case includes two shocked entities, one initial default, and one propagated default so cardinality-based logic cannot pass.

## Regression evidence

`standards/frontier/frontier_registry.json` may declare an `expected` subset for a case. `tools/validate_frontier_program.py` compares that subset recursively while allowing unrelated output fields to evolve. This binds the known counterexamples to every future release without freezing the complete result payload.
