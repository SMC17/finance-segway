"""The release loader's containment guard, and the reasons it gives.

`load_release` refuses to read a receipted artifact that is absent, that
sits outside the release root, or whose hash does not match. Those three
rejections used to be two: a containment failure and a missing file shared
one message, and it said "missing".

That mattered. On macOS a temp directory is `/var/...`, a symlink to
`/private/var/...`, so `(ROOT / relative).resolve()` produced a real,
present file that `is_relative_to(ROOT)` then rejected -- and the loader
reported the file as missing. It is the only thing it was not.

Fixing a containment check is exactly where a test has to prove the check
still contains something, so each rejection is exercised here rather than
only the happy path.
"""
from __future__ import annotations

import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from research.ram import build_universe_viz, fetch_real_universe

AS_OF = date(2026, 8, 4)


def _write_release(root: Path) -> dict:
    days = [(AS_OF - timedelta(days=300 - i)).isoformat() for i in range(301)]
    series = {
        ticker: {
            day: math.exp(4.0 + 0.0005 * i + 0.00001 * t * i)
            for i, day in enumerate(days)
        }
        for t, ticker in enumerate(fetch_real_universe.TICKERS)
    }
    snapshot, covariance = fetch_real_universe.prepare_snapshot(series, AS_OF)
    sources = [
        {"ticker": t, "url": f"https://example.test/{t}",
         "start": days[0], "end": days[-1], "observations": len(days)}
        for t in fetch_real_universe.TICKERS
    ]
    with (
        patch.object(fetch_real_universe, "ROOT", root),
        patch.object(fetch_real_universe, "DATA_DIR", root / "research/ram/data"),
        patch.object(fetch_real_universe, "EXPORT_DIR", root / "research/kdb/exports"),
    ):
        return fetch_real_universe.write_release(snapshot, covariance, sources)


def _load(root: Path):
    with (
        patch.object(build_universe_viz, "ROOT", root),
        patch.object(build_universe_viz, "DATA_DIR", root / "research/ram/data"),
    ):
        return build_universe_viz.load_release(AS_OF)


def _receipt_path(root: Path) -> Path:
    return root / "research/ram/data" / f"receipt_{AS_OF.isoformat()}.json"


class ReleaseContainmentTests(unittest.TestCase):
    def test_a_valid_release_loads(self) -> None:
        """The control. Every rejection below is only meaningful because
        this passes on an unmodified release built the same way."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = _write_release(root)
            _metadata, _covariance, regimes, loaded = _load(root)
            self.assertEqual(receipt["artifacts"], loaded["artifacts"])
            self.assertEqual(3, len(regimes))

    def test_an_artifact_outside_the_release_root_is_refused(self) -> None:
        """The guard still contains. A receipt naming a path that escapes
        the root must be rejected, and told apart from a missing file."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_release(root)
            outside = root.parent / "escaped_artifact.csv"
            outside.write_text("not part of this release\n", encoding="utf-8")
            self.addCleanup(outside.unlink)

            path = _receipt_path(root)
            receipt = json.loads(path.read_text(encoding="utf-8"))
            first = next(iter(receipt["artifacts"]))
            digest = receipt["artifacts"].pop(first)
            receipt["artifacts"][f"../{outside.name}"] = digest
            path.write_text(json.dumps(receipt), encoding="utf-8")

            with self.assertRaises(ValueError) as caught:
                _load(root)
            self.assertIn("escapes the release root", str(caught.exception))

    def test_a_genuinely_missing_artifact_is_still_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = _write_release(root)
            target = root / next(iter(receipt["artifacts"]))
            target.unlink()
            with self.assertRaises(FileNotFoundError) as caught:
                _load(root)
            self.assertIn("missing", str(caught.exception))

    def test_a_tampered_artifact_is_still_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = _write_release(root)
            target = root / next(iter(receipt["artifacts"]))
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaises(ValueError) as caught:
                _load(root)
            self.assertIn("hash mismatch", str(caught.exception))

    def test_the_three_refusals_give_three_different_reasons(self) -> None:
        """A shared message is how the macOS failure went unread for a
        month: the loader reported a present file as missing."""
        reasons = set()
        for scenario in ("escape", "missing", "tamper"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt = _write_release(root)
                first = next(iter(receipt["artifacts"]))
                if scenario == "escape":
                    outside = root.parent / "escaped_reason.csv"
                    outside.write_text("x\n", encoding="utf-8")
                    self.addCleanup(lambda p=outside: p.unlink(missing_ok=True))
                    path = _receipt_path(root)
                    data = json.loads(path.read_text(encoding="utf-8"))
                    digest = data["artifacts"].pop(first)
                    data["artifacts"][f"../{outside.name}"] = digest
                    path.write_text(json.dumps(data), encoding="utf-8")
                elif scenario == "missing":
                    (root / first).unlink()
                else:
                    target = root / first
                    target.write_bytes(target.read_bytes() + b"\n")
                try:
                    _load(root)
                except (ValueError, FileNotFoundError) as exc:
                    reasons.add(str(exc).split(":")[0])
        self.assertEqual(3, len(reasons), reasons)


if __name__ == "__main__":
    unittest.main()
