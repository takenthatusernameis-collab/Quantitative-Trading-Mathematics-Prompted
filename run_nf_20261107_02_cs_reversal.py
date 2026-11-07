"""NF-20261107-02 / H119 (pre-registered, Cycle 33): Short-term cross-sectional
return reversal among sector ETFs (liquidity provision / mean reversion).

Signal = cross-sectional rank of trailing `lookback`-day cumulative sector return
(past-only, known at close). Each week (fixed 5-bar rebalance cadence) go
long-only the weakest tercile (3 of 9 sectors), equal weight, each vol-targeted
to `vol_target`, max_position 0.5, hold until next weekly rebalance. Engine
`signals.shift(1)` gives t->t+1 causality. Distinct from H2/H16 cross-sectional
*momentum* (own-past-return trend): H119 is *reversal* (opposite sign, weekly
horizon, liquidity-provision causal path). Distinct from all H85-H118
constructions, which time SPY exposure off a stress signal: H119 trades the
sector cross-section directly and never times SPY market exposure.
9 sectors with full 2010+ history (XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLU,XLB);
XLC/XLRE excluded to preserve the 2010+ sample/splits. 4233 aligned rows each,
0 non-positive, 2010-01-04..2026-10-30 via DataFetcher/cache. No src/qtr change.
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

EXPERIMENT_NAME = "nf_20261107_02_cs_reversal"
EXPERIMENT_DESC = (
    "NF-20261107-02/H119: short-term cross-sectional return reversal among "
    "sector ETFs (liquidity provision/mean reversion). Weekly long-only "
    "weakest-tercile by trailing cumulative-return rank, equal weight, "
    "vol-targeted, fixed 5-bar rebalance cadence. Train-only WF selection; "
    "Test protected; OOS gates vs buy-hold SPY benchmark."
)

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
SPY = "SPY"
UNIVERSE = SECTORS
BENCHMARK = SPY

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
MAX_LEVERAGE = 1.0
N_LONG = 3  # weakest tercile of 9 sectors
REBALANCE_EVERY = 5  # bars; fixed weekly cadence, not price-tuned

LOOKBACKS = [5, 10]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4
VOL_WINDOW = 63
VOL_MIN_PERIODS = 21

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


def _cum_return_rank(rets: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Cross-sectional rank of trailing cumulative return (past-only).
    Rank 1 = weakest sector; computed exclusively from returns strictly before
    each bar so the signal is causal at the close of bar t-1.
    """
    cum = (1.0 + rets).rolling(lookback, min_periods=max(5, lookback // 2)).apply(
        np.prod, raw=True
    ) - 1.0
    rank = cum.rank(axis=1, ascending=True, method="first")
    return rank


def _realized_vol_scale(prices: pd.DataFrame, vol_target: float) -> pd.DataFrame:
    rets = prices.pct_change()
    vol = rets.rolling(VOL_WINDOW, min_periods=VOL_MIN_PERIODS).std() * np.sqrt(252.0)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0)
    return scale.fillna(0.0)


def build_reversal_signal(
    prices: pd.DataFrame,
    lookback: int,
    vol_target: float,
) -> pd.DataFrame:
    for sym in SECTORS:
        if sym not in prices.columns:
            raise ValueError(f"Missing {sym}")
    rets = prices[SECTORS].pct_change()
    rank = _cum_return_rank(rets, lookback)
    vol_scale = _realized_vol_scale(prices, vol_target)

    # Weakest tercile selected each bar; target weights applied only on fixed
    # rebalance days (5-bar cadence), held between rebalances via engine ffill.
    selected = rank.le(N_LONG)
    base_weight = (1.0 / N_LONG) * vol_scale[SECTORS]
    raw = selected.astype(float).multiply(base_weight, axis=0).clip(0.0, MAX_POS)

    rebalance = pd.Series(False, index=prices.index)
    warmup = lookback + VOL_WINDOW
    rebalance.iloc[warmup::REBALANCE_EVERY] = True
    sig = raw.where(rebalance, np.nan)
    sig = sig.reindex(index=prices.index, columns=SECTORS)
    sig.iloc[:warmup] = np.nan
    sig[sig.isna()] = np.nan  # explicit: non-rebalance days hold via ffill in engine
    return sig


def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown(returns: np.ndarray) -> float:
    equity = (1.0 + returns).cumprod()
    roll = pd.Series(equity).expanding().max().to_numpy()
    safe = np.where(roll > 0.0, roll, 1.0)
    dd = (equity - roll) / safe
    return float(abs(dd.min())) if dd.size > 0 else 0.0


def evaluate_gates(oos_res, train_res, benchmark_oos, prices, oos_mask, selected_params, cfg):
    oos_rets = oos_res.returns.fillna(0.0).values
    train_rets = train_res.returns.fillna(0.0).values
    metrics = oos_res.metrics
    sharpe = float(metrics.get("sharpe", 0.0))
    trades = int(metrics.get("num_trades", 0))
    pf = _profit_factor(oos_rets)
    max_dd_abs = _max_drawdown(oos_rets)

    wf_stab = 0.0
    if len(train_rets) > 0 and np.std(train_rets) > 1e-12:
        train_sh = float(sharpe_ratio(train_rets))
        if abs(train_sh) > 1e-12:
            wf_stab = float(sharpe / train_sh)
        elif abs(sharpe) < 1e-12:
            wf_stab = 1.0

    roll_window = 252
    s = pd.Series(oos_rets)
    roll = s.rolling(roll_window).apply(
        lambda x: sharpe_ratio(x.values) if np.std(x) > 1e-12 else 0.0, raw=False
    )
    worst_reg = float(roll.dropna().min()) if roll.notna().any() else 0.0

    try:
        cmp = compare_to_benchmark(
            oos_res.returns.fillna(0.0),
            benchmark_oos.returns.fillna(0.0),
        )
        pval = float(cmp.get("p_value", 1.0))
        ir = float(cmp.get("information_ratio", -1.0))
    except Exception:
        cmp = {}
        pval, ir = 1.0, -1.0

    base_sh = sharpe if abs(sharpe) > 1e-12 else 1e-12
    pert_ratios = []
    for mult in (0.8, 1.2):
        for key in ("lookback", "vol_target"):
            p = dict(selected_params)
            p[key] = type(p[key])(p[key] * mult)
            if key == "lookback":
                p[key] = max(3, int(round(p[key])))
            try:
                sig = build_reversal_signal(prices, **p)
                res = run_backtest(prices.loc[oos_mask, SECTORS], sig.loc[oos_mask], cfg)
                pert_ratios.append(float(res.metrics.get("sharpe", 0.0)) / base_sh)
            except Exception:
                pert_ratios.append(0.0)
    pert = float(np.min(pert_ratios)) if pert_ratios else 0.0

    pass_sh = sharpe >= GATES["min_sharpe"]
    pass_tr = trades >= GATES["min_trades"]
    pass_pf = pf >= GATES["min_profit_factor"]
    pass_dd = max_dd_abs <= GATES["max_drawdown"]
    pass_wf = (wf_stab >= GATES["min_walkforward_stability"]) if np.isfinite(wf_stab) else False
    pass_reg = worst_reg >= GATES["min_worst_regime_sharpe"] if np.isfinite(worst_reg) else False
    pass_bench = (
        (pval <= GATES["max_p_value"] and ir >= GATES["min_information_ratio"])
        if (np.isfinite(pval) and np.isfinite(ir))
        else False
    )
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "sharpe_ge_1_0": {
            "value": sharpe,
            "threshold": GATES["min_sharpe"],
            "pass": pass_sh,
        },
        "trades_ge_200": {
            "value": trades,
            "threshold": GATES["min_trades"],
            "pass": pass_tr,
        },
        "profit_factor_ge_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": pass_pf,
        },
        "max_drawdown_le_15pct": {
            "value": max_dd_abs,
            "threshold": GATES["max_drawdown"],
            "pass": pass_dd,
        },
        "walkforward_stability_ge_0_7": {
            "value": wf_stab,
            "threshold": GATES["min_walkforward_stability"],
            "pass": pass_wf,
        },
        "worst_regime_rolling252_sharpe_ge_0_3": {
            "value": worst_reg,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": pass_reg,
        },
        "benchmark_p_le_0_05_ir_ge_0": {
            "value": {"p_value": pval, "information_ratio": ir},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": pass_bench,
        },
        "perturbation_min_ratio_ge_0_5": {
            "value": pert,
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": pass_pert,
        },
    }
    passed = sum(1 for g in gates.values() if g["pass"])
    verdict = "PASS" if passed == len(gates) else "REJECT"
    return {
        "verdict": verdict,
        "passed": passed,
        "total": len(gates),
        "gates": gates,
        "comparison": cmp,
    }


def _select_on_train(prices: pd.DataFrame, train_mask: pd.Series, cfg: BacktestConfig):
    tr_prices = prices.loc[train_mask, SECTORS]
    rows = []
    for lb in LOOKBACKS:
        for vt in VOL_TARGETS:
            params = {"lookback": lb, "vol_target": vt}
            try:
                sig = build_reversal_signal(prices, **params)
            except Exception:
                continue
            try:
                tr_rets = (
                    run_backtest(tr_prices, sig.loc[train_mask], cfg).returns.fillna(0.0).values
                )
            except Exception:
                continue
            fold_sh = []
            try:
                for tr_i, te_i in walk_forward_splits(len(tr_rets), n_splits=WF_FOLDS_SELECTION):
                    if len(te_i) < 30:
                        continue
                    fold_sh.append(float(sharpe_ratio(tr_rets[te_i])))
            except Exception:
                continue
            rows.append(
                {
                    **params,
                    "wf_mean_sharpe": float(np.mean(fold_sh)) if fold_sh else -9.0,
                }
            )
    if not rows:
        raise RuntimeError("No valid train-selection candidates")
    df = pd.DataFrame(rows).sort_values("wf_mean_sharpe", ascending=False)
    return df.iloc[0].to_dict(), df


def _run_panel(prices_slice, sig_slice, cfg):
    return run_backtest(prices_slice, sig_slice, cfg)


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    t0 = time.time()
    try:
        tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    except Exception:
        pass
    try:
        tracker.log_params(
            {
                "hypothesis_id": "H119",
                "nf_id": "NF-20261107-02",
                "universe": SECTORS,
                "benchmark": BENCHMARK,
                "data_start": DATA_START,
                "data_end": DATA_END,
                "train_end": TRAIN_END,
                "val_end": VAL_END,
                "grid_size": len(LOOKBACKS) * len(VOL_TARGETS),
                "selection": "best_train_4fold_walkforward_sharpe",
                "gates": GATES,
                "seed": SEED,
                "max_position": MAX_POS,
                "n_long": N_LONG,
                "rebalance_every": REBALANCE_EVERY,
            }
        )
    except Exception:
        pass

    fetcher = DataFetcher(DataCache(Path(".cache/data")))
    prices = _align_prices(fetcher, SECTORS + [BENCHMARK], DATA_START, DATA_END)
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask

    cfg = make_equity_config()
    selected, grid_df = _select_on_train(prices, train_mask, cfg)
    params = {
        "lookback": int(selected["lookback"]),
        "vol_target": float(selected["vol_target"]),
    }
    sig = build_reversal_signal(prices, **params)
    tr_res = _run_panel(prices.loc[train_mask, SECTORS], sig.loc[train_mask], cfg)
    oos_res = _run_panel(prices.loc[oos_mask, SECTORS], sig.loc[oos_mask], cfg)

    bh_spy_oos = _run_panel(
        prices.loc[oos_mask, [BENCHMARK]],
        pd.DataFrame({BENCHMARK: 1.0}, index=prices.loc[oos_mask].index),
        cfg,
    )
    bh_sectors_ew_oos = _run_panel(
        prices.loc[oos_mask, SECTORS],
        pd.DataFrame({s: 1.0 / len(SECTORS) for s in SECTORS}, index=prices.loc[oos_mask].index),
        cfg,
    )
    gate_res = evaluate_gates(oos_res, tr_res, bh_spy_oos, prices, oos_mask, params, cfg)

    oos_index = prices.loc[oos_mask].index
    oos_rets = prices[SECTORS].loc[oos_mask].pct_change().fillna(0.0)

    strat_rets = oos_res.returns.fillna(0.0).values

    sig_full = build_reversal_signal(prices, **params)
    sig_oos = sig_full.loc[oos_mask, SECTORS].ffill().fillna(0.0)
    gross = sig_oos.sum(axis=1).values

    rng = np.random.default_rng(SEED)
    vol_scale_oos = _realized_vol_scale(prices, params["vol_target"]).loc[oos_mask]
    rnd_signal = pd.DataFrame(0.0, index=oos_index, columns=SECTORS)
    rebalance_days = sig_full.loc[oos_mask, SECTORS].notna().any(axis=1)
    for ts in oos_index[rebalance_days]:
        choice = rng.choice(SECTORS, size=N_LONG, replace=False)
        vs = vol_scale_oos.loc[ts, choice].values
        w = ((1.0 / N_LONG) * np.clip(vs, 0.0, 1.0)).clip(0.0, MAX_POS)
        rnd_signal.loc[ts, choice] = w
    rnd_signal = rnd_signal.ffill().fillna(0.0)
    rnd_rets = (rnd_signal.shift(1).fillna(0.0) * oos_rets).sum(axis=1).values
    rnd_metrics = _dict_metrics(rnd_rets)
    rnd_dd = _max_drawdown(rnd_rets)
    rnd_num_trades = int(np.sum(np.abs(np.diff(rnd_signal.values, axis=0)).sum(axis=1) > 1e-8))

    # Inverse-momentum ablation: long the strongest tercile instead of weakest.
    inv_sig = _inverse_signal(prices, params, oos_mask)
    inv_res = _run_panel(prices.loc[oos_mask, SECTORS], inv_sig.loc[oos_mask], cfg)

    ablations = {
        "buy_hold_spy_oos": bh_spy_oos.metrics,
        "buy_hold_sectors_equal_weight_oos": bh_sectors_ew_oos.metrics,
        "random_side_oos": {
            "sharpe": rnd_metrics["sharpe"],
            "profit_factor": rnd_metrics["profit_factor"],
            "max_drawdown": rnd_dd,
            "num_trades": rnd_num_trades,
        },
        "inverse_momentum_long_oos": inv_res.metrics,
    }

    turnover = _turnover(sig.loc[oos_mask], SECTORS)
    avg_trade_cost = float(oos_res.metrics.get("avg_trade_cost", 0.0))

    summary = {
        "experiment": EXPERIMENT_NAME,
        "description": EXPERIMENT_DESC,
        "hypothesis_id": "H119",
        "nf_id": "NF-20261107-02",
        "selected_params": params,
        "selection_score_wf_mean_sharpe": float(selected.get("wf_mean_sharpe", float("nan"))),
        "train_metrics": tr_res.metrics,
        "oos_val_test_metrics": oos_res.metrics,
        "gate_evaluation": gate_res,
        "ablations": ablations,
        "diagnostics": {
            "oos_turnover_weight_changes": turnover,
            "avg_trade_cost": avg_trade_cost,
            "rebalance_days_oos": int(sig_full.loc[oos_mask, SECTORS].notna().any(axis=1).sum()),
        },
        "data": {
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "rows": int(len(prices)),
            "train_rows": int(train_mask.sum()),
            "val_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "sectors_used": SECTORS,
            "feasibility_note": "XLC/XLRE excluded (2018/2015 inception); 9 sectors + SPY, 0 non-positive",
        },
        "elapsed_s": round(time.time() - t0, 3),
    }
    out = Path(".experiments") / "nf_runs" / EXPERIMENT_NAME
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (out / "grid.csv").write_text(grid_df.to_csv(index=False))
    try:
        tracker.log_metrics(
            {
                "oos_sharpe": gate_res["gates"]["sharpe_ge_1_0"]["value"],
                "oos_trades": gate_res["gates"]["trades_ge_200"]["value"],
                "oos_pf": gate_res["gates"]["profit_factor_ge_1_3"]["value"],
                "verdict_pass_count": gate_res["passed"],
            }
        )
        tracker.end_experiment(status="completed")
    except Exception:
        pass
    print(
        json.dumps(
            {
                "verdict": gate_res["verdict"],
                "passed": gate_res["passed"],
                "total": gate_res["total"],
                "summary": str(out / "summary.json"),
            },
            indent=2,
        )
    )


def _inverse_signal(prices: pd.DataFrame, params: dict, oos_mask: pd.Series) -> pd.DataFrame:
    lookback = int(params["lookback"])
    vol_target = float(params["vol_target"])
    rets = prices[SECTORS].pct_change()
    cum = (1.0 + rets).rolling(lookback, min_periods=max(5, lookback // 2)).apply(
        np.prod, raw=True
    ) - 1.0
    rank = cum.rank(axis=1, ascending=False, method="first")  # 1 = strongest
    selected = rank.le(N_LONG)
    vol_scale = _realized_vol_scale(prices, vol_target)
    base_weight = (1.0 / N_LONG) * vol_scale[SECTORS]
    raw = selected.astype(float).multiply(base_weight, axis=0).clip(0.0, MAX_POS)
    warmup = lookback + VOL_WINDOW
    rebalance = pd.Series(False, index=prices.index)
    rebalance.iloc[warmup::REBALANCE_EVERY] = True
    sig = raw.where(rebalance, np.nan)
    sig = sig.reindex(index=prices.index, columns=SECTORS)
    sig.iloc[:warmup] = np.nan
    sig = sig.loc[oos_mask]
    return sig.ffill().fillna(0.0)


def _turnover(sig_oos: pd.DataFrame, sectors) -> float:
    sig = sig_oos[sectors].fillna(0.0)
    prior = sig.shift(1).fillna(0.0)
    change = sig - prior
    return float((change.abs().sum(axis=1)).sum())


def _dict_metrics(returns: np.ndarray) -> dict:
    pf = _profit_factor(returns)
    dd = _max_drawdown(returns)
    return {
        "sharpe": float(sharpe_ratio(returns)),
        "profit_factor": pf,
        "max_drawdown": dd,
        "num_trades": float(len(returns)),
    }


if __name__ == "__main__":
    main()
