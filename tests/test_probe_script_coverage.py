"""Invariant: every ``scripts/probe_*.py`` ships with a ``tests/test_probe_*.py``.

Probes are the durable, repeatedly-added evidence harnesses that verify
free-data availability claims (FRED, Binance, SEC XBRL, commodity term
structure, S&P 500 membership price leg).  A probe landed without a test can
silently break -- and a broken probe silently re-creates the "data-blocked
without probing the named source" defect the register keeps correcting.  This
test fails if a new ``probe_*.py`` appears without a matching test, catching the
gap at commit time instead of a cycle later.

Offline and read-only: it only lists files under ``scripts/`` and ``tests/``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"


def _probe_script_names() -> list[str]:
    return sorted(path.name for path in SCRIPTS_DIR.glob("probe_*.py"))


def test_probe_scripts_are_discovered():
    # Guard against a vacuous pass if the glob/path ever breaks.
    assert _probe_script_names(), "no scripts/probe_*.py found"


def test_every_probe_script_has_a_matching_test():
    missing = [name for name in _probe_script_names() if not (TESTS_DIR / f"test_{name}").is_file()]
    assert not missing, "probe scripts without tests/test_<name>.py: " + ", ".join(missing)
