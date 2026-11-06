"""NF-20261105-10 / H92 (pre-registered): Equity/bond relative-momentum risk-premium timing.

The equity risk premium relative to bonds is time-varying: when equities have
outperformed Treasuries over a trailing window, the risk premium is elevated and
the cross-asset relative momentum persists into the next window. A vol-targeted
long SPY position when the equity/bond relative momentum is positive (and short
when negative, if allow_short) clears the PROMPT_V2 gates on OOS Val+Test.

New family dimension (cross-asset risk premium / relative momentum), distinct
from:
- H86 VIX term-structure slope equity timing (ATM vol term structure signal).
- H89 SKEW tail-risk regime (implied skewness/tail shape signal).
- H91 turn-of-month calendar seasonality (ex-ante calendar boundaries).
- H2/H16 cross-sectional momentum (own-past-return ranking within equities).
H92 conditions on the *relative performance of equities vs bonds* -- a
cross-asset risk-premium signal, not an equity-only trend, vol, or calendar
signal.

Causality / timing (pre-registered): the relative-momentum signal for day t is
computable from prices observed through close t (trailing window of
close-to-close returns, past-only). The engine applies signals.shift(1), so the
target set at close t earns the return t -> t+1 -- no same-day look-ahead.

Data: yfinance daily SPY + TLT (free, cached), 2010-01-01 -> 2026-10-31.
Splits: Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout, final ~20%).
Grid: lookback in {21,63,126,252} x vol_target in {0.10,0.15} x
allow_short in {False, True} (16 combos). Selection = best train-only
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1%
ADV). Turnover moderate (weekly-ish rebalance at lookback=21).

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

EXPERIMENT_NAME = "nf_20261105_10_equity_bond_relmom"
EXPERIMENT_DESC = (
    "NF-20261105-10/H92: Equity/bond relative-momentum risk-premium timing. "
    "Vol-targeted long SPY when trailing SPY-vs-TLT relative momentum is "
    "positive (short when negative if allow_short), 1-bar execution delay. "
    "Grid search on Train/WF; Test protected; gates on OOS Val+Test."
)

SPY = "SPY"
TLT = "TLT"
UNIVERSE = [SPY, TLT]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [21, 63, 126, 252]
VOL_TARGETS = [0.10, 0.15]
ALLOW_SHORT = [False, True]
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


def make_equity_config(allow_short: bool) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=allow_short,
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


def build_relmom_targets(
    prices: pd.DataFrame,
    lookback: int,
    vol_target: float,
    allow_short: bool,
) -> pd.DataFrame:
    """Vol-targeted SPY targets from trailing SPY-vs-TLT relative momentum.

    relmom[t] = (SPY return over lookback) - (TLT return over lookback),
    computed from close[t-lookback]..close[t] (past-only). Sign of relmom sets
    the SPY side; engine applies signals.shift(1) so the target at close t earns
    the return t -> t+1. No same-day look-ahead: relmom[t] uses only prices
    through close[t].
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SPY])
    if SPY not in prices.columns or TLT not in prices.columns:
        return targets
    lookback = int(max(2, lookback))
    vol_target = float(max(0.01, vol_target))

    spy_ret = prices[SPY].astype(float).pct_change()
    tlt_ret = prices[TLT].astype(float).pct_change()
    # Cumulative window return from close[t-lookback] to close[t].
    spy_window = (1.0 + spy_ret).rolling(lookback).apply(lambda x: np.prod(x) - 1.0, raw=True)
    tlt_window = (1.0 + tlt_ret).rolling(lookback).apply(lambda x: np.prod(x) - 1.0, raw=True)
    relmom = spy_window - tlt_window

    realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)

    side = pd.Series(1.0, index=idx)
    if allow_short:
        side = side.where(relmom >= 0, -1.0)
    else:
        side = side.where(relmom >= 0, 0.0)
    targets[SPY] = (side * scale).clip(-MAX_POS if allow_short else 0.0, MAX_POS)
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
    for param in ["lookback", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            kw = dict(selected)
            if param == "lookback":
                kw[param] = int(max(2, round(base * factor)))
            else:
                kw[param] = float(max(0.01, min(0.5, base * factor)))
            if kw == selected:
                continue
            pos = build_relmom_targets(prices, kw["lookback"], kw["vol_target"], kw["allow_short"])
            res = run_backtest(prices=prices[[SPY]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={kw[param]}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    t_start = time.time()
    print("=" * 72)
    print(" NF-20261105-10 / H92: Equity/bond relative-momentum risk-premium timing")
    print("=" * 72)
    print(f"  Universe: {UNIVERSE}  |  {DATA_START} -> {DATA_END}")

    np.random.seed(SEED)

    cache_dir = Path(".cache") / "nf_20261105_10_h92" / str(int(time.time()))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = DataCache(cache_dir=cache_dir)
    fetcher = DataFetcher(cache=cache)

    data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END)
    prices_list = []
    for sym in UNIVERSE:
        df = data.get(sym, pd.DataFrame())
        if len(df) == 0:
            raise RuntimeError(f"no data for universe symbol {sym}")
        prices_list.append(df["close"].rename(sym))
    prices = pd.concat(prices_list, axis=1, sort=True).sort_index().dropna(how="any")
    print(f"  Prices: {prices.shape}")

    spy_prices = prices[[SPY]]
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    print(f"  Train {train_mask.sum()} | Val {val_mask.sum()} | Test {test_mask.sum()}")

    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "hypothesis": "NF-20261105-10/H92 equity-bond relative-momentum risk-premium timing",
            "universe": UNIVERSE,
            "data_window": [DATA_START, DATA_END],
            "splits": {
                "train": [DATA_START, TRAIN_END],
                "val": [TRAIN_END, VAL_END],
                "test_protected": [VAL_END, DATA_END],
            },
            "grid": {
                "lookback": LOOKBACKS,
                "vol_target": VOL_TARGETS,
                "allow_short": ALLOW_SHORT,
            },
            "selection": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "gates": GATES,
        },
        data_sources={"source": "yahoo_daily_cached", "symbols": UNIVERSE, "interval": "1d"},
        compute_budget={
            "max_cpu_hours": 2.0,
            "grid_size": len(LOOKBACKS) * len(VOL_TARGETS) * len(ALLOW_SHORT),
        },
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-10/H92] started {exp_id}")

    try:
        bench_pos = pd.DataFrame(1.0, index=spy_prices.index, columns=[SPY])
        bench_result = run_backtest(
            prices=spy_prices,
            signals=bench_pos,
            volumes=None,
            config=make_equity_config(allow_short=False),
        )

        grid_rows = []
        best = None
        t0 = time.time()
        grid = [(lb, vt, sh) for lb in LOOKBACKS for vt in VOL_TARGETS for sh in ALLOW_SHORT]
        for i, (lookback, vol_target, allow_short) in enumerate(grid, 1):
            cfg = make_equity_config(allow_short)
            pos = build_relmom_targets(prices, lookback, vol_target, allow_short)
            result = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
            sel_score = train_only_wf_sharpe(result.returns, train_mask)
            tr_m = _period_metrics(
                result.returns[train_mask],
                _count_in(result.trades, train_mask, prices),
            )
            va_m = _period_metrics(
                result.returns[val_mask],
                _count_in(result.trades, val_mask, prices),
            )
            row = {
                "lookback": lookback,
                "vol_target": vol_target,
                "allow_short": allow_short,
                "selection_train_wf_sharpe": sel_score,
                "train_sharpe": tr_m["sharpe"],
                "val_sharpe": va_m["sharpe"],
                "train_trades": tr_m["trades"],
                "val_trades": va_m["trades"],
                "train_pf": tr_m["profit_factor"],
            }
            grid_rows.append(row)
            key = (lookback, vol_target, allow_short)
            if best is None or sel_score > best[0]:
                best = (sel_score, key, result, cfg)
            if i % 8 == 0:
                print(f"  grid {i}/{len(grid)} ({time.time() - t0:.1f}s)")

        grid_df = pd.DataFrame(grid_rows).sort_values("selection_train_wf_sharpe", ascending=False)
        tracker.log_dataframe("grid_results", grid_df)
        grid_elapsed = time.time() - t0
        _, sel, sel_result, cfg = best
        selected = {"lookback": sel[0], "vol_target": sel[1], "allow_short": sel[2]}

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
        # Random direction ablation (same frequency of long/short days, deterministic)
        rng = np.random.default_rng(SEED)
        base_pos = build_relmom_targets(prices, sel[0], sel[1], sel[2])
        active = base_pos[SPY].abs() > 1e-12
        n_active = int(active.sum())
        n_pos = int((base_pos[SPY] > 1e-12).sum())
        rand_side = np.zeros(len(prices), dtype=float)
        if n_active > 0:
            idxs = np.flatnonzero(active.values)
            pick = rng.choice(idxs, size=n_active, replace=False)
            pos_pick = pick[:n_pos] if sel[2] else pick
            rand_side[pos_pick] = 1.0
            if sel[2]:
                rand_side[pick[n_pos:]] = -1.0
        spy_ret = prices[SPY].astype(float).pct_change()
        realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
        scale = (sel[1] / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
        rand_pos = pd.DataFrame(
            {
                SPY: (pd.Series(rand_side, index=prices.index) * scale).clip(
                    -MAX_POS if sel[2] else 0.0, MAX_POS
                )
            }
        )
        rand_res = run_backtest(prices=spy_prices, signals=rand_pos, volumes=None, config=cfg)
        ablations["random_direction"] = _period_metrics(
            rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
        )
        # Long-only ablation when selected is short-allowed (and vice versa)
        alt_short = not sel[2]
        alt_cfg = make_equity_config(alt_short)
        alt_pos = build_relmom_targets(prices, sel[0], sel[1], alt_short)
        alt_res = run_backtest(prices=spy_prices, signals=alt_pos, volumes=None, config=alt_cfg)
        ablations[f"allow_short={alt_short}"] = _period_metrics(
            alt_res.returns[oos_mask], _count_in(alt_res.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_relmom_targets(prices, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261105-10/H92",
            "selected_config": selected,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": len(grid),
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "signal": {
                "type": "equity-bond relative momentum (SPY trailing return minus TLT trailing return)",
                "causal": "relmom at close t uses prices through t; engine shift(1) earns t->t+1",
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
