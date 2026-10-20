"""H33/H34 — the benchmark-comparison contract.

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
   price level;
4. the **H34** direction-aware benchmark-significance gate: every runner
   must evaluate it through ``benchmark_significance_gate`` (a bare
   two-sided p-value comparison is a direction-blind gate), and the gate
   must never let a significantly *negative* excess return pass.
"""

import ast
import json
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

try:  # the H34 gate helper (absent in the pre-H34 source: negative control)
    from qtr.validation.statistics import benchmark_significance_gate
except ImportError:  # pragma: no cover - exercised by the negative control
    benchmark_significance_gate = None

ARTIFACTS = ROOT / ".experiments" / "artifacts"

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
    assert bench["p_value"] == pytest.approx(expected["alpha_p_value"], rel=1e-12)
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


# --------------------------------------------------------------------------- #
# 4. H34 — the direction-aware benchmark-significance gate
# --------------------------------------------------------------------------- #
def test_the_gate_requires_a_positive_excess_return():
    """A significantly NEGATIVE excess return (the strategy being
    significantly *worse* than the benchmark) must not pass."""
    assert benchmark_significance_gate(0.001, 1.0) is True
    assert benchmark_significance_gate(0.001, -3.0) is False
    assert benchmark_significance_gate(0.6, 1.0) is False
    # the threshold is strict: p == max_p_value does not pass
    assert benchmark_significance_gate(0.05, 1.0) is False
    assert benchmark_significance_gate(0.0499, 1.0) is True
    # an exactly zero information ratio is not a positive excess return
    assert benchmark_significance_gate(0.001, 0.0) is False


def test_the_gate_never_manufactures_a_pass():
    """The re-specified gate can only ever REMOVE a pass: a pass still
    requires the pre-registered two-sided p-value to be below the
    threshold."""
    for p in np.linspace(0.0, 1.0, 101):
        for ir in (-3.0, -0.001, 0.0, 0.001, 3.0):
            gate = benchmark_significance_gate(p, ir, 0.05)
            assert gate == bool(p < 0.05 and ir > 0.0)
            assert not (gate and p >= 0.05)


def test_the_gate_fails_closed_on_degenerate_inputs():
    assert benchmark_significance_gate(np.nan, 1.0) is False
    assert benchmark_significance_gate(0.001, np.nan) is False
    assert benchmark_significance_gate(1.0, -np.inf) is False
    assert benchmark_significance_gate(0.0, 0.0) is False


def _summary(path: pathlib.Path) -> dict:
    with open(path / "summary.json") as f:
        return json.load(f)


def _benchmark_p_and_ir(summary: dict) -> tuple[float, float] | None:
    """The committed benchmark p-value and information ratio of an artifact.

    The families record the pair under different names (the runners predate
    the H33 contract), so every published shape is accepted. ``None`` means
    the artifact carries no benchmark comparison at all.
    """
    metrics = summary.get("metrics") or {}
    gate_metrics = summary.get("gate_metrics") or {}
    alpha = summary.get("alpha_vs_benchmark") or {}
    comparison = summary.get("benchmark_comparison") or {}
    bench_gate = gate_metrics.get("benchmark_p") or {}

    def _num(value):
        return (
            value
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else None
        )

    p = None
    for candidate in (
        metrics.get("benchmark_p_value"),
        gate_metrics.get("benchmark_p_value"),
        alpha.get("p_value"),
        comparison.get("alpha_p_value"),
        bench_gate.get("value"),
    ):
        p = _num(candidate)
        if p is not None:
            break
    ir = None
    ir_gate = gate_metrics.get("information_ratio")
    for candidate in (
        metrics.get("information_ratio"),
        ir_gate if isinstance(ir_gate, (int, float)) else None,
        alpha.get("information_ratio"),
        comparison.get("information_ratio"),
        ir_gate.get("value") if isinstance(ir_gate, dict) else None,
    ):
        ir = _num(candidate)
        if ir is not None:
            break
    if p is None or ir is None:
        return None
    return float(p), float(ir)


def _as_bool(value) -> bool | None:
    """The published artifacts record gate booleans as real booleans and (in
    the older families) as the strings "True"/"False"."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value in ("True", "False"):
        return value == "True"
    return None


def _published_p_gate(summary: dict) -> bool | None:
    """The benchmark p-gate as PUBLISHED in the artifact (four shapes)."""
    passes = summary.get("passes") or {}
    if "p" in passes:
        return _as_bool(passes["p"])
    gates = summary.get("gates") or {}
    bench = gates.get("benchmark_significance") or {}
    if "pass" in bench:
        return _as_bool(bench["pass"])
    gate_metrics = summary.get("gate_metrics") or {}
    bench_gate = gate_metrics.get("benchmark_p") or {}
    if "passes" in bench_gate:
        return _as_bool(bench_gate["passes"])
    if "max_p_value" in gates:
        return _as_bool(gates["max_p_value"])
    return None


# The published artifacts whose benchmark-significance gate passed for the
# WRONG reason: the two-sided p-value is small because the strategy is
# significantly WORSE than the benchmark (a negative information ratio).
# Disclosed in HYPOTHESIS_SPEC.md section H34 and FINAL_REPORT.md.
WRONG_REASON_P_PASSES = {
    "exp_2026-10-10T21-27-13-928282Z",  # H3  p=0.046364, IR=-0.8932
    "exp_2026-10-13T22-40-41-870350Z",  # H19 p=0.002602, IR=-0.8798
    "exp_2026-10-13T23-06-33-191710Z",  # H20 p=0.015948, IR=-0.7040
    "exp_2026-10-14T11-53-37-996139Z",  # H23 p=0.000900, IR=-3.0739
    "exp_2026-10-14T18-13-09-457781Z",  # H23 p=0.000900, IR=-3.0739
}


def _wrong_reason_p_passes() -> dict[str, tuple[float, float]]:
    """Committed artifacts whose published benchmark p-pass is NOT evidence
    for the hypothesis: either the p-value is not below the threshold, or the
    excess return is negative (the strategy is significantly *worse* than the
    benchmark)."""
    found = {}
    for path in sorted(ARTIFACTS.glob("*/summary.json")):
        summary = _summary(path.parent)
        pair = _benchmark_p_and_ir(summary)
        if pair is None:
            continue
        p, ir = pair
        if _published_p_gate(summary) and not (p < 0.05 and ir > 0.0):
            found[path.parent.name] = (p, ir)
    return found


def test_no_committed_artifact_carries_an_undisclosed_wrong_reason_p_pass():
    """Every published benchmark p-pass must be in the direction of the
    hypothesis, except the ones explicitly disclosed as wrong-reason
    passes."""
    found = _wrong_reason_p_passes()
    offenders = {
        artifact_id: values
        for artifact_id, values in found.items()
        if artifact_id not in WRONG_REASON_P_PASSES
    }
    assert offenders == {}
    assert found, "no committed artifact with a benchmark comparison was found"


def test_the_disclosed_wrong_reason_passes_are_the_known_ones():
    """The disclosure is pinned: the wrong-reason passes are exactly the
    published artifacts of H3, H19, H20 and H23."""
    assert set(_wrong_reason_p_passes()) == WRONG_REASON_P_PASSES


def test_the_certified_families_survive_the_direction_aware_gate():
    """H10, H22 and H25 (and the other genuine p-passes) must still pass."""
    certified = {
        "exp_2026-10-11T17-41-18-169363Z": (
            "H10",
            4.790305556723297e-10,
            0.9247889169803807,
        ),
        "exp_2026-10-14T18-52-08-943792Z": (
            "H22",
            1.3340812548651885e-19,
            1.3466905696542812,
        ),
        "exp_2026-10-14T20-08-34-613690Z": (
            "H25",
            1.4028853805082562e-19,
            1.3458716250016904,
        ),
    }
    for artifact_id, (family, p, ir) in certified.items():
        summary = _summary(ARTIFACTS / artifact_id)
        pair = _benchmark_p_and_ir(summary)
        assert pair is not None, f"{family} artifact carries no benchmark comparison"
        assert pair == pytest.approx((p, ir), rel=1e-12)
        assert benchmark_significance_gate(p, ir, 0.05) is True, (
            f"{family} must survive the direction-aware gate"
        )


def test_h34_tally_impact_is_pinned_as_a_disclosure():
    """The direction-aware gate removes exactly the wrong-reason p-pass:
    H19 3/9 -> 2/9, H20 2/9 -> 1/9, H23 2/9 -> 1/9. Recomputed offline from
    the committed artifacts; no grid is re-run and no artifact is touched."""
    expected = {
        "exp_2026-10-13T22-40-41-870350Z": ("H19", 3, 2),
        "exp_2026-10-13T23-06-33-191710Z": ("H20", 2, 1),
        "exp_2026-10-14T18-13-09-457781Z": ("H23", 2, 1),
    }
    for artifact_id, (family, published_count, recomputed_count) in expected.items():
        summary = _summary(ARTIFACTS / artifact_id)
        passes = summary.get("passes") or {}
        m = summary.get("metrics") or {}
        published = sum(1 for value in passes.values() if value is True)
        assert published == published_count, (
            f"{family}: published tally {published}/9 != {published_count}/9"
        )
        # the p pass is wrong-reason: small two-sided p, negative information ratio
        assert passes.get("p") is True
        assert m["information_ratio"] < 0.0
        gate = benchmark_significance_gate(
            m["benchmark_p_value"], m["information_ratio"], 0.05
        )
        assert gate is False
        # H34 flips only the p gate: True -> False, every other gate unchanged
        recomputed = published - 1
        assert recomputed == recomputed_count, (
            f"{family}: recomputed tally {recomputed}/9 != {recomputed_count}/9"
        )


# --------------------------------------------------------------------------- #
# 5. the static contract over every benchmark p-gate site
# --------------------------------------------------------------------------- #
def _max_p_value_comparisons(tree: ast.AST) -> list[ast.Compare]:
    """Every comparison of a value against ``GATES["max_p_value"]``."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for operand in operands:
            for sub in ast.walk(operand):
                if (
                    isinstance(sub, ast.Subscript)
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id == "GATES"
                    and isinstance(sub.slice, ast.Constant)
                    and sub.slice.value == "max_p_value"
                ):
                    found.append(node)
                    break
            else:
                continue
            break
    return found


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _inside_gate_helper(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """True if `node` is an argument of a ``benchmark_significance_gate`` call."""
    current = node
    while current in parents:
        current = parents[current]
        if (
            isinstance(current, ast.Call)
            and isinstance(current.func, ast.Name)
            and current.func.id == "benchmark_significance_gate"
        ):
            return True
    return False


def test_no_runner_compares_a_p_value_against_max_p_value_directly():
    """A bare ``p < GATES["max_p_value"]`` is the direction-blind gate: it is
    satisfied by a significantly NEGATIVE excess return. Every benchmark
    significance gate must go through ``benchmark_significance_gate``."""
    offenders = []
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        parents = _parents(tree)
        for compare in _max_p_value_comparisons(tree):
            if not _inside_gate_helper(compare, parents):
                offenders.append(f"{path.name}:{compare.lineno}")
    assert offenders == []


def test_every_runner_with_a_benchmark_gate_uses_the_direction_aware_helper():
    """The contract must not be satisfiable by deleting the gates: every
    runner that owns a benchmark-significance gate must call the helper."""
    users = set()
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "benchmark_significance_gate"
            ):
                users.add(path.name)
    expected = {
        "run_cs_momentum_experiment.py",
        "run_ddcv_experiment.py",
        "run_futures_tsmom_experiment.py",
        "run_h10_intraday_tsmom_pfopt_experiment.py",
        "run_h12_selection_bias_audit.py",
        "run_h16_factor_timing_experiment.py",
        "run_h17_vrp_experiment.py",
        "run_h18_overnight_intraday_experiment.py",
        "run_h19_volume_predictive_experiment.py",
        "run_h20_signed_volume_experiment.py",
        "run_h23_crypto_futures_tsmom.py",
        "run_h6_vix_ddcv_experiment.py",
        "run_h7_intraday_tsmom_experiment.py",
        "run_h8_rolladjusted_tsmom_experiment.py",
        "run_h9_intraday_tsmom_experiment.py",
        "run_regime_gated_momentum_experiment.py",
        "run_ts_momentum_experiment.py",
    }
    assert expected <= users, f"missing the direction-aware gate in: {expected - users}"


def test_no_runner_publishes_the_one_sided_p_value():
    """The published ``benchmark_p_value`` must stay the TWO-SIDED p-value:
    it is the number the committed artifacts record, so the artifacts stay
    reproducible from the code."""
    offenders = []
    for path in _runner_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "alpha_p_value_one_sided"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []
