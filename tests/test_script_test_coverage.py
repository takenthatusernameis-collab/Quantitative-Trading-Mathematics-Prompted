"""Invariant: every ``scripts/*.py`` ships with a dedicated test module.

The repository already pins this discipline for two script families --
``probe_*.py`` (``tests/test_probe_script_coverage.py``) and ``run_nf_*.py``
(``tests/test_nf_runner_test_coverage.py``) -- because a script landed without a
test silently rots and re-creates the "verified without probing" defect class the
register keeps correcting.  The remaining infrastructure scripts
(``analyze_*``, ``backtest_perf_regression_gate``, ``fetch_*``, ``generate_*``,
``plan_*``, ``repair_*``, ``verify_*``) had no such guard: a new one could land
untested and nothing would fail until a later audit.

This module generalises the invariant to every ``scripts/*.py``: a new script
that lacks ``tests/test_<stem>.py`` fails here at commit time.  It is a strict
superset of the probe-specific guard and complements the runner-specific one.

A small number of scripts are *intentionally* test-less; they are pinned in
``INTENTIONALLY_TESTLESS`` with the concrete reason, and kept honest by
``test_intentionally_testless_entries_are_current`` so the allowlist cannot rot.

Offline and read-only: it only lists files under ``scripts/`` and ``tests/``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"

# ``scripts/<stem>.py`` stem -> why this script intentionally has no
# ``tests/test_<stem>.py`` module.  Keep entries current; see
# ``test_intentionally_testless_entries_are_current``.
INTENTIONALLY_TESTLESS: dict[str, str] = {}


def _script_stems() -> list[str]:
    """Every ``scripts/*.py`` filename stem, sorted."""
    return sorted(path.stem for path in SCRIPTS_DIR.glob("*.py"))


def _dedicated_test_path(stem: str) -> Path:
    """The conventional test module for a script stem (``tests/test_<stem>.py``)."""
    return TESTS_DIR / f"test_{stem}.py"


def test_scripts_are_discovered():
    # Guard against a vacuous pass if the glob/path ever breaks.
    assert _script_stems(), "no scripts/*.py found"


def test_every_unlisted_script_has_a_dedicated_test():
    missing = [
        stem
        for stem in _script_stems()
        if stem not in INTENTIONALLY_TESTLESS and not _dedicated_test_path(stem).is_file()
    ]
    assert not missing, (
        "scripts/*.py without tests/test_<stem>.py (add a dedicated test, or add a "
        "documented INTENTIONALLY_TESTLESS entry with a reason): " + ", ".join(missing)
    )


def test_intentionally_testless_entries_are_current():
    stems = set(_script_stems())
    stale = sorted(
        stem
        for stem in INTENTIONALLY_TESTLESS
        if stem not in stems or _dedicated_test_path(stem).is_file()
    )
    assert not stale, (
        "INTENTIONALLY_TESTLESS entries that are now stale (the script was deleted, "
        "or a dedicated test was added) — remove them so the allowlist stays honest: "
        + ", ".join(stale)
    )
