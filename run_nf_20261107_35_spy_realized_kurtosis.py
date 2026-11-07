"""NF-20261107-35 / H132 (pre-registered, Cycle 46): SPY timing from
trailing realized return kurtosis (4th standardized moment) stress regime.

Signal = z-score of trailing rolling realized kurtosis of SPY daily returns
(past-only). Abnormally high realized kurtosis (fat tails / tail-clustering
stress relative to trailing history) reduces vol-targeted long SPY exposure
continuously (linear stress), with 1-bar execution delay
(engine signals.shift(1)).

Repo-relative novelty (honest). H128 (NF-20261107-28, REJECT 2/8) used
*realized skewness* (3rd moment, asymmetry/crash-risk). H122 (NF-20261107-07,
REJECT 3/8) used *downside semivariance ratio* (2nd-moment asymmetry).
H124 (NF-20261107-09, REJECT 3/8) used cross-sectional MAX/lottery demand
(higher-moment attention, different construction/universe). H89 (REJECT 4/9)
used *implied* SKEW (^SKEW, options surface) — different observable (implied
vs realized). H132 uses *realized kurtosis* (4th moment, tail fatness/
extreme-return clustering of SPY itself) — a repo-new realized-moment
observable; honest adjacency to higher-moment stress families (H89/H122/H124/
H128) is acknowledged and novelty scored moderately.

Data (free, yfinance): SPY daily Close (auto_adjust). Common sample aligned
to prior pattern (2010-01-04 onward). Point-in-time (trailing returns only).

Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): kurt_window {63,126} x z_window {126} x entry_scale {1.0,1.5,2.0}
  x vol_target {0.10,0.15} (12 combos). Selection = best train-only 4-fold
  walk-forward mean Sharpe; Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
  with IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no
  src/qtr change.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import sharpe_ratio  # noqa: E402

EXPERIMENT_DESC = (
    "NF-20261107-35/H132: SPY timing from trailing realized kurtosis (4th "
    "moment) stress regime. Continuous de-risking when kurtosis z-score "
    "elevated; 1-bar delay. Train-only WF selection; Test protected; "
    "OOS Val+Test gates."
)

SPY = "SPY"
UNIVERSE = [SPY]
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

KURT_WINDOWS = [63, 126]
Z_WINDOWS = [126]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.dropna()
    raw = raw[raw[SPY] > 0]
    return raw.sort_index()


def _splits(idx: pd.DatetimeIndex):
    train = pd.Series(idx <= pd.Timestamp(TRAIN_END), index=idx)
    val = pd.Series((idx > pd.Timestamp(TRAIN_END)) & (idx <= pd.Timestamp(VAL_END)), index=idx)
    test = pd.Series(idx > pd.Timestamp(VAL_END), index=idx)
    return train, val, test


def realized_kurtosis_z(prices: pd.DataFrame, kurt_window: int, z_window: int) -> pd.Series:
    ret = prices[SPY].astype(float).pct_change()
    kurt = ret.rolling(kurt_window, min_periods=kurt_window).kurt()
    mean = kurt.rolling(z_window, min_periods=z_window).mean()
    std = kurt.rolling(z_window, min_periods=z_window).std(ddof=0)
    z = (kurt - mean) / std.replace(0.0, np.nan)
    return z


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    stress = (z.clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    exposure = exposure.where(z.notna(), 0.0)
    return exposure.clip(0.0, float(vol_target))


def run_one(prices: pd.DataFrame, params: dict) -> dict:
    z = realized_kurtosis_z(prices, int(params["kurt_window"]), int(params["z_window"]))
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(z, float(params["entry_scale"]), float(params["vol_target"]))
    exposure = exposure * (vol_scale(spy_ret, float(params["vol_target"])) > 0).astype(
        float
    ).replace(0.0, np.nan).ffill().fillna(0.0)
    exposure = exposure.clip(0.0, float(params["vol_target"]))
    signals = pd.DataFrame(
        {SPY: exposure * MAX_POS / float(params["vol_target"])}, index=prices.index
    )
    signals = signals.clip(0.0, MAX_POS)
    bt = run_backtest(
        prices[[SPY]],
        signals,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    return {"backtest": bt, "z": z, "signals": signals}


def _returns_series(bt, idx: pd.DatetimeIndex) -> pd.Series:
    eq = bt.equity_curve if hasattr(bt, "equity_curve") else bt["equity_curve"]
    s = pd.Series(eq, index=idx[: len(eq)]).pct_change().fillna(0.0)
    return s


def metrics_from(bt, mask: pd.Series) -> dict:
    idx = mask.index
    r = _returns_series(bt, idx)[mask].dropna()
    if r.empty:
        return {
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
            "n": 0,
            "total_return": 0.0,
        }
    sh = float(sharpe_ratio(r.values))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    tc = 0
    trades = getattr(bt, "trades", None)
    if trades is not None:
        try:
            tc = len(trades)
        except Exception:
            tc = 0
    if tc == 0 and hasattr(bt, "trade_count"):
        tc = int(getattr(bt, "trade_count") or 0)
    if tc == 0 and isinstance(getattr(bt, "metrics", None), dict):
        tc = int(bt.metrics.get("n_trades", bt.metrics.get("num_trades", 0)) or 0)
    return {
        "sharpe": sh,
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": tc,
        "n": int(r.shape[0]),
        "total_return": float(eq.iloc[-1] - 1.0) if len(eq) > 0 else 0.0,
    }


def wf_train_sharpe(
    prices: pd.DataFrame, train_mask: pd.Series, params: dict, folds: int = WF_FOLDS_SELECTION
) -> float:
    train_idx = prices.index[train_mask]
    if len(train_idx) < folds * 60:
        return -1e18
    fold_size = len(train_idx) // folds
    sharpes = []
    for k in range(folds):
        end = (k + 1) * fold_size
        if end < 252:
            continue
        sub = prices.loc[train_idx[:end]].copy()
        res = run_one(sub, params)
        m = metrics_from(res["backtest"], pd.Series(True, index=sub.index))
        if m["n"] > 50:
            sharpes.append(m["sharpe"])
    if not sharpes:
        return -1e18
    return float(np.mean(sharpes))


def benchmark_buyhold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    ret = prices[SPY].pct_change().fillna(0.0)
    r = ret[mask].dropna()
    if r.empty:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    sh = float(sharpe_ratio(r.values))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    return {"sharpe": sh, "profit_factor": pf, "max_drawdown": dd, "trades": 1}


def benchmark_test(
    prices: pd.DataFrame, strat_r_oos: pd.Series, oos_mask: pd.Series
) -> tuple[dict, float, float]:
    from scipy import stats

    bh = benchmark_buyhold(prices, oos_mask)
    bh_r = prices[SPY].pct_change().fillna(0.0)[oos_mask].dropna()
    s = strat_r_oos.reindex(bh_r.index).dropna()
    b = bh_r.reindex(s.index).dropna()
    s = s.reindex(b.index)
    if len(s) < 30 or b.std(ddof=0) < 1e-12:
        return bh, 1.0, 0.0
    diff = s.values - b.values
    _t, p = stats.ttest_1samp(diff, 0.0, alternative="greater")
    ir = float(np.mean(diff) / (np.std(diff, ddof=0) + 1e-12) * np.sqrt(252))
    return bh, float(p), ir


def worst_regime_rolling_sharpe(returns: pd.Series, window: int = 252) -> float:
    if returns.shape[0] < window:
        return 0.0
    rs = returns.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    rs = rs.dropna()
    if rs.empty:
        return 0.0
    return float(rs.min())


def perturbation_test(prices: pd.DataFrame, best_params: dict, oos_mask: pd.Series) -> float:
    res_best = run_one(prices, best_params)
    base = metrics_from(res_best["backtest"], oos_mask)["sharpe"]
    if abs(base) < 1e-12:
        return 0.0
    ratios = []
    for dk in [-21, 21]:
        p = dict(best_params)
        p["kurt_window"] = max(21, int(best_params["kurt_window"]) + dk)
        ratios.append(metrics_from(run_one(prices, p)["backtest"], oos_mask)["sharpe"] / base)
    for de in [-0.25, 0.25]:
        p = dict(best_params)
        p["entry_scale"] = max(0.25, float(best_params["entry_scale"]) + de)
        ratios.append(metrics_from(run_one(prices, p)["backtest"], oos_mask)["sharpe"] / base)
    return float(np.min(ratios)) if ratios else 0.0


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_exposure: float, seed: int
) -> dict:
    rng = np.random.RandomState(seed)
    idx = prices.index[mask]
    exp = (rng.rand(len(idx)) < float(np.clip(mean_exposure, 0.0, 1.0))).astype(float)
    spy_ret = prices[SPY].pct_change().fillna(0.0).loc[idx].values
    r = pd.Series(exp * spy_ret * MAX_POS, index=idx)
    if r.empty:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    sh = float(sharpe_ratio(r.values))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    return {
        "sharpe": sh,
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": int((np.diff(exp, prepend=0) != 0).sum()),
    }


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    z = realized_kurtosis_z(prices, int(params["kurt_window"]), int(params["z_window"]))
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(z, float(params["entry_scale"]), float(params["vol_target"]))
    exposure = exposure * (vol_scale(spy_ret, float(params["vol_target"])) > 0).astype(
        float
    ).replace(0.0, np.nan).ffill().fillna(0.0)
    inv = (float(params["vol_target"]) - exposure).clip(0.0, float(params["vol_target"]))
    signals = pd.DataFrame({SPY: inv * MAX_POS / float(params["vol_target"])}, index=prices.index)
    signals = signals.clip(0.0, MAX_POS)
    bt = run_backtest(
        prices[[SPY]],
        signals,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    return {"backtest": bt}


def main():
    t0 = time.time()
    prices = _fetch()
    train_mask, val_mask, test_mask = _splits(prices.index)
    oos_mask = val_mask | test_mask

    grid = []
    for kw in KURT_WINDOWS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    grid.append(
                        {"kurt_window": kw, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    )

    scored = []
    for params in grid:
        try:
            ws = wf_train_sharpe(prices, train_mask, params)
            scored.append((ws, params))
        except Exception:
            scored.append((-1e18, params))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_ws, best_params = scored[0]

    res_best = run_one(prices, best_params)
    m_train = metrics_from(res_best["backtest"], train_mask)
    m_val = metrics_from(res_best["backtest"], val_mask)
    m_test = metrics_from(res_best["backtest"], test_mask)
    m_oos = metrics_from(res_best["backtest"], oos_mask)

    strat_r_oos = _returns_series(res_best["backtest"], prices.index)[oos_mask].dropna()
    wf_stab = float(m_oos["sharpe"] / m_train["sharpe"]) if m_train["sharpe"] > 1e-12 else 0.0
    worst_reg = worst_regime_rolling_sharpe(strat_r_oos)
    bh, bench_p, bench_ir = benchmark_test(prices, strat_r_oos, oos_mask)
    pert = perturbation_test(prices, best_params, oos_mask)
    mean_exp = float(res_best["signals"][SPY][oos_mask].mean())
    randm = random_exposure_matched(prices, oos_mask, mean_exp, SEED)
    inv = inverse_regime(prices, best_params)
    m_inv = metrics_from(inv["backtest"], oos_mask)

    gates = {
        "sharpe_oos_ge_1_0": bool(m_oos["sharpe"] >= 1.0),
        "trades_oos_ge_200": bool(m_oos["trades"] >= 200),
        "pf_oos_ge_1_3": bool(m_oos["profit_factor"] >= 1.3),
        "maxdd_oos_le_15pct": bool(m_oos["max_drawdown"] >= -0.15),
        "wf_stability_ge_0_7": bool(wf_stab >= 0.7),
        "worst_regime_rolling252_sharpe_ge_0_3": bool(worst_reg >= 0.3),
        "benchmark_p_le_0_05_and_ir_ge_0": bool((bench_p <= 0.05) and (bench_ir >= 0.0)),
        "perturbation_min_ratio_ge_0_5": bool(pert >= 0.5),
    }
    gates_passed = int(sum(1 for v in gates.values() if v))
    verdict = "PASS" if gates_passed >= 6 else "REJECT"

    out = {
        "experiment": EXPERIMENT_DESC,
        "nf_id": "NF-20261107-35",
        "h_id": "H132",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_s": round(time.time() - t0, 2),
        "data": {
            "universe": UNIVERSE,
            "start": DATA_START,
            "end": DATA_END,
            "rows": int(prices.shape[0]),
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_n": int(train_mask.sum()),
            "val_n": int(val_mask.sum()),
            "test_n": int(test_mask.sum()),
        },
        "selection": {
            "grid": grid,
            "best_params": best_params,
            "train_wf_mean_sharpe": float(best_ws),
        },
        "metrics": {
            "train": m_train,
            "val": m_val,
            "test": m_test,
            "oos_val_test": m_oos,
        },
        "oos_diagnostics": {
            "wf_stability_oos_over_train": wf_stab,
            "worst_regime_rolling252_sharpe_oos": worst_reg,
            "benchmark_buyhold": bh,
            "benchmark_p_le_0_05_and_ir": {"p": bench_p, "ir": bench_ir},
            "perturbation_min_ratio": pert,
            "random_exposure_matched": randm,
            "inverse_regime": m_inv,
            "mean_exposure_oos": float(res_best["signals"][SPY][oos_mask].mean()),
        },
        "gates": gates,
        "gates_passed": gates_passed,
        "verdict": verdict,
    }

    expdir = ROOT / ".experiments" / "nf_runs" / "nf_20261107_35_spy_realized_kurtosis"
    expdir.mkdir(parents=True, exist_ok=True)
    (expdir / "summary.json").write_text(json.dumps(out, indent=2))
    pd.DataFrame([{"params": json.dumps(p), "train_wf_sharpe": s} for s, p in scored]).to_csv(
        expdir / "grid.csv", index=False
    )
    meta = {
        "nf_id": "NF-20261107-35",
        "h_id": "H132",
        "runner": "run_nf_20261107_35_spy_realized_kurtosis.py",
        "description": EXPERIMENT_DESC,
        "free_data": True,
        "src_qtr_changed": False,
    }
    (expdir / "data_meta.json").write_text(json.dumps(meta, indent=2))
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": gates_passed,
                "summary": str(expdir / "summary.json"),
            }
        )
    )
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
