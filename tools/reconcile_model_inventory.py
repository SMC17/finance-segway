"""Update model inventory entries after reconciled builders pass their promotion gate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "standards" / "model_inventory.json"

UPDATES = {
    "05": {
        "builder": "tools/builders/build_private_credit_template.py",
        "declared_maturity": "M2",
        "reference_checks": ["approximate_cash_ytm", "recovery_lgd_bounds", "debt_cash_schedule_conservation"],
    },
    "06": {
        "builder": "tools/builders/build_debt_finance_template.py",
        "declared_maturity": "M2",
        "reference_checks": ["sources_uses_balance", "maturity_concentration", "recovery_lgd_bounds"],
    },
    "07": {
        "builder": "tools/builders/build_public_finance_template.py",
        "declared_maturity": "M2",
        "reference_checks": ["debt_stabilizing_primary_balance", "projected_debt_ratio_identity", "coverage_bounds"],
    },
}


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    payload["version"] = "1.1.0"
    found = set()
    for model in payload["models"]:
        model_id = model.get("id")
        if model_id in UPDATES:
            model.update(UPDATES[model_id])
            found.add(model_id)
    missing = set(UPDATES) - found
    if missing:
        raise SystemExit(f"inventory entries not found: {sorted(missing)}")
    PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("promoted inventory entries: 05, 06, 07")


if __name__ == "__main__":
    main()
