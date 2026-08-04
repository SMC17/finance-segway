"""Tests for the real-only market-data release boundary."""

from __future__ import annotations

import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from research.ram import build_universe_viz, fetch_real_universe
from research.ram.simple_covariance import is_positive_semidefinite


class RealUniverseTests(unittest.TestCase):
    def test_source_url_is_bound_to_explicit_dates(self) -> None:
        url = fetch_real_universe.source_url(
            "AAPL", date(2025, 1, 1), date(2026, 1, 1)
        )
        self.assertIn("AAPL", url)
        self.assertIn("period1=", url)
        self.assertIn("period2=", url)

    def test_sample_covariance_matches_manual_identity(self) -> None:
        covariance = fetch_real_universe.sample_covariance(
            [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]]
        )
        self.assertAlmostEqual(252.0, covariance[0][0])
        self.assertAlmostEqual(504.0, covariance[0][1])
        self.assertAlmostEqual(1008.0, covariance[1][1])
        self.assertTrue(is_positive_semidefinite(covariance))

    def test_release_is_receipted_and_loads_without_fallback(self) -> None:
        as_of = date(2026, 8, 4)
        days = [(as_of - timedelta(days=300 - index)).isoformat() for index in range(301)]
        series = {
            ticker: {
                day: math.exp(4.0 + 0.0005 * index + 0.00001 * ticker_index * index)
                for index, day in enumerate(days)
            }
            for ticker_index, ticker in enumerate(fetch_real_universe.TICKERS)
        }
        snapshot, covariance = fetch_real_universe.prepare_snapshot(series, as_of)
        sources = [
            {"ticker": ticker, "url": f"https://example.test/{ticker}", "start": days[0], "end": days[-1], "observations": len(days)}
            for ticker in fetch_real_universe.TICKERS
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "research/ram/data"
            exports = root / "research/kdb/exports"
            with (
                patch.object(fetch_real_universe, "ROOT", root),
                patch.object(fetch_real_universe, "DATA_DIR", data),
                patch.object(fetch_real_universe, "EXPORT_DIR", exports),
            ):
                receipt = fetch_real_universe.write_release(
                    snapshot, covariance, sources
                )
            self.assertEqual(
                "external_historical_market_observation",
                receipt["classification"],
            )
            self.assertEqual(4, len(receipt["artifacts"]))

            with (
                patch.object(build_universe_viz, "ROOT", root),
                patch.object(build_universe_viz, "DATA_DIR", data),
            ):
                metadata, loaded_covariance, regimes, loaded_receipt = (
                    build_universe_viz.load_release(as_of)
                )
            self.assertEqual(snapshot["metadata"], metadata)
            self.assertEqual(covariance, loaded_covariance)
            self.assertEqual(3, len(regimes))
            self.assertEqual(receipt["artifacts"], loaded_receipt["artifacts"])


if __name__ == "__main__":
    unittest.main()
