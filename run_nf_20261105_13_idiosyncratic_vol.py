"""NF-20261105-13 / H93 (pre-registered): Idiosyncratic-volatility cross-section timing.

Lottery-demand / low-idiosyncratic-volatility premium: investors overpay for
lottery-like (high-idiosyncratic-volatility) names, so high idiosyncratic
volatility predicts low future risk-adjusted returns (Ang, Hodrick, Xing &
Zhang 2006). Each month, rank liquid ETFs by trailing idiosyncratic volatility
vs SPY (rolling residual std of symbol-minus-SPY daily returns), long the
low-IVOL quintile, short the high-IVOL quintile, equal-weight within legs,
vol-targeted to `vol_target` annualized. Rebalances monthly (last trading day
of each month); the engine applies signals.shift(1), so the target set at close
t earns the return t -> t+1 -- strictly causal, no same-day look-ahead.

New family dimension (cross-section risk premium / limits of arbitrage), distinct
from:
- H2/H16 cross-sectional momentum (own-past-return *trend* ranking; IVOL is a
  risk/lottery measure, not a trend signal, and the sign is opposite: low IVOL
  is favored, not recent winners).
- H17 VRP (single vol vehicle SVXY timed by the spot-VIX *level*; not a
  cross-sectional IVOL spread).
- H86/H89 (vol-surface/tail-shape signals on SPY; not cross-sectional IVOL).
- H91 calendar seasonality (ex-ante month boundaries; not an IVOL signal).

Data: yfinance daily (free, cached), 2010-01-01 -> 2026-10-31.
Universe: SPY (market proxy, excluded from the tradable book) + 12 liquid ETFs
across equities/bonds/commodities/FX/intl (same liquid universe as H1-H3).
Splits: Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout, final ~20%).
Grid: ivol_lookback in {63,126,252} x quintile_share in {0.2,0.33} x
vol_target in {0.10,0.15} = 12 combos. Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity defaults (1 bp commission + 0.5 bp spread + 0.1 bp impact
per 1% ADV). Max position 0.5 per name, max leverage 1.0, shorts allowed.
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
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_13_idiosyncratic_vol"
EXPERIMENT_DESC = (
    "NF-20261105-13/H93: Idiosyncratic-volatility cross-section timing. "
    "Monthly long low-IVOL / short high-IVOL ETF quintiles (IVOL vs SPY), "
    "vol-targeted, 1-bar execution delay. Grid search on Train/WF; Test "
    "protected; gates on OOS Val+Test."
)

SPY = "SPY"
UNIVERSE = [
    "QQQ",
    "IWM",
    "EFA",
    "EEM",
    "VWO",
    "TLT",
    "AGG",
    "HYG",
    "GLD",
    "USO",
    "VNQ",
    "XLB",
]
TRADEABLE = list(UNIVERSE)  # SPY is the market proxy only, not traded

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
MAX_LEVERAGE = 1.0

IVOL_LOOKBACKS = [63, 126, 252]
QUINTILE_SHARES = [0.2, 0.33]
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
        max_leverage=MAX_LEVERAGE,
        allow_short=True,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    sr = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if len(r) > 0:
        cum = (1 + r).cumprod()
        dd = float((cum / cum.cummax() - 1.0).min())
        gp = float(r[r > 0].sum())
        gl = float(abs(r[r < 0].sum()))
    else:
        dd, gp, gl = 0.0, 0.0, 0.0
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


def _month_end_dates(idx: pd.DatetimeIndex) -> list:
    s = pd.Series(idx, index=idx)
    return list(s.groupby([s.index.year, s.index.month]).apply(lambda x: x.max()).sort_values())


def build_ivol_targets(
    prices: pd.DataFrame,
    ivol_lookback: int,
    quintile_share: float,
    vol_target: float,
) -> pd.DataFrame:
    """Monthly long low-IVOL / short high-IVOL targets vs SPY.

    ivol[s][t] = rolling std of (rets[s] - rets[SPY]) over ivol_lookback *
    sqrt(252), computed from prices through close t (past-only). At each month
    end the symbols are ranked by current IVOL; the bottom quintile_share get
    side +1, the top quintile_share side -1, the middle 0. Weights are held
    constant until the next month end. Per-symbol scale = vol_target /
    trailing 21-day realized vol, clipped to [0, MAX_POS]. No look-ahead: the
    month-end IVOL and realized vol are knowable at that close; the engine
    shifts targets by one bar so close t targets earn t -> t+1.
    """
    idx = prices.index
    targets = pd.DataFrame(np.nan, index=idx, columns=TRADEABLE)
    if SPY not in prices.columns:
        return targets.fillna(0.0)
    ivol_lookback = int(max(10, ivol_lookback))
    vol_target = float(max(0.01, vol_target))
    quintile_share = float(max(0.05, min(0.5, quintile_share)))

    rets = prices.pct_change()
    spy_ret = rets[SPY].astype(float)
    ivol_cols = {}
    for s in TRADEABLE:
        if s not in prices.columns:
            continue
        res = rets[s].astype(float) - spy_ret
        ivol_cols[s] = res.rolling(ivol_lookback).std() * np.sqrt(252.0)
    ivol_df = pd.DataFrame(ivol_cols, index=idx)

    realized = rets[TRADEABLE].rolling(21, min_periods=21).std() * np.sqrt(252.0)
    realized = realized.reindex(index=idx)

    rebalance = _month_end_dates(idx)
    for d in rebalance:
        if d not in ivol_df.index:
            continue
        row = ivol_df.loc[d].dropna()
        if len(row) < 4:
            rebalance_row = pd.Series(0.0, index=TRADEABLE)
            targets.loc[d] = rebalance_row
            continue
        k = max(1, int(round(len(row) * quintile_share)))
        ranked = row.sort_values()
        long_syms = list(ranked.index[:k])
        short_syms = list(ranked.index[-k:])
        day_realized = realized.loc[d] if d in realized.index else pd.Series(dtype=float)
        rebalance_row = pd.Series(0.0, index=TRADEABLE)
        for s in long_syms:
            scale = (
                float(vol_target / day_realized[s])
                if s in day_realized.index and np.isfinite(day_realized[s]) and day_realized[s] > 0
                else 0.0
            )
            rebalance_row[s] = float(np.clip(scale, 0.0, MAX_POS))
        for s in short_syms:
            scale = (
                float(vol_target / day_realized[s])
                if s in day_realized.index and np.isfinite(day_realized[s]) and day_realized[s] > 0
                else 0.0
            )
            rebalance_row[s] = -float(np.clip(scale, 0.0, MAX_POS))
        targets.loc[d] = rebalance_row

    targets = targets.reindex(idx).ffill().fillna(0.0)
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
        "p_value": benchmark_significance_gate(bench_p, ir, GATES["max_p_value"]),
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
    for param in ["ivol_lookback", "vol_target", "quintile_share"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            kw = dict(selected)
            if param == "ivol_lookback":
                kw[param] = int(max(10, round(base * factor)))
            elif param == "quintile_share":
                kw[param] = float(max(0.05, min(0.5, base * factor)))
            else:
                kw[param] = float(max(0.01, min(0.5, base * factor)))
            if kw == selected:
                continue
            pos = build_ivol_targets(
                prices, kw["ivol_lookback"], kw["quintile_share"], kw["vol_target"]
            )
            res = run_backtest(prices=prices[TRADEABLE], signals=pos, volumes=None, config=cfg)
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
    print(" NF-20261105-13 / H93: Idiosyncratic-volatility cross-section timing")
    print("=" * 72)
    print(
        f"  Tradable universe: {TRADEABLE}  |  market proxy: {SPY}  |  {DATA_START} -> {DATA_END}"
    )

    np.random.seed(SEED)

    cache_dir = Path(".cache") / "nf_20261105_13_h93" / str(int(time.time()))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = DataCache(cache_dir=cache_dir)
    fetcher = DataFetcher(cache=cache)

    symbols = [SPY] + TRADEABLE
    data = fetcher.fetch_yahoo(symbols, start=DATA_START, end=DATA_END)
    prices_list = []
    for sym in symbols:
        df = data.get(sym, pd.DataFrame())
        if len(df) == 0:
            raise RuntimeError(f"no data for universe symbol {sym}")
        prices_list.append(df["close"].rename(sym))
    prices = pd.concat(prices_list, axis=1, sort=True).sort_index().dropna(how="any")
    print(f"  Prices: {prices.shape}")

    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    print(f"  Train {train_mask.sum()} | Val {val_mask.sum()} | Test {test_mask.sum()}")

    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "hypothesis": "NF-20261105-13/H93 idiosyncratic-volatility cross-section timing",
            "universe": symbols,
            "data_window": [DATA_START, DATA_END],
            "splits": {
                "train": [DATA_START, TRAIN_END],
                "val": [TRAIN_END, VAL_END],
                "test_protected": [VAL_END, DATA_END],
            },
            "grid": {
                "ivol_lookback": IVOL_LOOKBACKS,
                "quintile_share": QUINTILE_SHARES,
                "vol_target": VOL_TARGETS,
            },
            "selection": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "gates": GATES,
        },
        data_sources={"source": "yahoo_daily_cached", "symbols": symbols, "interval": "1d"},
        compute_budget={
            "max_cpu_hours": 2.0,
            "grid_size": len(IVOL_LOOKBACKS) * len(QUINTILE_SHARES) * len(VOL_TARGETS),
        },
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-13/H93] started {exp_id}")

    try:
        bench_pos = pd.DataFrame(1.0 / len(TRADEABLE), index=prices.index, columns=TRADEABLE)
        bench_result = run_backtest(
            prices=prices[TRADEABLE], signals=bench_pos, volumes=None, config=make_equity_config()
        )

        grid_rows = []
        best = None
        t0 = time.time()
        grid = [
            (lb, qs, vt) for lb in IVOL_LOOKBACKS for qs in QUINTILE_SHARES for vt in VOL_TARGETS
        ]
        for i, (ivol_lookback, quintile_share, vol_target) in enumerate(grid, 1):
            cfg = make_equity_config()
            pos = build_ivol_targets(prices, ivol_lookback, quintile_share, vol_target)
            result = run_backtest(prices=prices[TRADEABLE], signals=pos, volumes=None, config=cfg)
            sel_score = train_only_wf_sharpe(result.returns, train_mask)
            tr_m = _period_metrics(
                result.returns[train_mask],
                _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices),
            )
            va_m = _period_metrics(
                result.returns[val_mask], _count_in(result.trades, val_mask, prices)
            )
            row = {
                "ivol_lookback": ivol_lookback,
                "quintile_share": quintile_share,
                "vol_target": vol_target,
                "selection_train_wf_sharpe": sel_score,
                "train_sharpe": tr_m["sharpe"],
                "val_sharpe": va_m["sharpe"],
                "train_trades": tr_m["trades"],
                "val_trades": va_m["trades"],
                "train_pf": tr_m["profit_factor"],
            }
            grid_rows.append(row)
            key = (ivol_lookback, quintile_share, vol_target)
            if best is None or sel_score > best[0]:
                best = (sel_score, key, result, cfg)
            if i % 4 == 0:
                print(f"  grid {i}/{len(grid)} ({time.time() - t0:.1f}s)")

        grid_df = pd.DataFrame(grid_rows).sort_values("selection_train_wf_sharpe", ascending=False)
        tracker.log_dataframe("grid_results", grid_df)
        grid_elapsed = time.time() - t0
        _, sel, sel_result, cfg = best
        selected = {"ivol_lookback": sel[0], "quintile_share": sel[1], "vol_target": sel[2]}

        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, bench_result)
        pert = perturbation_eval(selected, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        ablations["equal_weight_universe_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, prices)
        )
        # Random-side ablation: same long/short exposure frequency, random assignment.
        rng = np.random.default_rng(SEED)
        base_pos = build_ivol_targets(prices, sel[0], sel[1], sel[2])
        rand_pos = base_pos.copy()
        for d in _month_end_dates(prices.index):
            if d not in rand_pos.index:
                continue
            row = rand_pos.loc[d]
            active_syms = row.index[row.abs() > 1e-12]
            if len(active_syms) == 0:
                continue
            k_long = int((row > 1e-12).sum())
            n_active = len(active_syms)
            pick = rng.choice(active_syms, size=n_active, replace=False)
            new_row = pd.Series(0.0, index=row.index)
            new_row[pick[:k_long]] = row[pick[:k_long]].abs()
            if k_long < n_active:
                new_row[pick[k_long:]] = -row[pick[k_long:]].abs()
            rand_pos.loc[d] = new_row
        rand_pos = rand_pos.reindex(prices.index).ffill().fillna(0.0)
        rand_res = run_backtest(
            prices=prices[TRADEABLE], signals=rand_pos, volumes=None, config=cfg
        )
        ablations["random_side"] = _period_metrics(
            rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
        )
        # Long-only ablation (low IVOL only, no short leg).
        lon_only = build_ivol_targets(prices, sel[0], sel[1], sel[2]).clip(lower=0.0)
        lon_res = run_backtest(prices=prices[TRADEABLE], signals=lon_only, volumes=None, config=cfg)
        ablations["long_only_low_ivol"] = _period_metrics(
            lon_res.returns[oos_mask], _count_in(lon_res.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_ivol_targets(prices, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261105-13/H93",
            "selected_config": selected,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": len(grid),
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "signal": {
                "type": "idiosyncratic volatility vs SPY cross-section (long low-IVOL, short high-IVOL)",
                "causal": "month-end IVOL and realized vol knowable at that close; engine shift(1) earns t->t+1",
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
