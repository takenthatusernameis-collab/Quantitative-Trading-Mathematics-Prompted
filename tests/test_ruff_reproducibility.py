"""Guard the ruff reproducibility invariant.

The published record quotes ``ruff check src tests run_*.py`` and
``ruff format --check src tests run_*.py`` as passing. Those commands are only
meaningful if ruff is declared in ``pyproject.toml``'s
``[project.optional-dependencies] lint`` and its configuration is committed
under ``[tool.ruff]*``. This test pins both so the reproducibility gap recorded
in HANDOFF.md cannot silently return.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _section(text: str, header: str) -> str:
    """Return the body of a TOML section (everything up to the next header)."""
    start = text.index(f"[{header}]") + len(f"[{header}]")
    rest = text[start:]
    end = len(rest)
    for index, line in enumerate(rest.splitlines()):
        if line.startswith("["):
            end = index
            break
    return "\n".join(rest.splitlines()[:end])


def test_ruff_is_declared_as_a_lint_dependency():
    """ruff must be an optional ``lint`` dependency so it is installable."""
    pyproject = PYPROJECT.read_text()
    deps = _section(pyproject, "project.optional-dependencies")
    assert 'lint = ["ruff>=0.6.0"]' in deps, (
        "ruff must be declared under [project.optional-dependencies] lint"
    )


def test_ruff_configuration_is_committed():
    """The [tool.ruff]* configuration must be committed so the quoted
    ruff commands are reproducible from the repository."""
    pyproject = PYPROJECT.read_text()
    for header in ("tool.ruff", "tool.ruff.lint", "tool.ruff.format"):
        assert f"[{header}]" in pyproject, f"missing committed [{header}] section"
