"""Invariant: every executed ``run_nf_*.py`` ships with a dedicated test module.

Cycle 275 (2026-11-23) shipped the H199 size-premium runner
(``run_nf_20261122_04_size_premium.py``) without a dedicated test module while
every sibling H187-H198 experiment had one; the gap was found a cycle later and
fixed reactively.  This test turns that discipline into an invariant: a new
``run_nf_*.py`` that lacks ``tests/test_<stem-without-run_>.py`` fails here at
commit time instead of in a later audit.

A small number of runners are *intentionally* test-less (superseded drafts).  They
are pinned in ``INTENTIONALLY_TESTLESS`` with the concrete reason.  Each entry is
kept honest by ``test_intentionally_testless_entries_are_current``: if the runner
is deleted, or a dedicated test is later added, the stale entry fails the suite and
must be removed, so the allowlist cannot silently rot.

Offline and read-only: it only lists files under the repo root and ``tests/``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

# ``run_*.py`` stem (filename without ``.py``) -> why this runner intentionally
# has no ``tests/test_<stem-without-run_>.py`` module.  Keep entries current; see
# ``test_intentionally_testless_entries_are_current``.
INTENTIONALLY_TESTLESS: dict[str, str] = {
    "run_nf_20261107_06_cs_retail_flow_draft": (
        "Superseded UNEXECUTED draft: no main(), no experiment tracking and no "
        "committed artifact (its own docstring declares it test-less). Must not be "
        "treated as NF-20261107-06 / H122 evidence."
    ),
    "run_nf_20261110_07_es_basis": (
        "UNEXECUTED draft: HYPOTHESIS = 'TBD' and no main(); never produced a committed artifact."
    ),
}


def _nf_runner_stems() -> list[str]:
    """Every ``run_nf_*.py`` at the repo root, as filename stems, sorted."""
    return sorted(path.stem for path in ROOT.glob("run_nf_*.py"))


def _dedicated_test_path(stem: str) -> Path:
    """The conventional test module for a runner stem.

    ``run_nf_<rest>`` -> ``tests/test_nf_<rest>.py`` (the ``run_`` prefix is
    dropped, matching every existing sibling module).
    """
    return TESTS_DIR / f"test_{stem[len('run_') :]}.py"


def test_nf_runners_are_discovered():
    # Guard against a vacuous pass if the glob/path ever breaks.
    assert _nf_runner_stems(), "no run_nf_*.py found at the repo root"


def test_every_unlisted_nf_runner_has_a_dedicated_test():
    missing = [
        stem
        for stem in _nf_runner_stems()
        if stem not in INTENTIONALLY_TESTLESS and not _dedicated_test_path(stem).is_file()
    ]
    assert not missing, (
        "run_nf_*.py without tests/test_<stem-without-run_>.py (add a dedicated "
        "test, or add a documented INTENTIONALLY_TESTLESS entry with a reason): "
        + ", ".join(missing)
    )


def test_intentionally_testless_entries_are_current():
    stems = set(_nf_runner_stems())
    stale = sorted(
        stem
        for stem in INTENTIONALLY_TESTLESS
        if stem not in stems or _dedicated_test_path(stem).is_file()
    )
    assert not stale, (
        "INTENTIONALLY_TESTLESS entries that are now stale (the runner was deleted, "
        "or a dedicated test was added) — remove them so the allowlist stays honest: "
        + ", ".join(stale)
    )
