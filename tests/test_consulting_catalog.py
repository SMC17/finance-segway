from pathlib import Path
import unittest

from finance_segway.consulting.schema import BusinessFunction
from tools.validate_consulting_catalog import load_catalog, validate_catalog


ROOT = Path(__file__).resolve().parents[1]


class ConsultingCatalogTests(unittest.TestCase):
    def test_catalog_covers_every_function_and_implementation_claim(self):
        self.assertEqual(validate_catalog(ROOT), [])
        catalog = load_catalog(ROOT / "standards/consulting/capability_catalog.json")
        functions = {entry["function"] for entry in catalog["capabilities"]}
        self.assertEqual(functions, {item.value for item in BusinessFunction})
        self.assertTrue(all(entry["maturity"] == "A1" for entry in catalog["capabilities"]))
        platform = {entry["id"]: entry["maturity"] for entry in catalog["platform_capabilities"]}
        self.assertEqual(platform["value-realization-attribution"], "A1")
        self.assertEqual({"A1"}, set(platform.values()))


if __name__ == "__main__":
    unittest.main()
