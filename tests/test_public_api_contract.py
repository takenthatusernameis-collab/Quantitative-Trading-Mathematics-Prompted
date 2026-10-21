"""The package's public API is declared, complete, and actually exported.

H44 added "convenience exports" to the top-level ``qtr`` package and verified
them with ``from qtr import *; print('ok')`` -- a check that passes whether the
import exports **zero** names or five hundred.  The check was vacuous, and the
surface it claimed to add was empty:

* ``qtr.__all__`` was ``["__version__"]``, so ``from qtr import *`` exported
  exactly one name and the wildcard re-exports were unreachable through it;
* ``qtr.backtest``, ``qtr.data`` and ``qtr.tracking`` had **empty**
  ``__init__.py`` files and ``qtr.utils`` had none at all, so four of the six
  subpackages exported nothing at all -- ``qtr.BacktestEngine``,
  ``qtr.get_data_fetcher``, ``qtr.create_experiment`` and ``qtr.get_config``
  did not exist;
* ``qtr.utils`` was not a *package* the build backend knew about:
  ``setuptools.find_packages(where="src")`` returned six packages and
  ``qtr.utils`` was not one of them.  It shipped only because
  ``setuptools`` copies the stray ``config.py`` as package data and PEP 420
  turns the directory into a namespace package at import time -- and because
  ``qtr/__init__.py`` imports it, the *whole package* was one directory away
  from failing to import.

This module pins the surface so the defect cannot silently return:

1. every subpackage is a **regular** package and is **discovered** by the
   build backend (the ``qtr.utils`` hole);
2. every subpackage declares an explicit, non-empty ``__all__`` and uses
   explicit imports (so the declaration is meaningful);
3. every subpackage's ``__all__`` is **exactly** the public API of the
   module(s) it re-exports -- a new public function that nobody exports fails
   this test, and so does an export of a name that does not exist;
4. the top-level ``__all__`` is the union of the subpackages' ``__all__``s;
5. ``from qtr import *`` exports **exactly** the declared API, and that set is
   not empty -- the non-vacuous replacement for ``print('ok')``.

The measurement of the gate is a separate step (it needs the whole suite):

    python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

import qtr

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "qtr"
PYPROJECT = ROOT / "pyproject.toml"


def _subpackage_dirs() -> list[pathlib.Path]:
    """Every directory under ``src/qtr`` that holds a module."""
    return sorted(d for d in PKG.iterdir() if d.is_dir() and any(d.glob("*.py")))


def _public_names(module_path: pathlib.Path) -> set[str]:
    """The public module-level names defined by a module (AST, not runtime).

    Public means: a top-level function, class, or assignment whose name does
    not start with an underscore.  Imported names are deliberately excluded --
    ``engine.py`` imports ``numpy`` and ``pandas``, and neither is part of the
    package's API.
    """
    tree = ast.parse(module_path.read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)
    return names


def _init_facts(package: str) -> dict:
    """Parse a subpackage's ``__init__.py``.

    Returns the declared ``__all__``, the names it actually imports, the
    modules it re-exports from, and whether it uses a star import.
    """
    init = PKG / package / "__init__.py"
    tree = ast.parse(init.read_text())
    declared: list[str] | None = None
    imported: set[str] = set()
    modules: set[str] = set()
    star_imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    declared = [elt.value for elt in node.value.elts]
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    star_imports.append(node.module or "")
                else:
                    imported.add(alias.asname or alias.name)
                    if node.module:
                        modules.add(node.module)

    return {
        "declared": declared,
        "imported": imported,
        "modules": modules,
        "star_imports": star_imports,
    }


SUBPACKAGES = sorted(d.name for d in _subpackage_dirs())


# --------------------------------------------------------------------------- #
# 1. The packaging hole: every subpackage must be a discoverable package
# --------------------------------------------------------------------------- #
def test_every_subpackage_is_a_regular_package():
    """A directory without ``__init__.py`` is a namespace package.

    ``setuptools.packages.find`` only discovers regular packages, so a
    namespace subdirectory is not part of the distribution: it is copied as
    stray data and only importable by PEP 420 luck.  ``qtr/utils`` was in
    exactly that state.
    """
    for name in SUBPACKAGES:
        init = PKG / name / "__init__.py"
        assert init.exists(), (
            f"src/qtr/{name} has no __init__.py: it is a namespace package, "
            "not a discoverable distribution package"
        )


def test_every_subpackage_is_discovered_by_the_build_backend():
    """The build backend must find every subpackage.

    ``qtr.utils`` was invisible to ``setuptools.find_packages(where="src")``:
    the distribution shipped ``qtr/utils/config.py`` without a package marker
    for ``qtr.utils`` itself.
    """
    setuptools = pytest.importorskip("setuptools")
    found = set(setuptools.find_packages(where=str(ROOT / "src")))
    for name in SUBPACKAGES:
        assert f"qtr.{name}" in found, (
            f"qtr.{name} is not discovered by the build backend (found: {sorted(found)})"
        )


def test_the_declared_package_root_is_the_src_layout():
    """The distribution's package root must be ``src`` (the layout in use)."""
    setuptools = pytest.importorskip("setuptools")
    found = set(setuptools.find_packages(where=str(ROOT / "src")))
    assert "qtr" in found, f"qtr is not a discoverable package (found: {sorted(found)})"


# --------------------------------------------------------------------------- #
# 2. Every subpackage declares its API
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("package", SUBPACKAGES)
def test_every_subpackage_declares_an_explicit_non_empty_all(package):
    """``__all__`` must be declared and non-empty."""
    facts = _init_facts(package)
    declared = facts["declared"]
    assert declared is not None, f"src/qtr/{package}/__init__.py does not declare __all__"
    assert declared, f"src/qtr/{package}/__init__.py declares an empty __all__"
    assert len(declared) == len(set(declared)), (
        f"src/qtr/{package}/__init__.py repeats a name in __all__"
    )


@pytest.mark.parametrize("package", SUBPACKAGES)
def test_no_subpackage_uses_a_star_import(package):
    """A star import makes ``__all__`` the only description of the surface.

    The subpackages use explicit imports so the declaration and the code can
    be compared; only the top-level aggregator composes one.
    """
    facts = _init_facts(package)
    assert not facts["star_imports"], (
        f"src/qtr/{package}/__init__.py uses a star import "
        f"({facts['star_imports']}); use explicit imports so __all__ is checkable"
    )


@pytest.mark.parametrize("package", SUBPACKAGES)
def test_each_subpackage_all_is_exactly_the_public_api_of_its_module(package):
    """``__all__`` must equal the public API of the module(s) it re-exports.

    This is the invariant that makes the declaration meaningful in both
    directions: a new public function that nobody exports fails here, and so
    does an export of a name the module does not define.
    """
    facts = _init_facts(package)
    declared = set(facts["declared"] or [])

    expected: set[str] = set()
    for module in facts["modules"]:
        path = ROOT / "src" / pathlib.Path(*module.split(".")).with_suffix(".py")
        assert path.exists(), f"src/qtr/{package}/__init__.py re-exports a missing module: {module}"
        expected |= _public_names(path)

    assert declared == expected, (
        f"src/qtr/{package}/__init__.py __all__ does not match the public API of "
        f"{sorted(facts['modules'])}: missing {sorted(expected - declared)}, "
        f"unexpected {sorted(declared - expected)}"
    )


@pytest.mark.parametrize("package", SUBPACKAGES)
def test_each_subpackage_actually_imports_every_name_in_its_all(package):
    """Every declared name must really be bound at runtime."""
    module = __import__(f"qtr.{package}", fromlist=["__all__"])
    for name in module.__all__:
        assert hasattr(module, name), f"qtr.{package}.{name} is declared in __all__ but not bound"


# --------------------------------------------------------------------------- #
# 3. The top level aggregates them
# --------------------------------------------------------------------------- #
def test_the_top_level_all_is_the_union_of_the_subpackage_alls():
    """The top level must export exactly what its subpackages export."""
    expected = {"__version__"}
    for package in SUBPACKAGES:
        module = __import__(f"qtr.{package}", fromlist=["__all__"])
        expected |= set(module.__all__)
    assert set(qtr.__all__) == expected, (
        f"qtr.__all__ differs from the union of the subpackages: "
        f"missing {sorted(expected - set(qtr.__all__))}, "
        f"unexpected {sorted(set(qtr.__all__) - expected)}"
    )


def test_every_name_in_the_top_level_all_is_importable():
    """Every declared name must be bound at runtime."""
    for name in qtr.__all__:
        assert hasattr(qtr, name), f"qtr.{name} is declared in __all__ but not bound"


def test_the_top_level_all_is_not_empty():
    """A one-name ``__all__`` is what H44 shipped: the star export was void."""
    assert len(qtr.__all__) > 1, (
        f"qtr.__all__ exports {len(qtr.__all__)} name(s); the star export is effectively empty"
    )


# --------------------------------------------------------------------------- #
# 4. The star import is not vacuous
# --------------------------------------------------------------------------- #
def _star_import_namespace() -> dict:
    """Execute ``from qtr import *`` and return the resulting namespace."""
    namespace: dict = {}
    exec("from qtr import *", namespace)  # noqa: S102 - the statement under test
    return namespace


def test_the_star_import_exports_exactly_the_declared_api():
    """``from qtr import *`` must reach the declared API -- and only it.

    This is the check that replaces ``from qtr import *; print('ok')``.  The
    old check was satisfied by an import that exported nothing at all.
    """
    namespace = _star_import_namespace()
    exported = {name for name in namespace if not name.startswith("__")}
    declared = {name for name in qtr.__all__ if not name.startswith("__")}
    assert exported == declared, (
        f"the star import exports {sorted(exported - declared)} unexpectedly and "
        f"misses {sorted(declared - exported)}"
    )


def test_the_star_import_reaches_every_subpackage():
    """Each subpackage must be reachable through the star import.

    Before the fix, ``qtr.backtest``, ``qtr.data``, ``qtr.tracking`` and
    ``qtr.utils`` contributed nothing to the top-level namespace, so
    ``from qtr import *`` could never have exported ``run_backtest``,
    ``get_data_fetcher``, ``create_experiment`` or ``get_config``.
    """
    namespace = _star_import_namespace()
    representatives = {
        "qtr.backtest": "run_backtest",
        "qtr.data": "get_data_fetcher",
        "qtr.strategies": "momentum_signals",
        "qtr.tracking": "create_experiment",
        "qtr.utils": "get_config",
        "qtr.validation": "sharpe_ratio",
    }
    for package, representative in representatives.items():
        assert representative in namespace, (
            f"the star import does not reach {package} (via {representative})"
        )


# --------------------------------------------------------------------------- #
# 5. The declared version is the packaged version
# --------------------------------------------------------------------------- #
def test_the_version_matches_the_packaged_version():
    """``qtr.__version__`` must equal the version the distribution ships."""
    text = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml does not declare a static version"
    assert qtr.__version__ == match.group(1), (
        f"qtr.__version__ is {qtr.__version__!r} but the distribution ships {match.group(1)!r}"
    )
