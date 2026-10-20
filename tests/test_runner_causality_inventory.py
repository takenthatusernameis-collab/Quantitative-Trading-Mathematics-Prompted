"""The runners' inline signal code must be point-in-time (H37).

``tests/test_causality_invariant.py`` (H36) pinned the point-in-time contract
for the *shared* infrastructure -- ``qtr.strategies`` (the signal library) and
``qtr.backtest`` (the vectorized engine).  That is the code path behind almost
every runner, but each runner also builds its **own** position series inline,
and a look-ahead there is invisible to the library probe.

This module extends the invariant to the runners.  It has four parts.

**1. The probe.**  The same *future perturbation* as H36, applied to the
runners' own constructors: the market data strictly after a cut is replaced by
a different path and everything the constructor produced at or before the cut
must come out bit-identical.  The dense sweep makes every bar of a reduced
sample a cut point (completeness for the common one-bar-ahead leak); the
sparse sweep uses the lookbacks the runners actually use (realism).  A
**negative control** (a deliberately leaky signal) must be *detected*, so a
passing probe means something, and every probed constructor must actually
*react* to the perturbation, so an inert output cannot pass trivially.

**2. The inventory.**  Every module-level function of every in-scope runner is
classified:

``probed``
    Covered by a future-perturbation probe; the probe must find no violation.
``lookahead``
    A **known** look-ahead.  The probe *must detect* it, and the detection is
    pinned, so the disclosure cannot be silently dropped and the defect cannot
    be silently "fixed" without updating the record.
``static``
    Not probe-able.  Covered by a static look-ahead-operator check plus a
    written argument for why no dynamic probe applies.

A new function in an in-scope runner is not classified -> the suite fails.

**3. The static sweep.**  An exhaustive, by-construction sweep of the runners'
source for the operators that *are* look-aheads -- a negative shift, a backward
period, a centred window, a backward fill, a same-period collapse.  The site
list is pinned, so a new look-ahead operator anywhere in the runners fails the
suite even if it sits in a function the inventory does not probe.

**4. The findings.**  The probe confirms the published look-ahead of the
intraday family (H27/H28/H29: the daily collapse is expanded over the same
day) and it finds one the record does not yet state: **H18's ``vix_regime``
predictor omits the pre-registered one-day lag**, so it trades day ``t``'s
overnight leg with the VIX close of day ``t``.  The published H18 row is
unaffected (the selected combo is ``prior_5d_return_sign_next_intraday``) and
the verdict (REJECT) cannot change; it is a disclosure.

Scope: the runners' *inline* code.  No published artifact, gate threshold,
verdict or certified number is touched, and no grid is re-run.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import sys
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --------------------------------------------------------------------------- #
# scope
# --------------------------------------------------------------------------- #
# The runners whose inline signal code this module pins.  H9 and H23 are in
# scope because the in-scope runners *import* their primitives: H9 owns
# ``vol_scaled_tsmom_hourly`` and ``_daily_target_from_hourly`` (the collapse
# that carries the published look-ahead) and H23 is the crypto copy of the H10
# pipeline.
IN_SCOPE_RUNNERS = (
    "run_h9_intraday_tsmom_experiment.py",
    "run_h10_intraday_tsmom_pfopt_experiment.py",
    "run_h12_selection_bias_audit.py",
    "run_h16_factor_timing_experiment.py",
    "run_h18_overnight_intraday_experiment.py",
    "run_h19_volume_predictive_experiment.py",
    "run_h20_signed_volume_experiment.py",
    "run_h21_futures_tsmom_multicontract.py",
    "run_h22_futures_tsmom_voltarget.py",
    "run_h23_crypto_futures_tsmom.py",
    "run_h25_futures_tsmom_pfmargin.py",
    "run_h27_pnl_level_audit.py",
    "run_h29_lookahead_sweep.py",
    "run_ts_momentum_experiment.py",
    "run_cs_momentum_experiment.py",
)

# The runners named by the H36 handoff (the ones with inline signal code).
NAMED_BY_HANDOFF = (
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
)

# The dense sweep uses a reduced sample so that *every* bar can be a cut
# point; the sparse sweep uses the lookbacks the runners actually use.
DENSE_BARS = 80
DENSE_CUTS = tuple(range(0, DENSE_BARS - 1))
N_BARS = 1400
SPARSE_CUTS = (400, 700, 900, 1000, 1100, 1200, 1300, 1380, 1398)

# Perturbation seeds (fixed -> the probe is deterministic).
PERTURB_SEED = 99


# --------------------------------------------------------------------------- #
# synthetic market data
# --------------------------------------------------------------------------- #
def _hourly_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h")


def _daily_index(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-01", periods=n)


# The intraday runners work on futures contracts, and several of them look the
# contract specs up by symbol (H27's P&L replication, H21/H22/H25's contract
# selection), so the hourly market carries the real futures universe.
FUTURES_SYMBOLS = ("ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F")


def _prices(
    index: pd.DatetimeIndex, n_syms: int, seed: int, symbols: tuple[str, ...] | None = None
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    names = symbols if symbols is not None else tuple(f"S{i}" for i in range(n_syms))
    data = {}
    for i, name in enumerate(names):
        rets = rng.normal(0.0003, 0.012, len(index)) + 0.0001 * i
        data[name] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=index)


def _ohlc(index: pd.DatetimeIndex, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.011, len(index))))
    open_ = close * (1.0 + rng.normal(0.0, 0.003, len(index)))
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.002, len(index))))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.002, len(index))))
    volume = rng.integers(1_000_000, 5_000_000, len(index)).astype(float)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )


def _vix(index: pd.DatetimeIndex, seed: int) -> pd.Series:
    """A VIX series that spans the bull (<20) / sideways (20-30) / bear (>30)
    regimes, so a regime change is observable."""
    rng = np.random.default_rng(seed)
    values = 25.0 + 9.0 * np.sin(np.arange(len(index)) * 1.7) + rng.normal(0.0, 0.5, len(index))
    return pd.Series(values, index=index)


def _weights(index: pd.DatetimeIndex, n_syms: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    values = rng.normal(0.0, 1.0, (len(index), n_syms)).clip(-1.0, 1.0)
    return pd.DataFrame(values, index=index, columns=[f"S{i}" for i in range(n_syms)])


def _market(kind: str, n: int, seed: int) -> dict:
    if kind == "hourly":
        index = _hourly_index(n)
        return {
            "index": index,
            "prices": _prices(index, len(FUTURES_SYMBOLS), seed, symbols=FUTURES_SYMBOLS),
            "vix": _vix(index, seed + 1),
            "signal": _weights(index, 3, seed + 2),
        }
    if kind == "daily":
        index = _daily_index(n)
        return {
            "index": index,
            "prices": _prices(index, 3, seed),
            "vix": _vix(index, seed + 1),
            "signal": _weights(index, 3, seed + 2),
        }
    if kind == "daily_ohlc":
        index = _daily_index(n)
        return {
            "index": index,
            "ohlc": _ohlc(index, seed),
            "vix": _vix(index, seed + 1),
        }
    if kind == "hourly_signal":
        index = _hourly_index(n)
        return {
            "index": index,
            "signal": _weights(index, 3, seed),
            "vix": _vix(index, seed + 1),
        }
    raise AssertionError(f"unknown market kind {kind!r}")


# --------------------------------------------------------------------------- #
# the perturbation
# --------------------------------------------------------------------------- #
# The columns of an OHLC frame that are only known at the *close* of their bar.
CLOSE_LIKE_OHLC = ("high", "low", "close")


def _factors(rows: int, cols: int, seed: int) -> np.ndarray:
    """Per-(bar, column) multiplicative factors.

    Independent factors per column matter: a factor shared by open and close
    would leave ``close - open`` (and therefore a sign rule) unchanged, and a
    shared factor across symbols would leave the cross-sectional ordering of
    the signals unchanged.  The first perturbed bar is halved, which forces the
    sign of a one-bar-ahead return to flip, so a leak that is expressed as a
    sign test is detected rather than hidden behind an unchanged sign.
    """
    rng = np.random.default_rng(seed)
    factors = rng.uniform(0.6, 1.4, size=(rows, cols))
    factors[0, :] = 0.5
    return factors


def _perturb_frame(
    df: pd.DataFrame,
    cut: int,
    seed: int,
    scope: str,
    close_like_cols: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    values = df.to_numpy(dtype=float).copy()
    n_rows, n_cols = values.shape
    close_like = np.array(
        [
            c in (close_like_cols if close_like_cols is not None else tuple(df.columns))
            for c in df.columns
        ]
    )

    start_after = cut + 1
    if start_after < n_rows:
        values[start_after:] *= _factors(n_rows - start_after, n_cols, seed)

    if scope == "close" and cut < n_rows:
        # The decision is executed *at the open* of the bar, so the close-like
        # observations of the cut bar itself must not influence it.
        cols = np.flatnonzero(close_like)
        if cols.size:
            values[cut : cut + 1, cols] *= _factors(1, cols.size, seed + 991)

    return pd.DataFrame(values, index=df.index, columns=df.columns)


def _perturb_ohlc(df: pd.DataFrame, cut: int, seed: int, scope: str) -> pd.DataFrame:
    out = _perturb_frame(df, cut, seed, scope, close_like_cols=CLOSE_LIKE_OHLC)
    # keep the frame a valid OHLC frame after the independent column factors
    high = np.maximum.reduce(
        [out["high"].to_numpy(), out["open"].to_numpy(), out["close"].to_numpy()]
    )
    low = np.minimum.reduce(
        [out["low"].to_numpy(), out["open"].to_numpy(), out["close"].to_numpy()]
    )
    out["high"] = high
    out["low"] = low
    return out


def _perturb_vix(series: pd.Series, cut: int, seed: int, scope: str) -> pd.Series:
    values = series.to_numpy(dtype=float).copy()
    start = cut if scope == "close" else cut + 1
    if start < len(values):
        base = values[start]
        rng = np.random.default_rng(seed)
        factors = rng.uniform(0.6, 1.4, size=len(values) - start)
        values[start:] *= factors
        # Move the first perturbed observation across *both* regime boundaries
        # (20 and 30), so a regime-dependent signal always changes.  The
        # decision is taken on the *base* value, so the move always crosses
        # the boundary the base value was on the other side of.
        values[start] = 20.0 if base > 30.0 else 40.0
    return pd.Series(values, index=series.index)


def _perturb_market(market: dict, cut: int, seed: int, scope: str) -> dict:
    out = dict(market)
    for key, obj in market.items():
        if key == "index":
            continue
        if key == "vix":
            out[key] = _perturb_vix(obj, cut, seed, scope)
        elif key == "ohlc":
            out[key] = _perturb_ohlc(obj, cut, seed, scope)
        else:
            out[key] = _perturb_frame(obj, cut, seed, scope)
    return out


# --------------------------------------------------------------------------- #
# the probe
# --------------------------------------------------------------------------- #
def _as_arrays(obj) -> list[np.ndarray]:
    """Flatten a constructor's output into comparable arrays."""
    if isinstance(obj, pd.DataFrame):
        return [obj.to_numpy()]
    if isinstance(obj, pd.Series):
        return [obj.to_numpy()]
    if isinstance(obj, (tuple, list)):
        arrays: list[np.ndarray] = []
        for item in obj:
            arrays.extend(_as_arrays(item))
        return arrays
    if isinstance(obj, dict):
        arrays = []
        for item in obj.values():
            arrays.extend(_as_arrays(item))
        return arrays
    return []


def _values_equal(left, right) -> bool:
    if left is None or right is None:
        return left is right
    try:
        if pd.isna(left) and pd.isna(right):
            return True
    except (TypeError, ValueError):
        pass
    return bool(left == right)


def _arrays_equal(left: np.ndarray, right: np.ndarray) -> bool:
    if left.shape != right.shape:
        return False
    if left.dtype.kind in "fc" and right.dtype.kind in "fc":
        return bool(np.array_equal(left, right, equal_nan=True))
    if left.dtype.kind == "O" or right.dtype.kind == "O":
        return all(
            _values_equal(a, b) for a, b in zip(left.ravel().tolist(), right.ravel().tolist())
        )
    return bool(np.array_equal(left, right))


def _call(case: dict, market: dict, builder: str):
    if "call" in case:
        func = case["call"]
    else:
        module = importlib.import_module(case["runner"][:-3])
        func = getattr(module, case["func"])
    args, kwargs = case[builder](market)
    return func(*args, **kwargs)


def _probe(
    case: dict, market: dict, cuts: tuple[int, ...], builder: str, scope: str
) -> tuple[list[int], bool]:
    """Return (violating cuts, the perturbation changed the output at all)."""
    base = _call(case, market, builder)
    base_arrays = _as_arrays(base)
    assert base_arrays, f"{case['id']} produced no comparable output"

    violations: list[int] = []
    changed = False
    for cut in cuts:
        perturbed_market = _perturb_market(market, cut, PERTURB_SEED + cut, scope)
        perturbed = _call(case, perturbed_market, builder)
        perturbed_arrays = _as_arrays(perturbed)
        for base_array, perturbed_array in zip(base_arrays, perturbed_arrays):
            assert base_array.shape == perturbed_array.shape, (
                f"{case['id']} changed shape under a future-only perturbation"
            )
            if not _arrays_equal(base_array, perturbed_array):
                changed = True
            if not _arrays_equal(base_array[: cut + 1], perturbed_array[: cut + 1]):
                violations.append(cut)
                break
    return violations, changed


# --------------------------------------------------------------------------- #
# helpers shared by several runners (causal by construction)
# --------------------------------------------------------------------------- #
def _exit_inputs(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The runners' own price-derived exit inputs (H12/H21/H22/H25)."""
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol = vol.replace(0, np.nan).ffill()
    return atr, vol


def _causal_target(prices: pd.DataFrame) -> pd.DataFrame:
    """A *causal* stand-in for the intraday target.

    The published target is built by the daily collapse, which carries the
    published look-ahead; the exit machinery is therefore probed against a
    target that has no look-ahead of its own, so a violation can be attributed
    to the exits and not to their input.
    """
    return (prices.pct_change(20).shift(1) > 0).astype(float)


# The multi-contract runners read their (frozen) configuration from the
# module-level ``SEL``.  The dense sweep shortens it -- exactly as H36's dense
# sweep shortens the lookbacks -- so that every bar of a reduced sample can be
# a cut point; the sparse sweep keeps the runner's real configuration.
_DENSE_SEL = {
    "vol_window_long": 40,
    "smooth_span": None,
    "regime_scaling": False,
    "min_trade_interval": 0,
    "trailing_mult": 2.0,
    "max_hold_bars": 20,
    "vol_limit_mult": 1.5,
    "vol_floor_fraction": 0.25,
}


# --------------------------------------------------------------------------- #
# the probe cases
# --------------------------------------------------------------------------- #
# ``scope``:
#   "after"  the decision for bar t is made at the close of bar t and traded at
#            bar t+1 (the engine's one-bar delay) -> the signal at bar t may
#            use the data of bar t.
#   "close"  the decision is executed *at the open* of bar t -> the signal at
#            bar t may not use the close of bar t (H18 trades the leg that is
#            realised at the open of the same day).
Case = dict


def _h9_dense(m: dict):
    return (
        (m["prices"],),
        {
            "lookback": 40,
            "fast_lookback": 20,
            "skip": 8,
            "vol_window_long": 40,
            "vol_window_short": 20,
        },
    )


def _h9_sparse(m: dict):
    return (
        (m["prices"],),
        {
            "lookback": 252,
            "fast_lookback": 63,
            "skip": 1,
            "vol_window_long": 252,
            "vol_window_short": 63,
        },
    )


CASES: dict[str, Case] = {
    # ---------------- H9: the shared intraday primitives ---------------- #
    "h9.regime_labels": {
        "id": "h9.regime_labels",
        "runner": "run_h9_intraday_tsmom_experiment.py",
        "func": "regime_labels",
        "market": "hourly",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h9.vol_scaled_tsmom_hourly": {
        "id": "h9.vol_scaled_tsmom_hourly",
        "runner": "run_h9_intraday_tsmom_experiment.py",
        "func": "vol_scaled_tsmom_hourly",
        "market": "hourly",
        "dense": _h9_dense,
        "sparse": _h9_sparse,
        "expect": "clean",
    },
    "h9.apply_path_dependent_exits_hourly": {
        "id": "h9.apply_path_dependent_exits_hourly",
        "runner": "run_h9_intraday_tsmom_experiment.py",
        "func": "apply_path_dependent_exits_hourly",
        "market": "hourly",
        "dense": lambda m: (
            (_causal_target(m["prices"]), m["prices"], _exit_inputs(m["prices"])[0]),
            {"trailing_mult": 2.0, "max_hold_bars": 20, "vol_limit_mult": 2.0},
        ),
        "sparse": lambda m: (
            (_causal_target(m["prices"]), m["prices"], _exit_inputs(m["prices"])[0]),
            {"trailing_mult": 2.0, "max_hold_bars": 120, "vol_limit_mult": 2.0},
        ),
        "expect": "clean",
    },
    # ---------------- H10: the intraday signal / exit pipeline ----------- #
    "h10.smooth_signal": {
        "id": "h10.smooth_signal",
        "runner": "run_h10_intraday_tsmom_pfopt_experiment.py",
        "func": "smooth_signal",
        "market": "hourly_signal",
        "dense": lambda m: ((m["signal"],), {"span": 4}),
        "sparse": lambda m: ((m["signal"],), {"span": 16}),
        "expect": "clean",
    },
    "h10.regime_factor_hourly": {
        "id": "h10.regime_factor_hourly",
        "runner": "run_h10_intraday_tsmom_pfopt_experiment.py",
        "func": "regime_factor_hourly",
        "market": "hourly_signal",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h10.build_hourly_target": {
        "id": "h10.build_hourly_target",
        "runner": "run_h10_intraday_tsmom_pfopt_experiment.py",
        "func": "build_hourly_target",
        "market": "hourly_signal",
        "dense": lambda m: (
            (m["signal"],),
            {
                "smooth_span": 4,
                "vol_window_long": 40,
                "regime_scaling": False,
                "vix_hourly": m["vix"],
                "prices_index": m["index"],
            },
        ),
        "sparse": lambda m: (
            (m["signal"],),
            {
                "smooth_span": 16,
                "vol_window_long": 252,
                "regime_scaling": True,
                "vix_hourly": m["vix"],
                "prices_index": m["index"],
            },
        ),
        # KNOWN LOOK-AHEAD (H27/H28/H29): the daily collapse's value for day D
        # is expanded over day D itself.
        "expect": "lookahead",
    },
    "h10.apply_exits_hourly": {
        "id": "h10.apply_exits_hourly",
        "runner": "run_h10_intraday_tsmom_pfopt_experiment.py",
        "func": "apply_exits_hourly",
        "market": "hourly",
        "dense": lambda m: (
            (_causal_target(m["prices"]), m["prices"]) + _exit_inputs(m["prices"]),
            {"trailing_mult": 2.0, "max_hold_bars": 20, "vol_limit_mult": 2.0},
        ),
        "sparse": lambda m: (
            (_causal_target(m["prices"]), m["prices"]) + _exit_inputs(m["prices"]),
            {"trailing_mult": 2.0, "max_hold_bars": 120, "vol_limit_mult": 2.0},
        ),
        "expect": "clean",
    },
    # ---------------- H12: the selection-bias audit ---------------------- #
    "h12._build_exit_inputs": {
        "id": "h12._build_exit_inputs",
        "runner": "run_h12_selection_bias_audit.py",
        "func": "_build_exit_inputs",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    # ---------------- H16: cross-sectional factor timing ----------------- #
    "h16.regime_labels": {
        "id": "h16.regime_labels",
        "runner": "run_h16_factor_timing_experiment.py",
        "func": "regime_labels",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h16.regime_factor_series": {
        "id": "h16.regime_factor_series",
        "runner": "run_h16_factor_timing_experiment.py",
        "func": "regime_factor_series",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {"exposure": (1.0, 0.5, 0.25)}),
        "sparse": lambda m: ((m["vix"],), {"exposure": (1.0, 0.25, 0.10)}),
        "expect": "clean",
    },
    "h16.factor_momentum": {
        "id": "h16.factor_momentum",
        "runner": "run_h16_factor_timing_experiment.py",
        "func": "factor_momentum",
        "market": "daily",
        "dense": lambda m: ((m["prices"],), {"lookback": 20, "skip": 5}),
        "sparse": lambda m: ((m["prices"],), {"lookback": 252, "skip": 21}),
        "expect": "clean",
    },
    "h16.build_daily_targets": {
        "id": "h16.build_daily_targets",
        "runner": "run_h16_factor_timing_experiment.py",
        "func": "build_daily_targets",
        "market": "daily",
        "dense": lambda m: (
            (m["prices"], m["vix"]),
            {
                "lookback": 20,
                "skip": 5,
                "regime_exposure": (1.0, 0.5, 0.25),
                "n_factors": 1,
                "families": {"synthetic": ["S0", "S1", "S2"]},
            },
        ),
        "sparse": lambda m: (
            (m["prices"], m["vix"]),
            {
                "lookback": 252,
                "skip": 21,
                "regime_exposure": (1.0, 0.25, 0.10),
                "n_factors": 3,
                "families": {"synthetic": ["S0", "S1", "S2"]},
            },
        ),
        "expect": "clean",
    },
    "h16.monthly_rebalance": {
        "id": "h16.monthly_rebalance",
        "runner": "run_h16_factor_timing_experiment.py",
        "func": "monthly_rebalance",
        "market": "daily",
        "dense": lambda m: ((m["signal"],), {}),
        "sparse": lambda m: ((m["signal"],), {}),
        "expect": "clean",
    },
    # ---------------- H18: overnight / intraday decomposition ------------- #
    "h18.signal.lagged_1d_overnight_sign": {
        "id": "h18.signal.lagged_1d_overnight_sign",
        "runner": "run_h18_overnight_intraday_experiment.py",
        "func": "_overnight_intraday_signal",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (
                "lagged_1d_overnight_sign",
                "next_overnight",
                m["ohlc"]["close"],
                m["ohlc"]["open"],
                m["vix"],
            ),
            {},
        ),
        "sparse": lambda m: (
            (
                "lagged_1d_overnight_sign",
                "next_overnight",
                m["ohlc"]["close"],
                m["ohlc"]["open"],
                m["vix"],
            ),
            {},
        ),
        "scope": "close",
        "expect": "clean",
    },
    "h18.signal.prior_5d_return_sign": {
        "id": "h18.signal.prior_5d_return_sign",
        "runner": "run_h18_overnight_intraday_experiment.py",
        "func": "_overnight_intraday_signal",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (
                "prior_5d_return_sign",
                "next_intraday",
                m["ohlc"]["close"],
                m["ohlc"]["open"],
                m["vix"],
            ),
            {},
        ),
        "sparse": lambda m: (
            (
                "prior_5d_return_sign",
                "next_intraday",
                m["ohlc"]["close"],
                m["ohlc"]["open"],
                m["vix"],
            ),
            {},
        ),
        "scope": "close",
        "expect": "clean",
    },
    "h18.signal.vix_regime": {
        "id": "h18.signal.vix_regime",
        "runner": "run_h18_overnight_intraday_experiment.py",
        "func": "_overnight_intraday_signal",
        "market": "daily_ohlc",
        "dense": lambda m: (
            ("vix_regime", "next_overnight", m["ohlc"]["close"], m["ohlc"]["open"], m["vix"]),
            {},
        ),
        "sparse": lambda m: (
            ("vix_regime", "next_overnight", m["ohlc"]["close"], m["ohlc"]["open"], m["vix"]),
            {},
        ),
        "scope": "close",
        # KNOWN LOOK-AHEAD (new, H37): the pre-registration requires a
        # one-day lag, but the vix_regime predictor reads vix_close[t] and the
        # runner applies the signal to day t's own legs.
        "expect": "lookahead",
    },
    # ---------------- H19: volume-predictive equity timing --------------- #
    "h19.regime_labels": {
        "id": "h19.regime_labels",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "regime_labels",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h19.build_targets.simple_lagged.zero": {
        "id": "h19.build_targets.simple_lagged.zero",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "simple_lagged", "threshold_type": "zero", "lookback": 10},
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "simple_lagged", "threshold_type": "zero", "lookback": 21},
        ),
        "expect": "clean",
    },
    "h19.build_targets.vol_scaled.median": {
        "id": "h19.build_targets.vol_scaled.median",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "vol_scaled", "threshold_type": "median", "lookback": 10},
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "vol_scaled", "threshold_type": "median", "lookback": 21},
        ),
        "expect": "clean",
    },
    "h19.build_targets.price_volume_residual.adaptive": {
        "id": "h19.build_targets.price_volume_residual.adaptive",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "adaptive",
                "lookback": 10,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "adaptive",
                "lookback": 21,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "expect": "clean",
    },
    "h19.build_targets.simple_lagged.median": {
        "id": "h19.build_targets.simple_lagged.median",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "simple_lagged", "threshold_type": "median", "lookback": 10},
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "simple_lagged", "threshold_type": "median", "lookback": 21},
        ),
        "expect": "clean",
    },
    "h19.build_targets.simple_lagged.adaptive": {
        "id": "h19.build_targets.simple_lagged.adaptive",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "simple_lagged",
                "threshold_type": "adaptive",
                "lookback": 10,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "simple_lagged",
                "threshold_type": "adaptive",
                "lookback": 21,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "expect": "clean",
    },
    "h19.build_targets.vol_scaled.zero": {
        "id": "h19.build_targets.vol_scaled.zero",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "vol_scaled", "threshold_type": "zero", "lookback": 10},
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {"volume_decomp_method": "vol_scaled", "threshold_type": "zero", "lookback": 21},
        ),
        "expect": "clean",
    },
    "h19.build_targets.vol_scaled.adaptive": {
        "id": "h19.build_targets.vol_scaled.adaptive",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "vol_scaled",
                "threshold_type": "adaptive",
                "lookback": 10,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "vol_scaled",
                "threshold_type": "adaptive",
                "lookback": 21,
                "adaptive_z_threshold": 0.5,
            },
        ),
        "expect": "clean",
    },
    "h19.build_targets.price_volume_residual.zero": {
        "id": "h19.build_targets.price_volume_residual.zero",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "zero",
                "lookback": 10,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "zero",
                "lookback": 21,
            },
        ),
        "expect": "clean",
    },
    "h19.build_targets.price_volume_residual.median": {
        "id": "h19.build_targets.price_volume_residual.median",
        "runner": "run_h19_volume_predictive_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "median",
                "lookback": 10,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"]["close"], m["ohlc"]["volume"]),
            {
                "volume_decomp_method": "price_volume_residual",
                "threshold_type": "median",
                "lookback": 21,
            },
        ),
        "expect": "clean",
    },
    # ---------------- H20: signed volume / order flow --------------------- #
    "h20.regime_labels": {
        "id": "h20.regime_labels",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "regime_labels",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h20.sign_rule_direction.tick": {
        "id": "h20.sign_rule_direction.tick",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "sign_rule_direction",
        "market": "daily_ohlc",
        "dense": lambda m: ((m["ohlc"],), {"rule": "tick"}),
        "sparse": lambda m: ((m["ohlc"],), {"rule": "tick"}),
        "expect": "clean",
    },
    "h20.sign_rule_direction.lee_ready": {
        "id": "h20.sign_rule_direction.lee_ready",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "sign_rule_direction",
        "market": "daily_ohlc",
        "dense": lambda m: ((m["ohlc"],), {"rule": "lee_ready"}),
        "sparse": lambda m: ((m["ohlc"],), {"rule": "lee_ready"}),
        "expect": "clean",
    },
    "h20.build_targets.tick.lag1": {
        "id": "h20.build_targets.tick.lag1",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.10,
                "max_pos": 1.0,
                "imbalance_lag": 1,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.10,
                "max_pos": 1.0,
                "imbalance_lag": 1,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20.build_targets.lee_ready.lag5": {
        "id": "h20.build_targets.lee_ready.lag5",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.15,
                "max_pos": 0.5,
                "imbalance_lag": 5,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.15,
                "max_pos": 0.5,
                "imbalance_lag": 5,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20.build_targets.tick.lag3": {
        "id": "h20.build_targets.tick.lag3",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.05,
                "max_pos": 0.5,
                "imbalance_lag": 3,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.05,
                "max_pos": 0.5,
                "imbalance_lag": 3,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20.build_targets.tick.lag5": {
        "id": "h20.build_targets.tick.lag5",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.15,
                "max_pos": 1.0,
                "imbalance_lag": 5,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "tick",
                "target_vol": 0.15,
                "max_pos": 1.0,
                "imbalance_lag": 5,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20.build_targets.lee_ready.lag1": {
        "id": "h20.build_targets.lee_ready.lag1",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.10,
                "max_pos": 1.0,
                "imbalance_lag": 1,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.10,
                "max_pos": 1.0,
                "imbalance_lag": 1,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20.build_targets.lee_ready.lag3": {
        "id": "h20.build_targets.lee_ready.lag3",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "build_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.10,
                "max_pos": 0.5,
                "imbalance_lag": 3,
                "vol_window": 20,
            },
        ),
        "sparse": lambda m: (
            (m["ohlc"],),
            {
                "sign_rule": "lee_ready",
                "target_vol": 0.10,
                "max_pos": 0.5,
                "imbalance_lag": 3,
                "vol_window": 63,
            },
        ),
        "expect": "clean",
    },
    "h20._signed_volume_targets": {
        "id": "h20._signed_volume_targets",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "_signed_volume_targets",
        "market": "daily_ohlc",
        "dense": lambda m: (
            (
                m["ohlc"],
                importlib.import_module("run_h20_signed_volume_experiment").sign_rule_direction(
                    m["ohlc"], "tick"
                ),
            ),
            {"target_vol": 0.10, "max_pos": 1.0, "imbalance_lag": 3},
        ),
        "sparse": lambda m: (
            (
                m["ohlc"],
                importlib.import_module("run_h20_signed_volume_experiment").sign_rule_direction(
                    m["ohlc"], "tick"
                ),
            ),
            {"target_vol": 0.10, "max_pos": 1.0, "imbalance_lag": 3},
        ),
        "expect": "clean",
    },
    "h20._h19_simple_lagged_targets": {
        "id": "h20._h19_simple_lagged_targets",
        "runner": "run_h20_signed_volume_experiment.py",
        "func": "_h19_simple_lagged_targets",
        "market": "daily_ohlc",
        "dense": lambda m: ((m["ohlc"],), {}),
        "sparse": lambda m: ((m["ohlc"],), {}),
        "expect": "clean",
    },
    # ---------------- H23: the crypto copy of the H10 pipeline ------------ #
    "h23.smooth_signal": {
        "id": "h23.smooth_signal",
        "runner": "run_h23_crypto_futures_tsmom.py",
        "func": "smooth_signal",
        "market": "hourly_signal",
        "dense": lambda m: ((m["signal"],), {"span": 4}),
        "sparse": lambda m: ((m["signal"],), {"span": 16}),
        "expect": "clean",
    },
    "h23.regime_factor_hourly": {
        "id": "h23.regime_factor_hourly",
        "runner": "run_h23_crypto_futures_tsmom.py",
        "func": "regime_factor_hourly",
        "market": "hourly_signal",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    "h23.build_hourly_target": {
        "id": "h23.build_hourly_target",
        "runner": "run_h23_crypto_futures_tsmom.py",
        "func": "build_hourly_target",
        "market": "hourly_signal",
        "dense": lambda m: (
            (m["signal"],),
            {
                "smooth_span": 4,
                "vol_window_long": 40,
                "regime_scaling": False,
                "vix_hourly": m["vix"],
                "prices_index": m["index"],
            },
        ),
        "sparse": lambda m: (
            (m["signal"],),
            {
                "smooth_span": 16,
                "vol_window_long": 252,
                "regime_scaling": False,
                "vix_hourly": m["vix"],
                "prices_index": m["index"],
            },
        ),
        # KNOWN LOOK-AHEAD (H27/H28/H29): H23 inherits the daily collapse.
        "expect": "lookahead",
    },
    "h23.apply_exits_hourly": {
        "id": "h23.apply_exits_hourly",
        "runner": "run_h23_crypto_futures_tsmom.py",
        "func": "apply_exits_hourly",
        "market": "hourly",
        "dense": lambda m: (
            (_causal_target(m["prices"]), m["prices"]) + _exit_inputs(m["prices"]),
            {"trailing_mult": 2.0, "max_hold_bars": 20, "vol_limit_mult": 2.0},
        ),
        "sparse": lambda m: (
            (_causal_target(m["prices"]), m["prices"]) + _exit_inputs(m["prices"]),
            {"trailing_mult": 2.0, "max_hold_bars": 120, "vol_limit_mult": 2.0},
        ),
        "expect": "clean",
    },
    # ---------------- H27: the P&L level audit --------------------------- #
    "h27.engine_positions": {
        "id": "h27.engine_positions",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "engine_positions",
        "market": "hourly_signal",
        "dense": lambda m: ((m["signal"],), {}),
        "sparse": lambda m: ((m["signal"],), {}),
        "expect": "clean",
    },
    "h27.dollar_pnl": {
        "id": "h27.dollar_pnl",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "dollar_pnl",
        "market": "hourly",
        "dense": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "sparse": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "expect": "clean",
    },
    "h27.engine_gross_returns": {
        "id": "h27.engine_gross_returns",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "engine_gross_returns",
        "market": "hourly",
        "dense": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "sparse": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "expect": "clean",
    },
    "h27.engine_costs": {
        "id": "h27.engine_costs",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "engine_costs",
        "market": "hourly",
        "dense": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "sparse": lambda m: ((m["prices"], _causal_target(m["prices"])), {}),
        "expect": "clean",
    },
    "h27._atr": {
        "id": "h27._atr",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "_atr",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    "h27._vol_exit": {
        "id": "h27._vol_exit",
        "runner": "run_h27_pnl_level_audit.py",
        "func": "_vol_exit",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    # ---------------- H21 / H22 / H25: the multi-contract family ---------- #
    "h21._build_exit_inputs": {
        "id": "h21._build_exit_inputs",
        "runner": "run_h21_futures_tsmom_multicontract.py",
        "func": "_build_exit_inputs",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    "h22._build_exit_inputs": {
        "id": "h22._build_exit_inputs",
        "runner": "run_h22_futures_tsmom_voltarget.py",
        "func": "_build_exit_inputs",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    "h25._build_exit_inputs": {
        "id": "h25._build_exit_inputs",
        "runner": "run_h25_futures_tsmom_pfmargin.py",
        "func": "_build_exit_inputs",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "expect": "clean",
    },
    "h21._build_per_contract_base_signals": {
        "id": "h21._build_per_contract_base_signals",
        "runner": "run_h21_futures_tsmom_multicontract.py",
        "func": "_build_per_contract_base_signals",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "patch": {
            "module": "run_h21_futures_tsmom_multicontract.py",
            "attr": "SEL",
            "dense": _DENSE_SEL,
        },
        "expect": "clean",
    },
    "h22._build_per_contract_base_signals": {
        "id": "h22._build_per_contract_base_signals",
        "runner": "run_h22_futures_tsmom_voltarget.py",
        "func": "_build_per_contract_base_signals",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "patch": {
            "module": "run_h22_futures_tsmom_voltarget.py",
            "attr": "SEL",
            "dense": _DENSE_SEL,
        },
        "expect": "clean",
    },
    "h25._build_per_contract_base_signals": {
        "id": "h25._build_per_contract_base_signals",
        "runner": "run_h25_futures_tsmom_pfmargin.py",
        "func": "_build_per_contract_base_signals",
        "market": "hourly",
        "dense": lambda m: ((m["prices"],), {}),
        "sparse": lambda m: ((m["prices"],), {}),
        "patch": {
            "module": "run_h25_futures_tsmom_pfmargin.py",
            "attr": "SEL",
            "dense": _DENSE_SEL,
        },
        "expect": "clean",
    },
    # ---------------- TS momentum: H1 vol-scaled time-series momentum -------- #
    "ts_momentum.vol_scaled_tsmom_signals": {
        "id": "ts_momentum.vol_scaled_tsmom_signals",
        "runner": "run_ts_momentum_experiment.py",
        "func": "vol_scaled_tsmom_signals",
        "market": "daily",
        "dense": lambda m: ((m["prices"],), {"lookback": 10, "skip": 2}),
        "sparse": lambda m: ((m["prices"],), {"lookback": 252, "skip": 21}),
        "expect": "clean",
    },
    "ts_momentum.regime_labels": {
        "id": "ts_momentum.regime_labels",
        "runner": "run_ts_momentum_experiment.py",
        "func": "regime_labels",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
    # ---------------- CS momentum: cross-sectional vol-scaled TSMOM ---------- #
    "cs_momentum.cs_momentum_vol_scaled": {
        "id": "cs_momentum.cs_momentum_vol_scaled",
        "runner": "run_cs_momentum_experiment.py",
        "func": "cs_momentum_vol_scaled",
        "market": "daily",
        "dense": lambda m: ((m["prices"],), {"lookback": 10, "skip": 2, "long_only": True}),
        "sparse": lambda m: ((m["prices"],), {"lookback": 252, "skip": 21, "long_only": True}),
        "expect": "clean",
    },
    "cs_momentum.regime_labels": {
        "id": "cs_momentum.regime_labels",
        "runner": "run_cs_momentum_experiment.py",
        "func": "regime_labels",
        "market": "daily",
        "dense": lambda m: ((m["vix"],), {}),
        "sparse": lambda m: ((m["vix"],), {}),
        "expect": "clean",
    },
}


# NOTE: ``_apply_exits_and_aggregate`` (H21/H22/H25) is deliberately NOT probed:
# its output is a *sticky* state machine (the exit holds the size it entered
# with), so a positional probe of the position series cannot see the look-ahead
# that its input target carries.  The pin is the call graph instead -- see
# INHERITED_LOOKAHEAD.


def _probe_daily_collapse(collapse: Callable, signal: pd.DataFrame, lag_days: int) -> None:
    """The day-aligned probe for a *daily collapse*.

    The generic probe compares rows positionally, which a daily output does
    not support.  The collapse's contract is stated on its own grid instead:
    the value of day ``D`` must be decided by the signal at the last bar of
    day ``D`` (the published collapse) or at the last bar of day ``D-1`` (H27's
    causal collapse) -- and by no later bar.

    ``lag_days`` is 0 for the published collapse and 1 for the causal one.
    """
    index = signal.index
    day = index.normalize()
    last_bar = pd.Series(index, index=index).groupby(day).transform("last")
    base = collapse(signal)
    for label in base.index:
        label_day = pd.Timestamp(label).normalize()
        same_day = day == label_day
        if not same_day.any():
            continue
        if lag_days:
            earlier = day < label_day
            if not earlier.any():
                continue
            limit = last_bar[earlier].iloc[-1]
        else:
            limit = last_bar[same_day].iloc[-1]
        mask = np.asarray(index > limit)
        values = signal.to_numpy(dtype=float).copy()
        values[mask] *= 0.5
        perturbed = pd.DataFrame(values, index=index, columns=signal.columns)
        out = collapse(perturbed)
        assert np.array_equal(
            out.loc[label].to_numpy(dtype=float),
            base.loc[label].to_numpy(dtype=float),
            equal_nan=True,
        ), (
            f"the collapse changed the value of {label.date()} when only bars after "
            f"{pd.Timestamp(limit)} changed"
        )


# The functions that are probed with the day-aligned collapse probe rather
# than the generic positional one.
DAY_ALIGNED_PROBES = {
    ("run_h9_intraday_tsmom_experiment.py", "_daily_target_from_hourly"): 0,
    ("run_h27_pnl_level_audit.py", "causal_daily_target_from_hourly"): 1,
}


# --------------------------------------------------------------------------- #
# the inventory
# --------------------------------------------------------------------------- #
# Shared arguments for the functions that are not trading decisions.
_ARG_METRIC = (
    "Metric aggregation over a realised return series: it consumes the outcome "
    "of a finished backtest, it decides no position."
)
_ARG_GATE = (
    "Gate evaluation over a finished backtest result: it scores the outcome "
    "against the published thresholds, it decides no position."
)
_ARG_SPLIT = "Split helper: it partitions the sample by date, it decides no position."
_ARG_IO = "Artifact / cache I/O: it reads committed data, it decides no position."
_ARG_CONFIG = (
    "Configuration and plumbing: it sets constants or calls the engine on an "
    "already-built position series, it decides no position."
)
_ARG_AUDIT = (
    "Post-hoc audit of the committed artifacts: it measures the published "
    "record, it decides no position."
)
_ARG_DETECTOR = (
    "Look-ahead detector: it *measures* the information timing of a "
    "construction, it decides no position."
)

# coverage:
#   "probed"    -> a probe case exists and must find no violation
#   "lookahead" -> a known look-ahead; the probe must detect it
#   "static"    -> no dynamic probe applies; covered by the static checks
INVENTORY: dict[str, dict[str, tuple[str, str]]] = {
    "run_h9_intraday_tsmom_experiment.py": {
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill is causal.",
        ),
        "make_futures_config": ("static", _ARG_CONFIG),
        "vol_scaled_tsmom_hourly": (
            "probed",
            "Trailing momentum and trailing rolling volatility of the prices up to bar t; the "
            "portfolio-volatility term uses the lagged weights, so nothing after bar t is read.",
        ),
        "_daily_target_from_hourly": (
            "probed",
            "The daily value of day D is the signal at the last bar of day D; the pinned "
            "day-aligned probe shows it reads no bar after that one.",
        ),
        "apply_path_dependent_exits_hourly": (
            "probed",
            "The exit state machine reads price[t] and target[t] only; the high-water mark and "
            "the bar counter are past state.",
        ),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h10_intraday_tsmom_pfopt_experiment.py": {
        "smooth_signal": (
            "probed",
            "EWMA with adjust=False is a trailing recursion: the value at bar t uses bars <= t.",
        ),
        "regime_factor_hourly": (
            "probed",
            "VIX regime exposure factor from the forward-filled VIX series; ffill is causal.",
        ),
        "build_hourly_target": (
            "lookahead",
            "KNOWN LOOK-AHEAD (H27/H28/H29): the daily collapse's value for day D is expanded "
            "over day D itself, so the target at a bar of day D carries the signal computed at "
            "the *end* of day D. The published verdicts stand as published; H28's causal collapse "
            "is the repair.",
        ),
        "apply_exits_hourly": (
            "probed",
            "The exit state machine reads price[t], atr[t] and vol[t] only; the high-water mark, "
            "the bar counter and the last-trade bar are past state.",
        ),
        "_splits": ("static", _ARG_SPLIT),
        "_period_metrics": ("static", _ARG_METRIC),
        "_count_in": ("static", _ARG_METRIC),
        "_full_gate_eval": ("static", _ARG_GATE),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h12_selection_bias_audit.py": {
        "_expected_max_sharpe": ("static", _ARG_METRIC),
        "deflated_sharpe_ratio": ("static", _ARG_METRIC),
        "_moments": ("static", _ARG_METRIC),
        "_cscv_pbo_multi": ("static", _ARG_METRIC),
        "_rebuild_grid_oos": (
            "lookahead",
            "INHERITS the H10 collapse look-ahead: the OOS matrix is rebuilt with "
            "build_hourly_target, so it is the published (look-ahead) return stream. The "
            "inheritance is pinned by an executable call-graph check.",
        ),
        "_build_exit_inputs": (
            "probed",
            "Trailing rolling ATR and realised volatility of the prices up to bar t.",
        ),
        "_load_cached_data": ("static", _ARG_IO),
        "_selected_row": ("static", _ARG_IO),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h16_factor_timing_experiment.py": {
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill is causal.",
        ),
        "regime_factor_series": (
            "probed",
            "VIX regime exposure factor from the forward-filled VIX series; ffill is causal.",
        ),
        "factor_momentum": (
            "probed",
            "close[t-skip] / close[t-skip-lookback] - 1 with skip >= 1: both inputs are strictly "
            "before bar t.",
        ),
        "build_daily_targets": (
            "probed",
            "Cross-sectional selection over an already-lagged momentum plus the VIX regime "
            "factor; the rank is over the cross-section of bar t, never over time.",
        ),
        "monthly_rebalance": (
            "probed",
            "groupby(month).last() anchors each month's value on that month's last trading day "
            "and the value is in force from that bar onwards, so the hold lag is +1 bar (H29's "
            "CAUSAL verdict for the monthly families).",
        ),
        "make_equity_config": ("static", _ARG_CONFIG),
        "_splits": ("static", _ARG_SPLIT),
        "_period_metrics": ("static", _ARG_METRIC),
        "_count_in": ("static", _ARG_METRIC),
        "train_only_wf_sharpe": ("static", _ARG_METRIC),
        "full_gate_eval": ("static", _ARG_GATE),
        "perturbation_eval": ("static", _ARG_GATE),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h18_overnight_intraday_experiment.py": {
        "_overnight_intraday_signal": (
            "lookahead",
            "MIXED: the lagged_1d_overnight_sign and prior_5d_return_sign predictors are "
            "probed clean, but the pre-registered vix_regime predictor reads vix_close[t] while "
            "the runner applies the signal to day t's own legs -- the pre-registration requires "
            "a one-day lag ('at the prior day's close'). The published row is unaffected (the "
            "selected combo is prior_5d_return_sign_next_intraday) and the verdict is REJECT.",
        ),
        "_run_ablation": ("static", _ARG_AUDIT),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h19_volume_predictive_experiment.py": {
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill is causal.",
        ),
        "build_targets": (
            "probed",
            "Every rolling statistic is computed on the volume lagged by one bar; the signal at "
            "bar t compares today's volume (known at the close) with a threshold estimated from "
            "bars <= t-1.",
        ),
        "_splits": ("static", _ARG_SPLIT),
        "_count_in": ("static", _ARG_METRIC),
        "_period_metrics": ("static", _ARG_METRIC),
        "full_gate_eval": ("static", _ARG_GATE),
        "perturbation_eval": ("static", _ARG_GATE),
        "make_config": ("static", _ARG_CONFIG),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h20_signed_volume_experiment.py": {
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill is causal.",
        ),
        "sign_rule_direction": (
            "probed",
            "The trade direction of day t is a function of day t's own OHLC, which is known at "
            "the close of day t; the engine trades it with its one-bar delay.",
        ),
        "build_targets": (
            "probed",
            "The order-flow imbalance is a trailing rolling sum of signed volume and the "
            "realised volatility is lagged by one bar; the weight at bar t uses only data up to "
            "bar t.",
        ),
        "_splits": ("static", _ARG_SPLIT),
        "_count_in": ("static", _ARG_METRIC),
        "_period_metrics": ("static", _ARG_METRIC),
        "full_gate_eval": ("static", _ARG_GATE),
        "perturbation_eval": ("static", _ARG_GATE),
        "make_config": ("static", _ARG_CONFIG),
        "main": ("static", _ARG_CONFIG),
        "_signed_volume_targets": (
            "probed",
            "Same construction as build_targets with an explicit direction series: trailing "
            "rolling sum of signed volume, volatility lagged by one bar.",
        ),
        "_h19_simple_lagged_targets": (
            "probed",
            "H19's simple_lagged decomposition with a median threshold: the threshold is a "
            "trailing rolling median of the lagged unanticipated volume.",
        ),
    },
    "run_h21_futures_tsmom_multicontract.py": {
        "_build_data": ("static", _ARG_IO),
        "_build_exit_inputs": (
            "probed",
            "Trailing rolling ATR and realised volatility of the prices up to bar t.",
        ),
        "_build_per_contract_base_signals": (
            "probed",
            "Delegates to H9's vol_scaled_tsmom_hourly per contract, which is probed clean.",
        ),
        "_apply_exits_and_aggregate": (
            "lookahead",
            "INHERITS the H10 collapse look-ahead: the per-contract hourly targets are built "
            "with build_hourly_target, so the positions carry the end-of-day signal.",
        ),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h22_futures_tsmom_voltarget.py": {
        "_build_data": ("static", _ARG_IO),
        "_build_exit_inputs": (
            "probed",
            "Trailing rolling ATR and realised volatility of the prices up to bar t.",
        ),
        "_build_per_contract_base_signals": (
            "probed",
            "Delegates to H9's vol_scaled_tsmom_hourly per contract, which is probed clean.",
        ),
        "_apply_exits_and_aggregate": (
            "lookahead",
            "INHERITS the H10 collapse look-ahead: the per-contract hourly targets are built "
            "with build_hourly_target, so the positions carry the end-of-day signal.",
        ),
        "perturbation_eval": ("static", _ARG_GATE),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h23_crypto_futures_tsmom.py": {
        "smooth_signal": (
            "probed",
            "EWMA with adjust=False is a trailing recursion: the value at bar t uses bars <= t.",
        ),
        "regime_factor_hourly": (
            "probed",
            "VIX regime exposure factor from the forward-filled VIX series; ffill is causal.",
        ),
        "build_hourly_target": (
            "lookahead",
            "KNOWN LOOK-AHEAD (H27/H28/H29): H23 uses the same daily collapse as H10, so the "
            "target at a bar of day D carries the signal computed at the end of day D.",
        ),
        "apply_exits_hourly": (
            "probed",
            "The exit state machine reads price[t], atr[t] and vol[t] only; the high-water mark, "
            "the bar counter and the last-trade bar are past state.",
        ),
        "_splits": ("static", _ARG_SPLIT),
        "_period_metrics": ("static", _ARG_METRIC),
        "_count_in": ("static", _ARG_METRIC),
        "_full_gate_eval": ("static", _ARG_GATE),
        "perturbation_eval": ("static", _ARG_GATE),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h25_futures_tsmom_pfmargin.py": {
        "_build_data": ("static", _ARG_IO),
        "_build_exit_inputs": (
            "probed",
            "Trailing rolling ATR and realised volatility of the prices up to bar t.",
        ),
        "_build_per_contract_base_signals": (
            "probed",
            "Delegates to H9's vol_scaled_tsmom_hourly per contract, which is probed clean.",
        ),
        "_apply_exits_and_aggregate": (
            "lookahead",
            "INHERITS the H10 collapse look-ahead: the per-contract hourly targets are built "
            "with build_hourly_target, so the positions carry the end-of-day signal.",
        ),
        "perturbation_eval": ("static", _ARG_GATE),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h27_pnl_level_audit.py": {
        "make_cost_model": ("static", _ARG_CONFIG),
        "backtest_config": ("static", _ARG_CONFIG),
        "engine_positions": (
            "probed",
            "Leverage normalisation and per-name clipping of an already-built weight frame: a "
            "row-wise transform with no time dependence.",
        ),
        "dollar_pnl": (
            "probed",
            "Replicates the engine's contract arithmetic with the position lagged by one bar.",
        ),
        "engine_gross_returns": (
            "probed",
            "The engine's gross return series: positions.shift(1) * price returns.",
        ),
        "engine_costs": (
            "probed",
            "The engine's per-bar cost series: the cost of the weight change of bar t is "
            "charged at bar t.",
        ),
        "costs_from_trades": ("static", _ARG_METRIC),
        "causal_daily_target_from_hourly": (
            "probed",
            "H27's causal collapse: the value of day D is the signal at the last bar of day D-1; "
            "the pinned day-aligned probe shows it reads no bar after that one.",
        ),
        "causal_collapse": ("static", _ARG_CONFIG),
        "_atr": ("probed", "Trailing rolling ATR of the prices up to bar t."),
        "_vol_exit": ("probed", "Trailing rolling realised volatility of the prices up to bar t."),
        "rebuild_pipeline": ("static", _ARG_AUDIT),
        "contract_spec_check": ("static", _ARG_AUDIT),
        "expansion_check": ("static", _ARG_AUDIT),
        "artifact_lookahead": ("static", _ARG_AUDIT),
        "overnight_intraday_split": ("static", _ARG_AUDIT),
        "same_day_tilt": ("static", _ARG_AUDIT),
        "_window_metrics": ("static", _ARG_METRIC),
        "_vol_coherence": ("static", _ARG_METRIC),
        "audit_family": ("static", _ARG_AUDIT),
        "build_report": ("static", _ARG_AUDIT),
        "main": ("static", _ARG_CONFIG),
    },
    "run_h29_lookahead_sweep.py": {
        "art_dir_for": ("static", _ARG_IO),
        "read_parquet": ("static", _ARG_IO),
        "read_json": ("static", _ARG_IO),
        "_frame_max_abs_diff": ("static", _ARG_METRIC),
        "probe_collapse": (
            "static",
            "THE look-ahead detector: it measures the hold lag of a collapse construction. It "
            "is the negative control of the sweep, not a trading decision.",
        ),
        "probe_label_position": ("static", _ARG_DETECTOR),
        "source_sweep": ("static", _ARG_DETECTOR),
        "change_points": ("static", _ARG_DETECTOR),
        "predicted_change_points": ("static", _ARG_DETECTOR),
        "expansion_match_fractions": ("static", _ARG_DETECTOR),
        "classify": ("static", _ARG_DETECTOR),
        "rebuild_h1": ("static", _ARG_AUDIT),
        "rebuild_h2": ("static", _ARG_AUDIT),
        "rebuild_h3": ("static", _ARG_AUDIT),
        "rebuild_h4": ("static", _ARG_AUDIT),
        "rebuild_h5": ("static", _ARG_AUDIT),
        "rebuild_h6": ("static", _ARG_AUDIT),
        "rebuild_h7": ("static", _ARG_AUDIT),
        "rebuild_h8": ("static", _ARG_AUDIT),
        "audit_rebuild_family": ("static", _ARG_AUDIT),
        "audit_intraday_artifact": ("static", _ARG_AUDIT),
        "audit_inherited": ("static", _ARG_AUDIT),
        "audit_source_only": ("static", _ARG_AUDIT),
        "audit_family": ("static", _ARG_AUDIT),
        "negative_control": ("static", _ARG_DETECTOR),
        "h23_counterfactual": ("static", _ARG_AUDIT),
        "main": ("static", _ARG_CONFIG),
    },
    "run_ts_momentum_experiment.py": {
        "split_returns_by_date": ("static", _ARG_SPLIT),
        "make_config": ("static", _ARG_CONFIG),
        "resample_monthly_signals": (
            "static",
            "Resamples signals to month-end and forward-fills: each bar takes the last "
            "month-end close, which is known at that close, so the hold lag is +1 bar and "
            "no bar reads data after itself. The single resample collapse site is pinned "
            "in RESAMPLE_SITES.",
        ),
        "vol_scaled_tsmom_signals": (
            "probed",
            "Momentum is pct_change(lookback).shift(skip) with skip >= 1, so the direction "
            "at bar t uses prices up to bar t-skip (<= t). The vol-targeting scale is the "
            "portfolio vol estimated from returns up to bar t; nothing after bar t is read.",
        ),
        "evaluate_combo": (
            "static",
            "Builds the probed signal and runs the engine on an already-built position "
            "series; the decision logic itself is vol_scaled_tsmom_signals.",
        ),
        "selection_metric": ("static", _ARG_METRIC),
        "wf_oos_sharpes": ("static", _ARG_METRIC),
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill reads only past "
            "values, so the label at bar t uses VIX up to bar t.",
        ),
        "main": ("static", _ARG_CONFIG),
    },
    "run_cs_momentum_experiment.py": {
        "split_returns_by_date": ("static", _ARG_SPLIT),
        "make_config": ("static", _ARG_CONFIG),
        "resample_monthly_signals": (
            "static",
            "Resamples signals to month-end and forward-fills: each bar takes the last "
            "month-end close, which is known at that close, so the hold lag is +1 bar and "
            "no bar reads data after itself. The single resample collapse site is pinned "
            "in RESAMPLE_SITES.",
        ),
        "cs_momentum_vol_scaled": (
            "probed",
            "Direction is the sign of pct_change(lookback).shift(skip) with skip >= 1, so "
            "the signal at bar t uses prices up to bar t-skip (<= t). The vol-targeting "
            "scale uses portfolio vol estimated from returns up to bar t.",
        ),
        "regime_labels": (
            "probed",
            "VIX regime labels from the forward-filled VIX series; ffill reads only past "
            "values, so the label at bar t uses VIX up to bar t.",
        ),
        "wf_oos_sharpes": ("static", _ARG_METRIC),
        "main": ("static", _ARG_CONFIG),
    },
}

# The probe cases that belong to a *known look-ahead* (the detection is
# pinned: a "clean" outcome would mean the disclosure had been silently
# dropped or the defect silently repaired).
KNOWN_LOOKAHEAD_CASES = {
    case_id for case_id, case in CASES.items() if case["expect"] == "lookahead"
}

# The functions whose look-ahead is *inherited* from a known-leak constructor
# rather than probed directly (the call graph is pinned instead).
INHERITED_LOOKAHEAD = {
    ("run_h12_selection_bias_audit.py", "_rebuild_grid_oos"): "build_hourly_target",
    ("run_h21_futures_tsmom_multicontract.py", "_apply_exits_and_aggregate"): "build_hourly_target",
    ("run_h22_futures_tsmom_voltarget.py", "_apply_exits_and_aggregate"): "build_hourly_target",
    ("run_h25_futures_tsmom_pfmargin.py", "_apply_exits_and_aggregate"): "build_hourly_target",
}

# --------------------------------------------------------------------------- #
# the static look-ahead operator sweep
# --------------------------------------------------------------------------- #
# Every site that uses an operator which can read the future.  The inventory is
# pinned: a new site fails the suite.
BACKWARD_FILL_SITES = {
    ("run_h10_intraday_tsmom_pfopt_experiment.py", "main"): 1,
    ("run_h21_futures_tsmom_multicontract.py", "_build_data"): 1,
    ("run_h21_futures_tsmom_multicontract.py", "main"): 1,
    ("run_h22_futures_tsmom_voltarget.py", "_build_data"): 1,
    ("run_h22_futures_tsmom_voltarget.py", "main"): 1,
    ("run_h23_crypto_futures_tsmom.py", "main"): 1,
    ("run_h25_futures_tsmom_pfmargin.py", "_build_data"): 1,
    ("run_h25_futures_tsmom_pfmargin.py", "main"): 1,
}

RESAMPLE_SITES = {
    ("run_h9_intraday_tsmom_experiment.py", "_daily_target_from_hourly"): 1,
    ("run_h27_pnl_level_audit.py", "causal_daily_target_from_hourly"): 1,
    ("run_h27_pnl_level_audit.py", "expansion_check"): 1,
    ("run_h29_lookahead_sweep.py", "probe_collapse"): 1,
    ("run_ts_momentum_experiment.py", "resample_monthly_signals"): 1,
    ("run_cs_momentum_experiment.py", "resample_monthly_signals"): 1,
}


def _module_functions(path: pathlib.Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text())
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _enclosing_function(tree: ast.Module) -> dict[int, str]:
    """Map a line number to the name of the module-level function it is in."""
    mapping: dict[int, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                mapping[lineno] = node.name
    return mapping


def _is_negative(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return True
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value < 0
    return False


def _lookahead_operator_sites(tree: ast.Module) -> dict[str, list[str]]:
    """Every look-ahead-capable operator, by the function that contains it."""
    enclosing = _enclosing_function(tree)
    sites: dict[str, list[str]] = {}

    def record(lineno: int, kind: str) -> None:
        name = enclosing.get(lineno, "<module>")
        sites.setdefault(name, []).append(kind)

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        attr = node.func.attr
        if attr == "shift" and node.args and _is_negative(node.args[0]):
            record(node.lineno, "negative shift")
        if attr in {"pct_change", "diff"} and node.args and _is_negative(node.args[0]):
            record(node.lineno, "backward period")
        if attr == "bfill":
            record(node.lineno, "backward fill")
        if attr == "fillna":
            for arg in list(node.args) + [kw.value for kw in node.keywords if kw.arg == "method"]:
                if isinstance(arg, ast.Constant) and arg.value in {"bfill", "backfill"}:
                    record(node.lineno, "backward fill")
        if attr == "resample":
            record(node.lineno, "collapse")
        for kw in node.keywords:
            if kw.arg == "center" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                record(node.lineno, "centred window")
    return sites


def _called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                names.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                names.add(child.func.attr)
    return names


# --------------------------------------------------------------------------- #
# the tests
# --------------------------------------------------------------------------- #
class TestInventory:
    def test_in_scope_runners_exist(self):
        for runner in IN_SCOPE_RUNNERS:
            assert (ROOT / runner).exists(), f"missing runner {runner}"

    def test_the_named_runners_are_in_scope(self):
        for runner in NAMED_BY_HANDOFF:
            assert runner in IN_SCOPE_RUNNERS, f"{runner} is named by the handoff but not in scope"

    def test_every_function_of_every_runner_is_classified(self):
        """The pin: a new function in an in-scope runner must be classified."""
        for runner in IN_SCOPE_RUNNERS:
            functions = _module_functions(ROOT / runner)
            classified = set(INVENTORY.get(runner, {}))
            missing = sorted(set(functions) - classified)
            unknown = sorted(classified - set(functions))
            assert not missing, f"{runner} has unclassified functions: {missing}"
            assert not unknown, f"{runner} inventory names functions that do not exist: {unknown}"

    def test_inventory_entries_are_well_formed(self):
        for runner, entries in INVENTORY.items():
            for name, (coverage, argument) in entries.items():
                assert coverage in {"probed", "lookahead", "static"}, (
                    f"{runner}:{name} has an unknown coverage {coverage!r}"
                )
                assert len(argument.strip()) > 20, f"{runner}:{name} has no written argument"
                if coverage == "static":
                    assert (
                        argument
                        in {
                            _ARG_METRIC,
                            _ARG_GATE,
                            _ARG_SPLIT,
                            _ARG_IO,
                            _ARG_CONFIG,
                            _ARG_AUDIT,
                            _ARG_DETECTOR,
                        }
                        or len(argument) > 60
                    ), f"{runner}:{name} needs a specific written argument, not a generic one"

    def test_probed_functions_have_a_probe_case(self):
        for runner, entries in INVENTORY.items():
            for name, (coverage, _) in entries.items():
                if coverage != "probed":
                    continue
                has_case = any(
                    case["runner"] == runner and case["func"] == name for case in CASES.values()
                )
                has_day_aligned = (runner, name) in DAY_ALIGNED_PROBES
                assert has_case or has_day_aligned, (
                    f"{runner}:{name} is classified as probed but has no probe case"
                )

    def test_known_lookahead_functions_have_a_pinned_detection(self):
        """A known look-ahead must be pinned: either a probe that detects it, or
        a pinned call-graph inheritance."""
        for runner, entries in INVENTORY.items():
            for name, (coverage, _) in entries.items():
                if coverage != "lookahead":
                    continue
                probed = any(
                    case["runner"] == runner
                    and case["func"] == name
                    and case["expect"] == "lookahead"
                    for case in CASES.values()
                )
                inherited = (runner, name) in INHERITED_LOOKAHEAD
                assert probed or inherited, (
                    f"{runner}:{name} is a known look-ahead but nothing pins it"
                )

    def test_the_known_lookahead_case_set_is_pinned(self):
        """The set of detected look-aheads is a disclosure; it may not grow or
        shrink silently."""
        assert KNOWN_LOOKAHEAD_CASES == {
            "h10.build_hourly_target",
            "h18.signal.vix_regime",
            "h23.build_hourly_target",
        }


class TestStaticSweep:
    """The exhaustive, by-construction sweep of the runners' source."""

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_no_negative_shift_or_backward_period(self, runner):
        sites = _lookahead_operator_sites(ast.parse((ROOT / runner).read_text()))
        offenders = {
            name: kinds
            for name, kinds in sites.items()
            if any(k in kinds for k in ("negative shift", "backward period", "centred window"))
        }
        assert not offenders, f"{runner} contains a look-ahead operator: {offenders}"

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_the_backward_fill_sites_are_pinned(self, runner):
        sites = _lookahead_operator_sites(ast.parse((ROOT / runner).read_text()))
        found = {
            name: kinds.count("backward fill")
            for name, kinds in sites.items()
            if "backward fill" in kinds
        }
        expected = {
            name: count for (file, name), count in BACKWARD_FILL_SITES.items() if file == runner
        }
        assert found == expected, (
            f"{runner}: the backward-fill sites changed: {found} != {expected}"
        )

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_the_collapse_sites_are_pinned(self, runner):
        sites = _lookahead_operator_sites(ast.parse((ROOT / runner).read_text()))
        found = {
            name: kinds.count("collapse") for name, kinds in sites.items() if "collapse" in kinds
        }
        expected = {name: count for (file, name), count in RESAMPLE_SITES.items() if file == runner}
        assert found == expected, f"{runner}: the collapse sites changed: {found} != {expected}"

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_no_unpinned_lookahead_operator_in_a_classified_constructor(self, runner):
        """A function that decides a position may contain only the *pinned*
        look-ahead operators -- never a new one."""
        tree = ast.parse((ROOT / runner).read_text())
        sites = _lookahead_operator_sites(tree)
        for name, (coverage, _) in INVENTORY.get(runner, {}).items():
            if coverage == "static":
                continue
            found = sites.get(name, [])
            pinned: list[str] = []
            if (runner, name) in BACKWARD_FILL_SITES:
                pinned += ["backward fill"] * BACKWARD_FILL_SITES[(runner, name)]
            if (runner, name) in RESAMPLE_SITES:
                pinned += ["collapse"] * RESAMPLE_SITES[(runner, name)]
            assert sorted(found) == sorted(pinned), (
                f"{runner}:{name} decides a position but contains {found}; only the pinned "
                f"operators {pinned} are allowed there"
            )

    def test_the_backward_fill_can_only_fill_a_pre_inception_gap(self):
        """The written argument for the pinned backward fills.

        The runners align several contracts on one index with
        ``concat(...).ffill().bfill()``.  After the forward fill, the only
        remaining gaps are the *leading* ones -- the bars before a contract
        started trading -- and the backward fill replaces them with that
        contract's first observed price.  The fabricated segment is therefore
        flat: it contributes no return, and no real bar's price is altered.
        """
        index = _daily_index(60)
        early = _prices(index, 1, 1).rename(columns={"S0": "early"})
        # "late" starts 20 bars into the sample
        late = _prices(index, 1, 2).rename(columns={"S0": "late"}).iloc[20:]
        prices = pd.concat([early, late], axis=1).sort_index().ffill().bfill()
        assert prices["late"].isna().sum() == 0
        # the fabricated segment is flat -> it earns no return
        fabricated = prices["late"].iloc[:20]
        assert fabricated.nunique() == 1
        returns = prices["late"].pct_change().fillna(0.0)
        assert returns.iloc[:20].to_numpy() == pytest.approx(np.zeros(20))
        # and no bar at or after the contract's inception was altered
        assert prices["late"].iloc[20:].to_numpy() == pytest.approx(late["late"].to_numpy())

    def test_the_known_collapse_is_the_published_one(self):
        """The pinned collapse sites are the ones the published record names."""
        h9 = importlib.import_module("run_h9_intraday_tsmom_experiment")
        h27 = importlib.import_module("run_h27_pnl_level_audit")
        # H9's collapse: the value of day D is the signal at the last bar of D
        signal = pd.DataFrame(
            np.arange(len(_hourly_index(48)), dtype=float), index=_hourly_index(48)
        )
        collapsed = h9._daily_target_from_hourly(signal)
        assert collapsed.iloc[0, 0] == 23.0  # the last bar of the first day
        # H27's causal collapse: the value of day D is the signal at the last
        # bar of day D-1
        causal = h27.causal_daily_target_from_hourly(signal)
        assert np.isnan(causal.iloc[0, 0])
        assert causal.iloc[1, 0] == 23.0


def _apply_patch(case: dict, scope: str, monkeypatch) -> None:
    """Shorten the runner's frozen configuration for the dense sweep."""
    patch = case.get("patch")
    if not patch:
        return
    value = patch.get(scope)
    if value is None:
        return
    module = importlib.import_module(patch["module"][:-3])
    monkeypatch.setattr(module, patch["attr"], value)


class TestProbes:
    @pytest.mark.parametrize("case_id", sorted(CASES))
    def test_dense_sweep(self, case_id, monkeypatch):
        """Every bar of a reduced sample is a cut point."""
        case = CASES[case_id]
        _apply_patch(case, "dense", monkeypatch)
        market = _market(case["market"], DENSE_BARS, 11)
        scope = case.get("scope", "after")
        violations, changed = _probe(case, market, DENSE_CUTS, "dense", scope)
        if case["expect"] == "clean":
            assert not violations, (
                f"{case_id} is not point-in-time: the output at bars <= the cut changed when only "
                f"later data changed (cuts {violations[:5]})"
            )
        else:
            assert violations, (
                f"{case_id} is a known look-ahead but the probe did not detect it; the "
                "disclosure has been silently dropped or the defect silently repaired"
            )
            assert len(violations) >= 0.9 * len(DENSE_CUTS), (
                f"{case_id} was detected at only {len(violations)}/{len(DENSE_CUTS)} cut points; "
                "the detection is not systematic"
            )
        assert changed, f"{case_id} did not react to the perturbation, so the probe is vacuous"

    @pytest.mark.parametrize("case_id", sorted(CASES))
    def test_sparse_sweep(self, case_id, monkeypatch):
        """The lookbacks the runners actually use."""
        case = CASES[case_id]
        _apply_patch(case, "sparse", monkeypatch)
        market = _market(case["market"], N_BARS, 11)
        scope = case.get("scope", "after")
        violations, changed = _probe(case, market, SPARSE_CUTS, "sparse", scope)
        if case["expect"] == "clean":
            assert not violations, (
                f"{case_id} is not point-in-time at the runners' lookbacks (cuts {violations})"
            )
        else:
            assert violations, (
                f"{case_id} is a known look-ahead but the probe did not detect it at the "
                "runners' lookbacks"
            )
            assert len(violations) >= 0.9 * len(SPARSE_CUTS), (
                f"{case_id} was detected at only {len(violations)}/{len(SPARSE_CUTS)} cut points; "
                "the detection is not systematic"
            )
        assert changed, f"{case_id} did not react to the perturbation, so the probe is vacuous"

    def test_probe_detects_an_injected_look_ahead(self):
        """Negative control: the probe must reject a leaky signal."""
        case = {
            "id": "negative control",
            "market": "hourly",
            "call": lambda prices: (prices.pct_change().shift(-1) > 0).astype(float),
            "dense": lambda m: ((m["prices"],), {}),
            "sparse": lambda m: ((m["prices"],), {}),
        }
        market = _market("hourly", DENSE_BARS, 11)
        violations, _ = _probe(case, market, DENSE_CUTS, "dense", "after")
        assert violations, "the probe did not detect an injected look-ahead"

    def test_probe_detects_an_injected_backward_period(self):
        """A second negative control: a backward period reads the future too."""
        case = {
            "id": "negative control 2",
            "market": "hourly",
            "call": lambda prices: (prices.pct_change(-1) > 0).astype(float),
            "dense": lambda m: ((m["prices"],), {}),
            "sparse": lambda m: ((m["prices"],), {}),
        }
        market = _market("hourly", DENSE_BARS, 11)
        violations, _ = _probe(case, market, DENSE_CUTS, "dense", "after")
        assert violations, "the probe did not detect a backward period"


class TestDailyCollapse:
    """The daily collapse, probed on its own (daily) grid."""

    @pytest.mark.parametrize("key", sorted(DAY_ALIGNED_PROBES))
    def test_the_collapse_reads_only_its_decision_bar(self, key):
        runner, name = key
        lag_days = DAY_ALIGNED_PROBES[key]
        module = importlib.import_module(runner[:-3])
        collapse = getattr(module, name)
        index = _hourly_index(24 * 6)
        signal = pd.DataFrame(
            np.arange(len(index), dtype=float).reshape(-1, 1), index=index, columns=["S0"]
        )
        _probe_daily_collapse(collapse, signal, lag_days)

    def test_the_published_collapse_reads_the_last_bar_of_its_day(self):
        h9 = importlib.import_module("run_h9_intraday_tsmom_experiment")
        index = _hourly_index(24 * 3)
        signal = pd.DataFrame(
            np.arange(len(index), dtype=float).reshape(-1, 1), index=index, columns=["S0"]
        )
        collapsed = h9._daily_target_from_hourly(signal)
        assert collapsed.iloc[0, 0] == 23.0
        assert collapsed.iloc[1, 0] == 47.0

    def test_the_causal_collapse_reads_the_last_bar_of_the_previous_day(self):
        h27 = importlib.import_module("run_h27_pnl_level_audit")
        index = _hourly_index(24 * 3)
        signal = pd.DataFrame(
            np.arange(len(index), dtype=float).reshape(-1, 1), index=index, columns=["S0"]
        )
        causal = h27.causal_daily_target_from_hourly(signal)
        assert np.isnan(causal.iloc[0, 0])
        assert causal.iloc[1, 0] == 23.0
        assert causal.iloc[2, 0] == 47.0


class TestKnownLookAheads:
    """The published look-ahead of the intraday family, pinned from the code."""

    def test_the_daily_collapse_is_expanded_over_the_same_day(self):
        """H27/H28/H29: the published collapse positions every session with that
        session's own closing signal."""
        h10 = importlib.import_module("run_h10_intraday_tsmom_pfopt_experiment")
        index = _hourly_index(48)
        signal = pd.DataFrame(
            np.arange(len(index), dtype=float).reshape(-1, 1), index=index, columns=["S0"]
        )
        vix = pd.Series(20.0, index=index)
        target = h10.build_hourly_target(signal, None, 40, False, vix, index)
        # every bar of day 1 carries the value of the *last* bar of day 1
        day1 = target.loc["2024-01-01"]
        assert day1["S0"].nunique() == 1
        assert day1["S0"].iloc[0] == 23.0

    def test_the_causal_collapse_is_one_day_later(self):
        """H27's repair: the value of day D is the signal at the end of day D-1."""
        h27 = importlib.import_module("run_h27_pnl_level_audit")
        index = _hourly_index(48)
        signal = pd.DataFrame(
            np.arange(len(index), dtype=float).reshape(-1, 1), index=index, columns=["S0"]
        )
        causal = h27.causal_daily_target_from_hourly(signal)
        assert causal.loc["2024-01-02", "S0"] == 23.0

    def test_the_inheritance_of_the_lookahead_is_pinned(self):
        """H12's OOS rebuild inherits the look-ahead: the call graph is pinned."""
        for (runner, name), callee in INHERITED_LOOKAHEAD.items():
            functions = _module_functions(ROOT / runner)
            assert callee in _called_names(functions[name]), (
                f"{runner}:{name} no longer calls {callee}; the pinned inheritance is stale"
            )

    def test_h18_vix_predictor_lacks_the_preregistered_one_day_lag(self):
        """H37's finding: the vix_regime predictor reads vix_close[t] while the
        runner applies the signal to day t's own legs.

        The pre-registration requires a one-day lag ("Signal (causal, 1-day
        lag)"; "at the prior day's close"), and the two other predictors
        implement it with an explicit ``shift(1)``.
        """
        h18 = importlib.import_module("run_h18_overnight_intraday_experiment")
        index = _daily_index(40)
        close = pd.Series(np.linspace(100.0, 110.0, len(index)), index=index)
        open_ = close * 0.999
        vix = pd.Series(25.0, index=index)

        # the vix_regime predictor reacts to the VIX of the *same* day
        signal = h18._overnight_intraday_signal("vix_regime", "next_overnight", close, open_, vix)
        assert signal.iloc[0] == -1.0  # sideways -> long the intraday leg

        vix_bear = vix.copy()
        vix_bear.iloc[0] = 35.0  # only the first day's VIX changes
        signal_bear = h18._overnight_intraday_signal(
            "vix_regime", "next_overnight", close, open_, vix_bear
        )
        assert signal_bear.iloc[0] == 1.0, (
            "the vix_regime predictor no longer reacts to the same day's VIX close; the "
            "pinned H37 disclosure is stale"
        )

        # the lagged predictors do not react to the same day's observation
        lagged = h18._overnight_intraday_signal(
            "lagged_1d_overnight_sign", "next_overnight", close, open_, vix
        )
        lagged_bear = h18._overnight_intraday_signal(
            "lagged_1d_overnight_sign", "next_overnight", close, open_, vix_bear
        )
        assert lagged.equals(lagged_bear)

    def test_h18_applies_the_signal_to_the_same_day_legs(self):
        """The usage half of the H37 finding: the runner has no one-bar delay.

        The strategy return of day t is built from the signal of day t, so a
        predictor that reads day t's close decides the leg that day t's open
        already realised.
        """
        source = (ROOT / "run_h18_overnight_intraday_experiment.py").read_text()
        assert "position_overnight = (signal == 1).astype(float)" in source
        assert "overnight_ret = open_ / close.shift(1) - 1" in source
        assert (
            "strategy_ret = position_overnight * overnight_ret + position_intraday * intraday_ret"
            in source
        )

    def test_the_published_h18_row_does_not_use_the_leaky_predictor(self):
        """The disclosure is bounded: the published selection is a *causal* one.

        The look-ahead is in the ``vix_regime`` predictor only, and the
        published run selected on Val Sharpe.  The committed artifact shows
        that the selection was the causal ``prior_5d_return_sign`` combo, so
        the published numbers, the published verdict and the published gates
        are untouched by the finding.
        """
        import json

        artifact = ROOT / ".experiments" / "artifacts" / "exp_2026-10-13T22-14-50-729923Z"
        summary = json.loads((artifact / "summary.json").read_text())
        combos = {row["combo_name"]: row for row in summary["all_combo_results"]}
        assert len(combos) == 6

        selected = max(combos.values(), key=lambda row: row["val_sharpe"])
        assert selected["combo_name"] == "prior_5d_return_sign_next_intraday"

        # the leaky predictor's combos did not win the Val selection
        for name in ("vix_regime_next_overnight", "vix_regime_next_intraday"):
            assert combos[name]["val_sharpe"] < selected["val_sharpe"], (
                f"{name} now outranks the published selection; the H37 disclosure is stale"
            )
