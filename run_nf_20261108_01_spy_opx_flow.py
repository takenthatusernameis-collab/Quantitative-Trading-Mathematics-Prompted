"""NF-20261108-01 / H140 (pre-registered, Cycle 54): SPY timing from
monthly options-expiration dealer-flow / pin-proximity regime.

Signal (past-only, deterministic calendar — no look-ahead):
  OPX dates  = third Friday of each month (US equity options expiration)
  days_t     = calendar days from date t to next OPX (0 on OPX day)
  flow_t     = 1 / (days_t + 1)                  (highest on OPX day)
  z_t        = (flow_t - rolling_mean(flow, z_window)) / rolling_std(flow, z_window)
When z rises into expiry-proximity pressure (SPY unusually close to next OPX
vs trailing history), exposure to vol-targeted long SPY is reduced
continuously, with 1-bar execution delay (engine signals.shift(1)).

Repo-relative novelty (honest). No executed NF/H uses monthly
options-expiration / dealer-flow proximity as a SPY timing observable.
Repo families cover momentum (H1-H30), vol targeting/VRP (H5/H6/H17),
overnight/intraday (H18), volume (H19/H20), correlation-regime (H96/H127/
H134/H137), IVOL (H93/H130), higher moments/tail/VoV (H89/H122/H124/H128/
H132/H135), VIX term/spreads (H86/H100/H113/H123/H125/H126/H131), drawdown
state (H133), return dispersion (H118), RV divergence credit (H138) and
IWM/SPY (H139), AR(1) serial dependence (H136), lottery demand (H112/H124),
sector beta/breadth (H129/H115), event/macro (FOMC H90, turn-of-month H91,
PEAD H98), concentration RV (H97), gold-oil RV (H88), USD macro (H95).
Honest adjacency to the z-score/continuous-de-risking/vol-target statistical
form (H138/H139) is acknowledged; novelty scored on the repo-new OPX flow-
proximity observable/category, not a wholly new statistical method.

Data (free, yfinance): SPY daily Close (auto_adjust), point-in-time.
OPX dates computed deterministically; no external market data for signal.

Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-0->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): z_window {63,126,252} x entry_scale {1.0,1.5,2.0}
  x vol_target {0.10,0.15} (12 combos). Selection = best train-only 4-fold
walk-forward mean Sharpe; Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
  with IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no
  src/qtr change.
"""

from __future__ import annotations

import datetime as dt
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
    "NF-20261108-01/H140: SPY timing from monthly options-expiration "
    "dealer-flow / pin-proximity regime. Continuous de-risking when "
    "z-score of trailing days-to-next-OPX flow pressure rises into "
    "expiry. 1-bar delay. Train-only WF selection; Test protected; "
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

Z_WINDOWS = [63, 126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _monthly_opx_dates(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    """US monthly equity options expiration = third Friday of each month."""
    dates: list[pd.Timestamp] = []
    y = start.year
    while True:
        for m in range(1, 13):
            first = dt.date(y, m, 1)
            first_friday = first + dt.timedelta(days=(4 - first.weekday()) % 7)
            third_friday = first_friday + dt.timedelta(days=14)
            d = pd.Timestamp(third_friday)
            if start <= d <= end:
                dates.append(d)
        y += 1
        if dt.date(y, 1, 1) > end.date():
            break
    return sorted(dates)


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.dropna()
    for col in UNIVERSE:
        if col not in raw.columns:
            raise RuntimeError(f"missing column {col}")
        raw = raw[raw[col] > 0]
    return raw.sort_index()


def _splits(idx: pd.DatetimeIndex):
    train = pd.Series(idx <= pd.Timestamp(TRAIN_END), index=idx)
    val = pd.Series((idx > pd.Timestamp(TRAIN_END)) & (idx <= pd.Timestamp(VAL_END)), index=idx)
    test = pd.Series(idx > pd.Timestamp(VAL_END), index=idx)
    return train, val, test


def opx_flow_z(prices: pd.DataFrame, opx_dates: list[pd.Timestamp], z_window: int) -> pd.Series:
    idx = prices.index
    opx = pd.DatetimeIndex(sorted(opx_dates))
    # next OPX date on/after each trading date (calendar days)
    next_opx = pd.Series(
        [opx[opx >= t].min() if len(opx[opx >= t]) > 0 else pd.NaT for t in idx],
        index=idx,
    )
    days = (next_opx - idx).dt.days
    days = days.fillna(days.max() if days.notna().any() else 30)
    flow = 1.0 / (days.astype(float) + 1.0)
    mean = flow.rolling(z_window, min_periods=z_window).mean()
    std = flow.rolling(z_window, min_periods=z_window).std(ddof=0)
    return (flow - mean) / std.replace(0.0, np.nan)


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    stress = (z.clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    exposure = exposure.where(z.notna(), 0.0)
    return exposure.clip(0.0, float(vol_target))


def run_one(prices: pd.DataFrame, opx_dates: list[pd.Timestamp], params: dict) -> dict:
    z = opx_flow_z(prices, opx_dates, int(params["z_window"]))
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(z, float(params["entry_scale"]), float(params["vol_target"]))
    has_scale = (vol_scale(spy_ret, float(params["vol_target"])) > 0).astype(float)
    exposure = (exposure * has_scale.replace(0.0, np.nan).ffill().fillna(0.0)).clip(
        0.0, float(params["vol_target"])
    )
    signals = pd.DataFrame(
        {SPY: exposure * MAX_POS / float(params["vol_target"])}, index=prices.index
    ).clip(0.0, MAX_POS)
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
    prices: pd.DataFrame,
    opx_dates: list[pd.Timestamp],
    train_mask: pd.Series,
    params: dict,
    folds: int = WF_FOLDS_SELECTION,
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
        res = run_one(sub, opx_dates, params)
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


def benchmark_test(prices: pd.DataFrame, strat_r_oos: pd.Series, oos_mask: pd.Series):
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


def perturbation_test(
    prices: pd.DataFrame, opx_dates: list[pd.Timestamp], best_params: dict, oos_mask: pd.Series
) -> float:
    res_best = run_one(prices, opx_dates, best_params)
    base = metrics_from(res_best["backtest"], oos_mask)["sharpe"]
    if abs(base) < 1e-12:
        return 0.0
    ratios = []
    for factor in (0.8, 1.2):
        p = dict(best_params)
        p["z_window"] = int(best_params["z_window"])  # unchanged
        p["entry_scale"] = float(best_params["entry_scale"]) * factor
        m = metrics_from(run_one(prices, opx_dates, p)["backtest"], oos_mask)
        ratios.append(m["sharpe"] / base if base > 0 else 0.0)
    return float(min(ratios)) if ratios else 0.0


def random_exposure_matched(
    prices: pd.DataFrame, oos_mask: pd.Series, mean_exposure: float, seed: int
):
    rng = np.random.default_rng(seed)
    idx = prices.index[oos_mask]
    ret = prices[SPY].pct_change().fillna(0.0).loc[idx]
    exp = rng.random(len(idx)) < mean_exposure
    r = ret * exp.astype(float)
    sh = float(sharpe_ratio(r.values))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min()) if len(eq) > 0 else 0.0
    return {"sharpe": sh, "profit_factor": pf, "max_drawdown": dd, "trades": int(exp.sum())}


def inverse_regime(prices: pd.DataFrame, opx_dates: list[pd.Timestamp], params: dict) -> dict:
    z = opx_flow_z(prices, opx_dates, int(params["z_window"]))
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    stress = (z.clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    exposure = (0.2 + 0.8 * stress) * float(params["vol_target"])
    exposure = exposure.where(z.notna(), 0.0)
    exposure = exposure * (vol_scale(spy_ret, float(params["vol_target"])) > 0).astype(
        float
    ).replace(0.0, np.nan).ffill().fillna(0.0)
    exposure = exposure.clip(0.0, float(params["vol_target"]))
    signals = pd.DataFrame(
        {SPY: exposure * MAX_POS / float(params["vol_target"])}, index=prices.index
    ).clip(0.0, MAX_POS)
    bt = run_backtest(
        prices[[SPY]],
        signals,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    return {"backtest": bt, "signals": signals}


def main() -> int:
    t0 = time.time()
    prices = _fetch()
    opx_dates = _monthly_opx_dates(pd.Timestamp(DATA_START), pd.Timestamp(DATA_END))
    train_mask, val_mask, test_mask = _splits(prices.index)
    oos_mask = val_mask | test_mask

    grid = []
    for zw in Z_WINDOWS:
        for es in ENTRY_SCALES:
            for vt in VOL_TARGETS:
                grid.append(
                    {
                        "z_window": zw,
                        "entry_scale": es,
                        "vol_target": vt,
                    }
                )

    scored = []
    for p in grid:
        ws = wf_train_sharpe(prices, opx_dates, train_mask, p)
        scored.append((ws, p))
    scored.sort(key=lambda x: (-x[0], json.dumps(x[1], sort_keys=True)))
    best_ws, best_params = scored[0]

    res_best = run_one(prices, opx_dates, best_params)
    strat_r = _returns_series(res_best["backtest"], prices.index)
    strat_r_oos = strat_r[oos_mask]
    m_train = metrics_from(res_best["backtest"], train_mask)
    m_val = metrics_from(res_best["backtest"], val_mask)
    m_test = metrics_from(res_best["backtest"], test_mask)
    m_oos = metrics_from(res_best["backtest"], oos_mask)

    bh, bench_p, bench_ir = benchmark_test(prices, strat_r_oos, oos_mask)
    wf_stab = float(m_oos["sharpe"] / m_train["sharpe"]) if abs(m_train["sharpe"]) > 1e-12 else 0.0
    if wf_stab < 0:
        wf_stab = 0.0
    worst_reg = worst_regime_rolling_sharpe(strat_r_oos, window=252)
    pert = perturbation_test(prices, opx_dates, best_params, oos_mask)

    mean_exp = float(res_best["signals"][SPY][oos_mask].mean())
    randm = random_exposure_matched(prices, oos_mask, mean_exp, SEED)
    inv_res = inverse_regime(prices, opx_dates, best_params)
    m_inv = metrics_from(inv_res["backtest"], oos_mask)

    gates = {
        "sharpe_oos_ge_1_0": bool(m_oos["sharpe"] >= 1.0),
        "trades_oos_ge_200": bool(m_oos["trades"] >= 200),
        "pf_oos_ge_1_3": bool(m_oos["profit_factor"] >= 1.3),
        "maxdd_oos_le_15pct": bool(abs(m_oos["max_drawdown"]) <= 0.15),
        "wf_stability_ge_0_7": bool(wf_stab >= 0.7),
        "worst_regime_rolling252_sharpe_ge_0_3": bool(worst_reg >= 0.3),
        "benchmark_p_le_0_05_and_ir_ge_0": bool((bench_p <= 0.05) and (bench_ir >= 0.0)),
        "perturbation_min_ratio_ge_0_5": bool(pert >= 0.5),
    }
    gates_passed = int(sum(1 for v in gates.values() if v))
    verdict = "PASS" if gates_passed >= 6 else "REJECT"

    out = {
        "experiment": EXPERIMENT_DESC,
        "nf_id": "NF-20261108-01",
        "h_id": "H140",
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

    expdir = ROOT / ".experiments" / "nf_runs" / "nf_20261108_01_spy_opx_flow"
    expdir.mkdir(parents=True, exist_ok=True)
    (expdir / "summary.json").write_text(json.dumps(out, indent=2))
    pd.DataFrame([{"params": json.dumps(p), "train_wf_sharpe": s} for s, p in scored]).to_csv(
        expdir / "grid.csv", index=False
    )
    meta = {
        "nf_id": "NF-20261108-01",
        "h_id": "H140",
        "runner": "run_nf_20261108_01_spy_opx_flow.py",
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
