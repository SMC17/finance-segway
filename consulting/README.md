# Consulting Wing

This directory documents the governed consulting operating system implemented
under `finance_segway/consulting/`. Business evidence must be source-addressed
and real; fabricated reference companies and committed benchmark datasets are
prohibited.

The deterministic core implements:

- a P&L-linked operating graph and bottleneck analysis;
- confidence- and risk-adjusted initiative selection;
- a policy-controlled quoting agent with evidence and approval scopes;
- role-scoped knowledge retrieval with citations;
- hash-chained execution receipts;
- baseline-versus-redesigned service-business economics;
- deterministic adversarial and metamorphic tests in Python.

Those tests establish A1 deterministic-core maturity only. A2 requires a
source-addressed operational case, reproducible receipts, and independent
review; no platform capability currently claims A2.

Validate all declared functional capabilities with:

```bash
PYTHONPATH=. python tools/validate_consulting_catalog.py
PYTHONPATH=. python -m unittest tests.test_consulting_core \
  tests.test_consulting_functions tests.test_consulting_catalog \
  tests.test_consulting_frontier tests.test_consulting_real_data_policy -v
```

No confidential client data or external integration configuration belongs in
the public repository. See `docs/CONSULTING_OPERATING_SYSTEM.md` for the
architecture and maturity rules.
