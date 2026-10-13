"""
H20: Volume-Sign (Buy/Sell-Initiated) Decomposition + Order-Flow Imbalance.

Implements the pre-registered H20 hypothesis in HYPOTHESIS_SPEC.md:
decomposing daily volume into buyer-initiated (V+) and seller-initiated (V−)
components via the daily tick rule / Lee-Ready algorithm, and trading a
volatility-targeted long/short position on the cumulative order-flow
imbalance (V+ − V−) of SPY.

Faithfulness notes:
  * Universe: SPY (primary, traded); QQQ/IWM (cross-validation);
    ^VIX (regime labels only).
  * Sample: 2009-01-01 -> 2026-10-08 (~4,200 daily bars).
  * Splits: Train 2009-01-01 -> 2014-12-31; Val 2015-01-01 -> 2019-12-31;
    Test 2020-01-01 -> 2026-10-08 (protected). OOS = Val+Test.
  * Signal (causal, 1-day lag): trade direction from daily OHLC via the tick
    rule or Lee-Ready algorithm; signed volume sv_t = direction_t * V_t;
    order-flow imbalance = causal rolling sum of sv over `imbalance_lag`
    days; position_t = sign(imbalance_t) * clip(target_vol / realized_vol,
    0, max_pos). The engine applies signals.shift(1) internally, so a weight
    set at close of day t earns the return of day t+1. All rolling stats use
    .shift(1) to exclude the current observation (no lookahead).
  * Grid: sign_rule (2) x target_vol (3) x max_pos (2) x imbalance_lag (3)
    = 36 combos; selection by Val Sharpe; Test protected.
  * Gates: unchanged PROMPT_V2 set + +/-20% perturbation gate, on OOS.
  * Long/short permitted (allow_short=True); weight bounds [-max_pos, max_pos].
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import get_data_fetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "h20_signed_volume"
EXPERIMENT_DESC = (
    "H20: Volume-sign (buy/sell-initiated) decomposition + order-flow imbalance"
)

# Symbols
SPY_SYMBOL = "SPY"
QQQ_SYMBOL = "QQQ"
IWM_SYMBOL = "IWM"
VIX_SYMBOL = "^VIX"

# Splits (pre-registered)
DATA_START = "2009-01-01"
DATA_END = "2026-10-08"
TRAIN_END = "2014-12-31"
VAL_END = "2019-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

# Realized-volatility estimation (annualized, shifted for causality)
VOL_WINDOW = 63
ANNUALIZE = float(np.sqrt(252))

# Long/short signaling (order-flow imbalance can be positive OR negative).
ALLOW_SHORT = True

WF_FOLDS_STABILITY = 5

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}

# Grid (pre-registered)
SIGN_RULES = ["tick", "lee_ready"]
TARGET_VOLS = [0.05, 0.10, 0.15]
MAX_POSITIONS = [0.5, 1.0]
IMBALANCE_LAGS = [1, 3, 5]


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    """VIX regime labels: bull < 20, sideways 20-30, bear > 30."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def sign_rule_direction(ohlc: pd.DataFrame, rule: str) -> pd.Series:
    """
    Per-day trade-direction sign in {-1, 0, +1} from daily OHLCV.

    Causal: uses only close/open/high/low of day t (known at close of day t).

    tick       : sign(close - open); flat-day fallback sign(close - prev_close).
    lee_ready  : sign(close - prev_close); flat-primary fallback sign(close -
                 open); range tie-break (close closer to high => +1).
    """
    o = ohlc["open"]
    h = ohlc["high"]
    l = ohlc["low"]
    c = ohlc["close"]

    if rule == "tick":
        raw = (c - o).copy()
        flat = raw == 0
        raw[flat.values] = (c - c.shift(1))[flat.values]
        sign = raw.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
        return sign

    if rule == "lee_ready":
        primary = (c - c.shift(1)).copy()
        # flat primary -> intraday sign
        flat_primary = primary == 0
        primary[flat_primary.values] = (c - o)[flat_primary.values]
        # fully flat -> range tie-break
        range_pos = (c - l) - (h - c)  # >0 means closer to high (up-tick)
        still_flat = primary == 0
        primary[still_flat.values] = range_pos[still_flat.values]
        sign = primary.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
        return sign

    raise ValueError(f"Unknown sign_rule: {rule}")


def build_targets(
    ohlc: pd.DataFrame,
    sign_rule: str,
    target_vol: float,
    max_pos: float,
    imbalance_lag: int,
    vol_window: int = VOL_WINDOW,
) -> pd.DataFrame:
    """
    Build daily target weights for SPY from signed-volume / order-flow
    imbalance.

    Returns a DataFrame with column "SPY" containing weights in
    [-max_pos, +max_pos].

    Causal: every rolling statistic is shifted so that weight[t] depends
    only on data through day t (the engine's internal shift(1) then applies
    it to the return of day t+1).
    """
    direction = sign_rule_direction(ohlc, sign_rule)
    volume = ohlc["volume"].ffill()
    signed_vol = direction * volume

    # Order-flow imbalance: cumulative net signed volume over the trailing
    # window (causal; rolling sum includes only days <= t). imbalance_lag=1
    # collapses to the single-day signed volume.
    imbalance = signed_vol.rolling(imbalance_lag).sum()

    # Annualized realized volatility of returns, shifted(1) (past returns only).
    daily_ret = ohlc["close"].pct_change()
    realized_vol = (daily_ret.rolling(vol_window).std() * ANNUALIZE).shift(1)

    # Vol-targeted position magnitude, capped at max_pos.
    vol_scale = (target_vol / realized_vol).clip(lower=0.0, upper=max_pos)

    weight = np.sign(imbalance) * vol_scale
    weight = weight.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    targets = pd.DataFrame(index=ohlc.index)
    targets["SPY"] = weight
    return targets


def _splits(prices_idx: pd.Index):
    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)
    val_mask = (prices_idx > pd.Timestamp(TRAIN_END)) & (
        prices_idx <= pd.Timestamp(VAL_END)
    )
    test_mask = prices_idx > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    sr = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def full_gate_eval(
    result,
    oos_mask,
    val_mask,
    test_mask,
    prices,
    vix,
    bench_result,
):
    """The 9 pre-registered gates on OOS (Val+Test)."""
    prices_idx = prices.index

    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)

    oos_ret = result.returns[oos_mask]
    test_ret = result.returns[test_mask]
    n_oos_trades = _count_in(result.trades, oos_mask, prices)

    oos_m = _period_metrics(oos_ret, n_oos_trades)
    test_m = _period_metrics(test_ret, _count_in(result.trades, test_mask, prices))

    # Walk-forward stability (full series)
    wf_splits = walk_forward_splits(len(result.returns), n_splits=WF_FOLDS_STABILITY)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].dropna()
        te_r = result.returns.iloc[te_idx].dropna()
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r.values))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r.values))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes))
        if np.mean(train_sharpes) != 0 and len(train_sharpes) > 0
        else 0.0
    )

    # Regime sharpes on the OOS window
    regimes = regime_labels(vix.reindex(prices_idx))[oos_mask]
    oos_ret_r = result.returns[oos_mask]
    regime_sharpes = {}
    worst = np.inf
    for reg in ["bull", "sideways", "bear"]:
        m = regimes == reg
        r = oos_ret_r.iloc[m.values] if len(m) == len(oos_ret_r) else oos_ret_r[m]
        if len(r) > 1 and r.std() > 0:
            s = float(sharpe_ratio(r.values))
        else:
            s = 0.0
        regime_sharpes[reg] = s
        worst = min(worst, s)

    bench = compare_to_benchmark(
        oos_ret.dropna().values,
        bench_result.returns[oos_mask].dropna().values,
    )
    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_m["max_drawdown"]) <= GATES["max_drawdown"]
        if oos_m["max_drawdown"] < 0
        else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "worst": worst >= GATES["min_worst_regime_sharpe"]
        if worst != np.inf
        else False,
        "p": float(bench.get("alpha_p_value", 1.0)) < GATES["max_p_value"],
        "ir": float(bench.get("information_ratio", -np.inf))
        > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": oos_m,
        "test_metrics": test_m,
        "train_sharpe": float(
            sharpe_ratio(result.returns[train_mask].dropna().values)
        )
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": float(
            sharpe_ratio(result.returns[val_mask].dropna().values)
        )
        if val_mask.sum() > 1
        else 0.0,
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
        "regime_sharpes": regime_sharpes,
        "benchmark_p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "benchmark_alpha_annual": float(bench.get("alpha_annualized", 0.0)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def perturbation_eval(
    selected: dict,
    ohlc: pd.DataFrame,
    oos_mask,
    cfg,
    opt_oos_sharpe: float,
):
    """OAT +/-20% perturbation of target_vol and max_pos for the selected config."""
    variants = {}
    base_tv = selected["target_vol"]
    base_mp = selected["max_pos"]

    for factor in (0.8, 1.2):
        for param, base in (("target_vol", base_tv), ("max_pos", base_mp)):
            v = base * factor
            if v == base:
                continue
            kw = dict(selected)
            kw[param] = round(v, 4) if param == "target_vol" else float(v)
            targets = build_targets(
                ohlc,
                kw["sign_rule"],
                kw["target_vol"],
                kw["max_pos"],
                kw["imbalance_lag"],
            )
            res = run_backtest(prices=pd.DataFrame({"SPY": ohlc["close"]}, index=ohlc.index), signals=targets, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={kw[param]}"] = (
                float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            )

    if opt_oos_sharpe > 0:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe) if variants else 0.0
    else:
        # A non-positive optimum is not a stable reference; gate cannot pass.
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def make_config(max_pos: float) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=max_pos,
        max_leverage=1.0,
        allow_short=True,
    )


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(SIGN_RULES) * len(TARGET_VOLS) * len(MAX_POSITIONS) * len(IMBALANCE_LAGS)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SPY_SYMBOL],
            "cross_validation": [QQQ_SYMBOL, IWM_SYMBOL],
            "regime_labels": VIX_SYMBOL,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": ["2009-01-01", TRAIN_END],
                "val": ["2015-01-01", VAL_END],
                "test": ["2020-01-01", DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "sign_rule": SIGN_RULES,
                "target_vol": TARGET_VOLS,
                "max_pos": MAX_POSITIONS,
                "imbalance_lag": IMBALANCE_LAGS,
            },
            "grid_size": grid_size,
            "selection": (
                "argmax Val Sharpe; Test 2020-2026 protected (never used for "
                "selection); gates on OOS Val+Test"
            ),
            "vol_window": VOL_WINDOW,
            "realized_vol_annualize": ANNUALIZE,
            "allow_short": True,
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": [SPY_SYMBOL, QQQ_SYMBOL, IWM_SYMBOL, VIX_SYMBOL],
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H20] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        data = fetcher.fetch_yahoo(
            [SPY_SYMBOL, QQQ_SYMBOL, IWM_SYMBOL, VIX_SYMBOL],
            start=DATA_START,
            end=DATA_END,
            interval="1d",
        )
        spy_df = data.get(SPY_SYMBOL, pd.DataFrame())
        if spy_df.empty:
            raise RuntimeError(f"no data for {SPY_SYMBOL}")

        common = spy_df.index
        spy_ohlc = spy_df[["open", "high", "low", "close", "volume"]].reindex(common)
        qqq_close = (
            data.get(QQQ_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )
        iwm_close = (
            data.get(IWM_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )
        vix = (
            data.get(VIX_SYMBOL, pd.DataFrame())
            .get("close", pd.Series(index=common))
            .reindex(common)
        )

        prices = pd.DataFrame({"SPY": spy_ohlc["close"].values}, index=common)
        volumes = pd.DataFrame({"SPY": spy_ohlc["volume"].values}, index=common)

        train_mask, val_mask, test_mask = _splits(prices.index)
        oos_mask = ~train_mask
        print(
            f"[H20] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg_base = make_config(max_pos=1.0)

        # Benchmark: buy-and-hold SPY
        bench_signals = pd.DataFrame({"SPY": 1.0}, index=prices.index)
        bench_result = run_backtest(prices=prices, signals=bench_signals, config=cfg_base)

        # --- 36-combo grid: selection on Val Sharpe ---
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for sign_rule in SIGN_RULES:
            for target_vol in TARGET_VOLS:
                for max_pos in MAX_POSITIONS:
                    for lag in IMBALANCE_LAGS:
                        combo_name = f"{sign_rule}_tv{target_vol}_mp{max_pos}_lag{lag}"
                        print(f"  Testing {combo_name}...")

                        targets = build_targets(
                            spy_ohlc, sign_rule, target_vol, max_pos, lag
                        )
                        cfg = make_config(max_pos=max_pos)
                        res = run_backtest(
                            prices=prices, signals=targets, config=cfg
                        )

                        train_r = res.returns[train_mask].dropna()
                        train_sr = (
                            float(sharpe_ratio(train_r.values)) if len(train_r) > 1 else 0.0
                        )
                        val_r = res.returns[val_mask].dropna()
                        val_sr = float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0
                        test_r = res.returns[test_mask].dropna()
                        test_sr = float(sharpe_ratio(test_r.values)) if len(test_r) > 1 else 0.0
                        oos_r = res.returns[oos_mask].dropna()
                        oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0

                        grid_results[(sign_rule, target_vol, max_pos, lag)] = res
                        grid_rows.append(
                            {
                                "sign_rule": sign_rule,
                                "target_vol": target_vol,
                                "max_pos": max_pos,
                                "imbalance_lag": lag,
                                "combo_name": combo_name,
                                "vol_window": VOL_WINDOW,
                                "train_sharpe": train_sr,
                                "val_sharpe": val_sr,
                                "test_sharpe": test_sr,
                                "oos_sharpe": oos_sr,
                            }
                        )
        grid_df = pd.DataFrame(grid_rows).sort_values("val_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[H20] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best val Sharpe={grid_df.iloc[0]['val_sharpe']:.4f}"
        )

        # --- selection: best Val Sharpe (Test never used) ---
        best_row = grid_df.iloc[0]
        sel_key = (
            best_row["sign_rule"],
            float(best_row["target_vol"]),
            float(best_row["max_pos"]),
            int(best_row["imbalance_lag"]),
        )
        sel_result = grid_results[sel_key]
        selected = {
            "sign_rule": sel_key[0],
            "target_vol": sel_key[1],
            "max_pos": sel_key[2],
            "imbalance_lag": sel_key[3],
            "vol_window": VOL_WINDOW,
        }

        # --- full gate evaluation on protected OOS (Val+Test) ---
        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
        )

        # --- perturbation gate (OAT +/-20%) ---
        pert = perturbation_eval(
            selected,
            spy_ohlc,
            oos_mask,
            make_config(max_pos=selected["max_pos"]),
            gate["oos_metrics"]["sharpe"],
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # --- ablations (OOS) ---
        ablations = {}
        # (a) BH SPY (already computed as bench_result)
        ablations["bh_spy"] = {
            "oos_metrics": _period_metrics(
                bench_result.returns[oos_mask],
                _count_in(bench_result.trades, oos_mask, prices),
            ),
        }
        # (b) random-signed-volume: shuffle per-day direction signs
        rng = np.random.RandomState(SEED)
        n = len(spy_ohlc)
        shuffled_dir = pd.Series(
            rng.choice([-1.0, 1.0], size=n), index=spy_ohlc.index
        )
        # Inject randomized direction by building signed-volume targets with a
        # shuffled direction series (imbalance/vol-scale retained) - tests
        # whether the sign assignment itself carries information.
        random_targets = _signed_volume_targets(
            spy_ohlc, shuffled_dir, selected["target_vol"],
            selected["max_pos"], selected["imbalance_lag"],
        )
        random_res = run_backtest(
            prices=prices, signals=random_targets, config=make_config(max_pos=selected["max_pos"])
        )
        ablations["random_signed_volume"] = {
            "oos_metrics": _period_metrics(
                random_res.returns[oos_mask],
                _count_in(random_res.trades, oos_mask, prices),
            ),
        }
        # (c) constant 0.5 long position
        const_signals = pd.DataFrame({"SPY": 0.5}, index=prices.index)
        const_res = run_backtest(prices=prices, signals=const_signals, config=cfg_base)
        ablations["constant_0_5_position"] = {
            "oos_metrics": _period_metrics(
                const_res.returns[oos_mask],
                _count_in(const_res.trades, oos_mask, prices),
            ),
        }
        # (d) total-volume-only = H19's simple_lagged long-only volume surprise
        h19_targets = _h19_simple_lagged_targets(spy_ohlc)
        h19_res = run_backtest(prices=prices, signals=h19_targets, config=cfg_base)
        ablations["total_volume_only"] = {
            "oos_metrics": _period_metrics(
                h19_res.returns[oos_mask],
                _count_in(h19_res.trades, oos_mask, prices),
            ),
        }

        # --- cross-validation on QQQ/IWM (same selected signal, different returns) ---
        sel_targets = build_targets(
            spy_ohlc,
            selected["sign_rule"],
            selected["target_vol"],
            selected["max_pos"],
            selected["imbalance_lag"],
        )
        cross_val = {}
        for sym, close_cv in [("QQQ", qqq_close), ("IWM", iwm_close)]:
            if close_cv.isna().all():
                continue
            cv_ret = close_cv.pct_change()[oos_mask].dropna()
            cv_sr = float(sharpe_ratio(cv_ret.values)) if len(cv_ret) > 1 else 0.0
            sig_oos = sel_targets["SPY"][oos_mask]
            cv_oos_ret = (
                (sig_oos.shift(1) * close_cv.pct_change())
                .reindex(cv_ret.index)
                .dropna()
            )
            cv_strat_sr = (
                float(sharpe_ratio(cv_oos_ret.values)) if len(cv_oos_ret) > 1 else 0.0
            )
            cross_val[sym] = {
                "bh_sharpe": cv_sr,
                "signal_sharpe": cv_strat_sr,
            }

        # --- artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.rename("close").to_frame())
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", sel_result.positions)
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe(
            "benchmark_equity", bench_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe(
            "benchmark_returns", bench_result.returns.to_frame("returns")
        )
        for name, ab in ablations.items():
            tracker.log_metrics(
                {
                    f"ablation_{name}_oos_sharpe": ab["oos_metrics"]["sharpe"],
                    f"ablation_{name}_oos_dd": ab["oos_metrics"]["max_drawdown"],
                    f"ablation_{name}_oos_pf": ab["oos_metrics"]["profit_factor"],
                }
            )

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H20",
            "selected_config": selected,
            "selection_rule": (
                "argmax Val Sharpe; Test 2020-2026 protected (never used for "
                "selection); gates on OOS Val+Test"
            ),
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "vol_window": VOL_WINDOW,
            "allow_short": True,
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
                "regime_sharpes": gate["regime_sharpes"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "benchmark_alpha_annual": gate["benchmark_alpha_annual"],
                "perturbation": pert,
                "ablations": ablations,
                "cross_validation": cross_val,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: (
                    float(x) if isinstance(x, (np.integer, np.floating)) else str(x)
                ),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")

        end_time = time.time()
        metadata = {
            "run_id": exp_id,
            "script": "run_h20_signed_volume_experiment.py",
            "start_time": t_start,
            "end_time": end_time,
            "duration_seconds": end_time - t_start,
            "duration_cpu_hours": (end_time - t_start) / 3600.0,
            "timestamp_start": pd.Timestamp.fromtimestamp(t_start).isoformat(),
            "timestamp_end": pd.Timestamp.fromtimestamp(end_time).isoformat(),
        }
        metadata_path = exp_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        tracker.log_artifact("metadata", metadata_path)

        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        print(
            f"  sharpe={p['sharpe']} trades={p['trades']} pf={p['pf']} "
            f"dd={p['dd']} stab={p['stab']} worst={p['worst']} "
            f"p={p['p']} ir={p['ir']} perturb={p['perturbation']}"
        )
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} "
            f"Test={gate['test_metrics']['sharpe']:.3f} | "
            f"WF stab={gate['wf_stability']:.3f} | "
            f"worst-regime={gate['worst_regime_sharpe']:.3f}"
        )
        print(
            f"  Benchmark: p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | "
            f"total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:  # broad catch for experiment-level error reporting  # noqa: BLE001
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


def _signed_volume_targets(
    ohlc: pd.DataFrame,
    direction: pd.Series,
    target_vol: float,
    max_pos: float,
    imbalance_lag: int,
) -> pd.DataFrame:
    """Build signed-volume (order-flow) targets given an explicit direction series."""
    volume = ohlc["volume"].ffill()
    signed_vol = direction * volume
    imbalance = signed_vol.rolling(imbalance_lag).sum()
    daily_ret = ohlc["close"].pct_change()
    realized_vol = (daily_ret.rolling(VOL_WINDOW).std() * ANNUALIZE).shift(1)
    vol_scale = (target_vol / realized_vol).clip(lower=0.0, upper=max_pos)
    weight = np.sign(imbalance) * vol_scale
    weight = weight.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return pd.DataFrame({"SPY": weight}, index=ohlc.index)


def _h19_simple_lagged_targets(ohlc: pd.DataFrame) -> pd.DataFrame:
    """Total-volume-only ablation: H19's simple_lagged + median threshold (long only, [0,1])."""
    import run_h19_volume_predictive_experiment as h19

    vol = ohlc["volume"].ffill()
    vol_lag = vol.shift(1)
    vol_mean = vol_lag.rolling(h19.LOOKBACK).mean()
    unant_lag = (vol - vol_mean).shift(1)
    threshold = unant_lag.rolling(h19.LOOKBACK).median()
    signal = (vol - vol_mean > threshold).astype(float).fillna(0.0)
    return pd.DataFrame({"SPY": signal}, index=ohlc.index)


if __name__ == "__main__":
    sys.exit(main())
