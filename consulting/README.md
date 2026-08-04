# Consulting Wing

This directory contains public, synthetic reference cases for the governed
consulting operating system implemented under `finance_segway/consulting/`.

## Run the reference case

```bash
PYTHONPATH=. python tools/run_consulting_reference_case.py
```

The benchmark uses only committed synthetic inputs. It demonstrates:

- a P&L-linked operating graph and bottleneck analysis;
- confidence- and risk-adjusted initiative selection;
- a policy-controlled quoting agent with evidence and approval scopes;
- role-scoped knowledge retrieval with citations;
- hash-chained execution receipts;
- baseline-versus-redesigned service-business economics.

Validate all declared functional capabilities with:

```bash
PYTHONPATH=. python tools/validate_consulting_catalog.py
PYTHONPATH=. python -m unittest tests.test_consulting_core \
  tests.test_consulting_functions tests.test_consulting_catalog \
  tests.test_consulting_reference_case -v
```

No client data or external integration configuration belongs here. See
`docs/CONSULTING_OPERATING_SYSTEM.md` for the architecture and maturity rules.
