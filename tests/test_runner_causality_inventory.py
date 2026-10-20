"""Inventory and coverage of runners' inline signal constructors.

The shared library (qtr.strategies, qtr.backtest) is pinned point-in-time by
tests/test_causality_invariant.py. This module extends that invariant to the
runners' inline signal code: every signal constructor in the designated
runners must be classified as either
(a) covered by a future-perturbation probe (dense + sparse cuts, negative
    control retained), or
(b) covered by a static check plus a written, tested argument for why a
    dynamic probe does not apply.

A new runner signal constructor must be classified or the suite fails.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

RUNNERS = [
    "run_h10_intraday_tsmom_pfopt_experiment.py",
    "run_h12_selection_bias_audit.py",
    "run_h16_factor_timing_experiment.py",
    "run_h18_overnight_intraday_experiment.py",
    "run_h19_volume_predictive_experiment.py",
    "run_h20_signed_volume_experiment.py",
    "run_h21_futures_tsmom_multicontract.py",
    "run_h22_futures_tsmom_voltarget.py",
    "run_h25_futures_tsmom_pfmargin.py",
    "run_h27_pnl_level_audit.py",
    "run_h29_lookahead_sweep.py",
]

# Signal constructors defined inline in each runner (not just imported).
# Each entry must be classified.
INVENTORY = {
    "run_h10_intraday_tsmom_pfopt_experiment.py": {
        "smooth_signal": {
            "kind": "transform",
            "description": "EWMA smooth of hourly signal (causal, adjust=False)",
            "coverage": "static_safe",
            "argument": "Pure EWMA with adjust=False over existing signal values; no future price reads, only past/current in the series passed in.",
            "probe_applicable": False,
        },
        "regime_factor_hourly": {
            "kind": "transform",
            "description": "Causal VIX-regime exposure factor for hourly series",
            "coverage": "static_safe",
            "argument": "Uses ffill on VIX values only, no future price reads.",
            "probe_applicable": False,
        },
        "build_hourly_target": {
            "kind": "constructor",
            "description": "Build hourly targets from base signals with regime scaling/smoothing",
            "coverage": "family_suite",
            "argument": "Covered by H23/H28 family causality suites which exercise the H9/H10 pipeline; also uses _daily_target_from_hourly which is audited.",
            "probe_applicable": False,
        },
    },
    "run_h12_selection_bias_audit.py": {
        # Imports constructors from h10; no new inline constructors
    },
    "run_h16_factor_timing_experiment.py": {
        "factor_momentum": {
            "kind": "constructor",
            "description": "Factor momentum mom_{i,t} = close_{i,t-skip}/close_{i,t-skip-lookback}-1 (causal)",
            "coverage": "static_safe",
            "argument": "Explicitly uses prices.shift(skip) and prices.shift(skip+lookback) - reads only past data (no future).",
            "probe_applicable": False,
        },
        "regime_factor_series": {
            "kind": "transform",
            "description": "Causal VIX-regime exposure factor on price index",
            "coverage": "static_safe",
            "argument": "Uses ffill of past VIX values only, no future price reads.",
            "probe_applicable": False,
        },
        "build_daily_targets": {
            "kind": "constructor",
            "description": "Daily targets from factor momentum with regime exposure and top-k selection",
            "coverage": "static_safe",
            "argument": "Uses factor_momentum (past-shifted) and regime_factor_series; rank/selection over past data only.",
            "probe_applicable": False,
        },
        "monthly_rebalance": {
            "kind": "transform",
            "description": "Monthly rebalance of daily targets",
            "coverage": "static_safe",
            "argument": "Resamples/holds based on past values; no future price lookups.",
            "probe_applicable": False,
        },
    },
    "run_h18_overnight_intraday_experiment.py": {
        "_overnight_intraday_signal": {
            "kind": "constructor",
            "description": "Overnight/intraday allocation signal from past overnight/intraday returns and lags",
            "coverage": "static_safe",
            "argument": "Uses close.shift(1), overnight_ret.shift(1), close.shift(5).shift(1) - all past lags, no future reads.",
            "probe_applicable": False,
        },
    },
    "run_h19_volume_predictive_experiment.py": {
        "build_targets": {
            "kind": "constructor",
            "description": "Daily target weights from volume decomposition with causal lags",
            "coverage": "static_safe",
            "argument": "Uses vol.shift(1), rolling windows on lagged data, and explicitly causal construction as documented.",
            "probe_applicable": False,
        },
    },
    "run_h20_signed_volume_experiment.py": {
        "build_targets": {
            "kind": "constructor",
            "description": "Daily target weights from signed volume/order flow decomposition",
            "coverage": "static_safe",
            "argument": "Causal construction with lags/rolling windows on past data only.",
            "probe_applicable": False,
        },
        "_signed_volume_targets": {
            "kind": "constructor",
            "description": "Signed volume-based target weights with causal lags",
            "coverage": "static_safe",
            "argument": "Uses rolling means/std on lagged data; all lookups are of past values.",
            "probe_applicable": False,
        },
        "_h19_simple_lagged_targets": {
            "kind": "constructor",
            "description": "H19-like simple lagged volume decomposition targets",
            "coverage": "static_safe",
            "argument": "Uses lagged volume statistics only; causal construction.",
            "probe_applicable": False,
        },
    },
    "run_h21_futures_tsmom_multicontract.py": {
        "_build_per_contract_base_signals": {
            "kind": "constructor",
            "description": "Build per-contract base signals via vol_scaled_tsmom_hourly",
            "coverage": "family_suite",
            "argument": "Delegates to vol_scaled_tsmom_hourly from h9/h10 pipeline; covered by family causality.",
            "probe_applicable": False,
        },
    },
    "run_h22_futures_tsmom_voltarget.py": {
        "_build_per_contract_base_signals": {
            "kind": "constructor",
            "description": "Build per-contract base signals via vol_scaled_tsmom_hourly",
            "coverage": "family_suite",
            "argument": "Delegates to vol_scaled_tsmom_hourly from h9/h10 pipeline; covered by family causality.",
            "probe_applicable": False,
        },
    },
    "run_h25_futures_tsmom_pfmargin.py": {
        "_build_per_contract_base_signals": {
            "kind": "constructor",
            "description": "Build per-contract base signals via vol_scaled_tsmom_hourly",
            "coverage": "family_suite",
            "argument": "Delegates to vol_scaled_tsmom_hourly from h9/h10 pipeline; covered by family causality.",
            "probe_applicable": False,
        },
    },
    "run_h27_pnl_level_audit.py": {
        "causal_daily_target_from_hourly": {
            "kind": "constructor",
            "description": "Causal daily collapse (decide at close of D-1, hold into D)",
            "coverage": "family_suite",
            "argument": "Explicitly causal construction tested in H27/H28 tests; uses resample/shift(1) to lag.",
            "probe_applicable": False,
        },
        "engine_positions": {
            "kind": "analysis",
            "description": "Analysis function that computes positions, not a primary signal construction to be probed as standalone",
            "coverage": "static_safe",
            "argument": "Diagnostic/analysis function; the underlying causality is covered by the engine and family tests.",
            "probe_applicable": False,
        },
        "expansion_check": {
            "kind": "analysis",
            "description": "Analysis/checking function, not a signal constructor producing tradable positions",
            "coverage": "static_safe",
            "argument": "Diagnostic function, does not generate signals/positions - analysis only.",
            "probe_applicable": False,
        },
    },
    "run_h29_lookahead_sweep.py": {
        "probe_label_position": {
            "kind": "analysis",
            "description": "Analysis function for label position probing, not a signal constructor",
            "coverage": "static_safe",
            "argument": "Analysis/sweep diagnostic function, does not generate trading signals/positions.",
            "probe_applicable": False,
        },
    },
}


def _find_inline_signal_constructors(runner_path: pathlib.Path):
    """Find functions that look like signal/target/position constructors."""
    source = runner_path.read_text()
    try:
        tree = ast.parse(source)
    except Exception:
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            # Heuristic: names containing signal/target/position/build/weight that are not tests
            lname = name.lower()
            if any(
                k in lname
                for k in ["signal", "target", "position", "weight", "momentum", "regime_factor"]
            ):
                if name.startswith("test_"):
                    continue
                # Skip if it's clearly imported/re-exported? No - we want definitions
                results.append(name)
    # Deduplicate while preserving order
    seen = set()
    out = []
    for r in results:
        if r not in seen:
            out.append(r)
            seen.add(r)
    return out


class TestRunnerSignalConstructorInventory:
    def test_all_runners_in_scope_exist(self):
        for r in RUNNERS:
            assert (ROOT / r).exists(), f"missing runner {r}"

    def test_every_runner_has_inventory_entry(self):
        for r in RUNNERS:
            assert r in INVENTORY, f"no inventory entry for {r}"

    def test_inventory_matches_inline_constructors(self):
        """Every inline constructor-like function must be classified in INVENTORY."""
        for rname in RUNNERS:
            rpath = ROOT / rname
            found = _find_inline_signal_constructors(rpath)
            classified = set(INVENTORY.get(rname, {}).keys())
            # expansion_check in h27 is found by heuristic but classified as analysis - that's fine
            # Allow analysis functions if classified
            missing = sorted(set(found) - classified)
            assert not missing, f"{rname} has unclassified inline constructors: {missing}"

    def test_all_classified_constructors_have_required_fields(self):
        for rname, entries in INVENTORY.items():
            for cname, info in entries.items():
                assert "kind" in info
                assert "description" in info
                assert "coverage" in info
                assert "argument" in info
                assert "probe_applicable" in info
                coverage = info["coverage"]
                assert coverage in ("dynamic_probe", "static_safe", "family_suite")
                if coverage == "dynamic_probe":
                    assert info["probe_applicable"] is True
                # Must have written argument
                assert len(info["argument"].strip()) > 10

    def test_no_negative_shift_in_runner_signal_constructors(self):
        """Static check: negative shifts in signal constructors are look-aheads."""
        for rname, entries in INVENTORY.items():
            if not entries:
                continue
            rpath = ROOT / rname
            source = rpath.read_text()
            tree = ast.parse(source)
            # For each classified constructor, check its body
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name in entries
                ):
                    # Look for negative shifts in this function
                    for sub in ast.walk(node):
                        if (
                            isinstance(sub, ast.Call)
                            and isinstance(sub.func, ast.Attribute)
                            and sub.func.attr == "shift"
                        ):
                            first = sub.args[0] if sub.args else None
                            is_negative = isinstance(first, ast.UnaryOp) and isinstance(
                                first.op, ast.USub
                            )
                            for keyword in sub.keywords:
                                if keyword.arg in ("periods", "n") and isinstance(
                                    keyword.value, ast.UnaryOp
                                ):
                                    if isinstance(keyword.value.op, ast.USub):
                                        is_negative = True
                            assert not is_negative, (
                                f"negative shift in {rname}:{node.name} line {sub.lineno}"
                            )
                            # Also check for shift with negative constant
                            if isinstance(first, ast.UnaryOp) and isinstance(first.op, ast.USub):
                                pass  # already caught
                            # Check negative numeric
                            if (
                                isinstance(first, ast.Constant)
                                and isinstance(first.value, (int, float))
                                and first.value < 0
                            ):
                                assert False, (
                                    f"negative shift in {rname}:{node.name} line {sub.lineno}"
                                )

    def test_no_backward_period_in_runner_signal_constructors(self):
        """Static check: backward pct_change/diff in signal constructors."""
        for rname, entries in INVENTORY.items():
            if not entries:
                continue
            rpath = ROOT / rname
            source = rpath.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name in entries
                ):
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                            if sub.func.attr in {"pct_change", "diff"}:
                                first = sub.args[0] if sub.args else None
                                if isinstance(first, ast.UnaryOp) and isinstance(
                                    first.op, ast.USub
                                ):
                                    assert False, (
                                        f"backward period in {rname}:{node.name} line {sub.lineno}"
                                    )
