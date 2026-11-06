"""NF-20261105-09 / H91 (pre-registered): Turn-of-month equity seasonality.

Recurring turn-of-month liquidity/flow effect (pension contributions, index
rebalancing, window dressing): equity returns are elevated around the turn of
the month. Long SPY (vol-targeted) during the turn-of-month window
(last trading day of month m + first `head_days` trading days of month m+1),
flat otherwise. New family dimension (calendar-seasonality / supply-flow
constraints), distinct from:
- NF-08/H90 FOMC event drift (single pre-scheduled macro announcement, not a
  recurring monthly calendar pattern).
- H18 overnight/intraday persistence (arbitrary days, price-derived).
- H87 opening-gap fill (price gap signal, single day).
H91 conditions on ex-ante calendar month boundaries, not price-derived signals.

Causality / timing (pre-registered): the turn-of-month window for day t is
computable from the calendar at close t (month membership and within-month
trading-day rank are known once t's close is observed). The engine applies
signals.shift(1), so the target set at close t earns the return t -> t+1 -- no
same-day look-ahead. Month membership requires no future returns.

Data: yfinance daily SPY 2010-01-01 -> 2026-10-31 (free, cached).
Splits: Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout, final ~20%).
Grid: head_days in {1..5} x vol_target in {0.10, 0.15} (10 combos); tail fixed
at 1 (last trading day of month). Selection = best train-only walk-forward
Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1%
ADV). Turnover concentrated at month turns (low).

Gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe>=1.0, >=200 trades,
PF>=1.3, max DD<=15%, WF stability test>=0.7*train when train>0, benchmark
p<=0.05 vs buy-hold SPY, IR>=0, perturbation min ratio>=0.5.
Rejection: OOS Sharpe<0.5, PF<1.1, max DD>15%, <200 trades.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

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

EXPERIMENT_NAME = "nf_20261105_09_turn_of_month"
EXPERIMENT_DESC = (
    "NF-20261105-09/H91: Turn-of-month equity seasonality on SPY. "
    "Vol-targeted long SPY during the ex-ante turn-of-month calendar window "
    "(last trading day of month m + first head_days trading days of month m+1), "
    "flat otherwise; 1-bar execution delay. Grid search on Train/WF; Test "
    "protected; gates on OOS Val+Test."
)

SPY = "SPY"
UNIVERSE = [SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

# Last trading day of each month (tail=1, fixed) + first head_days of next month.
HEAD_DAYS = [1, 2, 3, 4, 5]
TAIL_DAYS = 1
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

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


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    if len(prices.index[mask]) == 0:
        return 0
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def build_turn_window_mask(idx: pd.DatetimeIndex, head_days: int) -> pd.Series:
    """Strictly causal turn-of-month window membership known at close of day t.

    Window = last trading day of month m OR first `head_days` trading days of
    month m+1 (the period that contains t). Month membership and within-month
    trading-day rank are calendar-known at close t; no future returns used.

    Implemented by grouping the actual timestamps by calendar month: the last
    timestamp of each month group is the last trading day; cumcount within each
    month group gives the within-month trading-day rank (0-indexed).
    """
    periods = idx.to_period("M")
    s = pd.Series(idx)
    last_of_month = s.groupby(periods).transform("max")
    is_last = s == last_of_month
    is_last.index = idx
    cumcount = s.groupby(periods).cumcount()
    cumcount.index = idx
    is_head = cumcount < int(head_days)
    return (is_last | is_head).astype(bool)


def build_daily_targets(
    prices: pd.DataFrame,
    head_days: int = 3,
    vol_target: float = 0.15,
) -> pd.DataFrame:
    """Vol-targeted long SPY turn-of-month targets, strictly causal.

    target[t] = (vol_target / trailing realized SPY vol known at t) when day t
    is in the turn-of-month window, else 0. Engine applies target[t] to the
    return t -> t+1 (signals.shift(1)).
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SPY])
    if SPY not in prices.columns:
        return targets
    head_days = int(max(1, head_days))
    vol_target = float(max(0.01, vol_target))

    in_window = build_turn_window_mask(idx, head_days)

    spy_ret = prices[SPY].astype(float).pct_change()
    realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
    targets[SPY] = (pd.Series(in_window, index=idx).astype(float) * scale).clip(0.0, MAX_POS)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask, n_splits=WF_FOLDS_SELECTION) -> float:
    train_r = returns[train_mask].dropna()
    if len(train_r) < 120:
        return 0.0
    try:
        splits = walk_forward_splits(len(train_r), n_splits=n_splits)
    except Exception:
        return 0.0
    sharpes = []
    for _, te_idx in splits:
        r = train_r.iloc[te_idx].dropna()
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
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))

    wf_stab = _stability_test_vs_train(train_m["sharpe"], test_m["sharpe"])

    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

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
        "val_sharpe": float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0,
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "benchmark_p_value": bench_p,
        "information_ratio": ir,
        "worst_regime_sharpe": worst_regime,
        "passes": passes,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, opt_oos_sharpe):
    variants = {}
    for param in ["head_days", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            kw = dict(selected)
            if param == "head_days":
                kw[param] = int(max(1, round(base * factor)))
            else:
                kw[param] = float(max(0.01, min(0.5, base * factor)))
            if kw == selected:
                continue
            pos = build_daily_targets(prices, kw["head_days"], kw["vol_target"])
            res = run_backtest(prices=prices[[SPY]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={kw[param]}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid = [(h, vt) for h in HEAD_DAYS for vt in VOL_TARGETS]
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SPY],
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
            "grid": {"head_days": HEAD_DAYS, "tail_days": TAIL_DAYS, "vol_target": VOL_TARGETS},
            "grid_size": len(grid),
            "calendar": "ex-ante month boundaries (turn-of-month window)",
            "timing": "last day of month m + first head_days of month m+1; "
            "target at close t earns return t->t+1 (1-bar delay)",
        },
        data_sources={"source": "yahoo_daily_cached", "symbols": UNIVERSE, "interval": "1d"},
        compute_budget={"max_cpu_hours": 2.0, "grid_size": len(grid)},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-09/H91] started {exp_id}  grid_size={len(grid)}")

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
            f"[NF-09/H91] prices={prices.shape} train/val/test="
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
        for head_days, vol_target in grid:
            pos = build_daily_targets(prices, head_days, vol_target)
            res = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
            wf_sel = train_only_wf_sharpe(res.returns, train_mask)
            oos_r = res.returns[oos_mask].dropna()
            oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
            key = (head_days, vol_target)
            grid_results[key] = res
            grid_rows.append(
                {
                    "head_days": head_days,
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
            f"[NF-09/H91] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best = grid_df.iloc[0]
        sel = (int(best["head_days"]), float(best["vol_target"]))
        sel_result = grid_results[sel]
        selected = {"head_days": sel[0], "vol_target": sel[1]}

        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, bench_result)
        pert = perturbation_eval(selected, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, spy_prices)
        )
        # Random window ablation (same frequency of window days, deterministic)
        rng = np.random.default_rng(SEED)
        n_window_days = int(build_turn_window_mask(prices.index, sel[0]).sum())
        rand_mask = np.zeros(len(prices), dtype=bool)
        rand_idx = rng.choice(len(prices), size=min(n_window_days, len(prices)), replace=False)
        rand_mask[rand_idx] = True
        spy_ret = prices[SPY].astype(float).pct_change()
        realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
        scale = (sel[1] / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
        rand_pos = pd.DataFrame(
            {
                SPY: (pd.Series(rand_mask, index=prices.index).astype(float) * scale).clip(
                    0.0, MAX_POS
                )
            }
        )
        rand_res = run_backtest(prices=spy_prices, signals=rand_pos, volumes=None, config=cfg)
        ablations["random_window_days"] = _period_metrics(
            rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
        )
        # Always-flat ablation
        flat_pos = pd.DataFrame(0.0, index=prices.index, columns=[SPY])
        flat_res = run_backtest(prices=spy_prices, signals=flat_pos, volumes=None, config=cfg)
        ablations["always_flat"] = _period_metrics(
            flat_res.returns[oos_mask], _count_in(flat_res.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", build_daily_targets(prices, sel[0], sel[1]))
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261105-09/H91",
            "selected_config": selected,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": len(grid),
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "calendar": {
                "source": "ex-ante month boundaries (turn-of-month window)",
                "coverage": [DATA_START, DATA_END],
            },
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
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | total {total_elapsed / 60:.1f} min"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        tracker.finish_experiment(status="failed", error=str(e))
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
