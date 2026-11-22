"""Tests for ``scripts/verify_hypothesis_inventory.py``.

The script is the executable ratchet against stale research-inventory claims: it must
(a) read the documented ``## H<ID>`` headings and the recorded AGENTS.md marker, (b)
report agreement or the precise mismatch, (c) fail closed on a missing/malformed
marker or a missing input file, and (d) accept the live repository so the invariant is
continuously proven.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_hypothesis_inventory.py"

SPEC_SYNCED = """\
# Hypothesis Spec

## H4: Something

## H12: Another

## H197 execution result (Cycle 253): EXECUTED -- REJECT (1/8)

Body text mentions H999 but that is not a heading.
"""

AGENTS_SYNCED = """\
# AGENTS.md

<!-- inventory-high-water-mark: H197 -->
Some prose that says H1-H150 for historical context.
"""


def _load_script():
    spec = importlib.util.spec_from_file_location("verify_hypothesis_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    # Register before exec: ``@dataclass`` resolves string annotations (PEP 563 via
    # ``from __future__ import annotations``) through ``sys.modules[cls.__module__]``.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_inputs(tmp_path: Path, spec_text: str, agents_text: str) -> Path:
    (tmp_path / "HYPOTHESIS_SPEC.md").write_text(spec_text)
    (tmp_path / "AGENTS.md").write_text(agents_text)
    return tmp_path


def test_documented_h_ids_reads_only_section_headings():
    module = _load_script()
    assert module.documented_h_ids(SPEC_SYNCED) == {4, 12, 197}


def test_max_documented_h_id():
    module = _load_script()
    assert module.max_documented_h_id(SPEC_SYNCED) == 197
    assert module.max_documented_h_id("no headings here") is None


def test_recorded_high_water_mark_reads_marker():
    module = _load_script()
    assert module.recorded_high_water_mark(AGENTS_SYNCED) == 197
    assert module.recorded_high_water_mark("no marker") is None


def test_recorded_high_water_mark_takes_max_of_duplicates():
    module = _load_script()
    doubled = "<!-- inventory-high-water-mark: H150 -->\n<!-- inventory-high-water-mark: H197 -->\n"
    assert module.recorded_high_water_mark(doubled) == 197


def test_reconcile_match_and_mismatch():
    module = _load_script()
    assert module.reconcile(SPEC_SYNCED, AGENTS_SYNCED).match
    stale = AGENTS_SYNCED.replace("H197", "H196")
    result = module.reconcile(SPEC_SYNCED, stale)
    assert not result.match
    assert result.max_documented == 197
    assert result.recorded == 196


def test_reconcile_reports_counts():
    module = _load_script()
    result = module.reconcile(SPEC_SYNCED, AGENTS_SYNCED)
    assert result.documented_count == 3


def test_format_report_flags_missing_marker():
    module = _load_script()
    result = module.reconcile(SPEC_SYNCED, "no marker here")
    report = "\n".join(module.format_report(result))
    assert "OUT OF SYNC" in report
    assert "no '<!-- inventory-high-water-mark" in report


def test_format_report_in_sync_message():
    module = _load_script()
    result = module.reconcile(SPEC_SYNCED, AGENTS_SYNCED)
    report = "\n".join(module.format_report(result))
    assert "IN SYNC" in report
    assert "H197" in report


def test_verify_returns_zero_when_in_sync(tmp_path):
    module = _load_script()
    _write_inputs(tmp_path, SPEC_SYNCED, AGENTS_SYNCED)
    exit_code, report = module.verify(tmp_path)
    assert exit_code == 0
    assert "IN SYNC" in "\n".join(report)


def test_verify_returns_one_on_stale_marker(tmp_path):
    module = _load_script()
    _write_inputs(tmp_path, SPEC_SYNCED, AGENTS_SYNCED.replace("H197", "H196"))
    exit_code, report = module.verify(tmp_path)
    assert exit_code == 1
    assert "OUT OF SYNC" in "\n".join(report)


def test_verify_returns_two_when_input_missing(tmp_path):
    module = _load_script()
    (tmp_path / "AGENTS.md").write_text(AGENTS_SYNCED)
    exit_code, report = module.verify(tmp_path)
    assert exit_code == 2
    assert any(line.startswith("MISSING:") for line in report)


def test_main_prints_report(tmp_path, capsys):
    module = _load_script()
    _write_inputs(tmp_path, SPEC_SYNCED, AGENTS_SYNCED)
    assert module.main(["--repo-root", str(tmp_path)]) == 0
    assert "IN SYNC" in capsys.readouterr().out


def test_live_repository_high_water_mark_matches_documented_maximum(capsys):
    module = _load_script()
    assert module.main(["--repo-root", str(ROOT)]) == 0
    assert "IN SYNC" in capsys.readouterr().out
