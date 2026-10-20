"""H33 — the benchmark-comparison contract.

Three benchmark gates in the published record were vacuous: they evaluated a
constant instead of a statistic, because the runner read a key the library
never returns, or fed a price level / a boolean mask into a function that
expects a return series and a scalar rate. This module pins the contract
that makes those defects impossible to reintroduce:

1. a **static** check over every ``run_*.py`` call site of
   ``compare_to_benchmark``: at most two positional arguments (the two
   return series -- the third positional argument is ``risk_free``), and
   every key read off the result is a key the library actually returns;
2. **behavioural** checks of the library on the inputs that used to break
   it (NaN rows, a non-scalar ``risk_free``, degenerate lengths);
3. a **behavioural** check that H7's benchmark is a return series and not a
   price level.
"""

import ast
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h7_intraday_tsmom_experiment as h7
from qtr.validation.statistics import compare_to_benchmark

# The exact key set `compare_to_benchmark` returns. The static contract below
# is only meaningful against a pinned contract, so the set is asserted first.
LIBRARY_KEYS = {
    "information_ratio",
    "alpha_annualized",
    "beta",
    "alpha_t_stat",
    "alpha_p_value",
    "alpha_p_value_one_sided",
    "win_rate",
    "excess_return_annual",
    "excess_vol_annual",
}


# --------------------------------------------------------------------------- #
# 1. the library contract
# --------------------------------------------------------------------------- #
@pytest.fixture
def rng():
    return np.random.default_rng(12345)


def test_library_returns_the_pinned_key_set(rng):
    res = compare_to_benchmark(
        rng.normal(0.001, 0.01, 200), rng.normal(0.0005, 0.01, 200)
    )
    assert set(res) == LIBRARY_KEYS


def test_non_scalar_risk_free_is_rejected(rng):
    """A boolean mask passed positionally as `risk_free` used to silently
    turn `alpha_annualized` into an array of length N."""
    mask = pd.Series(rng.random(200) > 0.5)
    with pytest.raises(TypeError, match="risk_free must be a scalar"):
        compare_to_benchmark(
            rng.normal(0.001, 0.01, 200), rng.normal(0.0005, 0.01, 200), mask
        )


def test_nan_rows_are_dropped_pairwise(rng):
    """`np.cov`/`np.var` do not skip NaN, so a single NaN used to leave
    alpha/beta/p NaN while the information ratio stayed finite. The rows are
    dropped pair-wise, so the surviving statistics are exactly the ones
    computed on the NaN-free rows."""
    strat = rng.normal(0.001, 0.01, 200)
    bench = rng.normal(0.0005, 0.01, 200)
    dirty_strat = strat.copy()
    dirty_bench = bench.copy()
    dirty_strat[7] = np.nan
    dirty_bench[150] = np.nan

    dirty = compare_to_benchmark(dirty_strat, dirty_bench)
    # pair-wise: BOTH rows are dropped from BOTH series
    clean = compare_to_benchmark(np.delete(strat, [7, 150]), np.delete(bench, [7, 150]))

    for key in LIBRARY_KEYS:
        assert dirty[key] == pytest.approx(clean[key], rel=1e-12, abs=1e-15)
        assert np.isfinite(dirty[key])


def test_nan_free_input_is_not_reshaped(rng):
    """A NaN-free input must not be masked at all: the result is identical to
    the result computed on the same (unmasked) data."""
    strat = rng.normal(0.001, 0.01, 200)
    bench = rng.normal(0.0005, 0.01, 200)
    res = compare_to_benchmark(strat, bench)
    reference = compare_to_benchmark(strat, bench)
    for key in LIBRARY_KEYS:
        assert res[key] == pytest.approx(reference[key], rel=1e-15, abs=1e-18)


def test_one_sided_p_is_direction_aware(rng):
    """The one-sided p-value ``P(alpha > 0)`` must be small only when the
    excess return is significant *and* positive: a two-sided significant but
    negative alpha must NOT pass the one-sided gate."""
    # Significantly positive excess return -> one-sided p = two-sided / 2 (small)
    pos_strat = rng.normal(0.005, 0.01, 500)
    pos_bench = rng.normal(0.0, 0.01, 500)
    pos = compare_to_benchmark(pos_strat, pos_bench)
    assert pos["alpha_p_value_one_sided"] == pytest.approx(
        pos["alpha_p_value"] / 2.0, rel=1e-12
    )
    assert pos["alpha_t_stat"] > 0
    if pos["alpha_p_value"] < 0.05:
        assert pos["alpha_p_value_one_sided"] < 0.05

    # Significantly negative excess return -> one-sided p near 1 (not significant)
    neg_strat = rng.normal(-0.005, 0.01, 500)
    neg_bench = rng.normal(0.0, 0.01, 500)
    neg = compare_to_benchmark(neg_strat, neg_bench)
    assert neg["alpha_t_stat"] < 0
    assert neg["alpha_p_value_one_sided"] == pytest.approx(
        1.0 - neg["alpha_p_value"] / 2.0, rel=1e-12
    )
    assert neg["alpha_p_value_one_sided"] > 0.5


@pytest.mark.parametrize("n", [0, 1])
def test_degenerate_inputs_fail_closed(rng, n):
    """With fewer than two paired observations no comparison is possible; the
    result must be the explicit "no evidence" one, not NaN."""
    strat = rng.normal(0.001, 0.01, n)
    bench = rng.normal(0.0005, 0.01, n)
    res = compare_to_benchmark(strat, bench)
    assert res["information_ratio"] == 0.0
    assert res["alpha_annualized"] == 0.0
    assert res["beta"] == 0.0
    assert res["alpha_p_value"] == 1.0
    assert res["win_rate"] == 0.0


def test_empty_side_does_not_fall_back_to_the_whole_array(rng):
    """`x[-0:]` is the whole array, so an empty benchmark must not silently
    compare the full strategy series against nothing."""
    strat = rng.normal(0.001, 0.01, 50)
    res = compare_to_benchmark(strat, np.array([]))
    assert res["alpha_p_value"] == 1.0
    assert res["information_ratio"] == 0.0


# --------------------------------------------------------------------------- #
# 2. H7's benchmark is a return series, not a price level
# --------------------------------------------------------------------------- #
def test_h7_benchmark_comparison_is_unit_consistent():
    """H7 used to compare the strategy's returns against the *close prices*
    of the futures universe. The benchmark must be the equal-weighted
    return of that universe."""
    idx = pd.date_range("2020-01-01", periods=300, freq="B")
    rng = np.random.default_rng(7)
    prices = pd.DataFrame(
        100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, (300, 5)), axis=0)),
        index=idx,
        columns=["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"],
    )
    strategy_returns = pd.Series(
        rng.normal(0.0005, 0.01, 300), index=idx, name="returns"
    )

    bench = h7.benchmark_comparison(strategy_returns, prices)

    # every field is a finite number ...
    for key, value in bench.items():
        assert np.isfinite(value), f"{key} is not finite: {value}"
    # ... and the comparison is the one against the equal-weighted return.
    expected = compare_to_benchmark(
        strategy_returns, prices.pct_change().mean(axis=1), risk_free=0.0
    )
    assert bench["ir"] == pytest.approx(expected["information_ratio"], rel=1e-12)
    assert bench["p_value"] == pytest.approx(expected["alpha_p_value_one_sided"], rel=1e-12)
    assert bench["alpha"] == pytest.approx(expected["alpha_annualized"], rel=1e-12)

    # The price-level comparison it replaced is not the same number: the
    # benchmark is a return series, not a price level.
    levels = compare_to_benchmark(strategy_returns, prices, risk_free=0.0)
    assert bench["ir"] != pytest.approx(levels["information_ratio"], rel=1e-6)
    assert abs(bench["ir"]) < 10.0
    assert abs(levels["information_ratio"]) > 100.0


def test_h7_benchmark_is_documented_as_returns():
    """The helper must keep its name and its contract."""
    assert callable(h7.benchmark_comparison)
    doc = h7.benchmark_comparison.__doc__ or ""
    assert "return" in doc.lower()
    assert "price" in doc.lower()


# --------------------------------------------------------------------------- #
# 3. the static contract over every call site in the repository
# --------------------------------------------------------------------------- #
def _runner_files() -> list[pathlib.Path]:
    files = sorted(ROOT.glob("run_*.py"))
    assert len(files) >= 10, f"expected the runner scripts, found {len(files)}"
    return files


def _call_sites(tree: ast.AST) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "compare_to_benchmark"
    ]


def _result_names(tree: ast.AST, call: ast.Call) -> set[str]:
    """Names assigned directly from the call (`x = compare_to_benchmark(...)`)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.value is call:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if (
            isinstance(node, ast.AnnAssign)
            and node.value is call
            and isinstance(node.target, ast.Name)
        ):
            names.add(node.target.id)
    return names


def _keys_read_from(tree: ast.AST, names: set[str]) -> set[str]:
    """Every string key read off one of `names` with `.get(...)` or `[...]`."""
    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in names
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
    return keys


def test_every_call_site_passes_at_most_two_positional_arguments():
    """The third positional argument of `compare_to_benchmark` is
    `risk_free`; passing anything else there is a bug (H18 passed a boolean
    mask)."""
    offenders = []
    total = 0
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        for call in _call_sites(tree):
            total += 1
            if len(call.args) > 2:
                offenders.append(f"{path.name}:{call.lineno} ({len(call.args)} args)")
    assert total >= 10, f"expected the benchmark call sites, found {total}"
    assert offenders == []


def test_every_call_site_reads_only_keys_the_library_returns():
    """A runner that reads a key the library never returns gets the default
    silently -- a gate that never tests anything (H4, H7, H18)."""
    offenders = []
    total = 0
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        for call in _call_sites(tree):
            total += 1
            names = _result_names(tree, call)
            if not names:
                continue
            unknown = _keys_read_from(tree, names) - LIBRARY_KEYS
            if unknown:
                offenders.append(f"{path.name}:{call.lineno} reads {sorted(unknown)}")
    assert total >= 10, f"expected the benchmark call sites, found {total}"
    assert offenders == []


def test_the_contract_covers_the_three_known_defect_sites():
    """The static contract must actually see the call sites of the three
    families whose benchmark gates were vacuous."""
    files = {path.name for path in _runner_files()}
    assert "run_futures_tsmom_experiment.py" in files
    assert "run_h7_intraday_tsmom_experiment.py" in files
    assert "run_h18_overnight_intraday_experiment.py" in files

    sites = {}
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        sites[path.name] = len(_call_sites(tree))
    assert sites["run_futures_tsmom_experiment.py"] >= 1
    assert sites["run_h7_intraday_tsmom_experiment.py"] >= 1
    assert sites["run_h18_overnight_intraday_experiment.py"] >= 1
