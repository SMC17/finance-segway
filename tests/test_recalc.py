"""Regression tests for safe workbook recalculation installation."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import recalc


class RecalcTests(unittest.TestCase):
    def test_conversion_fallback_stages_on_source_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "repository-mount"
            profile_dir = root / "temporary-profile" / "profile"
            source_dir.mkdir()
            source = source_dir / "model.xlsx"
            source.write_bytes(b"old")

            def fake_run(command, **_kwargs):
                output_dir = Path(command[command.index("--outdir") + 1])
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / source.name).write_bytes(b"recalculated")
                return subprocess.CompletedProcess(command, 0, "", "")

            real_replace = os.replace

            def same_filesystem_replace(staged, destination):
                self.assertEqual(Path(staged).parent, Path(destination).parent)
                return real_replace(staged, destination)

            with (
                patch.object(recalc.subprocess, "run", side_effect=fake_run),
                patch.object(recalc.os, "replace", side_effect=same_filesystem_replace),
            ):
                error = recalc._recalc_via_conversion(
                    str(source), timeout=30, profile_dir=profile_dir
                )

            self.assertIsNone(error)
            self.assertEqual(b"recalculated", source.read_bytes())


if __name__ == "__main__":
    unittest.main()
