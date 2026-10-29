"""Guard the quick-start dependency invariant for requirements.txt.

The documented quick start is ``pip install -r requirements.txt``. Pinned
contract tests import setuptools (build backend), pyarrow (parquet engine) and
ruff (lint/format gate), so all three must be declared in requirements.txt or
those tests skip instead of running in a bare-clone environment.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"


def _declared_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # strip environment markers / extras
        name = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip().lower()
        if name:
            names.add(name)
    return names


def test_requirements_declares_pinned_contract_dependencies():
    names = _declared_names(REQUIREMENTS.read_text())
    for dep in ("setuptools", "pyarrow", "ruff"):
        assert dep in names, f"{dep} must be declared in requirements.txt"
