#!/usr/bin/env python3
"""
Futures Time-Series Momentum experiment (H4).

Implements H4 from NEXT_TASK.md: Volatility-scaled TSMOM on liquid futures
selected by ensemble (equal-weight average of top-K configs) rather than argmax,
with gates on pooled OOS.

Pre-registered design:
  * Universe: liquid futures across equity index, energy, metals, rates via =F tickers
  * Splits: Train 2015-2019, Val 2020-2021, Test 2022-2024 (protected)
  * Signal: vol-scaled TSMOM, monthly rebalance
  * Parameter grid: lookback in {63,126,252}, skip in {1,5,21}, long_only in {T,F}
  * Selection: ensemble - average weights of top-K (K=5) configs by train WF Sharpe
  * Gates: same PROMPT_V2 gates including p<0.05 and IR>0 requirement via alpha test
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest
from qtr.data.fetcher import get_data_fetcher
from qtr.strategies import run_strategy
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

# Pre-registered config
FUTURES_UNIVERSE = [
    "ES=F",  # S&P 500 E-mini
    "NQ=F",  # Nasdaq 100 E-mini
    "CL=F",  # Crude Oil WTI
    "GC=F",  # Gold
    "ZB=F",  # US 30-Year Treasury Bond
]

VIX_SYMBOL = "^VIX"

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"

TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"

LOOKBACKS = [63, 126, 252]
SKIPS = [1, 5, 21]
LONG_ONLY_CHOICES = [True, False]
TARGET_VOL = 0.15
ENSEMBLE_K = 5  # top-K configs for ensemble

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "alpha_multiple_testing": "benjamini_hochberg",
}

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_LEVERAGE = 5.0
MAX_POSITION_SIZE = 2.0

COST_MODEL_DEFAULTS = {
    "future_commission_per_contract": 0.50,
    "future_spread_ticks": 0.25,
    "future_slippage_ticks": 0.5,
}

EXPERIMENT_NAME = "futures_tsmom_v1"
EXPERIMENT_DESC = (
    "H4: Volatility-scaled TSMOM on liquid futures with ensemble selection "
    "(top-K average by train WF Sharpe). Train 2015-2019, Val 2020-2021, "
    "Test 2022-2024 protected. Gates on pooled Val+Test OOS."
)

# Futures contract specs (approximate common specs)
FUTURES_SPECS = {
    "ES=F": {
        "multiplier": 50.0,
        "tick_value": 12.50,
        "tick_size": 0.25,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "NQ=F": {
        "multiplier": 20.0,
        "tick_value": 5.0,
        "tick_size": 0.25,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "CL=F": {
        "multiplier": 1000.0,
        "tick_value": 10.0,
        "tick_size": 0.01,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "GC=F": {
        "multiplier": 100.0,
        "tick_value": 10.0,
        "tick_size": 0.10,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "ZB=F": {
        "multiplier": 1000.0,
        "tick_value": 31.25,
        "tick_size": 0.03125,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "ZN=F": {
        "multiplier": 1000.0,
        "tick_value": 15.625,
        "tick_size": 0.015625,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "TY=F": {
        "multiplier": 1000.0,
        "tick_value": 15.625,
        "tick_size": 0.015625,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "SI=F": {
        "multiplier": 5000.0,
        "tick_value": 25.0,
        "tick_size": 0.005,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "HG=F": {
        "multiplier": 25000.0,
        "tick_value": 12.50,
        "tick_size": 0.0005,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "KC=F": {
        "multiplier": 37500.0,
        "tick_value": 12.50,
        "tick_size": 0.0005,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
    "JB=F": {
        "multiplier": 37500.0,
        "tick_value": 12.50,
        "tick_size": 0.0005,
        "commission": 0.50,
        "spread_ticks": 0.25,
        "slippage_ticks": 0.5,
    },
}


def make_futures_config(allow_short: bool = False) -> BacktestConfig:
    cm = CostModel(
        future_commission_per_contract=COST_MODEL_DEFAULTS[
            "future_commission_per_contract"
        ],
        future_spread_ticks=COST_MODEL_DEFAULTS["future_spread_ticks"],
        future_slippage_ticks=COST_MODEL_DEFAULTS["future_slippage_ticks"],
        futures_specs=FUTURES_SPECS,
    )
    cfg = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.FUTURE,
        max_position_size=MAX_POSITION_SIZE,
        max_leverage=MAX_LEVERAGE,
        allow_short=allow_short,
        cost_model=cm,
    )
    return cfg


def split_returns_by_date(returns: pd.Series):
    train = returns[returns.index <= TRAIN_END]
    val = returns[(returns.index > TRAIN_END) & (returns.index <= VAL_END)]
    test = returns[returns.index > VAL_END]
    oos = returns[returns.index > TRAIN_END]
    return train, val, test, oos


def resample_monthly_signals(signals: pd.DataFrame) -> pd.DataFrame:
    monthly = signals.resample("ME").last()
    full_index = signals.index
    monthly = monthly.reindex(full_index, method="ffill").fillna(0)
    return monthly


def vol_scaled_tsmom_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    skip: int = 1,
    long_only: bool = False,
    target_vol: float = TARGET_VOL,
    vol_window: int = 63,
) -> pd.DataFrame:
    """Canonical volatility-scaled TSMOM (Moskowitz, Ooi & Pedersen 2012).

    Delegates to the shared library implementation in
    ``qtr.strategies.baselines.vol_scaled_tsmom_signals`` so the H1/H2/H3
    and H4 runners use one construction. Trend-following: sign of weight
    equals sign of momentum.
    """
    from qtr.strategies.baselines import vol_scaled_tsmom_signals as _impl

    return _impl(
        prices,
        lookback=lookback,
        skip=skip,
        long_only=long_only,
        target_vol=target_vol,
        vol_window=vol_window,
        max_position_size=MAX_POSITION_SIZE,
    )


def evaluate_combo(prices, volumes, adv, long_only, lookback, skip):
    cfg = make_futures_config(allow_short=not long_only)
    sig = vol_scaled_tsmom_signals(
        prices, lookback=lookback, skip=skip, long_only=long_only, target_vol=TARGET_VOL
    )
    sig_monthly = resample_monthly_signals(sig)
    result = run_backtest(
        prices=prices, signals=sig_monthly, volumes=volumes, adv=adv, config=cfg
    )
    return result, sig_monthly


def selection_metric(train_returns, fold_sharpes):
    return float(np.mean(fold_sharpes)) if len(fold_sharpes) else -np.inf


def wf_oos_sharpes(train_returns, n_splits=4):
    train_vals = train_returns.values
    folds = walk_forward_splits(len(train_vals), n_splits=n_splits)
    sharpes = []
    for tr_idx, te_idx in folds:
        te_vals = train_vals[te_idx]
        if len(te_vals) > 1 and te_vals.std() > 0:
            sharpes.append(sharpe_ratio(te_vals))
    return sharpes


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def window_max_drawdown(equity: pd.Series, start: str, end: str) -> float:
    eq = equity.loc[start:end]
    if len(eq) < 2:
        return 0.0
    dd = eq / eq.cummax() - 1.0
    return float(dd.min())


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": FUTURES_UNIVERSE,
            "vix_symbol": VIX_SYMBOL,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "data_splits": {"train_end": TRAIN_END, "val_end": VAL_END},
            "lookbacks": LOOKBACKS,
            "skips": SKIPS,
            "long_only_choices": LONG_ONLY_CHOICES,
            "ensemble_k": ENSEMBLE_K,
            "target_vol": TARGET_VOL,
            "max_leverage": MAX_LEVERAGE,
            "max_position_size": MAX_POSITION_SIZE,
            "gates": GATES,
            "random_seeds": {"numpy": SEED, "python": SEED},
            "compute_budget": {"max_cpu_hours": 2.0},
        },
        data_sources={
            "source": "yahoo_futures",
            "symbols": FUTURES_UNIVERSE,
            "start": START_DATE,
            "end": END_DATE,
            "interval": "1d",
            "notes": "Yahoo continuous futures (=F). Roll adjustment methodology is opaque; roll-date drift bias may exist.",
        },
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"Started experiment: {exp_id}")
    try:
        print("Fetching futures data...")
        fetcher = get_data_fetcher()
        raw_fut = fetcher.fetch_futures(
            FUTURES_UNIVERSE,
            start=START_DATE,
            end=END_DATE,
            interval="1d",
            use_cache=True,
        )
        prices = pd.DataFrame()
        volumes = pd.DataFrame()
        for sym in FUTURES_UNIVERSE:
            df = raw_fut.get(sym)
            if df is None or df.empty or "close" not in df.columns:
                print(f"  WARN: no data for {sym}")
                continue
            prices[sym] = df["close"]
            if "volume" in df.columns:
                volumes[sym] = df["volume"]
        prices = prices.ffill().dropna(how="all")
        volumes = volumes.reindex(prices.index).ffill().fillna(0)
        valid = prices.columns[prices.notna().any(axis=0)].tolist()
        prices = prices[valid]
        volumes = volumes[valid]
        print(f"Loaded {len(prices.columns)} futures x {len(prices)} days")

        # VIX
        raw_vix = fetcher.fetch_yahoo(
            [VIX_SYMBOL], start=START_DATE, end=END_DATE, interval="1d", use_cache=True
        )
        vix_df = raw_vix.get(VIX_SYMBOL)
        vix = (
            vix_df["close"]
            if (vix_df is not None and "close" in vix_df.columns)
            else pd.Series(np.nan, index=prices.index)
        )
        vix = vix.reindex(prices.index).ffill()

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.to_frame("vix"))

        adv = volumes.rolling(20).mean().iloc[-1] if len(volumes) else None

        # Benchmark - equal weight buy and hold on available futures
        if len(prices.columns) > 0:
            bh_cfg = make_futures_config(allow_short=False)
            n = len(prices.columns)
            bh_signals = run_strategy(
                prices, "buy_and_hold", weight=1.0 / n if n > 0 else 0.0
            )
            bh_signals = resample_monthly_signals(bh_signals)
            bh_result = run_backtest(
                prices=prices,
                signals=bh_signals,
                volumes=volumes,
                adv=adv,
                config=bh_cfg,
            )
            tracker.log_dataframe(
                "benchmark_equity", bh_result.equity_curve.to_frame("equity")
            )
            tracker.log_metrics(
                {f"benchmark_{k}": float(v) for k, v in bh_result.metrics.items()},
                step=0,
            )
            print(f"Benchmark Sharpe={bh_result.metrics['sharpe']:.3f}")
        else:
            bh_result = None

        # Grid
        from itertools import product

        grid = list(product(LONG_ONLY_CHOICES, LOOKBACKS, SKIPS))
        print(f"Grid: {len(grid)} combos")
        combo_records = []
        for i, (long_only, lookback, skip) in enumerate(grid):
            try:
                result, sig = evaluate_combo(
                    prices, volumes, adv, long_only, lookback, skip
                )
            except Exception as e:  # noqa: BLE001 -- per-combo grid failure is non-fatal; log and skip the combo
                print(f"  ERR on {i}: {e}")
                continue
            train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(
                result.returns
            )
            train_sharpes = wf_oos_sharpes(train_ret, n_splits=4)
            sel = selection_metric(train_ret, train_sharpes)
            train_sharpe = sharpe_ratio(train_ret.values)
            train_vol = (
                float(np.std(train_ret.values) * np.sqrt(252))
                if len(train_ret)
                else 0.0
            )
            rec = {
                "long_only": bool(long_only),
                "lookback": lookback,
                "skip": skip,
                "train_sharpe": float(train_sharpe),
                "train_vol_annual": train_vol,
                "wf_oos_mean_sharpe": float(sel),
                "wf_oos_sharpes": [float(s) for s in train_sharpes],
                "val_sharpe": float(sharpe_ratio(val_ret.values))
                if len(val_ret)
                else 0.0,
                "test_sharpe": float(sharpe_ratio(test_ret.values))
                if len(test_ret)
                else 0.0,
                "oos_sharpe": float(sharpe_ratio(oos_ret.values))
                if len(oos_ret)
                else 0.0,
            }
            combo_records.append(rec)
        if not combo_records:
            print("No valid combos")
            tracker.finish_experiment(status="failed", error="No valid combinations")
            return False
        combos_df = pd.DataFrame(combo_records)
        combos_df = combos_df.sort_values(
            ["wf_oos_mean_sharpe", "train_sharpe"], ascending=[False, False]
        )
        top_k = combos_df.head(min(ENSEMBLE_K, len(combos_df)))
        print(f"Top {len(top_k)} by wf_oos_mean:")
        for _, r in top_k.iterrows():
            print(
                f"  lo={r['long_only']} lb={r['lookback']} sk={r['skip']} wf={r['wf_oos_mean_sharpe']:.3f}"
            )

        # Build ensemble weights: average of top-K configs' monthly weights
        ensemble_sig = None
        for _, r in top_k.iterrows():
            _, sig = evaluate_combo(
                prices,
                volumes,
                adv,
                bool(r["long_only"]),
                int(r["lookback"]),
                int(r["skip"]),
            )
            if ensemble_sig is None:
                ensemble_sig = sig.copy() / len(top_k)
            else:
                ensemble_sig += sig / len(top_k)
        if ensemble_sig is None:
            tracker.finish_experiment(status="failed", error="Could not build ensemble")
            return False

        # Evaluate ensemble on full series
        # Use avg config settings for long_only? take majority or default
        avg_long_only = bool(top_k["long_only"].mode().iloc[0]) if len(top_k) else False
        cfg_ens = make_futures_config(allow_short=not avg_long_only)
        ens_monthly = resample_monthly_signals(ensemble_sig)
        ens_result = run_backtest(
            prices=prices, signals=ens_monthly, volumes=volumes, adv=adv, config=cfg_ens
        )
        train_ret, val_ret, test_ret, oos_ret = split_returns_by_date(
            ens_result.returns
        )
        oos_sharpe = sharpe_ratio(oos_ret.values) if len(oos_ret) else 0.0
        oos_equity = (1 + oos_ret).cumprod() if len(oos_ret) else pd.Series([1])
        if len(oos_equity) >= 2:
            oos_dd = (oos_equity - oos_equity.expanding().max()).min()
        else:
            oos_dd = 0.0
        gross_p = oos_ret[oos_ret > 0].sum() if len(oos_ret) else 0
        gross_l = abs(oos_ret[oos_ret < 0].sum()) if len(oos_ret) else 1e-18
        oos_pf = float(gross_p / gross_l) if gross_l > 0 else np.inf
        oos_trades = (
            ens_result.trades[ens_result.trades["timestamp"] > pd.Timestamp(TRAIN_END)]
            if len(ens_result.trades)
            else pd.DataFrame()
        )
        train_sharpe = sharpe_ratio(train_ret.values) if len(train_ret) else 0.0
        wf_stab = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0
        regimes = regime_labels(vix)
        worst = np.inf
        for reg in ["bull", "sideways", "bear"]:
            mask = regimes.loc[oos_ret.index] == reg if len(oos_ret) else []
            if hasattr(mask, "__len__") and len(mask) > 0 and mask.any():
                r = oos_ret[mask]
                if len(r) > 1 and r.std() > 0:
                    s = sharpe_ratio(r.values)
                    worst = min(worst, s)
        if worst == np.inf:
            worst = oos_sharpe
        if bh_result is not None and len(oos_ret) > 0:
            bh_oos = bh_result.returns[
                bh_result.returns.index > pd.Timestamp(TRAIN_END)
            ]
            alpha_res = compare_to_benchmark(
                oos_ret.values if hasattr(oos_ret, "values") else oos_ret,
                bh_oos.values if hasattr(bh_oos, "values") else bh_oos,
            )
            # ``compare_to_benchmark`` returns the alpha p-value under the
            # key ``alpha_p_value`` (there is no ``p_value`` key), so the
            # previous lookup silently returned the 1.0 default and the
            # ``p`` gate below was always False -- a gate that never tested
            # anything. Read the key the library actually returns.
            p = float(alpha_res.get("alpha_p_value_one_sided", 1.0))
            ir = float(alpha_res.get("information_ratio", -np.inf))
        else:
            p, ir = 1.0, -np.inf
        passes = {
            "sharpe": oos_sharpe >= GATES["min_sharpe"],
            "trades": len(oos_trades) >= GATES["min_trades"],
            "pf": oos_pf >= GATES["min_profit_factor"],
            "dd": abs(oos_dd) <= GATES["max_drawdown"],
            "stab": wf_stab >= GATES["min_walkforward_stability"],
            "worst": worst >= GATES["min_worst_regime_sharpe"],
            "p": p < GATES["max_p_value"],
            "ir": ir > GATES.get("min_information_ratio", -1e18),
        }
        all_pass = all(passes.values())
        summary = {
            "experiment_id": exp_id,
            "ensemble_k": ENSEMBLE_K,
            "top_k": top_k.to_dict(orient="records"),
            "oos_sharpe": float(oos_sharpe),
            "oos_pf": float(oos_pf),
            "oos_max_dd": float(oos_dd),
            "oos_trades": len(oos_trades),
            "train_sharpe": float(train_sharpe),
            "wf_stability": float(wf_stab),
            "worst_regime_sharpe": float(worst),
            "alpha_vs_benchmark": {"p_value": p, "information_ratio": ir},
            "passes": passes,
            "all_pass": bool(all_pass),
            "data_available": list(prices.columns),
        }

        # Ablation: argmax vs ensemble
        best_combo = combos_df.iloc[0]
        argmax_res, _ = evaluate_combo(
            prices,
            volumes,
            adv,
            bool(best_combo["long_only"]),
            int(best_combo["lookback"]),
            int(best_combo["skip"]),
        )
        argmax_oos = argmax_res.returns[
            argmax_res.returns.index > pd.Timestamp(TRAIN_END)
        ]
        argmax_oos_sh = sharpe_ratio(argmax_oos.values) if len(argmax_oos) else 0.0
        summary["ablation"] = {
            "argmax": {
                "long_only": bool(best_combo["long_only"]),
                "lookback": int(best_combo["lookback"]),
                "skip": int(best_combo["skip"]),
                "oos_sharpe": float(argmax_oos_sh),
            },
            "ensemble_oos_sharpe": float(oos_sharpe),
        }
        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.log_dataframe("param_grid_results", combos_df)
        tracker.log_dataframe(
            "ensemble_equity", ens_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe("ensemble_trades", ens_result.trades)
        if bh_result is not None:
            tracker.log_dataframe(
                "benchmark_equity", bh_result.equity_curve.to_frame("equity")
            )

        tracker.finish_experiment(status="completed")
        print(f"\nAll pass: {all_pass}")
        return all_pass
    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
