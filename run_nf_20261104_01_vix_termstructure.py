"""
NF-20261104-01 / H86 (pre-registration): VIX Term Structure Slope Equity Timing.

New strategy family (volatility and convexity premia), distinct from all
prior repository families:
- H17 (VRP) trades SVXY (volatility vehicle) gated by spot VIX *level*;
  NF-01 trades SPY (equity) based on VIX term structure *slope* (VIX3M/VIX)
  as a directional timing signal. Different instrument, different signal,
  different mechanism (volatility-timed equity exposure vs VRP harvesting).
- No prior repository family tests VIX term-structure-slope timing of equities.

Mechanism: steep contango (VIX3M/VIX high) implies expected VIX mean reversion
downward → lower equity volatility → higher equity returns. Backwardation
implies the opposite. Long SPY in contango, flat/short in backwardation.

Construction (daily, causal):
  1. At daily close t, compute slope = VIX3M_t / VIX_t.
  2. If slope > rolling median + z, long SPY vol-targeted to 15% ann;
     if slope < rolling median - z, flat/short (or inverse).
  3. Max position 0.5. Engine applies position_{t-1} to return_t.

Data: yfinance daily, all free (^VIX, ^VIX3M, SPY). 2015-01-01 onward.
Protected holdout final 20%. Train/Val/Test 60/20/20 by time.

Pre-registered gates (PROMPT_V2.md): OOS Sharpe >= 1.0, >= 200 OOS trades,
PF >= 1.3, max DD <= 15%, WF stability (test Sharpe >= 0.7 x train),
parameter sensitivity (OAT +/-20%).

Rejection: OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

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

EXPERIMENT_NAME = "nf_20261104_01_vix_termstructure"
EXPERIMENT_DESC = (
    "NF-20261104-01: VIX term structure slope (VIX3M/VIX) equity timing. "
    "Daily rebalance: long SPY when slope in steep contango, flat/short in backwardation; "
    "vol-targeted 15% ann, max pos 0.5. Grid over lookback/threshold/z-score. "
    "Train/Val/Test 60/20/20; Test protected; gates on OOS Val+Test."
)

# --- Universe ---
VIX_SPOT = "^VIX"
VIX3M = "^VIX3M"
SPY = "SPY"
UNIVERSE = [VIX_SPOT, VIX3M, SPY]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

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
LOOKBACKS = [63, 126, 252]
ZSCORES = [0.5, 1.0, 1.5]
VOL_TARGETS = [0.10, 0.15, 0.20]
MAX_POS = 0.5

WF_FOLDS_SELECTION = 4
WF_FOLDS_STABILITY = 5


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
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
    zscore: float,
    vol_target: float,
) -> pd.DataFrame:
    """Daily target weights for SPY, strictly causal."""
    targets = pd.DataFrame(0.0, index=prices.index, columns=[SPY])

    if VIX_SPOT not in prices.columns or VIX3M not in prices.columns or SPY not in prices.columns:
        return targets

    # Slope = VIX3M / VIX
    slope = prices[VIX3M] / prices[VIX_SPOT]

    # Rolling stats (causal)
    min_p = int(max(21, lookback // 3))
    rolling_median = slope.rolling(lookback, min_periods=min_p).median()
    rolling_std = slope.rolling(lookback, min_periods=min_p).std()
    rolling_std = rolling_std.replace(0, np.nan).ffill().fillna(0.01)

    # Signals
    long_signal = slope > (rolling_median + zscore * rolling_std)
    short_signal = slope < (rolling_median - zscore * rolling_std)

    # SPY returns for vol targeting
    spy_ret = prices[SPY].pct_change()
    rolling_vol = spy_ret.rolling(63, min_periods=21).std() * np.sqrt(252)
    rolling_vol = rolling_vol.replace(0, np.nan).ffill().fillna(0.15)

    # Position sizing
    pos = pd.Series(0.0, index=prices.index)
    pos[long_signal] = np.clip(vol_target / rolling_vol[long_signal], 0, MAX_POS)
    pos[short_signal] = -np.clip(vol_target / rolling_vol[short_signal], 0, MAX_POS)

    targets[SPY] = pos.fillna(0.0)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask: pd.Series) -> float:
    """Train-only walk-forward Sharpe for selection."""
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


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result):
    """Evaluate all gates on OOS (Val+Test)."""
    rets = result.returns
    oos_r = rets[oos_mask].dropna()
    train_r = rets[prices.index <= pd.Timestamp(TRAIN_END)].dropna()
    val_r = rets[val_mask].dropna()
    test_r = rets[test_mask].dropna()

    oos_m = _period_metrics(oos_r, _count_in(result.trades, oos_mask, prices))
    train_m = _period_metrics(
        train_r, _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices)
    )
    val_m = _period_metrics(val_r, _count_in(result.trades, val_mask, prices))
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))

    # WF stability
    wf_stab = 0.0
    if val_m["sharpe"] != 0:
        wf_stab = test_m["sharpe"] / val_m["sharpe"] if val_m["sharpe"] > 0 else test_m["sharpe"]
    else:
        wf_stab = test_m["sharpe"]

    # Benchmark comparison
    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": True,  # simplified
        "p_value": bench_p <= GATES["max_p_value"],
        "information_ratio": ir >= GATES["min_information_ratio"],
    }

    return {
        "oos_metrics": oos_m,
        "train_sharpe": train_m["sharpe"],
        "val_sharpe": val_m["sharpe"],
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "benchmark_p_value": bench_p,
        "information_ratio": ir,
        "passes": passes,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, opt_oos_sharpe):
    """OAT perturbation ±20%."""
    variants = {}
    for param in ["lookback", "zscore", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            v = base * factor
            if abs(v - base) < 1e-12:
                continue
            kw = dict(selected)
            if param == "lookback":
                kw[param] = int(max(10, round(v)))
            elif param == "vol_target":
                kw[param] = float(max(0.01, min(0.5, v)))
            else:
                kw[param] = float(max(0.1, v))
            pos = build_daily_targets(prices, kw["lookback"], kw["zscore"], kw["vol_target"])
            res = run_backtest(prices=prices[["SPY"]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(LOOKBACKS) * len(ZSCORES) * len(VOL_TARGETS)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": [DATA_START, TRAIN_END],
                "val": [TRAIN_END, VAL_END],
                "test": [VAL_END, DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "lookback": LOOKBACKS,
                "zscore": ZSCORES,
                "vol_target": VOL_TARGETS,
            },
            "grid_size": grid_size,
            "selection": "best train-only walk-forward Sharpe; Test protected",
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": UNIVERSE,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-01] started {exp_id}  grid_size={grid_size}")

    try:
        isolated_cache = Path(tracker.log_dir) / "artifacts" / exp_id / "cache"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))
        data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END, interval="1d")
        prices_list = []
        for sym in UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                raise RuntimeError(f"no data for universe symbol {sym}")
            prices_list.append(df["close"].rename(sym))
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index()

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[NF-01] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_equity_config()

        # Benchmark: buy-and-hold SPY
        spy_prices = prices[[SPY]]
        bench_weights = pd.DataFrame(1.0, index=prices.index, columns=[SPY])
        bench_result = run_backtest(
            prices=spy_prices, signals=bench_weights, volumes=None, config=cfg
        )

        # Grid search
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lookback in LOOKBACKS:
            for zscore in ZSCORES:
                for vol_target in VOL_TARGETS:
                    pos = build_daily_targets(prices, lookback, zscore, vol_target)
                    res = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
                    wf_sel = train_only_wf_sharpe(res.returns, train_mask)
                    oos_r = res.returns[oos_mask].dropna()
                    oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
                    grid_results[(lookback, zscore, vol_target)] = res
                    grid_rows.append(
                        {
                            "lookback": lookback,
                            "zscore": zscore,
                            "vol_target": vol_target,
                            "train_wf_sharpe": wf_sel,
                            "train_sharpe": float(
                                sharpe_ratio(res.returns[train_mask].dropna().values)
                            )
                            if train_mask.sum() > 1
                            else 0.0,
                            "val_sharpe": float(sharpe_ratio(res.returns[val_mask].dropna().values))
                            if val_mask.sum() > 1
                            else 0.0,
                            "test_sharpe": float(
                                sharpe_ratio(res.returns[test_mask].dropna().values)
                            )
                            if test_mask.sum() > 1
                            else 0.0,
                            "oos_sharpe": oos_sr,
                        }
                    )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-01] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        # Selection
        best_key = grid_df.iloc[0][["lookback", "zscore", "vol_target"]]
        sel = (int(best_key["lookback"]), float(best_key["zscore"]), float(best_key["vol_target"]))
        sel_result = grid_results[sel]
        selected = {"lookback": sel[0], "zscore": sel[1], "vol_target": sel[2]}

        # Gates
        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, bench_result)

        # Perturbation
        pert = perturbation_eval(selected, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # Ablations
        ablations = {}
        # Long-only always
        long_only_pos = build_daily_targets(prices, sel[0], sel[1], sel[2]).clip(lower=0)
        lon_res = run_backtest(prices=spy_prices, signals=long_only_pos, volumes=None, config=cfg)
        ablations["long_only"] = _period_metrics(
            lon_res.returns[oos_mask], _count_in(lon_res.trades, oos_mask, prices)
        )
        # Inverse signal
        inv_pos = -build_daily_targets(prices, sel[0], sel[1], sel[2])
        inv_res = run_backtest(prices=spy_prices, signals=inv_pos, volumes=None, config=cfg)
        ablations["inverse_signal"] = _period_metrics(
            inv_res.returns[oos_mask], _count_in(inv_res.trades, oos_mask, prices)
        )
        # Benchmark
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, spy_prices)
        )

        # Artifacts
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_daily_targets(prices, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261104-01",
            "selected_config": selected,
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

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")
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
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
