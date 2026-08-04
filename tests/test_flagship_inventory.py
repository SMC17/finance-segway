import unittest

from tools.promote_flagship_inventory import PROMOTIONS, promote


class FlagshipInventoryTests(unittest.TestCase):
    def test_promote_updates_all_flagships(self):
        inventory = {
            "version": "1.0.0",
            "models": [
                {
                    "id": model_id,
                    "builder": "old.py",
                    "declared_maturity": "M1",
                    "required_engines": [],
                    "required_perspectives": [],
                    "reference_checks": [],
                }
                for model_id in PROMOTIONS
            ],
        }
        result = promote(inventory, version="9.9.9")
        self.assertEqual(result["version"], "9.9.9")
        by_id = {item["id"]: item for item in result["models"]}
        for model_id, promotion in PROMOTIONS.items():
            self.assertEqual(by_id[model_id]["builder"], promotion["builder"])
            self.assertEqual(by_id[model_id]["declared_maturity"], "M2")
            self.assertTrue(by_id[model_id]["required_engines"])
            self.assertTrue(by_id[model_id]["reference_checks"])

    def test_missing_inventory_model_rejected(self):
        inventory = {"version": "1.0.0", "models": []}
        with self.assertRaisesRegex(ValueError, "missing flagship IDs"):
            promote(inventory, version="2.0.0")


if __name__ == "__main__":
    unittest.main()
