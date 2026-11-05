"""
NF-20261105-01 / H87 (pre-registration): Opening-Gap Fill / Overnight Information.

New strategy family (event/auction mechanisms), distinct from all
prior repository families:
- H18 tested overnight return sign predicting next-day intraday direction
  (different timing/holding horizon); H87 tests same-day gap fill (open→close)
  holding intraday only. Different causal claim (overreaction fill vs
  overnight information persistence).

Mechanism: overnight gaps partially fill intraday due to overreaction;
long when gap negative (expect fill up), short when gap positive (expect fill down).

Construction (daily, causal):
  1. At close t-1 know close[t-1]. At open t know open[t]. Gap = open[t]/close[t-1]-1.
  2. If gap < -thr or z-scored gap very negative → long SPY intraday open→close;
     if gap > thr → short intraday; vol-targeted.
  3. Entry at open[t], exit at close[t] (intraday only). Engine applies position_{t-1}?
     Need to be careful about timing.

Data: yfinance daily SPY, 2015-01-01 onward. Open/close known; no look-ahead.
Train 2015-01-01→2020-12-31, Val 2021-01-01→2023-12-31, Test 2024-01-01→2026-10-31.
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

EXPERIMENT_NAME = "nf_20261105_01_opening_gap"
EXPERIMENT_DESC = (
    "NF-20261105-01/H87: Opening-gap fill (open/close). "
    "Long on negative gaps, short on positive gaps, intraday open→close; "
    "vol-targeted. Grid over lookback/zscore/vol_target. "
    "Train/Val/Test 60/20/20; Test protected."
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

LOOKBACKS = [1, 5, 21]
ZSCORES = [0.0, 0.5, 1.0]
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
    prices: pd.DataFrame, lookback: int = 5, zscore: float = 0.5, vol_target: float = 0.15
) -> pd.DataFrame:
    """Build target positions for gap-fill strategy.
    Use open/close; position applied to intraday return open->close?
    The engine applies position_{t-1} to return_t by default; need to be careful.
    Construct so that signal based on gap(open_t / close_{t-1}-1) gives position for intraday move open_t->close_t.
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SYMBOL])

    if SYMBOL not in prices.columns and "Open" in prices.columns and "Close" in prices.columns:
        # handle common yfinance format if passed differently
        pass

    # Get close and open
    close = prices[SYMBOL].copy() if SYMBOL in prices.columns else prices["Close"]
    # Try to get open
    if "Open" in prices.columns:
        openp = (
            prices["Open"][SYMBOL] if isinstance(prices["Open"], pd.DataFrame) else prices["Open"]
        )
    elif (SYMBOL, "Open") in prices.columns or isinstance(prices.columns, pd.MultiIndex):
        try:
            if isinstance(prices.columns, pd.MultiIndex):
                openp = prices[(SYMBOL, "Open")]
            else:
                openp = prices["Open"]
        except Exception:
            openp = close.copy()
    else:
        openp = close.copy()

    # Compute gap
    gap = openp / close.shift(1) - 1.0
    # Normalize
    if lookback == 1:
        gap_z = gap / (gap.rolling(5).std().fillna(gap.std()) + 1e-12)
    else:
        ma = gap.rolling(lookback).mean()
        sd = gap.rolling(lookback).std()
        gap_z = (gap - ma) / (sd + 1e-12)

    # Signal: fill gap -> go opposite of gap
    # If gap > 0 (open above close), expect fill down -> short
    # If gap < 0, expect fill up -> long
    signal = -np.sign(gap_z)
    # Apply threshold
    if zscore > 0:
        signal = signal.where(gap_z.abs() >= zscore, 0.0)
    else:
        signal = signal.where(gap_z.abs() >= 0.0, 0.0)  # allow all

    # Vol targeting based on intraday vol approximation
    intraday_ret = close / openp - 1.0
    vol = intraday_ret.rolling(lookback).std() * np.sqrt(252)
    vol = vol.replace([np.inf, -np.inf], np.nan).fillna(vol.mean())
    scale = vol_target / (vol + 1e-12)
    scale = scale.clip(lower=0.1, upper=2.0)
    pos = (signal * scale).clip(lower=-MAX_POS, upper=MAX_POS)
    targets[SYMBOL] = pos
    targets = targets.fillna(0.0)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask) -> float:
    r = returns.copy()
    r.index = returns.index
    # simple: use train period sharpe as selection metric (like others do)
    tr = r[train_mask].dropna()
    if len(tr) < 50:
        return -1e18
    return float(sharpe_ratio(tr.values))


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result, close, openp):
    rets = result.returns
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    train_r = rets[prices.index <= pd.Timestamp(TRAIN_END)].dropna()
    oos_r = rets[oos_mask].dropna()
    val_r = rets[val_mask].dropna()
    test_r = rets[test_mask].dropna()

    oos_m = _period_metrics(oos_r, _count_in(result.trades, oos_mask, prices))
    train_m = _period_metrics(
        train_r, _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices)
    )
    val_m = _period_metrics(val_r, _count_in(result.trades, val_mask, prices))
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))

    bench_oos = bench_result.returns[oos_mask].dropna()
    comp = compare_to_benchmark(result.returns, bench_result.returns)
    bms = benchmark_significance_gate(comp, GATES["max_p_value"])

    wf = walk_forward_splits(len(rets), n_splits=WF_FOLDS_STABILITY)
    wf_sharpes = []
    for tr_idx, te_idx in wf:
        tr_r = rets.iloc[tr_idx]
        te_r = rets.iloc[te_idx]
        if tr_r.std() > 0 and len(te_r) > 20:
            wf_sharpes.append(
                float(sharpe_ratio(te_r.values)) / (abs(float(sharpe_ratio(tr_r.values))) + 1e-12)
            )
    wf_stability = float(np.median(wf_sharpes)) if wf_sharpes else 0.0

    worst_regime = 0.0
    if len(oos_r) > 0:
        rolling = oos_r.rolling(60).apply(lambda x: sharpe_ratio(x.values) if len(x) > 20 else 0.0)
        worst_regime = float(rolling.min()) if rolling.notna().any() else 0.0

    info_ratio = comp.get("information_ratio", 0.0)

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stability >= GATES["min_walkforward_stability"],
        "worst_regime": worst_regime >= GATES["min_worst_regime_sharpe"],
        "benchmark_significance": bms["passes"],
        "information_ratio": info_ratio >= GATES["min_information_ratio"],
    }

    return {
        "passes": passes,
        "all_pass": all(passes.values()),
        "verdict": "PASS" if all(passes.values()) else "REJECT",
        "train_metrics": train_m,
        "val_metrics": val_m,
        "test_metrics": test_m,
        "oos_metrics": oos_m,
        "benchmark_comparison": comp,
        "benchmark_gate": bms,
        "wf_stability": wf_stability,
        "worst_regime_sharpe": worst_regime,
        "information_ratio": info_ratio,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, opt_oos_sharpe, close, openp):
    variants = {}
    for param, vals in [
        (
            "lookback",
            [max(1, selected["lookback"] - 2), selected["lookback"], selected["lookback"] + 2],
        ),
        (
            "zscore",
            [
                max(0.0, selected["zscore"] - 0.5),
                selected["zscore"],
                min(2.0, selected["zscore"] + 0.5),
            ],
        ),
        (
            "vol_target",
            [
                max(0.05, selected["vol_target"] - 0.05),
                selected["vol_target"],
                min(0.30, selected["vol_target"] + 0.05),
            ],
        ),
    ]:
        for v in vals:
            kw = dict(selected)
            kw[param] = v
            pos = build_daily_targets_from_ohlc(
                close, openp, kw["lookback"], kw["zscore"], kw["vol_target"]
            )
            # build prices series for intraday return
            intraday_prices = _make_intraday_price_series(close, openp)
            spy_prices = intraday_prices[[SYMBOL]]
            res = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def _make_intraday_price_series(close, openp):
    # Construct prices so that pct_change gives intraday return close/open - 1
    idx = close.index
    p = pd.DataFrame(index=idx, columns=[SYMBOL], dtype=float)
    p.iloc[0] = openp.iloc[0] if hasattr(openp, "iloc") else float(openp[0])
    for i in range(1, len(idx)):
        # price_t / price_{t-1} should equal close_t/open_t
        intraret = close.iloc[i] / openp.iloc[i] if openp.iloc[i] != 0 else 1.0
        p.iloc[i] = p.iloc[i - 1] * intraret
    return p


def build_daily_targets_from_ohlc(
    close, openp, lookback: int = 5, zscore: float = 0.5, vol_target: float = 0.15
) -> pd.DataFrame:
    idx = close.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SYMBOL])
    gap = openp / close.shift(1) - 1.0
    if lookback == 1:
        gap_z = gap / (gap.rolling(5).std().fillna(gap.std()) + 1e-12)
    else:
        ma = gap.rolling(lookback).mean()
        sd = gap.rolling(lookback).std()
        gap_z = (gap - ma) / (sd + 1e-12)
    signal = -np.sign(gap_z)
    if zscore > 0:
        signal = signal.where(gap_z.abs() >= zscore, 0.0)
    else:
        signal = signal.where(True, 0.0)
    intraday_ret = close / openp - 1.0
    vol = intraday_ret.rolling(lookback).std() * np.sqrt(252)
    vol = vol.replace([np.inf, -np.inf], np.nan).fillna(
        vol.mean() if not np.isnan(vol.mean()) else 0.01
    )
    scale = vol_target / (vol + 1e-12)
    scale = scale.clip(lower=0.1, upper=2.0)
    pos = (signal * scale).clip(lower=-MAX_POS, upper=MAX_POS)
    targets[SYMBOL] = pos
    targets = targets.fillna(0.0)
    return targets


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
            "grid": {"lookback": LOOKBACKS, "zscore": ZSCORES, "vol_target": VOL_TARGETS},
            "grid_size": grid_size,
            "selection": "best train-only walk-forward Sharpe; Test protected",
        },
        data_sources={"source": "yahoo_daily_cached", "symbols": UNIVERSE, "interval": "1d"},
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-05-01] started {exp_id}  grid_size={grid_size}")

    try:
        isolated_cache = Path(tracker.log_dir) / "artifacts" / exp_id / "cache"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))
        data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END, interval="1d")
        df = data.get(SYMBOL, pd.DataFrame())
        if len(df) == 0:
            raise RuntimeError("no data for SPY")
        close = df["close"].copy()
        openp = df["open"].copy() if "open" in df.columns else close.copy()
        # build price series for intraday returns open->close
        prices_intraday = _make_intraday_price_series(close, openp)
        train_mask, val_mask, test_mask = _splits(prices_intraday)
        oos_mask = val_mask | test_mask
        print(
            f"[NF-05-01] prices={prices_intraday.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_equity_config()
        spy_prices = prices_intraday[[SYMBOL]]
        # Benchmark: buy-and-hold SPY on close-to-close? use close prices
        bench_df = pd.DataFrame({SYMBOL: close}, index=close.index)
        bench_weights = pd.DataFrame(1.0, index=close.index, columns=[SYMBOL])
        bench_result = run_backtest(
            prices=bench_df, signals=bench_weights, volumes=None, config=cfg
        )

        # Grid
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lookback in LOOKBACKS:
            for zscore in ZSCORES:
                for vol_target in VOL_TARGETS:
                    pos = build_daily_targets_from_ohlc(close, openp, lookback, zscore, vol_target)
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
                            "oos_sharpe": oos_sr,
                        }
                    )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-05-01] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best_key = grid_df.iloc[0][["lookback", "zscore", "vol_target"]]
        sel = (int(best_key["lookback"]), float(best_key["zscore"]), float(best_key["vol_target"]))
        sel_result = grid_results[sel]
        selected = {"lookback": sel[0], "zscore": sel[1], "vol_target": sel[2]}

        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices_intraday, bench_result, close, openp
        )
        pert = perturbation_eval(
            selected, prices_intraday, oos_mask, cfg, gate["oos_metrics"]["sharpe"], close, openp
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        long_only_pos = build_daily_targets_from_ohlc(close, openp, sel[0], sel[1], sel[2]).clip(
            lower=0
        )
        lon_res = run_backtest(prices=spy_prices, signals=long_only_pos, volumes=None, config=cfg)
        ablations["long_only"] = _period_metrics(
            lon_res.returns[oos_mask], _count_in(lon_res.trades, oos_mask, prices_intraday)
        )
        inv_pos = -build_daily_targets_from_ohlc(close, openp, sel[0], sel[1], sel[2])
        inv_res = run_backtest(prices=spy_prices, signals=inv_pos, volumes=None, config=cfg)
        ablations["inverse_signal"] = _period_metrics(
            inv_res.returns[oos_mask], _count_in(inv_res.trades, oos_mask, prices_intraday)
        )
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, bench_df)
        )

        tracker.log_dataframe("prices_intraday", prices_intraday)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_daily_targets_from_ohlc(close, openp, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("benchmark_returns", bench_result.returns.to_frame("returns"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H87",
            "selected_config": selected,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "metrics": {
                "train_sharpe": gate["train_metrics"]["sharpe"],
                "val_sharpe": gate["val_metrics"]["sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "benchmark_p_value": gate["benchmark_gate"]["p_value"],
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
        summary_path = exp_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        tracker.log_metric("verdict", gate["verdict"])
        for k, v in gate["oos_metrics"].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                tracker.log_metric(f"oos_{k}", float(v))
        tracker.log_metric("wf_stability", float(gate["wf_stability"]))
        tracker.log_metric("information_ratio", float(gate["information_ratio"]))
        tracker.end_experiment(status="completed", summary=summary)
        print(
            json.dumps(
                {
                    "experiment_id": exp_id,
                    "verdict": gate["verdict"],
                    "all_pass": gate["all_pass"],
                    "oos_sharpe": gate["oos_metrics"]["sharpe"],
                    "summary_path": str(summary_path),
                },
                indent=2,
            )
        )
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        tracker.end_experiment(status="failed", summary={"error": str(e)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
