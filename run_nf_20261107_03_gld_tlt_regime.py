"""NF-20261107-03 / H120 (pre-registered, Cycle 34): GLD/TLT real-asset vs
duration relative-strength regime timing for SPY.

Signal = z-score of trailing GLD/TLT ratio momentum (lookback return of
GLD/TLT) over z_window. When gold outperforms long Treasuries abnormally
(real-asset/inflation-uncertainty or stagflationary pressure regime proxy),
reduce vol-targeted long SPY exposure continuously, 1-bar delay
(engine signals.shift(1)). Long-only, max_position 0.5, equity costs.

Data: GLD, TLT, SPY yfinance daily adjusted close (DataFetcher/cache),
2010-01-01 -> 2026-10-31. Point-in-time. No src/qtr change.
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

EXPERIMENT_NAME = "nf_20261107_03_gld_tlt_regime"
EXPERIMENT_DESC = (
    "NF-20261107-03/H120: GLD/TLT real-asset vs duration relative-strength "
    "regime timing SPY. Signal = z-score of trailing GLD/TLT ratio momentum "
    "over z_window. When gold leads long Treasuries abnormally, reduce "
    "vol-targeted long SPY exposure continuously, 1-bar delay. Train-only WF "
    "selection; Test protected; OOS gates."
)

GOLD = "GLD"
DURATION = "TLT"
SPY = "SPY"
UNIVERSE = [GOLD, DURATION, SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [21, 63]
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


def _align_prices(fetcher: DataFetcher, symbols, start: str, end: str) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    frames = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "adj_close"
            if "adj_close" in df.columns
            else (
                "close"
                if "close" in df.columns
                else ("Close" if "Close" in df.columns else df.columns[0])
            )
        )
        c = df[col].astype(float)
        if (c <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        frames[s] = c.rename(s)
    prices = pd.concat(frames.values(), axis=1).dropna()
    if prices.empty:
        raise RuntimeError("No aligned data")
    return prices


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _ratio_momentum(prices: pd.DataFrame, lookback: int) -> pd.Series:
    ratio = prices[GOLD] / prices[DURATION]
    mom = ratio.pct_change(lookback)
    return mom.replace([np.inf, -np.inf], np.nan)


def build_gld_tlt_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    mom = _ratio_momentum(prices, lookback)
    mu = mom.rolling(z_window, min_periods=max(30, z_window // 2)).mean()
    sigma = mom.rolling(z_window, min_periods=max(30, z_window // 2)).std(ddof=0)
    z = (mom - mu) / sigma.replace(0.0, np.nan)

    rets = prices[SPY].pct_change()
    vol = rets.rolling(21, min_periods=10).std() * np.sqrt(252)
    vol_scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0)

    warm = max(lookback, z_window) + 21
    stress = (z - entry_scale).clip(lower=0.0, upper=1.0)
    exposure = MAX_POS * (1.0 - stress) * vol_scale
    exposure = exposure.fillna(0.0)
    exposure.iloc[:warm] = 0.0
    exposure = exposure.clip(lower=0.0, upper=MAX_POS)

    return pd.DataFrame({SPY: exposure}, index=prices.index)


def _profit_factor(returns: np.ndarray) -> float:
    pos = returns[returns > 0].sum()
    neg = -returns[returns < 0].sum()
    if neg <= 1e-12:
        return float("inf") if pos > 0 else 0.0
    return float(pos / neg)


def _max_drawdown_abs(returns: np.ndarray) -> float:
    eq = (1.0 + np.nan_to_num(returns, nan=0.0)).cumprod()
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = eq / np.where(peak > 1e-12, peak, 1.0) - 1.0
    return float(abs(np.min(dd)))


def _rolling_sharpe_min(returns: np.ndarray, window: int = 252) -> float:
    s = pd.Series(returns)
    if len(s) < window:
        return float(sharpe_ratio(returns))
    roll = s.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    vals = roll.dropna().values
    return float(np.min(vals)) if len(vals) else float(sharpe_ratio(returns))


def _perturbation_oos_sharpe(
    prices: pd.DataFrame, mask: pd.Series, params: dict, cfg: BacktestConfig
) -> list[float]:
    lookback = int(params["lookback"])
    z_window = int(params["z_window"])
    entry_scale = float(params["entry_scale"])
    vol_target = float(params["vol_target"])
    candidates = []
    for lb in sorted({max(5, int(round(lookback * 0.8))), lookback, int(round(lookback * 1.2))}):
        for zw in sorted(
            {max(30, int(round(z_window * 0.8))), z_window, int(round(z_window * 1.2))}
        ):
            for es in [round(entry_scale * 0.8, 6), entry_scale, round(entry_scale * 1.2, 6)]:
                if (lb, zw, es, vol_target) == (lookback, z_window, entry_scale, vol_target):
                    continue
                candidates.append((lb, zw, es, vol_target))
    sharpes = []
    p = prices.loc[mask, [SPY]]
    for lb, zw, es, vt in candidates:
        sig = build_gld_tlt_signal(prices, lb, zw, es, vt).loc[mask]
        res = run_backtest(p, sig, cfg)
        if _res_n_trades(res) < 50:
            continue
        r = res.returns.values
        if np.std(r) > 1e-12:
            sharpes.append(float(sharpe_ratio(r)))
    return sharpes


def _res_metrics(res) -> dict:
    return getattr(res, "metrics", {}) or {}


def _res_n_trades(res) -> int:
    m = _res_metrics(res)
    if "num_trades" in m:
        return int(m["num_trades"])
    if "n_trades" in m:
        return int(m["n_trades"])
    return int(getattr(res, "n_trades", 0))


def evaluate_gates(oos_result, train_result, bench_oos, prices, oos_mask, params) -> dict:
    cfg = make_equity_config()
    ret = oos_result.returns.values
    oos_sharpe = float(sharpe_ratio(ret))
    pf = _profit_factor(ret)
    oos_m = _res_metrics(oos_result)
    max_dd = abs(float(oos_m.get("max_drawdown", _max_drawdown_abs(ret))))
    n_trades = _res_n_trades(oos_result)
    train_sharpe = float(sharpe_ratio(train_result.returns.values))
    stability = float(oos_sharpe / train_sharpe) if train_sharpe > 1e-9 else 0.0
    worst_regime = _rolling_sharpe_min(ret, 252)

    def _eq(res):
        idx = res.equity_curve.index
        vals = res.equity_curve.values
        if vals.ndim > 1:
            vals = vals.sum(axis=1)
        return pd.Series(vals, index=idx)

    try:
        bench_cmp = compare_to_benchmark(_eq(oos_result), _eq(bench_oos))
        ir = float(bench_cmp.get("information_ratio", 0.0) or 0.0)
        bench_p = float(bench_cmp.get("p_value", 1.0) or 1.0)
    except Exception:
        ir, bench_p = -1.0, 1.0

    pert_sharpes = _perturbation_oos_sharpe(prices, oos_mask, params, cfg)
    if pert_sharpes and oos_sharpe > 1e-9:
        pert_min_ratio = float(min(pert_sharpes) / oos_sharpe)
    elif pert_sharpes:
        pert_min_ratio = 0.0
    else:
        pert_min_ratio = 1.0

    gates = {
        "sharpe": {
            "value": oos_sharpe,
            "threshold": GATES["min_sharpe"],
            "pass": bool(oos_sharpe >= GATES["min_sharpe"]),
        },
        "profit_factor": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": bool(pf >= GATES["min_profit_factor"]),
        },
        "max_drawdown": {
            "value": max_dd,
            "threshold": GATES["max_drawdown"],
            "pass": bool(max_dd <= GATES["max_drawdown"]),
        },
        "trade_count": {
            "value": n_trades,
            "threshold": GATES["min_trades"],
            "pass": bool(n_trades >= GATES["min_trades"]),
        },
        "walkforward_stability": {
            "value": stability,
            "threshold": GATES["min_walkforward_stability"],
            "pass": bool(stability >= GATES["min_walkforward_stability"]),
        },
        "worst_regime_sharpe": {
            "value": worst_regime,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": bool(worst_regime >= GATES["min_worst_regime_sharpe"]),
        },
        "benchmark_p_ir": {
            "p_value": bench_p,
            "ir": ir,
            "pass": bool(bench_p <= GATES["max_p_value"] and ir >= GATES["min_information_ratio"]),
        },
        "perturbation": {
            "min_ratio": pert_min_ratio,
            "n": len(pert_sharpes),
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": bool(pert_min_ratio >= GATES["min_perturbed_sharpe_ratio"]),
        },
    }
    n_pass = sum(1 for g in gates.values() if g["pass"])
    return {
        "gates": gates,
        "pass_count": n_pass,
        "pass_total": len(gates),
        "verdict": "PASS" if n_pass == len(gates) else "REJECT",
        "train_sharpe": train_sharpe,
        "oos_sharpe": oos_sharpe,
        "ir": ir,
        "benchmark_p": bench_p,
    }


def _select_on_train(prices: pd.DataFrame, train_mask: pd.Series) -> tuple[dict, float]:
    tr = prices.loc[train_mask]
    cfg = make_equity_config()
    best = None
    best_score = -1e9
    for lookback in LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    sig = build_gld_tlt_signal(prices, lookback, z_window, entry_scale, vol_target)
                    tr_sig = sig.loc[train_mask]
                    if (tr_sig[SPY] != 0).sum() < 40:
                        continue
                    wf_vals = []
                    splits = walk_forward_splits(len(tr), n_splits=WF_FOLDS_SELECTION)
                    tr_idx = tr.index
                    for tr_i, te_i in splits:
                        te = tr_idx[te_i]
                        te_sig = sig.loc[te]
                        te_p = prices.loc[te, [SPY]]
                        if (te_sig[SPY] != 0).sum() < 10:
                            continue
                        res = run_backtest(te_p, te_sig, cfg)
                        r = res.returns.values
                        if len(r) > 20 and np.std(r) > 1e-12:
                            wf_vals.append(float(sharpe_ratio(r)))
                    if not wf_vals:
                        continue
                    score = float(np.mean(wf_vals))
                    if score > best_score:
                        best_score = score
                        best = {
                            "lookback": lookback,
                            "z_window": z_window,
                            "entry_scale": entry_scale,
                            "vol_target": vol_target,
                        }
    if best is None:
        best = {
            "lookback": LOOKBACKS[0],
            "z_window": Z_WINDOWS[0],
            "entry_scale": ENTRY_SCALES[0],
            "vol_target": VOL_TARGETS[0],
        }
        best_score = float("nan")
    return best, best_score


def _random_exposure(
    prices: pd.DataFrame, mask: pd.Series, exposure: pd.Series, seed: int
) -> pd.Series:
    rng = np.random.default_rng(seed)
    vals = exposure.loc[mask].values.copy()
    nz = np.where(vals > 1e-12)[0]
    if len(nz) > 1:
        shuffled = vals[nz].copy()
        rng.shuffle(shuffled)
        vals[nz] = shuffled
    return pd.Series(vals, index=prices.loc[mask].index, name=SPY)


def _inverse_signal(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    base = build_gld_tlt_signal(prices, **params)
    inv = pd.DataFrame({SPY: (MAX_POS - base[SPY]).clip(lower=0.0, upper=MAX_POS)})
    inv.iloc[: max(params["lookback"], params["z_window"]) + 21] = 0.0
    return inv


def main() -> dict:
    t0 = time.time()
    tracker = get_tracker()
    cache = DataCache(Path(".cache/data"))
    fetcher = DataFetcher(cache=cache)
    tracker.start_experiment(
        EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        data_sources=[f"yfinance:{s}" for s in UNIVERSE],
        random_seeds={"numpy": SEED},
    )
    prices = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    if oos_mask.sum() < 400:
        raise RuntimeError(f"OOS too small: {oos_mask.sum()}")

    params, sel_score = _select_on_train(prices, train_mask)
    cfg = make_equity_config()
    signal = build_gld_tlt_signal(prices, **params)

    oos_sig = signal.loc[oos_mask]
    oos_prices = prices.loc[oos_mask, [SPY]]
    oos_res = run_backtest(oos_prices, oos_sig, cfg)
    train_res = run_backtest(prices.loc[train_mask, [SPY]], signal.loc[train_mask], cfg)

    bh = pd.DataFrame({SPY: 1.0}, index=prices.index)
    bench_oos = run_backtest(oos_prices, bh.loc[oos_mask], cfg)

    gate_eval = evaluate_gates(oos_res, train_res, bench_oos, prices, oos_mask, params)

    rnd_exp = _random_exposure(prices, oos_mask, signal[SPY], SEED)
    rnd_res = run_backtest(oos_prices, pd.DataFrame({SPY: rnd_exp}, index=oos_prices.index), cfg)
    inv = _inverse_signal(prices, params)
    inv_res = run_backtest(oos_prices, inv.loc[oos_mask], cfg)

    def _m(res, key, default=0.0):
        return float(_res_metrics(res).get(key, default))

    ablations = {
        "buy_hold_spy": {
            "sharpe": float(sharpe_ratio(bench_oos.returns.values)),
            "pf": _profit_factor(bench_oos.returns.values),
            "max_dd": abs(
                _m(bench_oos, "max_drawdown", _max_drawdown_abs(bench_oos.returns.values))
            ),
            "n_trades": _res_n_trades(bench_oos),
        },
        "random_exposure_matched": {
            "sharpe": float(sharpe_ratio(rnd_res.returns.values)),
            "pf": _profit_factor(rnd_res.returns.values),
            "max_dd": abs(_m(rnd_res, "max_drawdown", _max_drawdown_abs(rnd_res.returns.values))),
            "n_trades": _res_n_trades(rnd_res),
        },
        "inverse_stress_long": {
            "sharpe": float(sharpe_ratio(inv_res.returns.values)),
            "pf": _profit_factor(inv_res.returns.values),
            "max_dd": abs(_m(inv_res, "max_drawdown", _max_drawdown_abs(inv_res.returns.values))),
            "n_trades": _res_n_trades(inv_res),
        },
    }

    oos_m = _res_metrics(oos_res)
    tr_m = _res_metrics(train_res)
    summary = {
        "experiment": EXPERIMENT_NAME,
        "nf_id": "NF-20261107-03",
        "hypothesis_id": "H120",
        "description": EXPERIMENT_DESC,
        "data": {
            "rows": int(len(prices)),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "train_rows": int(train_mask.sum()),
            "val_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "universe": UNIVERSE,
        },
        "selected_params": params,
        "selection_score_wf_mean_sharpe": sel_score,
        "oos_val_test_metrics": {
            "sharpe": gate_eval["oos_sharpe"],
            "profit_factor": gate_eval["gates"]["profit_factor"]["value"],
            "max_drawdown": gate_eval["gates"]["max_drawdown"]["value"],
            "n_trades": gate_eval["gates"]["trade_count"]["value"],
            "total_return": float(oos_m.get("total_return", 0.0)),
            "ann_return": float(oos_m.get("annualized_return", 0.0)),
            "ann_vol": float(oos_m.get("annualized_volatility", 0.0)),
        },
        "train_metrics": {
            "sharpe": gate_eval["train_sharpe"],
            "total_return": float(tr_m.get("total_return", 0.0)),
        },
        "gate_evaluation": gate_eval,
        "ablations": ablations,
        "elapsed_s": round(time.time() - t0, 3),
        "gates_spec": GATES,
    }

    out_dir = Path(".experiments/nf_runs") / EXPERIMENT_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    try:
        tracker.log_artifact("summary", out_dir / "summary.json")
        tracker.log_metrics(
            {
                "oos_sharpe": float(summary["oos_val_test_metrics"]["sharpe"]),
                "oos_pf": float(summary["oos_val_test_metrics"]["profit_factor"]),
                "oos_max_dd": float(summary["oos_val_test_metrics"]["max_drawdown"]),
                "oos_trades": float(summary["oos_val_test_metrics"]["n_trades"]),
                "gate_pass_count": float(gate_eval["pass_count"]),
            }
        )
        tracker.finish_experiment(status=gate_eval["verdict"])
    except Exception as e:
        summary["tracker_error"] = str(e)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(
        json.dumps(
            {"verdict": gate_eval["verdict"], "pass": gate_eval["pass_count"], **params},
            indent=2,
        )
    )
    return summary


if __name__ == "__main__":
    main()
