"""Run a legacy workbook builder and enrich its single XLSX artifact.

Legacy builders execute at import time and write a fixed file name in the
current working directory. Release wrappers use this adapter so they can expose
a modern ``--output`` interface without duplicating the legacy workbook body.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from openpyxl import load_workbook
from openpyxl.workbook import Workbook

try:
    from tools.builders.hardening_formula_compatibility import normalize_hardened_formulas
except ModuleNotFoundError:
    from hardening_formula_compatibility import normalize_hardened_formulas

ROOT = Path(__file__).resolve().parents[2]
BUILDERS = Path(__file__).resolve().parent


def load_legacy_workbook(script_name: str) -> Workbook:
    script = BUILDERS / script_name
    if not script.is_file():
        raise FileNotFoundError(f"legacy builder not found: {script}")
    with tempfile.TemporaryDirectory(prefix="finance-segway-legacy-") as temp_name:
        temp = Path(temp_name)
        env = os.environ.copy()
        paths = [str(ROOT), str(ROOT / "tools"), str(BUILDERS)]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=temp,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        artifacts = sorted(temp.glob("*.xlsx"))
        if result.returncode != 0 or len(artifacts) != 1:
            raise RuntimeError(
                f"legacy builder {script_name} returned {result.returncode} and "
                f"produced {len(artifacts)} workbooks\n{result.stdout}"
            )
        return load_workbook(artifacts[0])


def build_release(
    script_name: str,
    output: Path,
    enrich: Callable[[Workbook], None],
) -> None:
    workbook = load_legacy_workbook(script_name)
    enrich(workbook)
    normalize_hardened_formulas(workbook)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.calculation.calcMode = "auto"
    except AttributeError:
        pass
    workbook.save(output)
