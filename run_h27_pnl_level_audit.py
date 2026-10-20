"""H27: P&L **level** audit of the certified intraday family.

Pre-registered in ``HYPOTHESIS_SPEC.md`` §H27 (2026-10-19).  This is NOT a new
hypothesis and NOT a new selection: it is a post-hoc characterization of the
already-certified intraday results that asks two separate questions.

1. **Level.**  Is the *dollar* P&L implied by the committed artifacts consistent
   with the engine's contract arithmetic (``contracts = weight x capital /
   (price x multiplier)``, ``P&L = contracts x price change x multiplier``) and
   with the cost model?  A "yes" means there is no unit/scale error and the
   published Sharpe is not a factor-of-1000 slip.
2. **Information timing.**  Is the position that produced that P&L knowable at
   the time it was traded?

H26 deliberately did not attempt (2).  H27 measures it with a *causal
counterfactual*: every family's **selected** configuration is rebuilt from the
committed prices with the daily-target collapse replaced by a one-day-lagged
(causal) expansion, and re-run through the same engine.  No re-selection and no
grid re-run is performed, so the counterfactual is a lower bound on the defect,
never an improvement to a published number.

Method (frozen by the pre-registration):

  * L1  position-sizing consistency (dollar P&L vs. logged returns, 1e-9)
  * L2  contract-spec consistency (tick_value == tick_size x multiplier)
  * L3  cost-scale sanity (cost drag recomputed from ``trades.parquet``)
  * L4  vol-target coherence (target vs. realized, code scale vs. empirical scale)
  * L5a structural look-ahead proof from the committed artifacts alone
  * L5b causal counterfactual (selected config only)
  * L5c overnight / intraday P&L attribution + the same-day tilt fingerprint

No gate, threshold, verdict or certified number is changed by this audit.
"""

import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import run_h9_intraday_tsmom_experiment as h9
import run_h10_intraday_tsmom_pfopt_experiment as h10
import run_h21_futures_tsmom_multicontract as h21
import run_h22_futures_tsmom_voltarget as h22
import run_h25_futures_tsmom_pfmargin as h25
from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    VectorizedBacktester,
    run_backtest,
)
from qtr.validation.statistics import bars_per_year, sharpe_ratio

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / ".experiments" / "artifacts"
ART_DIR = ARTIFACTS / "h27_pnl_level"

HYPOTHESIS = "H27"

# --- frozen tolerances (pre-registration §H27) -------------------------------
LEVEL_TOL = 1e-9  # L1 / L3 absolute tolerance, in return units
LEVEL_FAIL_FRAC = 0.01  # "fails by more than 1%"
REPRODUCTION_TOL = 0.0  # L5b anchor: the rebuild must be bit-exact
LOOKAHEAD_STRUCT_FRAC = 0.99  # L5a: same-day expansion must match >= 99% of bars
LOOKAHEAD_SHARPE_DROP = 0.50  # L5b: > 50% relative OOS-Sharpe reduction

# --- engine constants (H9 make_futures_config) ------------------------------
INITIAL_CAPITAL = h9.INITIAL_CAPITAL
MAX_LEVERAGE = h9.MAX_LEVERAGE
MAX_POSITION_SIZE = h9.MAX_POSITION_SIZE
CODE_VOL_FACTOR = float(np.sqrt(252 * 6.5))  # the repo's own annualization

# --- audited families (frozen ids, pre-registration §H27) -------------------
FAMILIES = [
    {
        "family": "H9",
        "artifact": "exp_2026-10-11T16-52-38-694559Z",
        "published_verdict": "REJECT",
        "construction": "portfolio_h9",
        "target_vol": 0.15,
        "signal_artifact": "hourly_signal.parquet",
        "daily_artifact": "daily_target.parquet",
        "target_artifact": None,
        "target_artifact_reason": "H9 logs no expanded hourly target",
    },
    {
        "family": "H10",
        "artifact": "exp_2026-10-11T17-41-18-169363Z",
        "published_verdict": "PASS",
        "construction": "portfolio_h10",
        "target_vol": 0.15,
        "signal_artifact": "hourly_signal_h9.parquet",
        "daily_artifact": "daily_target_h9.parquet",
        "target_artifact": None,
        "target_artifact_reason": (
            "H10's logged hourly_target_selected is built from the 1008-bar "
            "signal while the logged daily_target_h9 collapses the 252-bar "
            "signal, so the two artifacts are not a matching pair"
        ),
    },
    {
        "family": "H21",
        "artifact": "exp_2026-10-13T23-27-52-101656Z",
        "published_verdict": "REJECT",
        "construction": "per_contract",
        "module": h21,
        "target_vol_mult": 0.5,
        "n_assets": 5,
        "signal_artifact": "hourly_signal_h10.parquet",
        "daily_artifact": "daily_target_h10.parquet",
        "target_artifact": "hourly_target_selected.parquet",
    },
    {
        "family": "H22",
        "artifact": "exp_2026-10-14T18-52-08-943792Z",
        "published_verdict": "PASS",
        "construction": "per_contract",
        "module": h22,
        "target_vol_mult": 1.0,
        "n_assets": 5,
        "signal_artifact": "hourly_signal_h10.parquet",
        "daily_artifact": "daily_target_h10.parquet",
        "target_artifact": "hourly_target_selected.parquet",
    },
    {
        "family": "H25",
        "artifact": "exp_2026-10-14T20-08-34-613690Z",
        "published_verdict": "PASS",
        "construction": "per_contract",
        "module": h25,
        "target_vol_mult": 1.75,
        "n_assets": 4,
        "signal_artifact": "hourly_signal_h10.parquet",
        "daily_artifact": "daily_target_h10.parquet",
        "target_artifact": "hourly_target_selected.parquet",
    },
]

# The certified family (the rows whose PASS is at stake).
CERTIFIED = ("H10", "H22", "H25")


# --------------------------------------------------------------------------- #
# engine replication helpers
# --------------------------------------------------------------------------- #
def make_cost_model() -> CostModel:
    """The H9 cost model (single source of truth for the contract specs)."""
    return CostModel(
        future_commission_per_contract=h9.COST_MODEL_DEFAULTS["future_commission_per_contract"],
        future_spread_ticks=h9.COST_MODEL_DEFAULTS["future_spread_ticks"],
        future_slippage_ticks=h9.COST_MODEL_DEFAULTS["future_slippage_ticks"],
        futures_specs=h9.FUTURES_SPECS,
    )


def backtest_config() -> BacktestConfig:
    """The H9 futures backtest configuration (capital, leverage, caps)."""
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.FUTURE,
        max_position_size=MAX_POSITION_SIZE,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
        cost_model=make_cost_model(),
    )


def engine_positions(raw: pd.DataFrame) -> pd.DataFrame:
    """Replicate the engine's signal normalization (leverage, then per-name cap).

    ``VectorizedBacktester.run`` normalizes gross leverage to ``max_leverage``
    and *then* clips each name to ``max_position_size``; the committed
    ``positions.parquet`` artifacts hold the **pre-normalization** weights, so
    the level audit has to apply the same two steps before comparing.
    """
    signals = raw.copy()
    gross = signals.abs().sum(axis=1)
    over = gross > MAX_LEVERAGE
    if over.any():
        signals.loc[over] = signals.loc[over].div(gross[over], axis=0) * MAX_LEVERAGE
    return signals.clip(-MAX_POSITION_SIZE, MAX_POSITION_SIZE)


def dollar_pnl(prices: pd.DataFrame, positions: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Per-bar dollar P&L from the engine's contract arithmetic.

    ``contracts = weight x capital / (price x multiplier)`` (held over the bar)
    and ``P&L = contracts x price change x multiplier``; the second return value
    is the same P&L expressed as a fraction of capital.
    """
    dollars = pd.Series(0.0, index=prices.index)
    for sym in prices.columns:
        mult = h9.FUTURES_SPECS[sym]["multiplier"]
        contracts = positions[sym].shift(1) * INITIAL_CAPITAL / (prices[sym].shift(1) * mult)
        price_change = (prices[sym] - prices[sym].shift(1)).fillna(0.0)
        dollars = dollars + contracts * price_change * mult
    return dollars, dollars / INITIAL_CAPITAL


def engine_gross_returns(prices: pd.DataFrame, positions: pd.DataFrame) -> pd.Series:
    """The engine's gross (pre-cost) portfolio return series."""
    price_returns = prices.pct_change().fillna(0)
    return (positions.shift(1) * price_returns).sum(axis=1)


def engine_costs(prices: pd.DataFrame, positions: pd.DataFrame) -> pd.Series:
    """The engine's per-bar transaction-cost series (fraction of capital)."""
    backtester = VectorizedBacktester(backtest_config())
    changes = positions.diff().fillna(positions.iloc[0])
    return backtester._calculate_costs(changes, prices, None, None)


def costs_from_trades(trades: pd.DataFrame) -> pd.Series:
    """Recompute the per-bar cost drag from the committed ``trades.parquet``.

    ``|dWeight| x capital / (price x multiplier)`` contracts are traded at
    ``price``; each costs ``cost_per_contract`` dollars; the result is expressed
    as a fraction of capital, exactly as the engine does.
    """
    if len(trades) == 0:
        return pd.Series(dtype=float)
    cm = make_cost_model()
    t = trades.copy()
    t["multiplier"] = t["symbol"].map(
        lambda s: h9.FUTURES_SPECS[s]["multiplier"] if s in h9.FUTURES_SPECS else np.nan
    )
    t["contracts"] = t["weight_change"].abs() * INITIAL_CAPITAL / (t["price"] * t["multiplier"])
    t["cost_per_contract"] = t["symbol"].map(cm.future_cost_per_contract)
    t["cost_frac"] = t["contracts"] * t["cost_per_contract"] / INITIAL_CAPITAL
    out = t.groupby("timestamp")["cost_frac"].sum()
    out.index = pd.to_datetime(out.index)
    return out


# --------------------------------------------------------------------------- #
# the causal counterfactual
# --------------------------------------------------------------------------- #
def causal_daily_target_from_hourly(hourly_signal: pd.DataFrame) -> pd.DataFrame:
    """Causal daily collapse: day D takes the signal at the last bar of day D-1.

    The published construction (``_daily_target_from_hourly``) takes the signal
    at the *last bar of day D* and expands it over day D, i.e. every bar of day D
    is positioned with information from the end of day D.  This variant lags the
    daily series by one calendar day, which is the "decide at the close, hold
    into the next session" reading of the documented intent.
    """
    daily = hourly_signal.resample("1D").last()
    calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="1D")
    if len(calendar) != len(daily):
        raise ValueError(
            f"calendar gap in the daily collapse: {len(daily)} labels vs "
            f"{len(calendar)} calendar days"
        )
    daily = daily.reindex(calendar).ffill()
    return daily.shift(1)


@contextmanager
def causal_collapse():
    """Temporarily install the causal daily collapse in the runner modules.

    ``build_hourly_target`` (H10) and ``apply_path_dependent_exits_hourly`` (H9)
    both call the module-global ``_daily_target_from_hourly``; patching the
    module attribute is therefore the *minimal* intervention -- every other
    stage of the pipeline is untouched.  The originals are restored on exit.
    """
    originals = {h9: h9._daily_target_from_hourly, h10: h10._daily_target_from_hourly}
    try:
        h9._daily_target_from_hourly = causal_daily_target_from_hourly
        h10._daily_target_from_hourly = causal_daily_target_from_hourly
        yield
    finally:
        for module, fn in originals.items():
            module._daily_target_from_hourly = fn


def _atr(prices: pd.DataFrame) -> pd.DataFrame:
    atr = prices * prices.pct_change().rolling(14, min_periods=7).std()
    return atr.replace(0, np.nan).ffill().fillna(prices * 0.001)


def _vol_exit(prices: pd.DataFrame) -> pd.DataFrame:
    vol = prices.pct_change().fillna(0).rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    return vol.replace(0, np.nan).ffill()


def rebuild_pipeline(
    spec: dict, prices: pd.DataFrame, volumes: pd.DataFrame, vix: pd.Series
) -> dict:
    """Rebuild a family's *selected* configuration from the committed prices.

    Returns the hourly signal, the *effective* hourly target that feeds the exit
    state machine, and the resulting positions.  The as-published rebuild is
    validated against the committed ``positions.parquet`` (bit-exact) before it
    is used as the counterfactual baseline.
    """
    construction = spec["construction"]
    if construction == "portfolio_h9":
        base = h9.vol_scaled_tsmom_hourly(prices)
        daily_target = h9._daily_target_from_hourly(base)
        # H9's exit function expands the day-labelled target onto the hourly
        # grid itself; that expansion is the effective target.
        target = daily_target.reindex(prices.index, method="ffill").fillna(0.0)
        positions = h9.apply_path_dependent_exits_hourly(daily_target, prices, _atr(prices))
        return {"signal": base, "target": target, "positions": positions}
    if construction == "portfolio_h10":
        base = h9.vol_scaled_tsmom_hourly(prices, vol_window_long=1008, vol_window_short=252)
        target = h10.build_hourly_target(base, None, 1008, False, vix, prices.index)
        positions = h10.apply_exits_hourly(
            target,
            prices,
            _atr(prices),
            _vol_exit(prices),
            trailing_mult=2.0,
            max_hold_bars=60,
            vol_limit_mult=1.5,
            vol_floor_fraction=0.25,
            target_vol=0.15,
            min_trade_interval=0,
        )
        return {"signal": base, "target": target, "positions": positions}
    if construction == "per_contract":
        module = spec["module"]
        base = {
            sym: h9.vol_scaled_tsmom_hourly(
                prices[[sym]], vol_window_long=1008, vol_window_short=252
            )
            for sym in prices.columns
        }
        targets = {
            sym: h10.build_hourly_target(base[sym], None, 1008, False, vix, prices.index)[sym]
            for sym in prices.columns
        }
        per_contract, _, _ = module._apply_exits_and_aggregate(
            prices,
            volumes,
            vix,
            _atr(prices),
            _vol_exit(prices),
            base,
            spec["target_vol_mult"],
            0.5,
            "equal",
            spec["n_assets"],
            min_trade_interval=0,
        )
        return {
            "signal": pd.DataFrame(
                {sym: base[sym].iloc[:, 0] for sym in prices.columns},
                index=prices.index,
            ),
            "target": pd.DataFrame(targets, index=prices.index),
            "positions": per_contract,
        }
    raise ValueError(f"unknown construction: {construction}")


# --------------------------------------------------------------------------- #
# measurements
# --------------------------------------------------------------------------- #
def contract_spec_check() -> dict:
    """L2: tick_value == tick_size x multiplier, and the per-contract cost."""
    cm = make_cost_model()
    rows = {}
    for sym, spec in h9.FUTURES_SPECS.items():
        tick_size = spec["tick_size"]
        mult = spec["multiplier"]
        implied_tick_value = tick_size * mult
        rows[sym] = {
            "multiplier": float(mult),
            "tick_size": float(tick_size),
            "tick_value": float(spec["tick_value"]),
            "implied_tick_value": float(implied_tick_value),
            "tick_value_consistent": bool(abs(implied_tick_value - spec["tick_value"]) <= 1e-12),
            "commission": float(spec["commission"]),
            "spread_ticks": float(spec["spread_ticks"]),
            "slippage_ticks": float(spec["slippage_ticks"]),
            "cost_per_contract": float(cm.future_cost_per_contract(sym)),
            "expected_cost_per_contract": float(
                spec["commission"]
                + (spec["spread_ticks"] + spec["slippage_ticks"]) * spec["tick_value"]
            ),
        }
    return {
        "per_symbol": rows,
        "all_tick_values_consistent": bool(all(r["tick_value_consistent"] for r in rows.values())),
        "all_costs_consistent": bool(
            all(
                abs(r["cost_per_contract"] - r["expected_cost_per_contract"]) <= 1e-12
                for r in rows.values()
            )
        ),
    }


def expansion_check(signal: pd.DataFrame, target: pd.DataFrame, index: pd.DatetimeIndex) -> dict:
    """Compare a published hourly target with the two candidate expansions.

    The daily collapse ``L`` holds, for each day D, the signal at the **last
    bar of D**.  Expanding it onto the hourly grid gives two candidates:

    * ``same_day``  -- every bar of day D takes ``L[D]``  (the signal at D's
      own close): the published construction, and a look-ahead for the bars of
      D that precede that close;
    * ``prev_day``  -- every bar of day D takes ``L[D-1]`` (the signal at the
      previous close): the causal construction.
    """
    daily = signal.resample("1D").last()
    calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="1D")
    complete = bool(len(calendar) == len(daily))
    daily = daily.reindex(calendar).ffill()
    same = daily.reindex(index, method="ffill")
    prev = daily.shift(1).reindex(index, method="ffill")

    per_symbol = {}
    for sym in signal.columns:
        t = target[sym].reindex(index).to_numpy(dtype=float)
        s = same[sym].reindex(index).to_numpy(dtype=float)
        p = prev[sym].reindex(index).to_numpy(dtype=float)
        ok = np.isfinite(t) & np.isfinite(s) & np.isfinite(p)
        per_symbol[sym] = {
            "same_day_match_fraction": float(np.mean(np.abs(t[ok] - s[ok]) <= 1e-12)),
            "prev_day_match_fraction": float(np.mean(np.abs(t[ok] - p[ok]) <= 1e-12)),
        }
    return {
        "per_symbol": per_symbol,
        "same_day_match_fraction": float(
            np.mean([v["same_day_match_fraction"] for v in per_symbol.values()])
        ),
        "prev_day_match_fraction": float(
            np.mean([v["prev_day_match_fraction"] for v in per_symbol.values()])
        ),
        "calendar_complete": complete,
        "n_daily_labels": len(daily),
    }


def artifact_lookahead(spec: dict, art_dir: Path, index: pd.DatetimeIndex) -> dict:
    """L5a (artifact-only): the look-ahead proved from the committed artifacts.

    The chain, using nothing but committed artifacts:

    1. the logged daily collapse holds the signal at the **last bar of day D**;
    2. expanding that day-labelled series onto the hourly grid puts ``L[D]`` on
       the **first bar of day D** -- i.e. the session is positioned with that
       session's own closing signal.

    Where the family also logs the expanded hourly target built from the *same*
    signal, the expansion is compared against it directly.
    """
    out = {"available": False}
    signal_name = spec["signal_artifact"]
    daily_name = spec["daily_artifact"]
    target_name = spec.get("target_artifact")
    signal_path = art_dir / signal_name
    daily_path = art_dir / daily_name
    if not signal_path.exists() or not daily_path.exists():
        out["reason"] = f"missing {signal_name} / {daily_name}"
        return out

    signal = pd.read_parquet(signal_path)
    daily = pd.read_parquet(daily_path)
    signal = signal.iloc[:, 0]
    daily = daily.iloc[:, 0]

    day = index.normalize()
    is_first = pd.Series(index, index=index).groupby(day).transform("first") == index
    is_last = pd.Series(index, index=index).groupby(day).transform("last") == index

    signal_at_close = signal.reindex(index).where(is_last)
    signal_at_open = signal.reindex(index).where(is_first)
    daily_on_grid = daily.reindex(index, method="ffill")

    close_chain = float(np.nanmax(np.abs(signal_at_close.to_numpy() - daily_on_grid.to_numpy())))
    open_chain = float(np.nanmax(np.abs(signal_at_open.to_numpy() - daily_on_grid.to_numpy())))
    same_day = daily.reindex(index, method="ffill").to_numpy()
    prev_day = daily.shift(1).reindex(index, method="ffill").to_numpy()
    finite = np.isfinite(same_day) & np.isfinite(prev_day)
    bite = float(np.mean(np.abs(same_day[finite] - prev_day[finite]) > 1e-12))

    out = {
        "available": True,
        "signal_artifact": signal_name,
        "daily_artifact": daily_name,
        "max_abs_diff_signal_at_day_close_vs_daily_collapse": close_chain,
        "max_abs_diff_signal_at_day_open_vs_daily_collapse": open_chain,
        "fraction_bars_where_same_day_differs_from_prev_day": bite,
    }

    if target_name and (art_dir / target_name).exists():
        target = pd.read_parquet(art_dir / target_name).iloc[:, 0]
        tv = target.reindex(index, method="ffill").to_numpy()
        ok = np.isfinite(tv) & np.isfinite(same_day) & np.isfinite(prev_day)
        out["target_artifact"] = target_name
        out["target_same_day_match_fraction"] = float(
            np.mean(np.abs(tv[ok] - same_day[ok]) <= 1e-12)
        )
        out["target_prev_day_match_fraction"] = float(
            np.mean(np.abs(tv[ok] - prev_day[ok]) <= 1e-12)
        )
    else:
        out["target_artifact"] = None
        out["target_artifact_reason"] = spec.get("target_artifact_reason", "")
    return out


def overnight_intraday_split(prices: pd.DataFrame, positions: pd.DataFrame) -> dict:
    """L5c: split the gross P&L into its overnight and intraday components.

    Uses the engine's own per-bar chain (``w[t-1] * r[t]`` summed over symbols),
    so it is the ground truth of what the backtest earned.  The **overnight**
    component is the first bar of each session (previous close -> session open);
    everything else is **intraday** (the open -> close part of the session).
    """
    weight = positions.shift(1)
    contribution = (weight * prices.pct_change().fillna(0)).sum(axis=1)
    index = prices.index
    day = index.normalize()
    is_first = pd.Series(index, index=index).groupby(day).transform("first") == index
    overnight = float(contribution[is_first].sum())
    intraday = float(contribution[~is_first].sum())
    total = overnight + intraday
    return {
        "total_overnight_pnl": overnight,
        "total_intraday_pnl": intraday,
        "total_pnl": total,
        "intraday_share": float(intraday / total) if abs(total) > 0 else float("nan"),
    }


def same_day_tilt(prices: pd.DataFrame, positions: pd.DataFrame) -> dict:
    """L5c: the model-free fingerprint of a same-day look-ahead.

    If the position held at a session's open is aligned with **that** session's
    actual move, the strategy is trading on information it could not have had at
    the open.  The statistic is the mean of ``sign(w_open) * r_intraday`` over
    the sessions in which the strategy is positioned, plus the hit rate.
    """
    index = prices.index
    day = index.normalize()
    rows = {}
    for sym in prices.columns:
        px = prices[sym]
        open_px = px.groupby(day).first()
        close_px = px.groupby(day).last()
        intraday_ret = close_px / open_px - 1.0
        w_open = positions[sym].groupby(day).first()
        frame = pd.DataFrame({"w": w_open, "r": intraday_ret}).dropna()
        frame = frame[frame["w"] != 0.0]
        if len(frame) < 20:
            continue
        sign = np.sign(frame["w"].to_numpy())
        ret = frame["r"].to_numpy()
        rows[sym] = {
            "n_sessions": len(frame),
            "mean_signed_intraday_return": float(np.mean(sign * ret)),
            "mean_abs_intraday_return": float(np.mean(np.abs(ret))),
            "same_day_hit_rate": float(np.mean(sign * ret > 0)),
        }
    if not rows:
        return {"per_symbol": {}}
    return {
        "per_symbol": rows,
        "mean_signed_intraday_return": float(
            np.mean([r["mean_signed_intraday_return"] for r in rows.values()])
        ),
        "mean_same_day_hit_rate": float(np.mean([r["same_day_hit_rate"] for r in rows.values()])),
    }


def _window_metrics(returns: pd.Series, mask, prices: pd.DataFrame) -> dict:
    ret = returns[mask].dropna()
    cum = (1.0 + ret).cumprod()
    gp = float(ret[ret > 0].sum())
    gl = float(abs(ret[ret < 0].sum()))
    return {
        "n_bars": len(ret),
        "sharpe": float(sharpe_ratio(ret.values)) if len(ret) > 1 else 0.0,
        "profit_factor": gp / gl if gl > 0 else float("inf"),
        "max_drawdown": float((cum / cum.cummax() - 1.0).min()) if len(cum) else 0.0,
        "equity_multiple": float((1.0 + ret).prod()),
        "mean_bar_return": float(ret.mean()) if len(ret) else 0.0,
        "std_bar_return": float(ret.std(ddof=0)) if len(ret) else 0.0,
    }


def _vol_coherence(returns: pd.Series, index: pd.DatetimeIndex, target_vol: float) -> dict:
    """L4: target vs. realized vol/return on the code scale and the empirical scale."""
    bpy = float(bars_per_year(index))
    empirical_factor = float(np.sqrt(bpy)) if np.isfinite(bpy) else float("nan")
    mean = float(returns.mean())
    std = float(returns.std(ddof=0))
    realized_vol_code = std * CODE_VOL_FACTOR
    realized_ret_code = mean * (252 * 6.5)
    return {
        "target_vol_annualized": float(target_vol),
        "target_applied_to": "hourly returns, scaled by sqrt(252 * 6.5)",
        "code_annualization_factor": CODE_VOL_FACTOR,
        "code_bars_per_year": float(252 * 6.5),
        "empirical_bars_per_year": bpy,
        "empirical_annualization_factor": empirical_factor,
        "annualization_ratio_empirical_over_code": float(empirical_factor / CODE_VOL_FACTOR),
        "realized_vol_code_scale": float(realized_vol_code),
        "realized_vol_empirical_scale": float(std * empirical_factor),
        "realized_return_code_scale": float(realized_ret_code),
        "realized_return_empirical_scale": float(mean * bpy),
        "realized_vol_over_target_code_scale": float(
            realized_vol_code / target_vol if target_vol else float("nan")
        ),
        "same_quantity_as_pnl": True,
        "note": (
            "The vol target is applied to the same hourly-return quantity the "
            "P&L is built from, so the target and the realized figure are "
            "internally consistent. The code annualizes hourly bars with "
            "sqrt(252 * 6.5) while the artifact's own bar index implies "
            "sqrt(bars_per_year); the ratio is reported above."
        ),
    }


def audit_family(spec: dict) -> dict:
    """Audit one frozen artifact end to end."""
    art_dir = ARTIFACTS / spec["artifact"]
    prices = pd.read_parquet(art_dir / "prices.parquet")
    raw_positions = pd.read_parquet(art_dir / "positions.parquet")
    logged_returns = pd.read_parquet(art_dir / "returns.parquet")["returns"].astype(float)
    trades = pd.read_parquet(art_dir / "trades.parquet")
    with open(art_dir / "summary.json") as f:
        summary = json.load(f)
    volumes = pd.read_parquet(art_dir / "volumes.parquet")
    vix_path = art_dir / "vix_hourly.parquet"
    vix = pd.read_parquet(vix_path).iloc[:, 0] if vix_path.exists() else pd.Series(0.0)

    positions = engine_positions(raw_positions)
    gross = engine_gross_returns(prices, positions)
    costs = engine_costs(prices, positions)
    net = gross - costs

    # --- L1: position-sizing consistency -----------------------------------
    _dollars, pnl_fraction = dollar_pnl(prices, positions)
    gross_diff = (pnl_fraction - gross).abs()
    net_diff = (net - logged_returns).abs()
    l1_dollar_vs_gross = float(gross_diff.max())
    l1_dollar_vs_logged = float(net_diff.max())
    n_total = len(prices.index)
    n_compared = int(gross_diff.notna().sum())
    price_nan_bars = int(prices.isna().any(axis=1).sum())
    l1 = {
        "dollar_pnl_matches_engine_gross_max_abs_diff": l1_dollar_vs_gross,
        "recomputed_net_matches_logged_returns_max_abs_diff": l1_dollar_vs_logged,
        "n_bars_total": n_total,
        "n_bars_compared": n_compared,
        "coverage_fraction": float(n_compared / n_total) if n_total else float("nan"),
        "n_bars_non_finite": n_total - n_compared,
        "n_bars_with_nan_price": price_nan_bars,
        "non_finite_note": (
            "the first bar has no previous price (the contract count is a "
            "lagged quantity); any further non-finite bars come from NaN "
            "prices in the committed artifact"
        ),
        "passes": bool(l1_dollar_vs_gross <= LEVEL_TOL and l1_dollar_vs_logged <= LEVEL_TOL),
    }

    # --- L3: cost-scale sanity ---------------------------------------------
    costs_from_tr = costs_from_trades(trades)
    aligned_costs = costs_from_tr.reindex(prices.index).fillna(0.0)
    l3_diff = float((aligned_costs - costs).abs().max())
    l3 = {
        "cost_from_trades_matches_engine_max_abs_diff": l3_diff,
        "n_trades": len(trades),
        "mean_cost_per_bar": float(costs.mean()),
        "mean_gross_return_per_bar": float(gross.mean()),
        "cost_share_of_gross_edge": float(costs.mean() / gross.mean())
        if gross.mean() != 0
        else float("nan"),
        "passes": bool(l3_diff <= LEVEL_TOL),
    }

    # --- L4: vol-target coherence ------------------------------------------
    _train_mask, val_mask, test_mask = h10._splits(prices)
    oos_mask = val_mask | test_mask
    target_vol = 0.15 * float(spec.get("target_vol_mult", 1.0))
    l4 = _vol_coherence(logged_returns[oos_mask], logged_returns[oos_mask].index, target_vol)
    l4["oos_vol_target_multiplier"] = float(spec.get("target_vol_mult", 1.0))

    # --- L5a: look-ahead, artifact-only and rebuild-based -------------------
    l5a_artifact = artifact_lookahead(spec, art_dir, prices.index)
    published_pipeline = rebuild_pipeline(spec, prices, volumes, vix)
    published_positions = published_pipeline["positions"]
    l5a_rebuild = expansion_check(
        published_pipeline["signal"], published_pipeline["target"], prices.index
    )
    l5a = {
        "artifact_only": l5a_artifact,
        "rebuild": l5a_rebuild,
        "same_day_match_fraction": l5a_rebuild["same_day_match_fraction"],
        "prev_day_match_fraction": l5a_rebuild["prev_day_match_fraction"],
    }

    # --- L5b: causal counterfactual ----------------------------------------
    with causal_collapse():
        causal_pipeline = rebuild_pipeline(spec, prices, volumes, vix)
    causal_positions = causal_pipeline["positions"]
    causal_result = run_backtest(
        prices=prices,
        signals=causal_positions,
        volumes=volumes,
        config=backtest_config(),
    )
    published_result = run_backtest(
        prices=prices,
        signals=published_positions,
        volumes=volumes,
        config=backtest_config(),
    )

    pos_diff = float(np.abs(published_positions.to_numpy() - raw_positions.to_numpy()).max())
    ret_diff = float(np.abs(published_result.returns.to_numpy() - logged_returns.to_numpy()).max())
    reproduced = bool(pos_diff <= REPRODUCTION_TOL and ret_diff <= REPRODUCTION_TOL)

    l5b = {
        "rebuild_positions_max_abs_diff": pos_diff,
        "rebuild_returns_max_abs_diff": ret_diff,
        "reproduced_bit_exact": reproduced,
        "published_oos": _window_metrics(published_result.returns, oos_mask, prices),
        "causal_oos": _window_metrics(causal_result.returns, oos_mask, prices),
        "published_full_sample": _window_metrics(
            published_result.returns, pd.Series(True, index=prices.index), prices
        ),
        "causal_full_sample": _window_metrics(
            causal_result.returns, pd.Series(True, index=prices.index), prices
        ),
    }
    l5b["oos_sharpe_relative_drop"] = (
        float(1.0 - l5b["causal_oos"]["sharpe"] / l5b["published_oos"]["sharpe"])
        if l5b["published_oos"]["sharpe"]
        else float("nan")
    )
    l5b["oos_pf_relative_drop"] = (
        float(1.0 - l5b["causal_oos"]["profit_factor"] / l5b["published_oos"]["profit_factor"])
        if l5b["published_oos"]["profit_factor"]
        else float("nan")
    )

    # --- L5c: overnight / intraday attribution -----------------------------
    causal_engine_positions = engine_positions(causal_positions)
    l5c_published = overnight_intraday_split(prices, positions)
    l5c_causal = overnight_intraday_split(prices, causal_engine_positions)
    tilt_published = same_day_tilt(prices, positions)
    tilt_causal = same_day_tilt(prices, causal_engine_positions)

    published_sharpe = float(summary["metrics"]["oos_sharpe"])
    reconciliation = float(abs(l5b["published_oos"]["sharpe"] - published_sharpe))

    # Buy-and-hold calibration: the same futures, equal-weighted, no signal.
    # Computed here (rather than read from the logged artifact) so that the
    # calibration is identical for every family -- the runners themselves use
    # different benchmarks (equal-weight for H9/H10, vol-weighted for
    # H21/H22/H25), which is recorded alongside.
    equal_weights = pd.DataFrame(
        1.0 / len(prices.columns), index=prices.index, columns=prices.columns
    )
    eq_result = run_backtest(
        prices=prices, signals=equal_weights, volumes=volumes, config=backtest_config()
    )
    benchmark = {
        "uniform_equal_weight_full_sample_equity_multiple": float(
            eq_result.equity_curve.iloc[-1] / eq_result.equity_curve.iloc[0]
        ),
        "uniform_equal_weight_oos_equity_multiple": float(
            eq_result.equity_curve[oos_mask].iloc[-1] / eq_result.equity_curve[oos_mask].iloc[0]
        ),
    }
    bench_path = art_dir / "benchmark_equity.parquet"
    if bench_path.exists():
        bench_equity = pd.read_parquet(bench_path).iloc[:, 0]
        benchmark["logged_benchmark_full_sample_equity_multiple"] = float(
            bench_equity.iloc[-1] / bench_equity.iloc[0]
        )
        benchmark["logged_benchmark_definition"] = (
            "vol-weighted buy-and-hold"
            if spec["family"] in ("H21", "H22", "H25")
            else "equal-weight buy-and-hold"
        )

    return {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "published_verdict": spec["published_verdict"],
        "construction": spec["construction"],
        "published_oos_sharpe": published_sharpe,
        "published_profit_factor": float(summary["metrics"]["profit_factor"]),
        "published_reconciliation_abs_diff": reconciliation,
        "benchmark": benchmark,
        "n_bars": len(prices.index),
        "oos_start": str(prices.index[oos_mask].min()),
        "oos_end": str(prices.index[oos_mask].max()),
        "level_checks": {"L1": l1, "L3": l3},
        "contract_specs": contract_spec_check(),
        "vol_target_coherence": l4,
        "lookahead": {
            "L5a_structural": l5a,
            "L5b_counterfactual": l5b,
            "L5c_attribution": {
                "published": l5c_published,
                "causal": l5c_causal,
                "same_day_tilt": {
                    "published": tilt_published,
                    "causal": tilt_causal,
                    "tilt_ratio_published_over_causal": float(
                        tilt_published["mean_signed_intraday_return"]
                        / tilt_causal["mean_signed_intraday_return"]
                    )
                    if tilt_causal["mean_signed_intraday_return"]
                    else float("nan"),
                },
            },
        },
    }


def build_report() -> dict:
    """Run the full audit (deterministic, offline, no network)."""
    audits = [audit_family(spec) for spec in FAMILIES]
    specs = contract_spec_check()

    l1_ok = all(a["level_checks"]["L1"]["passes"] for a in audits)
    l3_ok = all(a["level_checks"]["L3"]["passes"] for a in audits)
    level = (
        "LEVEL_CONFIRMED"
        if (l1_ok and l3_ok and specs["all_tick_values_consistent"])
        else "LEVEL_DEFECT"
    )

    structural_ok = all(
        a["lookahead"]["L5a_structural"].get("same_day_match_fraction", 0.0)
        >= LOOKAHEAD_STRUCT_FRAC
        for a in audits
        if a["lookahead"]["L5a_structural"].get("available")
    )
    certified = [a for a in audits if a["family"] in CERTIFIED]
    drop_ok = all(
        a["lookahead"]["L5b_counterfactual"]["oos_sharpe_relative_drop"] > LOOKAHEAD_SHARPE_DROP
        for a in certified
    )
    reproduced_ok = all(
        a["lookahead"]["L5b_counterfactual"]["reproduced_bit_exact"] for a in audits
    )
    lookahead = (
        "LOOKAHEAD_CONFIRMED"
        if (structural_ok and drop_ok and reproduced_ok)
        else "LOOKAHEAD_ABSENT"
    )

    return {
        "hypothesis": HYPOTHESIS,
        "kind": "audit",
        "capital": INITIAL_CAPITAL,
        "max_leverage": MAX_LEVERAGE,
        "max_position_size": MAX_POSITION_SIZE,
        "tolerances": {
            "level_abs": LEVEL_TOL,
            "level_fail_fraction": LEVEL_FAIL_FRAC,
            "reproduction": REPRODUCTION_TOL,
            "lookahead_structural_fraction": LOOKAHEAD_STRUCT_FRAC,
            "lookahead_sharpe_relative_drop": LOOKAHEAD_SHARPE_DROP,
        },
        "contract_specs": specs,
        "audited": audits,
        "verdict": {
            "level": level,
            "lookahead": lookahead,
            "level_checks_passed": {
                "L1_position_sizing": bool(l1_ok),
                "L2_contract_specs": bool(
                    specs["all_tick_values_consistent"] and specs["all_costs_consistent"]
                ),
                "L3_cost_scale": bool(l3_ok),
            },
            "certified_family_valid": bool(lookahead == "LOOKAHEAD_ABSENT"),
            "note": (
                "LEVEL_CONFIRMED means the P&L *level* carries no unit or scale "
                "error: the returns are exactly the returns the committed "
                "positions, prices and contract specs imply. It is NOT a "
                "statement that the certified family is valid. "
                "LOOKAHEAD_CONFIRMED means the daily-target collapse positions "
                "each session with the signal at that session's own close, so "
                "the certified family's edge is largely earned with "
                "same-day information; the family is invalidated pending an "
                "explicitly re-registered re-certification. No gate, threshold, "
                "verdict or certified number is changed by this audit."
            ),
        },
    }


def main() -> int:
    t0 = time.time()
    report = build_report()
    report["elapsed_sec"] = float(round(time.time() - t0, 2))

    ART_DIR.mkdir(parents=True, exist_ok=True)
    with open(ART_DIR / "summary.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda x: str(x))

    rows = []
    for a in report["audited"]:
        l5b = a["lookahead"]["L5b_counterfactual"]
        l5a = a["lookahead"]["L5a_structural"]
        rows.append(
            {
                "family": a["family"],
                "artifact": a["artifact"],
                "published_verdict": a["published_verdict"],
                "l1_max_abs_diff": a["level_checks"]["L1"][
                    "dollar_pnl_matches_engine_gross_max_abs_diff"
                ],
                "l3_max_abs_diff": a["level_checks"]["L3"][
                    "cost_from_trades_matches_engine_max_abs_diff"
                ],
                "same_day_match_fraction": l5a.get("same_day_match_fraction"),
                "prev_day_match_fraction": l5a.get("prev_day_match_fraction"),
                "published_oos_sharpe": l5b["published_oos"]["sharpe"],
                "causal_oos_sharpe": l5b["causal_oos"]["sharpe"],
                "published_oos_pf": l5b["published_oos"]["profit_factor"],
                "causal_oos_pf": l5b["causal_oos"]["profit_factor"],
                "published_equity_x": l5b["published_full_sample"]["equity_multiple"],
                "causal_equity_x": l5b["causal_full_sample"]["equity_multiple"],
                "sharpe_relative_drop": l5b["oos_sharpe_relative_drop"],
                "published_intraday_share": a["lookahead"]["L5c_attribution"]["published"][
                    "intraday_share"
                ],
                "causal_intraday_share": a["lookahead"]["L5c_attribution"]["causal"][
                    "intraday_share"
                ],
                "same_day_tilt_published": a["lookahead"]["L5c_attribution"]["same_day_tilt"][
                    "published"
                ]["mean_signed_intraday_return"],
                "same_day_tilt_causal": a["lookahead"]["L5c_attribution"]["same_day_tilt"][
                    "causal"
                ]["mean_signed_intraday_return"],
                "same_day_tilt_ratio": a["lookahead"]["L5c_attribution"]["same_day_tilt"][
                    "tilt_ratio_published_over_causal"
                ],
            }
        )
    pd.DataFrame(rows).to_parquet(ART_DIR / "level_table.parquet")

    print("=" * 110)
    print("[H27] P&L level audit + look-ahead attribution (pre-registered)")
    print(
        f"  {'fam':<5}{'L1 diff':>12}{'L3 diff':>12}{'same-day':>11}"
        f"{'pub SR':>9}{'causal SR':>11}{'drop':>8}{'pub eq':>10}{'causal eq':>11}"
        f"{'tilt pub':>11}{'tilt caus':>11}{'tilt x':>8}"
    )
    for a in report["audited"]:
        l5b = a["lookahead"]["L5b_counterfactual"]
        l5a = a["lookahead"]["L5a_structural"]
        tilt = a["lookahead"]["L5c_attribution"]["same_day_tilt"]
        print(
            f"  {a['family']:<5}"
            f"{a['level_checks']['L1']['dollar_pnl_matches_engine_gross_max_abs_diff']:>12.2e}"
            f"{a['level_checks']['L3']['cost_from_trades_matches_engine_max_abs_diff']:>12.2e}"
            f"{l5a.get('same_day_match_fraction', float('nan')):>11.4f}"
            f"{l5b['published_oos']['sharpe']:>9.4f}"
            f"{l5b['causal_oos']['sharpe']:>11.4f}"
            f"{l5b['oos_sharpe_relative_drop']:>8.3f}"
            f"{l5b['published_full_sample']['equity_multiple']:>10.2f}"
            f"{l5b['causal_full_sample']['equity_multiple']:>11.2f}"
            f"{tilt['published']['mean_signed_intraday_return']:>11.5f}"
            f"{tilt['causal']['mean_signed_intraday_return']:>11.5f}"
            f"{tilt['tilt_ratio_published_over_causal']:>8.2f}"
        )
    v = report["verdict"]
    print(f"  verdict: level={v['level']}  lookahead={v['lookahead']}")
    print(f"  certified_family_valid={v['certified_family_valid']}")
    print(f"  wrote {ART_DIR}  ({report['elapsed_sec']}s)")
    print("=" * 110)
    return 0


if __name__ == "__main__":
    sys.exit(main())
