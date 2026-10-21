"""The runners' import surface must be declared and importable.

H45 pinned the package's public API. This extends the executable contract to
the runners' import surface -- the other public entry points. A runner broken
by an import-level change (a renamed symbol, a moved module, a subpackage that
no longer re-exports what a runner expects) currently fails at *run* time, not
at *test* time.

This module pins:
1. every ``run_*.py`` in the repository is importable (module-level code only;
   no ``main()`` execution);
2. imports are classified (library / stdlib / third-party / local) and each
   class is pinned:
   - library imports (``qtr.*``) must resolve to names the package actually
     exports (``qtr.__all__`` / the relevant subpackage's ``__all__``), so a
     runner cannot reach a symbol through a path the public API does not
     declare;
   - third-party imports must be declared dependencies in ``pyproject.toml``
     (``[project.dependencies]`` or an optional extra under
     ``[project.optional-dependencies]``), so a runner cannot depend on an
     undeclared package;
   - local imports are only other ``run_*.py`` modules in the repository;
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pathlib
import sys
from collections import defaultdict

import pytest
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Put repo root first to avoid picking up .experiments copies
for p in [str(ROOT), str(ROOT / "src")]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "src"))

import qtr


def _find_repo_runners():
    runners = []
    for p in ROOT.iterdir():  # only top level
        if p.is_file() and p.name.startswith("run_") and p.suffix == ".py":
            runners.append(p)
    return sorted(set(runners))


ALL_RUNNERS = _find_repo_runners()


def _read_pyproject_deps():
    """Return the normalized set of declared third-party dependency names.

    Reads ``[project.dependencies]`` and every extra under
    ``[project.optional-dependencies]`` from ``pyproject.toml`` via ``tomllib``
    (not a loose regex over the whole file).  Names are lowercased with
    hyphens and dots mapped to underscores, matching how Python normalizes
    import top-level packages.
    """
    try:
        with open(ROOT / "pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
    except Exception:
        return set()
    deps: set[str] = set()
    project = data.get("project", {})
    for dep in project.get("dependencies", []):
        name = dep.split(" ")[0].split(">")[0].split("<")[0].split("=")[0].split("[")[0]
        deps.add(name.strip().lower().replace("-", "_").replace(".", "_"))
    for extra in project.get("optional-dependencies", {}).values():
        for dep in extra:
            name = dep.split(" ")[0].split(">")[0].split("<")[0].split("=")[0].split("[")[0]
            deps.add(name.strip().lower().replace("-", "_").replace(".", "_"))
    return deps


PYPROJECT_DEPS = _read_pyproject_deps()
STDLIB_MODULES = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()


def _get_subpackage_all():
    """Build a mapping of what names are exported from qtr and subpackages."""
    allowed = set()
    # top level
    if hasattr(qtr, "__all__"):
        allowed.update(getattr(qtr, "__all__"))
    # subpackages
    for pkg_name in ["backtest", "data", "strategies", "tracking", "utils", "validation"]:
        try:
            mod = getattr(qtr, pkg_name)
            if hasattr(mod, "__all__"):
                allowed.update(getattr(mod, "__all__"))
        except Exception:
            pass
    return allowed


ALLOWED_QTR_EXPORTS = _get_subpackage_all()


@pytest.mark.parametrize("runner_path", ALL_RUNNERS)
def test_runner_is_importable(runner_path):
    """Every runner must be importable without executing main()."""
    mod_name = runner_path.stem
    modules_to_remove = []
    for k in list(sys.modules.keys()):
        if k == mod_name or k.startswith(mod_name + "."):
            modules_to_remove.append(k)
    for k in modules_to_remove:
        sys.modules.pop(k)

    try:
        spec = importlib.util.spec_from_file_location(mod_name, runner_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {runner_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
    except SystemExit:
        raise
    except Exception as e:
        raise AssertionError(f"Runner {runner_path} is not importable: {e}") from e


def test_all_runners_inventory_exists():
    assert len(ALL_RUNNERS) >= 1


@pytest.mark.parametrize("runner_path", ALL_RUNNERS)
def test_runner_imports_are_classified_and_pinned(runner_path):
    """Classify each import and pin each class."""
    tree = ast.parse(runner_path.read_text())
    runner_stems = {p.stem for p in ALL_RUNNERS}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                _check_import(mod, runner_path, runner_stems)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:  # relative
                continue  # be conservative
            mod = node.module
            if mod is None:
                continue
            _check_import(mod, runner_path, runner_stems, node)


def _check_import(mod_name, runner_path, runner_stems, from_node=None):
    if not mod_name:
        return
    top = mod_name.split(".")[0]

    # library import: qtr or qtr.*
    if top == "qtr":
        # Verify each imported name is declared in the relevant __all__.
        if from_node is not None:
            for alias in from_node.names:
                if alias.name == "*":
                    continue  # star imports from qtr are fine; qtr declares __all__
                name = alias.name
                parts = mod_name.split(".")
                if len(parts) == 1:
                    # ``from qtr import X`` -> X must be in qtr.__all__
                    if name not in set(qtr.__all__):
                        raise AssertionError(
                            f"{runner_path.name}: from qtr import {name!r} is not declared "
                            f"in qtr.__all__"
                        )
                else:
                    # ``from qtr.<subpackage> import X`` -> X must be in that
                    # subpackage's __all__
                    subpkg = parts[1]
                    try:
                        mod = getattr(qtr, subpkg)
                    except AttributeError as e:
                        raise AssertionError(
                            f"{runner_path.name}: qtr.{subpkg} is not a subpackage of qtr"
                        ) from e
                    declared = set(getattr(mod, "__all__", []))
                    if name not in declared:
                        raise AssertionError(
                            f"{runner_path.name}: from qtr.{subpkg} import {name!r} is not "
                            f"declared in qtr.{subpkg}.__all__"
                        )
        # The module itself must be importable (covers bare ``import qtr`` and
        # ``import qtr.subpackage``).
        try:
            __import__(mod_name)
        except Exception as e:
            raise AssertionError(
                f"{runner_path.name}: cannot import library module {mod_name}"
            ) from e
        return

    # local import: another run_*.py module in the repository
    if top in runner_stems or mod_name in runner_stems:
        return

    # stdlib
    if top in STDLIB_MODULES or mod_name in STDLIB_MODULES:
        return

    # third-party: must be a declared dependency in pyproject.toml
    norm = top.lower().replace("-", "_")
    if norm in PYPROJECT_DEPS:
        return
    raise AssertionError(
        f"{runner_path.name}: third-party import '{mod_name}' is not declared in pyproject.toml"
    )
