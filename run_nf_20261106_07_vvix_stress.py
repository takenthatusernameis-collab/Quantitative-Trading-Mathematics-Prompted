"""NF-20261106-07 / H104 (pre-registered): VVIX (vol-of-vol) stress-timing for SPY.

Mechanism: VVIX measures implied volatility of VIX options. Spikes indicate
accelerating demand for volatility protection / stress in the volatility market,
which may precede or coincide with equity drawdowns. A vol-targeted, long-only
SPY position is held when trailing VVIX is calm (low z-score) and reduced/flat
when VVIX is elevated (stress), with a 1-bar execution delay.

New family dimension (volatility-of-volatility / second-order vol stress timing),
distinct from H17 VRP (VIX term structure/variance risk premium carry),
H89 (VIX level regime), H100 (^MOVE rates-vol), H102/H103 (cross-asset risk
appetite). VVIX is the implied volatility of VIX options (second-order),
not spot VIX level or term structure.

Causality / timing (pre-registered): VVIX trailing z-score for day t uses
prices/index levels through close t only (trailing windows, min_periods).
Signals are shifted by 1 bar (engine signals.shift(1)); target at close t earns
return t -> t+1.

Data: yfinance daily ^VVIX, SPY (free), 2010-01-01 -> 2026-10-31.
Splits (pre-registered): Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 ->
2022-12-31; Test 2023-01-01 -> 2026-10-31 (protected holdout).
Grid (bounded): lookback {63,126} x z_window {126,252} x entry_scale {1.0,1.5,2.0}
x vol_target {0.10,0.15} (24 combos). Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity defaults.

Gates (OOS Val+Test): OOS Sharpe>=1.0, >=200 trades, PF>=1.3, max DD<=15%,
WF stability test>=0.7*train when train>0, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.
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

EXPERIMENT_NAME = "nf_20261106_07_vvix_stress"
EXPERIMENT_DESC = (
    "NF-20261106-07/H104: VVIX (vol-of-vol) stress-timing SPY. Continuous "
    "vol-targeted long SPY exposure reduced when trailing ^VVIX z-score elevated "
    "(stress), 1-bar delay. Train-only WF selection; Test protected; OOS gates."
)

VVIX = "^VVIX"
SPY = "SPY"
UNIVERSE = [VVIX, SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [63, 126]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
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


def _align_prices(fetcher: DataFetcher, symbols, start, end) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    closes = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else df.columns[0])
        )
        close = df[col].astype(float)
        if (close <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        closes[s] = close.rename(s)
    prices = pd.concat(closes, axis=1).sort_index().ffill().dropna()
    return prices


def build_vvix_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    """Continuous causal VVIX stress-timing signal on SPY (no shift here).

    Exposure is higher when trailing VVIX z-score is calm (negative/low stress)
    and reduced when VVIX is elevated. Uses only trailing data (min_periods).
    Engine applies signals.shift(1) for 1-bar execution delay.
    """
    if VVIX not in prices.columns or SPY not in prices.columns:
        raise ValueError(f"prices must contain {VVIX} and {SPY}")
    level = prices[VVIX].rolling(lookback, min_periods=max(20, lookback // 2)).mean()
    mp = max(60, z_window // 2)
    z = (level - level.rolling(z_window, min_periods=mp).mean()) / level.rolling(
        z_window, min_periods=mp
    ).std()
    # calm (z <= 0) -> 1; stress (z >= entry_scale) -> 0
    raw = (1.0 - (z.clip(lower=0.0) / entry_scale)).clip(0.0, 1.0)
    spy_ret = prices[SPY].pct_change()
    vol = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
    sig = (raw * scale * MAX_POS).fillna(0.0)
    return pd.DataFrame({SPY: sig}, index=prices.index)


def _trade_count(result) -> int:
    return int(result.metrics.get("num_trades", 0))


def _worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    if len(returns) < window:
        return float("nan")
    rolling = returns.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    return float(rolling.min())


def _perturbation_ratio(
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    base_sharpe: float,
    cfg: BacktestConfig,
) -> float:
    if base_sharpe == 0 or not np.isfinite(base_sharpe):
        return 0.0
    ratios = []
    for key, deltas in [
        ("lookback", [-0.2, 0.2]),
        ("z_window", [-0.2, 0.2]),
        ("entry_scale", [-0.2, 0.2]),
        ("vol_target", [-0.2, 0.2]),
    ]:
        for d in deltas:
            p = dict(best)
            val = p[key]
            p[key] = type(val)(val * (1 + d)) if isinstance(val, int) else val * (1 + d)
            if key in ("lookback", "z_window"):
                p[key] = max(20, int(round(p[key])))
            try:
                sig = build_vvix_signal(prices, **p)
                r = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
                s = float(r.metrics.get("sharpe", 0.0))
                if np.isfinite(s):
                    ratios.append(s / base_sharpe)
            except Exception:
                pass
    return float(min(ratios)) if ratios else 0.0


def evaluate_gates(
    oos_result,
    train_result,
    bench_result,
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    cfg: BacktestConfig,
) -> dict:
    oos_sh = float(oos_result.metrics.get("sharpe", 0.0))
    train_sh = float(train_result.metrics.get("sharpe", 0.0))
    trades = _trade_count(oos_result)
    pf = float(oos_result.metrics.get("profit_factor", 0.0))
    mdd = abs(float(oos_result.metrics.get("max_drawdown", 1.0)))
    wf = oos_sh / train_sh if train_sh > 0 else 0.0
    worst = _worst_regime_sharpe(oos_result.returns)
    cmp = compare_to_benchmark(oos_result.returns, bench_result.returns)
    pval = cmp.get("alpha_p_value")
    ir = cmp.get("information_ratio")
    pert = _perturbation_ratio(prices, oos_mask, best, oos_sh, cfg)
    gates = {
        "sharpe>=1.0": oos_sh >= GATES["min_sharpe"],
        "trades>=200": trades >= GATES["min_trades"],
        "pf>=1.3": pf >= GATES["min_profit_factor"],
        "max_dd<=15%": mdd <= GATES["max_drawdown"],
        "wf_stability>=0.7*train": wf >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe>=0.3": (
            np.isfinite(worst) and worst >= GATES["min_worst_regime_sharpe"]
        ),
        "benchmark_p<=0.05": (pval is not None and float(pval) <= GATES["max_p_value"]),
        "ir>=0": (ir is not None and float(ir) >= GATES["min_information_ratio"]),
        "perturbation_min_ratio>=0.5": pert >= GATES["min_perturbed_sharpe_ratio"],
    }
    return {
        "metrics": {
            "oos_sharpe": oos_sh,
            "train_sharpe": train_sh,
            "trades": trades,
            "profit_factor": pf,
            "max_drawdown": mdd,
            "wf_stability": wf,
            "worst_regime_sharpe": worst,
            "benchmark_p_value": pval,
            "information_ratio": ir,
            "perturbation_min_ratio": pert,
        },
        "gates": gates,
        "passed": sum(gates.values()),
        "total": len(gates),
        "verdict": "ACCEPT" if all(gates.values()) else "REJECT",
    }


def _random_exposure_matched(signals: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    vals = signals[SPY].values.copy()
    nz = np.where(np.abs(vals) > 1e-12)[0]
    if len(nz) == 0:
        return signals.copy()
    shuffled = vals[nz].copy()
    rng.shuffle(shuffled)
    out = vals.copy()
    out[nz] = shuffled
    return pd.DataFrame({SPY: out}, index=signals.index)


def main() -> dict:
    np.random.seed(SEED)
    tracker = get_tracker()
    t0 = time.time()
    tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC, config={"hypothesis_id": "H104"})
    try:
        tracker.log_params(
            {
                "universe": UNIVERSE,
                "data_start": DATA_START,
                "data_end": DATA_END,
                "train_end": TRAIN_END,
                "val_end": VAL_END,
                "grid_size": len(LOOKBACKS) * len(Z_WINDOWS) * len(ENTRY_SCALES) * len(VOL_TARGETS),
                "selection": "best_train_4fold_walkforward_sharpe",
                "gates": GATES,
                "seed": SEED,
                "max_position": MAX_POS,
            }
        )
    except Exception:
        pass

    fetcher = DataFetcher(DataCache(Path(".cache/data")))
    prices = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    cfg = make_equity_config()

    # Grid search: selection on train only.
    grid_results = []
    for lookback in LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    params = dict(
                        lookback=lookback,
                        z_window=z_window,
                        entry_scale=entry_scale,
                        vol_target=vol_target,
                    )
                    sig = build_vvix_signal(prices, **params)
                    tr = run_backtest(prices.loc[train_mask, [SPY]], sig.loc[train_mask], cfg)
                    wf_scores = []
                    tr_rets = tr.returns
                    for tr_i, te_i in walk_forward_splits(
                        len(tr_rets), n_splits=WF_FOLDS_SELECTION
                    ):
                        if len(te_i) < 20:
                            continue
                        wf_scores.append(sharpe_ratio(tr_rets.iloc[te_i]))
                    sel = (
                        float(np.nanmean(wf_scores))
                        if wf_scores
                        else float(tr.metrics.get("sharpe", 0.0))
                    )
                    grid_results.append(
                        {
                            **params,
                            "train_sharpe": float(tr.metrics.get("sharpe", 0.0)),
                            "selection_wf_sharpe": sel,
                            "train_trades": _trade_count(tr),
                        }
                    )
    grid_results.sort(key=lambda x: x["selection_wf_sharpe"], reverse=True)
    best = {k: grid_results[0][k] for k in ("lookback", "z_window", "entry_scale", "vol_target")}

    sig_best = build_vvix_signal(prices, **best)
    train_res = run_backtest(prices.loc[train_mask, [SPY]], sig_best.loc[train_mask], cfg)
    val_res = run_backtest(prices.loc[val_mask, [SPY]], sig_best.loc[val_mask], cfg)
    test_res = run_backtest(prices.loc[test_mask, [SPY]], sig_best.loc[test_mask], cfg)
    oos_res = run_backtest(prices.loc[oos_mask, [SPY]], sig_best.loc[oos_mask], cfg)

    spy_buy = pd.DataFrame({SPY: 1.0}, index=prices.index)
    bench_oos = run_backtest(prices.loc[oos_mask, [SPY]], spy_buy.loc[oos_mask], cfg)
    rand_oos = run_backtest(
        prices.loc[oos_mask, [SPY]],
        _random_exposure_matched(sig_best, SEED).loc[oos_mask],
        cfg,
    )
    inv_sig = pd.DataFrame(
        {SPY: (MAX_POS * sig_best[SPY].rolling(21, min_periods=21).std() * 0 + 1)},
        index=prices.index,
    )
    # inverse: high stress (low raw) -> long; construct directly
    level = (
        prices[VVIX].rolling(best["lookback"], min_periods=max(20, best["lookback"] // 2)).mean()
    )
    mp = max(60, best["z_window"] // 2)
    z = (level - level.rolling(best["z_window"], min_periods=mp).mean()) / level.rolling(
        best["z_window"], min_periods=mp
    ).std()
    inv_raw = (z.clip(lower=0.0) / best["entry_scale"]).clip(0.0, 1.0)
    spy_ret = prices[SPY].pct_change()
    vol = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (best["vol_target"] / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
    inv_sig = pd.DataFrame({SPY: (inv_raw * scale * MAX_POS).fillna(0.0)}, index=prices.index)
    inv_oos = run_backtest(prices.loc[oos_mask, [SPY]], inv_sig.loc[oos_mask], cfg)

    verdict = evaluate_gates(oos_res, train_res, bench_oos, prices, oos_mask, best, cfg)

    def _m(r):
        return {
            k: (float(v) if isinstance(v, (int, float, np.floating)) and np.isfinite(v) else v)
            for k, v in r.metrics.items()
        }

    summary = {
        "experiment_id": (
            tracker.current_experiment.experiment_id if tracker.current_experiment else None
        ),
        "name": EXPERIMENT_NAME,
        "hypothesis": "H104",
        "family": "NF-20261106-07",
        "mechanism": "VVIX volatility-of-volatility stress-timing SPY",
        "verdict": verdict["verdict"],
        "gates_passed": f"{verdict['passed']}/{verdict['total']}",
        "gates": verdict["gates"],
        "gate_metrics": verdict["metrics"],
        "best_params": best,
        "top_grid": grid_results[:10],
        "splits": {
            "train": {"rows": int(train_mask.sum()), "metrics": _m(train_res)},
            "val": {"rows": int(val_mask.sum()), "metrics": _m(val_res)},
            "test": {"rows": int(test_mask.sum()), "metrics": _m(test_res)},
            "oos_val_test": {"rows": int(oos_mask.sum()), "metrics": _m(oos_res)},
        },
        "ablations": {
            "buy_hold_spy_oos": _m(bench_oos),
            "random_exposure_matched_oos": _m(rand_oos),
            "inverse_stress_long_oos": _m(inv_oos),
        },
        "data": {
            "rows": len(prices),
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
        },
        "elapsed_sec": round(time.time() - t0, 2),
        "src_qtr_changed": False,
    }

    tracker.log_metrics(
        {
            "oos_sharpe": verdict["metrics"]["oos_sharpe"],
            "oos_trades": verdict["metrics"]["trades"],
            "oos_pf": verdict["metrics"]["profit_factor"],
            "oos_mdd": verdict["metrics"]["max_drawdown"],
            "gates_passed": verdict["passed"],
        }
    )
    try:
        tracker.finish_experiment(
            notes=f"{verdict['verdict']} {verdict['passed']}/{verdict['total']}"
        )
    except TypeError:
        tracker.finish_experiment()

    out_dir = Path(".experiments/nf_runs/nf_20261106_07_vvix_stress")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(
        json.dumps(
            {
                "verdict": verdict["verdict"],
                "gates": verdict["gates"],
                "gate_metrics": verdict["metrics"],
                "best": best,
            },
            indent=2,
            default=str,
        )
    )
    return summary


if __name__ == "__main__":
    main()
