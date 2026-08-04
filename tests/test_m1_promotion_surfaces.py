from __future__ import annotations

import unittest

from tools import apply_m1_promotion_surfaces

EXPECTED_IDS = apply_m1_promotion_surfaces.EXPECTED_IDS


class M1PromotionSurfaceTests(unittest.TestCase):
    def test_exact_artifact_coverage(self):
        targets = apply_m1_promotion_surfaces.promotion_targets()
        self.assertEqual(len(targets), 27)
        self.assertEqual(
            sum(1 for item in targets if item["kind"] == "canonical"), 9
        )
        self.assertEqual(
            sum(1 for item in targets if item["kind"] != "canonical"), 18
        )
        self.assertEqual({item["model_id"] for item in targets}, EXPECTED_IDS)

    def test_paths_are_unique(self):
        targets = apply_m1_promotion_surfaces.promotion_targets()
        paths = [item["path"] for item in targets]
        self.assertEqual(len(paths), len(set(paths)))

    def test_every_model_has_canonical_conventional_and_adversarial(self):
        targets = apply_m1_promotion_surfaces.promotion_targets()
        by_model = {}
        for item in targets:
            by_model.setdefault(item["model_id"], set()).add(item["kind"])
        for model_id in EXPECTED_IDS:
            self.assertEqual(
                by_model[model_id],
                {"canonical", "conventional", "adversarial"},
                msg=model_id,
            )


if __name__ == "__main__":
    unittest.main()
