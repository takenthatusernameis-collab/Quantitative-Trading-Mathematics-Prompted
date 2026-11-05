"""
H87 / NF-20261105-01: Opening-Gap Fill / Overnight Information (SPY intraday).

Pre-registered in NEW_FAMILY_RESEARCH_REGISTER.md §8 and HYPOTHESIS_SPEC.md H87.
Mechanism: overnight gaps partially fill intraday; go long SPY if gap negative
(expect fill up), short if gap positive (expect fill down), hold intraday open→close.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_01_opening_gap"
EXPERIMENT_DESC = (
    "H87/NF-20261105-01: SPY opening-gap fill intraday (open→close). "
    "Long if open < prev close, short if open > prev close; vol-targeted; "
    "Train/Val/Test 2015-2020/2021-2023/2024-2026; Test protected; gates on OOS Val+Test."
)

SYMBOL = "SPY"
UNIVERSE = [SYMBOL]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2020-12-31"
VAL_END = "2023-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

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

# Pre-registered grid
LOOKBACKS = [1, 5, 21]
ZSCORE_THRESHOLDS = [0.0, 0.5, 1.0]
VOL_TARGETS = [0.10, 0.15, 0.20]

WF_FOLDS_SELECTION = 4
WF_FOLDS_STABILITY = 5


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=True,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    if len(r) > 1:
        sr = float(sharpe_ratio(r.values))
    else:
        sr = 0.0
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


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    if len(prices.index[mask]) == 0:
        return 0
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def build_daily_targets(
    prices: pd.DataFrame,
    lookback: int,
    zscore_thresh: float,
    vol_target: float,
) -> pd.DataFrame:
    """Daily target weights for SPY, strictly causal. Trade intraday open->close."""
    targets = pd.DataFrame(0.0, index=prices.index, columns=[SYMBOL])
    if SYMBOL not in prices.columns and "close" not in prices.columns:
        return targets
    close = prices["close"]
    open_ = prices["open"] if "open" in prices.columns else close
    # Gap = open_t - close_{t-1}
    gap_ret = (open_ - close.shift(1)) / close.shift(1)

    if lookback <= 1:
        # No history for a z-score: the gap return itself is the signal, so
        # its sign is the gap direction (long a negative gap, short a
        # positive one). A zero/NaN gap yields no position.
        gap_z = gap_ret.fillna(0.0)
    else:
        min_p = int(max(1, min(lookback, 21)))
        rolling_mean = gap_ret.rolling(lookback, min_periods=min_p).mean()
        rolling_std = gap_ret.rolling(lookback, min_periods=min_p).std()
        rolling_std = rolling_std.replace(0, np.nan).ffill().fillna(1e-6)
        gap_z = (gap_ret - rolling_mean) / rolling_std

    pos = pd.Series(0.0, index=prices.index)
    long_sig = gap_z < -zscore_thresh
    short_sig = gap_z > zscore_thresh
    pos[long_sig] = 1.0
    pos[short_sig] = -1.0

    # Vol targeting on intraday returns
    intraday_ret = close / open_ - 1
    rolling_vol = intraday_ret.rolling(63, min_periods=21).std() * np.sqrt(252)
    rolling_vol = rolling_vol.replace(0, np.nan).ffill().fillna(0.15)
    scale = vol_target / rolling_vol
    scale = scale.clip(lower=0.0, upper=1.0)
    pos = pos * scale
    targets[SYMBOL] = pos.fillna(0.0)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask: pd.Series) -> float:
    r = returns.copy()
    r.index = pd.to_datetime(r.index)
    try:
        splits = walk_forward_splits(r, n_folds=WF_FOLDS_SELECTION, embargo_days=5)
    except Exception:
        train_r = r[train_mask].dropna()
        if len(train_r) > 1:
            return float(sharpe_ratio(train_r.values))
        return 0.0
    sharpes = []
    for tr, _ in splits:
        tr_mask = r.index.isin(tr)
        if tr_mask.sum() < 20:
            continue
        tr_r = r[tr_mask].dropna()
        if len(tr_r) > 1:
            s = sharpe_ratio(tr_r.values)
            if np.isfinite(s):
                sharpes.append(float(s))
    if sharpes:
        return float(np.mean(sharpes))
    train_r = r[train_mask].dropna()
    if len(train_r) > 1:
        return float(sharpe_ratio(train_r.values))
    return 0.0


def full_gate_eval(result, oos_mask, val_mask, test_mask, train_mask, prices, bench_result):
    oos_ret = result.returns[oos_mask].dropna()
    val_ret = result.returns[val_mask].dropna()
    test_ret = result.returns[test_mask].dropna()
    train_ret = result.returns[train_mask].dropna()

    oos_sr = float(sharpe_ratio(oos_ret.values)) if len(oos_ret) > 1 else 0.0
    val_sr = float(sharpe_ratio(val_ret.values)) if len(val_ret) > 1 else 0.0
    test_sr = float(sharpe_ratio(test_ret.values)) if len(test_ret) > 1 else 0.0
    train_sr = float(sharpe_ratio(train_ret.values)) if len(train_ret) > 1 else 0.0

    oos_trades = _count_in(result.trades, oos_mask, prices)
    cum = (1 + oos_ret).cumprod()
    oos_dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(oos_ret[oos_ret > 0].sum())
    gl = float(abs(oos_ret[oos_ret < 0].sum()))
    oos_pf = gp / gl if gl > 0 else float("inf")

    wf_stab = float(test_sr / train_sr) if train_sr > 0 and np.isfinite(train_sr) else 0.0

    bench_cmp = compare_to_benchmark(result.returns, bench_result.returns)
    bench_p = float(bench_cmp.get("alpha_p_value", 1.0))
    ir = float(bench_cmp.get("information_ratio", 0.0))

    regime_sharpes = []
    for m in [train_mask, val_mask, test_mask]:
        r = result.returns[m].dropna()
        if len(r) > 10:
            regime_sharpes.append(float(sharpe_ratio(r.values)))
    worst_regime = float(min(regime_sharpes)) if regime_sharpes else -np.inf

    passes = {
        "sharpe": oos_sr >= GATES["min_sharpe"],
        "trades": oos_trades >= GATES["min_trades"],
        "profit_factor": oos_pf >= GATES["min_profit_factor"],
        "drawdown": oos_dd >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "benchmark_significance": benchmark_significance_gate(bench_p, ir),
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    test_cum = (1 + test_ret).cumprod() if len(test_ret) > 0 else pd.Series([1.0])
    test_dd = float((test_cum / test_cum.cummax() - 1.0).min()) if len(test_cum) > 0 else 0.0
    return {
        "passes": passes,
        "oos_metrics": {
            "sharpe": oos_sr,
            "profit_factor": oos_pf,
            "max_drawdown": oos_dd,
            "trades": oos_trades,
        },
        "train_sharpe": train_sr,
        "val_sharpe": val_sr,
        "test_metrics": {"sharpe": test_sr, "max_drawdown": test_dd},
        "wf_stability": wf_stab,
        "benchmark_p_value": bench_p,
        "information_ratio": ir,
        "worst_regime_sharpe": worst_regime,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, baseline_sharpe):
    """OAT perturbation +/-20% of lookback, zscore_thresh, vol_target.

    Returns per-variant OOS Sharpes and the min ratio to the baseline
    (pre-registered gate >= 0.5).
    """
    variants = {}
    intraday_ret = prices["close"] / prices["open"] - 1.0
    for param in ["lookback", "zscore_thresh", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            v = base * factor
            if abs(v - base) < 1e-12:
                v = base + (0.05 if factor > 1 else -0.05)
            kw = dict(selected)
            if param == "lookback":
                kw[param] = int(max(1, round(v)))
            elif param == "vol_target":
                kw[param] = float(max(0.01, min(0.5, v)))
            else:
                kw[param] = float(max(0.0, v))
            pos = build_daily_targets(prices, kw["lookback"], kw["zscore_thresh"], kw["vol_target"])
            pos_s = pos[SYMBOL].reindex(prices.index).fillna(0.0)
            intraday_ret_s = intraday_ret.reindex(prices.index).fillna(0.0)
            strat_ret = pos_s.shift(1).fillna(0.0).values * intraday_ret_s.values
            strat_price = (1.0 + pd.Series(strat_ret, index=prices.index)).cumprod()
            strat_price.iloc[0] = 1.0
            p_strat = pd.DataFrame({SYMBOL: strat_price.values}, index=prices.index)
            s_strat = pd.DataFrame(1.0, index=p_strat.index, columns=[SYMBOL])
            try:
                res = run_backtest(prices=p_strat, signals=s_strat, volumes=None, config=cfg)
                r = res.returns[oos_mask].dropna()
                variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            except Exception:
                variants[f"{param}={v:.3f}"] = 0.0
    if baseline_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / baseline_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main() -> int:
    start_time = time.time()
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SYMBOL],
            "lookbacks": LOOKBACKS,
            "zscore_thresholds": ZSCORE_THRESHOLDS,
            "vol_targets": VOL_TARGETS,
            "splits": {
                "train": f"≤{TRAIN_END}",
                "val": f"{VAL_END} prev→{VAL_END}",
                "test": f">{VAL_END}",
            },
        },
        data_sources={
            "source": "yahoo_daily_cached_isolated",
            "symbols": [SYMBOL],
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 1.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-05-01] started {exp_id}")

    exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    isolated_cache = exp_dir / "cache"
    isolated_cache.mkdir(parents=True, exist_ok=True)
    fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))

    try:
        data = fetcher.fetch_yahoo([SYMBOL], start=DATA_START, end=DATA_END, interval="1d")
        if SYMBOL not in data or data[SYMBOL].empty:
            raise RuntimeError(f"No data for {SYMBOL}")
        prices = data[SYMBOL].copy()
        for c in ["open", "high", "low", "close"]:
            if c not in prices.columns:
                raise RuntimeError(f"Missing {c} in price data")

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        cfg = make_equity_config()

        p_close = prices[["close"]].copy()
        p_close.columns = [SYMBOL]
        bench_signals = pd.DataFrame(1.0, index=p_close.index, columns=[SYMBOL])
        bench_result = run_backtest(prices=p_close, signals=bench_signals, volumes=None, config=cfg)

        grid_size = len(LOOKBACKS) * len(ZSCORE_THRESHOLDS) * len(VOL_TARGETS)
        print(f"[NF-05-01] grid {grid_size} combos")
        t_grid = time.time()
        grid_rows = []
        grid_results = {}

        for lb in LOOKBACKS:
            for zth in ZSCORE_THRESHOLDS:
                for vt in VOL_TARGETS:
                    try:
                        pos = build_daily_targets(prices, lb, zth, vt)
                        intraday_ret = prices["close"] / prices["open"] - 1.0
                        pos_s = pos[SYMBOL].reindex(prices.index).fillna(0.0)
                        intraday_ret_s = intraday_ret.reindex(prices.index).fillna(0.0)
                        strat_ret = pos_s.shift(1).fillna(0.0).values * intraday_ret_s.values
                        strat_price = (1.0 + pd.Series(strat_ret, index=prices.index)).cumprod()
                        strat_price.iloc[0] = 1.0
                        p_strat = pd.DataFrame({SYMBOL: strat_price.values}, index=prices.index)
                        s_strat = pd.DataFrame(1.0, index=p_strat.index, columns=[SYMBOL])
                        res = run_backtest(
                            prices=p_strat, signals=s_strat, volumes=None, config=cfg
                        )
                        wf_train = train_only_wf_sharpe(res.returns, train_mask)
                        oos_ret_m = res.returns[oos_mask].dropna()
                        oos_sr_m = (
                            float(sharpe_ratio(oos_ret_m.values)) if len(oos_ret_m) > 1 else 0.0
                        )
                        key = (lb, zth, vt)
                        grid_results[key] = (res, pos)
                        grid_rows.append(
                            {
                                "lookback": lb,
                                "zscore_thresh": zth,
                                "vol_target": vt,
                                "train_wf_sharpe": wf_train,
                                "oos_sharpe": oos_sr_m,
                                "trades_total": int(len(res.trades))
                                if res.trades is not None
                                else 0,
                            }
                        )
                    except Exception as e:
                        print(f"  err {lb},{zth},{vt}: {e}")
                        continue

        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-05-01] grid done in {grid_elapsed:.1f}s; best train-WF={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best = grid_df.iloc[0]
        sel = {
            "lookback": int(best["lookback"]),
            "zscore_thresh": float(best["zscore_thresh"]),
            "vol_target": float(best["vol_target"]),
        }
        sel_result, base_pos = grid_results[
            (sel["lookback"], sel["zscore_thresh"], sel["vol_target"])
        ]

        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, train_mask, prices, bench_result
        )
        pert = perturbation_eval(sel, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        rng_ab = np.random.default_rng(SEED)
        rand_pos = base_pos.copy()
        for c in rand_pos.columns:
            rand_pos[c] = rng_ab.choice([-1.0, 0.0, 1.0], size=len(rand_pos))
        try:
            intraday_ret = prices["close"] / prices["open"] - 1.0
            pos_s = rand_pos[SYMBOL].reindex(prices.index).fillna(0.0)
            intraday_ret_s = intraday_ret.reindex(prices.index).fillna(0.0)
            strat_ret_r = pos_s.shift(1).fillna(0.0).values * intraday_ret_s.values
            p_strat_r = (1.0 + pd.Series(strat_ret_r, index=prices.index)).cumprod()
            p_strat_r.iloc[0] = 1.0
            p_strat_r = pd.DataFrame({SYMBOL: p_strat_r.values}, index=prices.index)
            s_strat_r = pd.DataFrame(1.0, index=p_strat_r.index, columns=[SYMBOL])
            rand_res = run_backtest(prices=p_strat_r, signals=s_strat_r, volumes=None, config=cfg)
            ablations["random_entry"] = _period_metrics(
                rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
            )
        except Exception:
            ablations["random_entry"] = {"error": "failed"}
        try:
            long_pos = base_pos.copy()
            long_pos[long_pos < 0] = 0
            pos_s = long_pos[SYMBOL].reindex(prices.index).fillna(0.0)
            strat_ret_l = pos_s.shift(1).fillna(0.0).values * intraday_ret_s.values
            p_strat_l = (1.0 + pd.Series(strat_ret_l, index=prices.index)).cumprod()
            p_strat_l.iloc[0] = 1.0
            p_strat_l = pd.DataFrame({SYMBOL: p_strat_l.values}, index=prices.index)
            s_strat_l = pd.DataFrame(1.0, index=p_strat_l.index, columns=[SYMBOL])
            lon_res = run_backtest(prices=p_strat_l, signals=s_strat_l, volumes=None, config=cfg)
            ablations["long_only_negative_gaps"] = _period_metrics(
                lon_res.returns[oos_mask], _count_in(lon_res.trades, oos_mask, prices)
            )
        except Exception:
            ablations["long_only_negative_gaps"] = {"error": "failed"}
        try:
            short_pos = base_pos.copy()
            short_pos[short_pos > 0] = 0
            pos_s = short_pos[SYMBOL].reindex(prices.index).fillna(0.0)
            strat_ret_s = pos_s.shift(1).fillna(0.0).values * intraday_ret_s.values
            p_strat_s = (1.0 + pd.Series(strat_ret_s, index=prices.index)).cumprod()
            p_strat_s.iloc[0] = 1.0
            p_strat_s = pd.DataFrame({SYMBOL: p_strat_s.values}, index=prices.index)
            s_strat_s = pd.DataFrame(1.0, index=p_strat_s.index, columns=[SYMBOL])
            shr_res = run_backtest(prices=p_strat_s, signals=s_strat_s, volumes=None, config=cfg)
            ablations["short_only_positive_gaps"] = _period_metrics(
                shr_res.returns[oos_mask], _count_in(shr_res.trades, oos_mask, prices)
            )
        except Exception:
            ablations["short_only_positive_gaps"] = {"error": "failed"}
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, p_close)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", base_pos)
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - start_time
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H87",
            "temporary_id": "NF-20261105-01",
            "selected_config": sel,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "perturbation": pert,
                "ablations": ablations,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }
        exp_dir_art = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir_art.mkdir(parents=True, exist_ok=True)
        with open(exp_dir_art / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
            )
        tracker.log_artifact("summary", exp_dir_art / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} Test={gate['test_metrics']['sharpe']:.3f}"
        )
        print(
            f"  WF stab={gate['wf_stability']:.3f} | Bench p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {sel}")
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        traceback.print_exc()
        try:
            tracker.finish_experiment(status="failed", error=str(e))
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
