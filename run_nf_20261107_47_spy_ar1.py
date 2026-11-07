"""NF-20261107-47 / H136 (Cycle 50): SPY timing from realized lag-1 return
autocorrelation / serial-dependence state (microstructure-state transmission).

Signal = z-score of trailing realized AR(1) of SPY returns (past-only):
  r_t   = SPY return_t
  ar1_t = rolling_corr(r_t, r_{t-1}, ar_window)
  z_t   = (ar1_t - rolling_mean(ar1, z_window)) / rolling_std(ar1, z_window)
When z rises (serial dependence abnormally positive vs trailing history),
vol-targeted long SPY exposure is reduced continuously, with 1-bar execution
delay (engine signals.shift(1)). `rv_window` is retained in the grid schema
for structural compatibility with the NF runner template but is not used by the
AR(1) observable.

Repo-relative novelty (honest). The repo contains AR(1)/autocorrelation
*diagnostics* (e.g. `run_h26_sharpe_scale_audit.py`,
`run_nf_20261105_06_gold_oil_rv.py`) and H26 is a Sharpe annualization-scale
audit (not a timing family), but no pre-registered NF SPY AR(1)/lag-1
autocorrelation regime-timing family had been executed as a strategy. NF-47 was
held in Cycle 49 (NF-20261107-40 concept) with weak economic plausibility noted;
decisive separation from diagnostic-only AR(1) use is documented. Adjacency to
return-predictability/mean-reversion diagnostics is acknowledged; novelty is
scored on the pre-registered timing-family observable, not as wholly unrelated.
Distinct from VIX/vol-term/corr families (H86/H113/H123/H125/H126/H127/H131/
H134), higher moments (H89/H122/H124/H128/H132/H135), IVOL (H93/H130),
drawdown state (H133), and return dispersion (H118).

Data (free, yfinance): SPY daily Close (auto_adjust), point-in-time.

Splits (pre-registered design): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): rv_window {21} (unused by AR1) x ar_window {63,126}
  x z_window {126} x entry_scale {1.0,1.5,2.0} x vol_target {0.10,0.15}
  (12 combos). Selection = best train-only 4-fold walk-forward mean Sharpe;
  Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
  with IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no
  src/qtr change.

Executed artifact: `.experiments/nf_runs/nf_20261107_47_spy_ar1/summary.json`
(REJECT 2/8, 2026-11-07T18:56:16Z). The artifact's embedded experiment string
reflects the original mislabeled text; this source file and the spec/register
record the corrected AR(1) mechanism.
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
    "NF-20261107-47/H136: SPY timing from realized lag-1 return "
    "autocorrelation (AR1) serial-dependence state. Continuous de-risking "
    "when z-score of trailing AR(1) rises. 1-bar delay. Train-only WF "
    "selection; Test protected; OOS Val+Test gates."
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

RV_WINDOWS = [21]
AR_WINDOWS = [63, 126]
Z_WINDOWS = [126]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(SPY)
    raw = raw.dropna()
    raw = raw[raw[SPY] > 0]
    return raw.sort_index()


def _splits(idx: pd.DatetimeIndex):
    train = pd.Series(idx <= pd.Timestamp(TRAIN_END), index=idx)
    val = pd.Series((idx > pd.Timestamp(TRAIN_END)) & (idx <= pd.Timestamp(VAL_END)), index=idx)
    test = pd.Series(idx > pd.Timestamp(VAL_END), index=idx)
    return train, val, test


def realized_ar1_z(
    prices: pd.DataFrame, rv_window: int, ar_window: int, z_window: int
) -> pd.Series:
    ret = prices[SPY].astype(float).pct_change()
    ar1 = ret.rolling(ar_window, min_periods=ar_window).corr(ret.shift(1))
    mean = ar1.rolling(z_window, min_periods=z_window).mean()
    std = ar1.rolling(z_window, min_periods=z_window).std(ddof=0)
    z = (ar1 - mean) / std.replace(0.0, np.nan)
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
    z = realized_ar1_z(
        prices,
        int(params["rv_window"]),
        int(params["ar_window"]),
        int(params["z_window"]),
    )
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
    pf = float(pos / neg) if neg > 1e-12 else 0.0
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    return {"sharpe": sh, "profit_factor": pf, "max_drawdown": dd, "trades": 1}


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_exposure: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    ret = prices[SPY].pct_change().fillna(0.0)[mask].dropna()
    if ret.empty:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    on = rng.random(len(ret)) < float(np.clip(mean_exposure, 0, 1))
    r = ret.values * on.astype(float)
    sh = float(sharpe_ratio(r))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else 0.0
    eq = np.cumprod(1.0 + r)
    dd = float((eq / np.maximum.accumulate(eq) - 1.0).min()) if len(eq) > 0 else 0.0
    return {
        "sharpe": sh,
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": int(np.diff(on.astype(int)).clip(0, 1).sum()),
    }


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    z = realized_ar1_z(
        prices,
        int(params["rv_window"]),
        int(params["ar_window"]),
        int(params["z_window"]),
    )
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    stress = (z.clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    exposure = stress * float(params["vol_target"])
    exposure = exposure.where(z.notna(), 0.0)
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
    return {"backtest": bt, "z": z}


def worst_regime_rolling_sharpe(r: pd.Series, window: int = 252) -> float:
    if len(r) < window:
        return -1e18
    roll = r.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    roll = roll.dropna()
    if roll.empty:
        return -1e18
    return float(roll.min())


def perturbation_test(prices: pd.DataFrame, params: dict, oos_mask: pd.Series) -> float:
    base = metrics_from(run_one(prices, params)["backtest"], oos_mask)["sharpe"]
    if abs(base) < 1e-12:
        return 1.0
    ratios = []
    for dv in [-21, 21]:
        for de in [-0.25, 0.25]:
            p = dict(params)
            p["ar_window"] = max(21, int(params["ar_window"]) + dv)
            p["entry_scale"] = max(0.5, float(params["entry_scale"]) + de)
            s = metrics_from(run_one(prices, p)["backtest"], oos_mask)["sharpe"]
            ratios.append(s / base if base != 0 else 1.0)
    return float(min(ratios)) if ratios else 1.0


def _oos_trade_count(bt, oos_mask: pd.Series) -> int:
    trades = getattr(bt, "trades", None)
    if trades is None:
        return 0
    try:
        if hasattr(trades, "__len__") and len(trades) > 0 and hasattr(trades, "iloc"):
            if "exit_date" in trades.columns:
                return int(trades["exit_date"].isin(oos_mask.index[oos_mask]).sum())
        return len(trades)
    except Exception:
        return 0


def main() -> None:
    t0 = time.time()
    prices = _fetch()
    train_mask, val_mask, test_mask = _splits(prices.index)
    oos_mask = val_mask | test_mask

    grid = []
    for rvw in RV_WINDOWS:
        for vovw in AR_WINDOWS:
            for zw in Z_WINDOWS:
                for es in ENTRY_SCALES:
                    for vt in VOL_TARGETS:
                        grid.append(
                            {
                                "rv_window": rvw,
                                "ar_window": vovw,
                                "z_window": zw,
                                "entry_scale": es,
                                "vol_target": vt,
                            }
                        )

    wf_scores = []
    for params in grid:
        wf_scores.append(
            {
                "params": params,
                "wf_train_mean_sharpe": wf_train_sharpe(prices, train_mask, params),
            }
        )
    wf_scores.sort(key=lambda x: x["wf_train_mean_sharpe"], reverse=True)
    best = wf_scores[0]["params"]

    res = run_one(prices, best)
    oos = metrics_from(res["backtest"], oos_mask)
    val_m = metrics_from(res["backtest"], val_mask)
    test_m = metrics_from(res["backtest"], test_mask)
    train_m = metrics_from(res["backtest"], train_mask)

    oos_trades = _oos_trade_count(res["backtest"], oos_mask)
    oos["trades"] = max(oos["trades"], oos_trades)

    oos_ret = _returns_series(res["backtest"], prices.index)[oos_mask].dropna()
    bh = benchmark_buyhold(prices, oos_mask)
    mean_exposure = (
        float(res["signals"][SPY][oos_mask].mean() / (MAX_POS + 1e-12)) if oos_mask.any() else 0.0
    )
    rand = random_exposure_matched(prices, oos_mask, mean_exposure, SEED)
    inv_res = inverse_regime(prices, best)
    inv_m = metrics_from(inv_res["backtest"], oos_mask)

    wf_stab = 1.0
    if abs(train_m["sharpe"]) > 1e-12:
        wf_stab = float(oos["sharpe"] / train_m["sharpe"]) if train_m["sharpe"] > 0 else 0.0
    worst_reg = worst_regime_rolling_sharpe(oos_ret)
    perturb = perturbation_test(prices, best, oos_mask)

    try:
        from scipy import stats

        if len(oos_ret) > 10 and bh["trades"] >= 0:
            bh_ret = prices[SPY].pct_change().fillna(0.0)[oos_mask].dropna()
            aligned = pd.concat([oos_ret, bh_ret], axis=1, join="inner").dropna()
            if len(aligned) > 10:
                t_stat, p_two = stats.ttest_rel(aligned.iloc[:, 0], aligned.iloc[:, 1])
                bench_p = float(p_two / 2) if t_stat > 0 else 1.0
            else:
                bench_p = 1.0
        else:
            bench_p = 1.0
    except Exception:
        bench_p = 1.0

    ir = float(oos["sharpe"] - bh["sharpe"])

    gates = {
        "sharpe_gte_1": oos["sharpe"] >= 1.0,
        "trades_gte_200": oos["trades"] >= 200,
        "pf_gte_1_3": oos["profit_factor"] >= 1.3,
        "maxdd_lte_15pct": oos["max_drawdown"] >= -0.15,
        "wf_stability_gte_0_7": wf_stab >= 0.7,
        "worst_regime_gte_0_3": worst_reg >= 0.3,
        "benchmark_p_lte_0_05_ir_gte_0": (bench_p <= 0.05 and ir >= 0.0),
        "perturbation_gte_0_5": perturb >= 0.5,
    }
    gates_passed = sum(1 for v in gates.values() if v)
    verdict = "ACCEPT" if gates_passed == len(gates) else "REJECT"

    out = {
        "nf_id": "NF-20261107-47",
        "h_id": "H136",
        "experiment": EXPERIMENT_DESC,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "rows": int(prices.shape[0]),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "train_n": int(train_mask.sum()),
            "val_n": int(val_mask.sum()),
            "test_n": int(test_mask.sum()),
        },
        "selection": {"best_params": best, "wf_scores_top5": wf_scores[:5]},
        "oos_val_test": oos,
        "val": val_m,
        "test": test_m,
        "train": train_m,
        "benchmarks": {
            "buy_hold_spy": bh,
            "random_exposure_matched": rand,
            "inverse_regime": inv_m,
        },
        "diagnostics": {
            "wf_stability_oos_over_train": wf_stab,
            "worst_regime_rolling252_sharpe": worst_reg,
            "benchmark_p_value": bench_p,
            "information_ratio_vs_buyhold": ir,
            "perturbation_min_ratio": perturb,
            "mean_oos_exposure_fraction": mean_exposure,
        },
        "gates": gates,
        "gates_passed": gates_passed,
        "verdict": verdict,
    }

    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261107_47_spy_ar1"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2))
    print(
        json.dumps(
            {"verdict": verdict, "gates_passed": gates_passed, "oos": oos, "best": best}, indent=2
        )
    )
    print(f"artifact={out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
