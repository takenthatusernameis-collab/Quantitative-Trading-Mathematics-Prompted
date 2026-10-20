"""The shared research infrastructure must be point-in-time.

``qtr.strategies`` (the signal library) and ``qtr.backtest`` (the vectorized
engine) are the code path behind almost every experiment runner in this
repository: ``run_experiment.py``, ``run_baseline.py``, ``run_param_sweep.py``,
``run_alternatives.py``, ``run_cs_momentum_experiment.py``,
``run_ts_momentum_experiment.py``, ``run_ddcv_experiment.py``,
``run_h6_vix_ddcv_experiment.py``, ``run_futures_tsmom_experiment.py``,
``run_h7/h9/h10/h18/h21`` and more. A look-ahead in either module would
silently inflate every result that uses it, and would do so *in the direction
of a pass* -- the failure mode this repository cares about most.

Before this module the only causality coverage was:

* ``tests/test_backtest_engine.py::TestLookAheadSafety``, which pins one
  narrow property (a position established on day 0 earns the day-1 return);
* ``tests/test_h23_crypto_futures_tsmom.py::TestCausality`` and
  ``tests/test_h28_causal_recertification.py``, which cover the *runners'
  own* signal code, not the shared library.

Nothing pinned the shared library itself, so a look-ahead introduced in
``baselines.py`` or in ``engine.py`` would have reached every runner with no
test failing.

The contract pinned here is the standard point-in-time one:

    **No output observed at or before bar t may depend on any price
    strictly after bar t.**

It is checked by *future perturbation*: the prices after a cut are replaced
by a different (deterministic, seeded) path, and everything at or before the
cut must come out bit-identical. A perturbation at cut ``c`` can only reveal
a leak that reads *past* bar ``c``, so the probe is run at **every bar** of a
reduced sample (the dense sweep) as well as at a spread of cut points on the
full sample with the lookbacks the runners actually use (the sparse sweep).
The dense sweep is what makes the check complete for the common one-bar-ahead
leak; the sparse sweep is what makes it representative of the real
configurations.

The probes are checked for non-vacuity in both directions:

* a **negative control** -- a deliberately leaky signal -- must be *detected*
  by the probe, so a passing probe means something; and
* every *reactive* strategy must actually *change* after the cut, so a
  strategy that returned constant zeros could not pass trivially.

A **coverage pin** ties the probes to ``qtr.strategies.STRATEGY_REGISTRY``:
registering a new strategy fails the suite until it is probed, so the
invariant cannot silently stop covering the library.

Scope: this module covers the shared library. The runners' inline signal
code is covered, where it exists, by the family-specific suites (H23, H28).
"""

from __future__ import annotations

import ast
import pathlib

import numpy as np
import pandas as pd
import pytest

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest
from qtr.strategies import baselines

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIBRARY_ROOT = ROOT / "src" / "qtr"

# The long sample: realistic lookbacks, as the runners use them.
N_BARS = 600
SPARSE_CUTS = (300, 360, 420, 450, 500, 540, 570, 590, 598)

# The short sample: the dense sweep uses it so that *every* bar can be a cut
# point at an affordable cost. The property under test does not depend on the
# lookback length (it is the same code path), so the dense sweep measures
# completeness and the sparse sweep measures realism.
DENSE_BARS = 100
DENSE_CUTS = tuple(range(0, DENSE_BARS - 1))

# Probe configuration per strategy. The dense sweep uses lookbacks that fit
# the short sample; the sparse sweep uses the lookbacks the runners use.
# ``buy_and_hold`` is a constant position and is therefore not *reactive*:
# it satisfies the causality contract trivially, and requiring it to react
# would be wrong.
PROBE_CASES: dict[str, dict[str, object]] = {
    "ma_crossover": {
        "dense": {"fast_window": 10, "slow_window": 25},
        "sparse": {"fast_window": 20, "slow_window": 50},
        "reactive": True,
    },
    "buy_and_hold": {
        "dense": {"weight": 1.0},
        "sparse": {"weight": 1.0},
        "reactive": False,
    },
    "ewma_crossover": {
        "dense": {"fast_span": 10, "slow_span": 25},
        "sparse": {"fast_span": 20, "slow_span": 50},
        "reactive": True,
    },
    "momentum": {
        "dense": {"lookback": 40, "skip": 8},
        "sparse": {"lookback": 120, "skip": 21},
        "reactive": True,
    },
    "mean_reversion": {
        "dense": {"window": 15},
        "sparse": {"window": 20},
        "reactive": True,
    },
    "time_series_momentum": {
        "dense": {"lookback": 40, "skip": 8},
        "sparse": {"lookback": 120, "skip": 21},
        "reactive": True,
    },
    "vol_scaled_tsmom": {
        "dense": {"lookback": 40, "skip": 8, "vol_window": 20},
        "sparse": {"lookback": 120, "skip": 21, "vol_window": 63},
        "reactive": True,
    },
    "carry": {
        "dense": {"lookback": 60},
        "sparse": {"lookback": 252},
        "reactive": True,
    },
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _make_prices(n: int = N_BARS, seed: int = 7) -> pd.DataFrame:
    """A deterministic multi-symbol price frame."""
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2018-01-01", periods=n)
    data = {}
    for i, sym in enumerate(("A", "B", "C")):
        rets = rng.normal(0.0003, 0.012, n) + 0.0001 * i
        data[sym] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=index)


def _perturb_future(prices: pd.DataFrame, cut: int, seed: int = 99) -> pd.DataFrame:
    """Replace the prices strictly after ``cut`` with a different path.

    Bar ``cut`` itself is left untouched: it belongs to the invariant
    region. The factors are drawn per bar (not a single constant) so that
    both time-series and cross-sectional relationships inside the future
    change; a constant factor would leave, e.g., a *ratio* of two
    consecutive perturbed bars unchanged and could leave a reactive strategy
    inert.

    The *first* perturbed bar is halved. That forces the sign of any
    one-bar-ahead return to flip, so a leak that is expressed as a sign
    test (``(tomorrow > 0)``) is detected rather than hidden behind a
    return that happened to keep its sign.
    """
    rng = np.random.default_rng(seed + cut)
    start = cut + 1
    factors = rng.uniform(0.6, 1.4, size=len(prices) - start)
    if len(factors):
        factors[0] = 0.5
    out = prices.copy()
    out.iloc[start:] = out.iloc[start:].to_numpy() * factors[:, None]
    return out


def _past(values: pd.DataFrame, cut: int) -> np.ndarray:
    """The invariant region: bars 0..cut inclusive."""
    return values.iloc[: cut + 1].to_numpy()


def _future(values: pd.DataFrame, cut: int) -> np.ndarray:
    """The perturbed region: bars after the cut."""
    return values.iloc[cut + 1 :].to_numpy()


def _probe(fn, kwargs: dict, prices: pd.DataFrame, cuts: tuple[int, ...]) -> None:
    """Assert the signal at bars <= cut is invariant for every cut.

    The base signal is computed once and reused: only the perturbed signal
    has to be recomputed per cut.
    """
    base = fn(prices, **kwargs)
    for cut in cuts:
        perturbed = fn(_perturb_future(prices, cut), **kwargs)
        np.testing.assert_array_equal(
            _past(base, cut),
            _past(perturbed, cut),
            err_msg=(
                f"the signal at bars <= {cut} changed when only prices after "
                f"bar {cut} changed: the signal is not point-in-time"
            ),
        )


def _engine_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        cost_model=CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=1.0,
            equity_impact_bps_per_pct_adv=0.1,
        ),
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=True,
    )


# --------------------------------------------------------------------------- #
# the signal library
# --------------------------------------------------------------------------- #
class TestSignalLibraryCausality:
    def test_every_registered_strategy_is_probed(self):
        """Coverage pin: the probes must cover the whole registry.

        Registering a new strategy without probing it would leave the
        point-in-time contract unchecked for that strategy, so the suite
        fails until the new case is added to PROBE_CASES.
        """
        assert set(PROBE_CASES) == set(baselines.STRATEGY_REGISTRY), (
            "the strategy registry and the causality probes are out of sync; "
            f"missing probe for {sorted(set(baselines.STRATEGY_REGISTRY) - set(PROBE_CASES))}, "
            f"stale probe for {sorted(set(PROBE_CASES) - set(baselines.STRATEGY_REGISTRY))}"
        )

    @pytest.mark.parametrize("name", sorted(PROBE_CASES))
    def test_signal_is_point_in_time_at_every_bar(self, name):
        """Dense sweep: every bar of the short sample is a cut point.

        A perturbation at cut ``c`` can only expose a leak that reads past
        bar ``c``, so probing every bar is what makes the check complete
        for the common one-bar-ahead leak.
        """
        case = PROBE_CASES[name]
        fn = baselines.STRATEGY_REGISTRY[name]
        _probe(fn, case["dense"], _make_prices(DENSE_BARS), DENSE_CUTS)

    @pytest.mark.parametrize("name", sorted(PROBE_CASES))
    def test_signal_is_point_in_time_with_runner_lookbacks(self, name):
        """Sparse sweep: the lookbacks the runners actually use."""
        case = PROBE_CASES[name]
        fn = baselines.STRATEGY_REGISTRY[name]
        _probe(fn, case["sparse"], _make_prices(), SPARSE_CUTS)

    @pytest.mark.parametrize("name", sorted(PROBE_CASES))
    def test_probe_is_not_vacuous(self, name):
        """Reactive strategies must actually react to the perturbation."""
        case = PROBE_CASES[name]
        if not case["reactive"]:
            pytest.skip(f"{name} is a constant position by construction")
        fn = baselines.STRATEGY_REGISTRY[name]
        prices = _make_prices()
        cut = 450
        base = fn(prices, **case["sparse"])
        perturbed = fn(_perturb_future(prices, cut), **case["sparse"])
        assert not np.array_equal(
            _future(base, cut),
            _future(perturbed, cut),
            equal_nan=True,
        ), (
            f"{name} did not react to a perturbation of the future prices, so its "
            "causality probe cannot distinguish a leak from a constant output"
        )

    def test_probe_detects_an_injected_look_ahead(self):
        """Negative control: the probe must reject a leaky signal.

        ``shift(-1)`` moves tomorrow's return onto today, which is the
        canonical look-ahead. If the probe could not see it, the passing
        probes above would prove nothing.
        """

        def leaky_signal(prices: pd.DataFrame) -> pd.DataFrame:
            tomorrow = prices.pct_change().shift(-1)
            return (tomorrow > 0).astype(float)

        prices = _make_prices(DENSE_BARS)
        with pytest.raises(AssertionError):
            _probe(leaky_signal, {}, prices, DENSE_CUTS)

    def test_no_negative_shift_in_the_signal_library(self):
        """Static check: a negative shift is a look-ahead operator.

        Every function in ``qtr.strategies`` returns *position weights* --
        trading decisions -- so a negative shift there is unambiguously a
        leak, with no legitimate label-style use. ``qtr.backtest`` is
        included: the engine applies positions with a one-bar delay, and a
        negative shift there would undo that delay.
        """

        def negative_shift_calls(path: pathlib.Path) -> list[int]:
            tree = ast.parse(path.read_text())
            found = []
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr != "shift":
                    continue
                first = node.args[0] if node.args else None
                is_negative = isinstance(first, ast.UnaryOp) and isinstance(first.op, ast.USub)
                for keyword in node.keywords:
                    if keyword.arg in ("periods", "n") and isinstance(keyword.value, ast.UnaryOp):
                        is_negative = True
                if is_negative:
                    found.append(node.lineno)
            return found

        offenders = {}
        for path in sorted(LIBRARY_ROOT.rglob("*.py")):
            lines = negative_shift_calls(path)
            if lines:
                offenders[str(path.relative_to(ROOT))] = lines
        assert not offenders, (
            f"negative shift (look-ahead) found in the shared library: {offenders}"
        )

    def test_no_backward_period_in_the_signal_library(self):
        """Static check: a backward period reads the future.

        ``pct_change(-1)`` and ``diff(-1)`` compute the *backward* return,
        i.e. they read price[t + 1] at bar t. Like a negative shift, there
        is no legitimate use of them in a signal constructor, and -- unlike
        a negative shift -- a per-bar perturbation is the only way to catch
        them, so the static check is what closes this class.
        """

        def backward_period_calls(path: pathlib.Path) -> list[int]:
            tree = ast.parse(path.read_text())
            found = []
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr not in {"pct_change", "diff"}:
                    continue
                first = node.args[0] if node.args else None
                if isinstance(first, ast.UnaryOp) and isinstance(first.op, ast.USub):
                    found.append(node.lineno)
            return found

        offenders = {}
        for path in sorted(LIBRARY_ROOT.rglob("*.py")):
            lines = backward_period_calls(path)
            if lines:
                offenders[str(path.relative_to(ROOT))] = lines
        assert not offenders, (
            f"backward period (look-ahead) found in the shared library: {offenders}"
        )


# --------------------------------------------------------------------------- #
# the backtest engine
# --------------------------------------------------------------------------- #
class TestEngineCausality:
    def _run(self, prices: pd.DataFrame):
        signals = baselines.vol_scaled_tsmom_signals(prices, lookback=120, skip=21, vol_window=63)
        adv = pd.Series({sym: 1_000_000.0 for sym in prices.columns})
        return run_backtest(prices, signals, adv=adv, config=_engine_config())

    def test_backtest_outputs_do_not_depend_on_future_prices(self):
        """The engine's returns, positions, equity curve and trade log at
        bars <= the cut must be bit-identical when only later prices
        change."""
        prices = _make_prices()
        base = self._run(prices)

        for cut in SPARSE_CUTS:
            perturbed = self._run(_perturb_future(prices, cut))
            np.testing.assert_array_equal(
                _past(base.returns, cut),
                _past(perturbed.returns, cut),
                err_msg=f"engine returns before bar {cut} changed with a future-only perturbation",
            )
            np.testing.assert_array_equal(
                _past(base.positions, cut),
                _past(perturbed.positions, cut),
                err_msg=f"engine positions before bar {cut} changed with a future-only perturbation",
            )
            np.testing.assert_array_equal(
                _past(base.equity_curve, cut),
                _past(perturbed.equity_curve, cut),
                err_msg=f"engine equity curve before bar {cut} changed with a future-only perturbation",
            )

            cut_time = prices.index[cut]
            base_trades = base.trades[base.trades["timestamp"] <= cut_time].reset_index(drop=True)
            perturbed_trades = perturbed.trades[
                perturbed.trades["timestamp"] <= cut_time
            ].reset_index(drop=True)
            pd.testing.assert_frame_equal(base_trades, perturbed_trades)

    def test_engine_probe_is_not_vacuous(self):
        """The future perturbation must reach the engine's outputs."""
        prices = _make_prices()
        base = self._run(prices)
        perturbed = self._run(_perturb_future(prices, 450))
        assert not np.array_equal(
            _future(base.returns, 450),
            _future(perturbed.returns, 450),
            equal_nan=True,
        ), "the engine ignored the perturbation entirely, so the probe proves nothing"

    def test_rebalance_cost_is_charged_in_the_bar_of_the_trade(self):
        """A trade is executed in the bar its new weight is first held.

        The engine applies positions with a one-bar delay
        (``signals.shift(1) * price_returns``) and charges the cost of a
        rebalance in the same bar. Charging it earlier would let the cost
        be paid before the position exists; charging it later would give
        every trade a free bar of financing. Either way the net Sharpe
        would be a fiction.
        """
        prices = _make_prices(n=60)[["A"]]
        signals = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
        signals.iloc[10:] = 1.0  # enter at bar 10 and hold
        cfg = BacktestConfig(
            initial_capital=1_000_000.0,
            cost_model=CostModel(
                equity_commission_bps=1.0,
                equity_spread_bps=1.0,
                equity_impact_bps_per_pct_adv=0.0,
            ),
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
            max_leverage=1.0,
        )
        res = run_backtest(prices, signals, config=cfg)

        # No trade before bar 10 -> no cost before bar 10.
        assert res.returns.iloc[:10].to_numpy() == pytest.approx(np.zeros(10))
        # The cost is charged in bar 10, the bar the position is first held.
        assert res.returns.iloc[10] < 0.0
        expected_cost = (1.0 + 1.0) / 10_000.0
        assert res.returns.iloc[10] == pytest.approx(-expected_cost, abs=1e-12)
        # From bar 11 the position earns the asset return, and no further
        # cost is charged while the position is held.
        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert res.returns.iloc[11] == pytest.approx(asset_ret.iloc[11], abs=1e-12)
        assert len(res.trades) == 1
        assert res.trades["timestamp"].iloc[0] == prices.index[10]
