"""Guard the package metadata's single source of truth.

``src/qtr.egg-info/`` is a **setuptools build artifact**, not a source file.
It is rewritten by every build and every install, so the copy that was
committed to the repository could only ever be a stale snapshot of the tree.
It was: the tracked ``SOURCES.txt`` predated three test modules (the ones
added between H33 and H49) and listed ``61`` of the ``64`` entries the
current tree produces.

Two earlier sessions tried to close that by *regenerating* the manifest and
committing the result. The measurements below show why that route is not a
solution: the bytes of the generated metadata are a function of **which
setuptools built them**, so "regenerate and commit" cannot be reproducible.

    Metadata-Version: 2.4      <- built under pip's build isolation
    Requires-Dist: numpy>=1.24.0
    Requires-Dist: yfinance>=0.2.0; extra == "data"

    Metadata-Version: 2.1      <- built with the local setuptools 68.1.2
    Requires-Dist: numpy >=1.24.0
    Requires-Dist: yfinance >=0.2.0 ; extra == 'data'

Both builds describe the *same* package; only the serialisation differs
(the requirement markers are reformatted and the entries are reordered -- they
are **not** dropped). Committing either one freezes an accident of the build
environment into the repository.

The durable answer is the one the handoffs prescribe: the generated manifest
is **untracked** and **ignored**, and ``pyproject.toml`` is the only declared
source of the package's metadata. The invariants pinned here make that
structural rather than advisory, so the "stale tracked manifest" defect
class cannot come back:

1. The generated manifest is **ignored** (and git agrees).
2. The generated manifest is **not tracked**.
3. No module of the package **depends** on it, so the package cannot silently
   require a build artifact to exist.
4. ``pyproject.toml`` is the **only** declared source of package metadata --
   no second copy of the version, the requirements or the package list.
5. The metadata the build produces -- generated manifest and installed
   distribution alike -- **agrees** with ``pyproject.toml``.
6. A generated manifest that *does* exist is not **stale** against the package's own modules.

The git-backed checks are skipped when the checkout carries no git metadata
(a source tarball), so the suite still runs from a bare clone.
"""

from __future__ import annotations

import importlib.metadata
import pathlib
import subprocess
from collections.abc import Iterable

import pytest

try:  # tomllib is stdlib from 3.11; the package declares support for 3.10
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    tomllib = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_ROOT = ROOT / "src" / "qtr"
MANIFEST_DIR = ROOT / "src" / "qtr.egg-info"

#: The suffix setuptools gives its generated metadata directory.
MANIFEST_DIR_SUFFIX = ".egg-info"

#: Strings that would mean a module reads the generated manifest.
MANIFEST_REFERENCES = ("egg-info", "egg_info", "SOURCES.txt", "PKG-INFO", "top_level.txt")

#: git's exit code when the command runs outside a repository.
GIT_NOT_A_REPOSITORY = 128


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
class _GitMissing(Exception):
    """Raised when the git executable is not available at all."""


def _git(*args: str) -> tuple[int, str]:
    """Run a git command in the repository root and return ``(code, stdout)``.

    Only a missing *executable* is an error here: a command that ran and
    failed (``check-ignore`` exiting 1 because nothing matched) carries a
    verdict the caller must act on, so it must not be confused with "this
    checkout has no git".
    """
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise _GitMissing from exc
    return completed.returncode, completed.stdout


def _tracked_files() -> list[str] | None:
    """Return the repository's tracked paths, or ``None`` without a git repo."""
    try:
        code, out = _git("ls-files", "-z")
    except _GitMissing:
        return None
    if code == GIT_NOT_A_REPOSITORY:
        return None
    assert code == 0, f"git ls-files failed with exit code {code}"
    return [path for path in out.split("\0") if path]


def _manifest_paths(paths: Iterable[str]) -> list[str]:
    """Return the paths that live inside a generated metadata directory."""
    return [
        path
        for path in paths
        if any(part.endswith(MANIFEST_DIR_SUFFIX) for part in pathlib.PurePosixPath(path).parts)
    ]


def _tracked_modules(tracked: Iterable[str]) -> list[str]:
    """Return the tracked modules **of the package**.

    Only the package's own modules matter here: they are what the built
    distribution ships. A test module is not part of the distribution, so
    its absence from the manifest is not staleness -- it would only mean the
    developer has not rebuilt since adding a test, which is a local state
    the next build resolves and not a property of the repository.
    """
    return sorted(path for path in tracked if path.endswith(".py") and path.startswith("src/qtr/"))


def _manifest_sources() -> pathlib.Path | None:
    """Return the generated ``SOURCES.txt``, if a build has produced one."""
    path = MANIFEST_DIR / "SOURCES.txt"
    return path if path.exists() else None


def _normalize_requirement(text: str) -> str:
    """Normalise a requirement string for comparison across serialisations.

    setuptools 68 writes ``yfinance >=0.2.0 ; extra == 'data'`` where newer
    versions write ``yfinance>=0.2.0; extra == "data"``. The two describe
    the same requirement, so the comparison must not depend on the
    serialisation.
    """
    return text.replace("'", '"').replace(" ", "")


def _declared_requirements() -> set[str]:
    """Return the requirements ``pyproject.toml`` declares, normalised."""
    project = _pyproject_project()
    declared = {_normalize_requirement(req) for req in project["dependencies"]}
    for extra, requirements in project.get("optional-dependencies", {}).items():
        for requirement in requirements:
            base, _, marker = requirement.partition(";")
            extra_marker = f'extra=="{extra}"'
            if marker:
                declared.add(f"{_normalize_requirement(base)};{_normalize_requirement(marker)}")
            else:
                declared.add(f"{_normalize_requirement(base)};{extra_marker}")
    return declared


def _pyproject_project() -> dict:
    """Return the ``[project]`` table of ``pyproject.toml``."""
    if tomllib is None:  # pragma: no cover - Python 3.10
        pytest.skip("tomllib is unavailable (Python < 3.11); cannot parse pyproject.toml")
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def _parse_metadata_fields(text: str) -> dict[str, list[str]]:
    """Parse an RFC-822 style metadata file into its fields."""
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.strip():
            break  # the body follows the headers
        if line[:1] in (" ", "\t"):
            continue  # a folded continuation
        key, _, value = line.partition(":")
        fields.setdefault(key.strip(), []).append(value.strip())
    return fields


# --------------------------------------------------------------------------- #
# 1. the generated manifest is ignored
# --------------------------------------------------------------------------- #
def test_gitignore_declares_the_generated_metadata_rule():
    """The ignore rule must exist in the committed ``.gitignore``.

    A rule that is only present in a developer's global git config would
    leave the manifest tracked for everybody else.
    """
    rules = [line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()]
    assert f"*{MANIFEST_DIR_SUFFIX}/" in rules or f"*{MANIFEST_DIR_SUFFIX}" in rules, (
        f".gitignore must ignore the generated *{MANIFEST_DIR_SUFFIX}/ metadata"
    )


def test_git_ignores_the_generated_metadata_directory():
    """git itself must agree that the generated metadata is ignored.

    The textual rule and git's own matcher can disagree (``*.egg-info/``
    matches directories only, and git refuses to report a *tracked* path as
    ignored), so the check is made with git rather than by reading the file
    back.
    """
    try:
        code, out = _git("check-ignore", "-v", f"src/qtr{MANIFEST_DIR_SUFFIX}/SOURCES.txt")
    except _GitMissing:
        pytest.skip("git is not available in this environment")
    if code == GIT_NOT_A_REPOSITORY:
        pytest.skip("this checkout carries no git repository")
    assert code == 0, (
        "git must ignore the generated metadata directory "
        f"(check-ignore exited {code}): {out.strip()!r}"
    )


# --------------------------------------------------------------------------- #
# 2. the generated manifest is not tracked
# --------------------------------------------------------------------------- #
def test_generated_metadata_is_not_tracked():
    """No tracked path may live inside a generated metadata directory."""
    tracked = _tracked_files()
    if tracked is None:
        pytest.skip("this checkout carries no git repository")
    assert _manifest_paths(tracked) == [], (
        "the setuptools-generated metadata is a build artifact and must not be tracked; "
        f"tracked: {_manifest_paths(tracked)}"
    )


def test_pyproject_is_the_only_declared_source_of_package_metadata():
    """There must be exactly one place that declares the package's metadata.

    A second copy of the version, the requirements or the package list is a
    second source of truth: it drifts, and nothing in the suite notices.
    """
    tracked = _tracked_files()
    if tracked is None:
        pytest.skip("this checkout carries no git repository")
    forbidden = {"setup.py", "setup.cfg", "PKG-INFO", "requires.txt", "top_level.txt"}
    offenders = [path for path in tracked if pathlib.PurePosixPath(path).name in forbidden]
    assert offenders == [], f"package metadata must be declared only in pyproject.toml: {offenders}"


# --------------------------------------------------------------------------- #
# 3. the package does not depend on the generated manifest
# --------------------------------------------------------------------------- #
def test_no_package_module_references_the_generated_manifest():
    """No module of the package may read the generated metadata.

    The package is importable from a bare clone with no install step (the
    suite sets ``pythonpath = ["src"]``), so a module that read
    ``src/qtr.egg-info/...`` would work in a developer's checkout and fail in
    a fresh clone -- the exact failure the generated manifest invites.
    """
    offenders = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in MANIFEST_REFERENCES:
            if needle in text:
                offenders.append(f"{path.relative_to(ROOT)}: {needle}")
    assert offenders == [], f"the package must not depend on the generated manifest: {offenders}"


# --------------------------------------------------------------------------- #
# 4. the build agrees with the declared source of truth
# --------------------------------------------------------------------------- #
def _assert_agrees_with_pyproject(
    version: str, requires_python: str, requires: Iterable[str]
) -> None:
    project = _pyproject_project()
    assert version == project["version"], (
        f"the built metadata declares version {version!r}, pyproject declares "
        f"{project['version']!r}"
    )
    assert requires_python == project["requires-python"], (
        f"the built metadata declares Requires-Python {requires_python!r}, pyproject declares "
        f"{project['requires-python']!r}"
    )
    declared = _declared_requirements()
    built = {_normalize_requirement(req) for req in requires}
    missing = sorted(declared - built)
    assert missing == [], f"the build does not reproduce the declared requirements: {missing}"


def test_generated_manifest_metadata_agrees_with_pyproject():
    """The generated ``PKG-INFO`` must reproduce what ``pyproject.toml`` declares.

    The generated manifest is no longer tracked, but a build still writes it
    into the source tree -- and ``importlib.metadata`` resolves the
    distribution to *that* directory whenever the source tree is on the
    import path. A manifest that disagrees with the declaration would then
    describe a different package than the one the repository declares.
    """
    pkg_info = MANIFEST_DIR / "PKG-INFO"
    if not pkg_info.exists():
        pytest.skip("no generated manifest in this working tree")
    fields = _parse_metadata_fields(pkg_info.read_text(encoding="utf-8"))
    _assert_agrees_with_pyproject(
        fields["Version"][0],
        fields["Requires-Python"][0],
        fields.get("Requires-Dist", []),
    )


def test_installed_distribution_metadata_agrees_with_pyproject():
    """The installed distribution's metadata must match ``pyproject.toml``.

    This is the check that a stale *installed* manifest cannot satisfy: the
    declared version, the python floor, the base requirements and every
    extra's requirements must be reproduced by the build that was installed.
    """
    try:
        metadata = importlib.metadata.metadata("qtr")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("qtr is not installed as a distribution in this environment")

    _assert_agrees_with_pyproject(
        metadata["Version"],
        metadata["Requires-Python"],
        metadata.get_all("Requires-Dist") or [],
    )


# --------------------------------------------------------------------------- #
# 5. a manifest that exists is not stale
# --------------------------------------------------------------------------- #
def test_generated_manifest_is_not_stale_against_the_package():
    """A generated ``SOURCES.txt`` must list the package's current modules.

    The manifest is no longer tracked, so it cannot go stale in the
    repository; it can still go stale in a working tree, where a build
    skipped a module of the package -- so the *installed* distribution
    describes a different package than the one on disk.

    Only the package's own modules are checked: a test module is not part
    of the built distribution, so its absence from the manifest says
    nothing about what would be installed.
    """
    manifest = _manifest_sources()
    if manifest is None:
        pytest.skip("no generated manifest in this working tree")
    tracked = _tracked_files()
    if tracked is None:
        pytest.skip("this checkout carries no git repository")

    listed = {line.strip() for line in manifest.read_text(encoding="utf-8").splitlines()}
    missing = [module for module in _tracked_modules(tracked) if module not in listed]
    assert missing == [], f"the generated manifest is stale; it does not list: {missing}"


# --------------------------------------------------------------------------- #
# 6. negative controls -- the contract must fail against the pre-fix state
# --------------------------------------------------------------------------- #
def test_control_the_detector_flags_the_pre_fix_state():
    """The tracked-file detector must reject the state that was committed."""
    pre_fix = [
        "src/qtr.egg-info/PKG-INFO",
        "src/qtr.egg-info/SOURCES.txt",
        "src/qtr.egg-info/requires.txt",
        "src/qtr.egg-info/top_level.txt",
    ]
    assert _manifest_paths(pre_fix) == pre_fix
    assert _manifest_paths(["src/qtr/validation/statistics.py"]) == []


def test_control_the_staleness_detector_flags_a_stale_manifest():
    """The staleness check must reject a manifest that omits a module."""
    tracked = ["src/qtr/validation/statistics.py", "src/qtr/backtest/engine.py"]
    listed = {"src/qtr/validation/statistics.py"}  # `src/qtr/backtest/engine.py` missing
    missing = [module for module in _tracked_modules(tracked) if module not in listed]
    assert missing == ["src/qtr/backtest/engine.py"]


def test_control_the_requirement_normalisation_sees_both_serialisations():
    """The 2.1 and the 2.4 serialisations must compare equal.

    The two formats are the reason "regenerate and commit" is not a
    reproducible fix; the comparison the contract relies on must be immune
    to the difference between them.
    """
    old_style = "yfinance >=0.2.0 ; extra == 'data'"
    new_style = 'yfinance>=0.2.0; extra == "data"'
    assert _normalize_requirement(old_style) == _normalize_requirement(new_style)
    assert 'yfinance>=0.2.0;extra=="data"' in _declared_requirements()
