"""
NF-20261105-07 / H89 (pre-registration): CBOE SKEW tail-risk regime equity timing.

New strategy family dimension (volatility/convexity premia — implied tail/skew),
distinct from prior repository families:
- H86 (NF-20261104-01) times SPY using VIX term-structure slope (VIX3M/VIX).
- H17 trades SVXY on VRP gated by VIX level/contango.
- H3/H5/H6 use VIX level/regime gates on momentum.
NF-07 uses ^SKEW (implied S&P 500 return-distribution skewness/tail pricing), a
different options-surface observable and tail-risk/complacency mechanism.

Mechanism: elevated trailing SKEW z-score indicates richer implied tail-risk
pricing / crashophobia; reduce SPY exposure (long/flat baseline) in that regime
and hold vol-targeted long SPY otherwise. Position decided at close t, applied
to return t+1 (causal).

Data: yfinance daily via DataFetcher.fetch_yahoo (^SKEW, SPY), 2015-01-01 onward.
Protected holdout final segment (Test 2023-01-01+). Train/Val/Test by time.

Pre-registered gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe >= 1.0,
>= 200 trades, PF >= 1.3, max DD <= 15%, WF stability (test >= 0.7*train when
train>0), benchmark p<=0.05 vs buy-hold SPY, IR>=0, perturbation min ratio>=0.5.
Rejection: OOS Sharpe < 0.5, PF < 1.1, max DD > 15%, < 200 trades.
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
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_07_skew_tail_timing"
EXPERIMENT_DESC = (
    "NF-20261105-07/H89: CBOE SKEW tail-risk regime equity timing. "
    "Daily long/flat SPY: flat when trailing SKEW z-score elevated (risk-off), "
    "vol-targeted long otherwise; hysteresis. Grid over lookback/entry/exit/vol_target. "
    "Train/Val/Test by time; Test protected; gates on OOS Val+Test."
)

SKEW = "^SKEW"
SPY = "SPY"
UNIVERSE = [SKEW, SPY]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

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

LOOKBACKS = [63, 126, 252]
ENTRY_ZS = [0.5, 1.0, 1.5]
EXIT_ZS = [-0.5, 0.0, 0.5]
VOL_TARGETS = [0.10, 0.15]

WF_FOLDS_SELECTION = 4
WF_FOLDS_STABILITY = 5


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
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


def skew_zscore(skew: pd.Series, lookback: int) -> pd.Series:
    min_p = int(min(lookback, max(21, lookback // 3)))
    mu = skew.rolling(lookback, min_periods=min_p).mean()
    sd = skew.rolling(lookback, min_periods=min_p).std().replace(0, np.nan)
    return (skew - mu) / sd


def build_daily_targets(
    prices: pd.DataFrame,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    """Long/flat SPY target weights from trailing SKEW z-score, strictly causal.

    Position state decided from z_t (close t), applied at t+1 via shift(1).
    Vol targeting uses trailing SPY realized vol (causal).
    """
    targets = pd.DataFrame(0.0, index=prices.index, columns=[SPY])
    if SKEW not in prices.columns or SPY not in prices.columns:
        return targets
    if exit_z >= entry_z:
        return targets

    z = skew_zscore(prices[SKEW].astype(float), lookback)
    state = pd.Series(np.nan, index=prices.index, dtype=float)
    current = 1.0  # default long until enough history / signal
    for i in range(len(prices.index)):
        zi = z.iloc[i]
        if np.isfinite(zi):
            if zi >= entry_z:
                current = 0.0
            elif zi <= exit_z:
                current = 1.0
        state.iloc[i] = current
    state_delayed = state.shift(1).fillna(0.0)

    spy_ret = prices[SPY].astype(float).pct_change()
    realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)

    targets[SPY] = (state_delayed * scale).clip(0.0, MAX_POS)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask, n_splits=WF_FOLDS_SELECTION) -> float:
    train_r = returns[train_mask].dropna()
    if len(train_r) < 120:
        return 0.0
    try:
        splits = walk_forward_splits(train_r, n_splits=n_splits, expanding=True)
    except Exception:
        return 0.0
    sharpes = []
    for _, te in splits:
        r = te.dropna()
        if len(r) > 20:
            sharpes.append(float(sharpe_ratio(r.values)))
    return float(np.mean(sharpes)) if sharpes else 0.0


def _stability_test_vs_train(train_sharpe: float, test_sharpe: float) -> float:
    if train_sharpe > 0:
        return test_sharpe / train_sharpe
    if train_sharpe == 0:
        return test_sharpe
    return 0.0


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result):
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

    wf_stab = _stability_test_vs_train(train_m["sharpe"], test_m["sharpe"])

    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

    # Worst regime (simple): worst rolling-252 Sharpe on OOS
    worst_regime = 0.0
    if len(oos_r) >= 252:
        roll = oos_r.rolling(252).apply(lambda x: sharpe_ratio(x.values), raw=False)
        worst_regime = float(roll.min()) if roll.notna().any() else 0.0
    else:
        worst_regime = oos_m["sharpe"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
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
        "worst_regime_sharpe": worst_regime,
        "passes": passes,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, opt_oos_sharpe):
    variants = {}
    for param in ["lookback", "entry_z", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            v = base * factor
            if abs(v - base) < 1e-12:
                continue
            kw = dict(selected)
            if param == "lookback":
                kw[param] = int(max(21, round(v)))
            elif param == "vol_target":
                kw[param] = float(max(0.01, min(0.5, v)))
            else:
                kw[param] = float(v)
            if kw["exit_z"] >= kw["entry_z"]:
                continue
            pos = build_daily_targets(
                prices, kw["lookback"], kw["entry_z"], kw["exit_z"], kw["vol_target"]
            )
            res = run_backtest(prices=prices[[SPY]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    elif variants and opt_oos_sharpe <= 0:
        min_ratio = 0.0
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    valid_grid = [
        (l, e, x, vt)
        for l in LOOKBACKS
        for e in ENTRY_ZS
        for x in EXIT_ZS
        for vt in VOL_TARGETS
        if x < e
    ]
    grid_size = len(valid_grid)
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
                "entry_z": ENTRY_ZS,
                "exit_z": EXIT_ZS,
                "vol_target": VOL_TARGETS,
            },
            "grid_size": grid_size,
            "selection": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "construction": "long/flat SPY; flat when SKEW z >= entry_z, long when <= exit_z (hysteresis); 1-bar delay; vol-targeted",
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": UNIVERSE,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-07/H89] started {exp_id}  grid_size={grid_size}")

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
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index().dropna(how="any")

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[NF-07/H89] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_equity_config()
        spy_prices = prices[[SPY]]
        bench_weights = pd.DataFrame(1.0, index=prices.index, columns=[SPY])
        bench_result = run_backtest(
            prices=spy_prices, signals=bench_weights, volumes=None, config=cfg
        )

        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lookback, entry_z, exit_z, vol_target in valid_grid:
            pos = build_daily_targets(prices, lookback, entry_z, exit_z, vol_target)
            res = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
            wf_sel = train_only_wf_sharpe(res.returns, train_mask)
            oos_r = res.returns[oos_mask].dropna()
            oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
            key = (lookback, entry_z, exit_z, vol_target)
            grid_results[key] = res
            grid_rows.append(
                {
                    "lookback": lookback,
                    "entry_z": entry_z,
                    "exit_z": exit_z,
                    "vol_target": vol_target,
                    "train_wf_sharpe": wf_sel,
                    "train_sharpe": float(sharpe_ratio(res.returns[train_mask].dropna().values))
                    if train_mask.sum() > 1
                    else 0.0,
                    "val_sharpe": float(sharpe_ratio(res.returns[val_mask].dropna().values))
                    if val_mask.sum() > 1
                    else 0.0,
                    "test_sharpe": float(sharpe_ratio(res.returns[test_mask].dropna().values))
                    if test_mask.sum() > 1
                    else 0.0,
                    "oos_sharpe": oos_sr,
                }
            )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-07/H89] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best = grid_df.iloc[0]
        sel = (
            int(best["lookback"]),
            float(best["entry_z"]),
            float(best["exit_z"]),
            float(best["vol_target"]),
        )
        sel_result = grid_results[sel]
        selected = {
            "lookback": sel[0],
            "entry_z": sel[1],
            "exit_z": sel[2],
            "vol_target": sel[3],
        }

        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, bench_result)
        pert = perturbation_eval(selected, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        inv_pos = build_daily_targets(prices, sel[0], -sel[1], -sel[2], sel[3])
        inv_res = run_backtest(prices=spy_prices, signals=inv_pos, volumes=None, config=cfg)
        ablations["inverse_threshold_rule"] = _period_metrics(
            inv_res.returns[oos_mask], _count_in(inv_res.trades, oos_mask, prices)
        )
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, spy_prices)
        )
        # Randomized state ablation (deterministic seed)
        rng = np.random.default_rng(SEED)
        rand_state = pd.Series(
            rng.integers(0, 2, size=len(prices)), index=prices.index, dtype=float
        )
        spy_ret = prices[SPY].astype(float).pct_change()
        realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
        scale = (sel[3] / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
        rand_pos = pd.DataFrame(
            {(SPY): (rand_state.shift(1).fillna(0.0) * scale).clip(0.0, MAX_POS)},
            index=prices.index,
        )
        rand_res = run_backtest(prices=spy_prices, signals=rand_pos, volumes=None, config=cfg)
        ablations["random_state_ablation"] = _period_metrics(
            rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals",
            build_daily_targets(prices, sel[0], sel[1], sel[2], sel[3]),
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261105-07/H89",
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
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
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
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} "
            f"Test={gate['test_metrics']['sharpe']:.3f}"
        )
        print(
            f"  WF stab={gate['wf_stability']:.3f} | Bench p={gate['benchmark_p_value']:.4f} "
            f"IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | "
            f"total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        tracker.finish_experiment(status="failed", notes=str(e))
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
