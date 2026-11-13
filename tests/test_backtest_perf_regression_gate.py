"""Contract tests for ``scripts/backtest_perf_regression_gate.py``.

The performance regression gate is the CI/CD hardening item from
``STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`` §6. It fails when a 100-symbol x
252-bar equity backtest exceeds 5.0s, so an accidental O(n^2) engine path is
caught before merge.

These tests pin the gate's contract without depending on wall-clock speed of
the host: the measured elapsed time is injected through a fake ``perf_counter``
and the engine call is stubbed, so the pass/fail branch logic is deterministic
on any machine. ``generate_data`` is exercised for real (small universe) so the
shape/finiteness contract is covered.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "backtest_perf_regression_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("backtest_perf_regression_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate():
    return _load_gate()


class _FakeTime:
    """Return scripted ``perf_counter`` values in call order."""

    def __init__(self, values: list[float]):
        self._values = iter(values)

    def perf_counter(self) -> float:
        return next(self._values)


def _stub_run(monkeypatch, gate):
    monkeypatch.setattr(
        gate,
        "run_backtest",
        lambda **kwargs: SimpleNamespace(metrics={"num_trades": 10}),
    )


def test_gate_script_exists():
    assert GATE.is_file(), "scripts/backtest_perf_regression_gate.py is missing"


def test_gate_constants_are_pinned(gate):
    assert gate.N_SYMBOLS == 100
    assert gate.N_BARS == 252
    assert gate.MAX_ELAPSED_SECONDS == 5.0


def test_generate_data_shapes_and_finiteness(gate):
    prices, volumes = gate.generate_data(5, 20)
    assert prices.shape == (20, 5)
    assert volumes.shape == (20, 5)
    assert prices.columns.equals(volumes.columns)
    assert np.isfinite(prices.to_numpy()).all()
    assert (volumes.to_numpy() >= 0).all()


def test_main_passes_when_backtest_is_fast(gate, monkeypatch, capsys):
    _stub_run(monkeypatch, gate)
    monkeypatch.setattr(gate, "time", _FakeTime([100.0, 101.0]))
    assert gate.main() == 0
    assert "PERF GATE PASSED" in capsys.readouterr().out


def test_main_fails_when_backtest_exceeds_threshold(gate, monkeypatch, capsys):
    _stub_run(monkeypatch, gate)
    monkeypatch.setattr(gate, "time", _FakeTime([100.0, 106.0]))
    assert gate.main() == 1
    assert "PERF GATE FAILED" in capsys.readouterr().out
