"""NF-20261108-06 / H143 (pre-registered, Cycle 57): SPY timing from
overnight gap realized-volatility regime (liquidity/microstructure).

Observable (past-only, PIT OHLC):
  g_t = log(Open_t / Close_{t-1})   (overnight gap/jump return)
  rv_t = rolling_std(g, rv_window) * sqrt(252)
  z_t = (rv_t - rolling_mean(rv_t, z_window)) / rolling_std(rv_t, z_window)

Mechanism: elevated overnight gap realized volatility proxies higher
overnight information-arrival/jump risk and auction-open liquidity stress;
continuously de-risk a vol-targeted long SPY position when z is elevated
(1-bar execution delay via engine signals.shift(1)), long-only.

Repo-relative novelty (honest). H18 (REJECT) tested overnight return sign
predicting next-day intraday direction (persistence). H87 (REJECT) tested
same-day gap fill (open->close reversal direction). H121 (REJECT) used
Amihud illiquidity (close/volume). H136 (REJECT) used close-to-close
realized-vol term structure (short vs long RV of total returns). H122/H128/
H132/H135 used total-return higher moments/VoV, not the overnight gap
component. H143 uses the *second moment of overnight gap/jump returns* as
a liquidity/microstructure regime observable — a repo-new component/channel.
Honest adjacency to the realized-vol z-score de-risking construction class
(H122/H128/H132/H135/H136) and to the overnight/gap domain (H18/H87) is
acknowledged.

Data (free, yfinance): SPY daily OHLC (auto_adjust=False for raw Open/Close;
Close used for trading returns; Open/prev Close for gap). Point-in-time.
Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): rv_window {21,63} x z_window {63,126} x entry_scale {1,1.5,2}
  x vol_target {0.10,0.15} (24 combos). Selection = best train-only 4-fold
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
    "NF-20261108-06/H143: SPY timing from overnight gap realized-volatility regime. "
    "z-score of trailing RV(log(Open/prev Close)); de-risk vol-targeted long SPY when elevated. "
    "1-bar delay. Train-only WF selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

RV_WINDOWS = [21, 63]
Z_WINDOWS = [63, 126]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download([SPY], start=DATA_START, end=DATA_END, progress=False, auto_adjust=False)
    if isinstance(raw.columns, pd.MultiIndex):
        # columns like (Open, SPY)
        opens = raw[("Open", SPY)] if ("Open", SPY) in raw.columns else raw["Open"].squeeze()
        closes = raw[("Close", SPY)] if ("Close", SPY) in raw.columns else raw["Close"].squeeze()
    else:
        opens = raw["Open"]
        closes = raw["Close"]
    df = pd.DataFrame({"Open": opens, "Close": closes}).dropna()
    df = df[(df["Open"] > 0) & (df["Close"] > 0)].sort_index()
    if df.empty:
        raise RuntimeError("empty SPY OHLC")
    return df


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)), index=index
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def overnight_gap_rv_z(ohlc: pd.DataFrame, rv_window: int, z_window: int) -> pd.Series:
    gap = np.log(ohlc["Open"] / ohlc["Close"].shift(1))
    rv = gap.rolling(int(rv_window), min_periods=max(10, int(rv_window) // 2)).std() * np.sqrt(252)
    mp = max(30, int(z_window) // 2)
    mu = rv.rolling(int(z_window), min_periods=mp).mean()
    sd = rv.rolling(int(z_window), min_periods=mp).std()
    z = (rv - mu) / sd.replace(0.0, np.nan)
    return z


def build_exposure(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    stress = (z.clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    return exposure.clip(0.0, MAX_POS).fillna(float(vol_target))


def vol_scale(close: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    ret = close.astype(float).pct_change()
    rv = ret.rolling(window, min_periods=max(10, window // 2)).std() * np.sqrt(252)
    scale = (float(vol_target) / rv.replace(0, np.nan)).clip(0.0, 2.0).fillna(1.0)
    return scale


def run_one(ohlc: pd.DataFrame, params: dict) -> dict:
    z = overnight_gap_rv_z(ohlc, int(params["rv_window"]), int(params["z_window"]))
    exposure = build_exposure(z, float(params["entry_scale"]), float(params["vol_target"]))
    vscale = vol_scale(ohlc["Close"], float(params["vol_target"]))
    raw = exposure * vscale
    prices = ohlc[["Close"]].rename(columns={"Close": SPY})
    signals = pd.DataFrame({SPY: raw.clip(0.0, MAX_POS)}, index=prices.index)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    bt = run_backtest(prices, signals, cfg)
    return {"result": bt, "signals": signals, "z": z}


def metrics_from(bt_result, mask: pd.Series) -> dict:
    eq_full = pd.Series(bt_result.equity_curve, index=mask.index)
    active = mask.fillna(False)
    eq = eq_full.loc[active]
    n = int(active.sum())
    ret = eq.pct_change().dropna().to_numpy()
    if ret.size < 3:
        return {"n": n, "sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    cummax = eq.cummax().replace(0, np.nan)
    mdd = float((cummax.sub(eq) / cummax).max())
    gp = float(ret[ret > 0].sum())
    gl = float(-ret[ret < 0].sum())
    pf = gp / gl if gl > 1e-12 else (20.0 if gp > 0 else 0.0)
    trade_dates = getattr(bt_result, "trades", None)
    tcount = 0
    if trade_dates is not None and hasattr(trade_dates, "empty"):
        if not trade_dates.empty:
            tcount = int(len(trade_dates))
    elif trade_dates is not None:
        try:
            tcount = int(len(trade_dates))
        except Exception:
            tcount = 0
    return {
        "n": n,
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": float(pf),
        "max_drawdown": mdd,
        "trades": tcount,
    }


def wf_train_sharpe(ohlc: pd.DataFrame, mask: pd.Series, params: dict, folds: int) -> float:
    idx = ohlc.index[mask.fillna(False)]
    if len(idx) < 200:
        return -99.0
    splits = np.array_split(idx.to_numpy(), folds)
    sharpes = []
    for part in splits:
        pmask = pd.Series(ohlc.index.isin(pd.DatetimeIndex(part)), index=ohlc.index)
        try:
            out = run_one(ohlc, params)["result"]
            sharpes.append(metrics_from(out, pmask)["sharpe"])
        except Exception:
            continue
    return float(np.mean(sharpes)) if sharpes else -99.0


def perturbation_test(ohlc: pd.DataFrame, params: dict, mask: pd.Series) -> float:
    base = metrics_from(run_one(ohlc, params)["result"], mask)["sharpe"]
    if abs(base) < 1e-9:
        return 0.0
    ratios = []
    for rv in [max(5, int(params["rv_window"]) - 10), int(params["rv_window"]) + 10]:
        for zw in [max(21, int(params["z_window"]) - 21), int(params["z_window"]) + 21]:
            for es in [
                max(0.5, float(params["entry_scale"]) - 0.25),
                float(params["entry_scale"]) + 0.25,
            ]:
                p2 = dict(params)
                p2["rv_window"] = rv
                p2["z_window"] = zw
                p2["entry_scale"] = es
                try:
                    s2 = metrics_from(run_one(ohlc, p2)["result"], mask)["sharpe"]
                    ratios.append(s2 / base if base else 0.0)
                except Exception:
                    continue
    return float(min(ratios)) if ratios else 0.0


def random_exposure_matched(
    ohlc: pd.DataFrame, mask: pd.Series, mean_exposure: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    idx = ohlc.index
    raw = rng.uniform(0.0, MAX_POS, len(idx))
    raw = raw * (mean_exposure / max(float(raw.mean()), 1e-9))
    raw = np.clip(raw, 0.0, MAX_POS)
    prices = ohlc[["Close"]].rename(columns={"Close": SPY})
    signals = pd.DataFrame({SPY: raw}, index=idx)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    bt = run_backtest(prices, signals, cfg)
    return metrics_from(bt, mask)


def inverse_regime(ohlc: pd.DataFrame, params: dict) -> dict:
    z = overnight_gap_rv_z(ohlc, int(params["rv_window"]), int(params["z_window"]))
    # inverse: de-risk when gap RV unusually LOW (calm overnight); keep exposure when elevated
    stress = ((-z).clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(params["vol_target"])
    exposure = exposure.clip(0.0, MAX_POS).fillna(float(params["vol_target"]))
    vscale = vol_scale(ohlc["Close"], float(params["vol_target"]))
    raw = exposure * vscale
    prices = ohlc[["Close"]].rename(columns={"Close": SPY})
    signals = pd.DataFrame({SPY: raw.clip(0.0, MAX_POS)}, index=prices.index)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    bt = run_backtest(prices, signals, cfg)
    return {"result": bt, "signals": signals}


def worst_regime_sharpe(bt_result, mask: pd.Series, window: int = 252) -> float:
    eq_full = pd.Series(bt_result.equity_curve, index=mask.index)
    eq = eq_full.loc[mask.fillna(False)]
    ret = eq.pct_change().dropna()
    if len(ret) < window:
        return float(sharpe_ratio(ret.to_numpy())) if len(ret) >= 3 else 0.0
    vals = []
    for i in range(window, len(ret) + 1):
        vals.append(float(sharpe_ratio(ret.iloc[i - window : i].to_numpy())))
    return float(min(vals)) if vals else 0.0


def benchmark_buy_hold(ohlc: pd.DataFrame, mask: pd.Series) -> dict:
    prices = ohlc[["Close"]].rename(columns={"Close": SPY})
    signals = pd.DataFrame({SPY: 1.0}, index=prices.index)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=1.0,
        allow_short=False,
    )
    bt = run_backtest(prices, signals, cfg)
    return metrics_from(bt, mask)


def benchmark_p_ir(strat_ret: np.ndarray, bench_ret: np.ndarray) -> tuple[float, float]:
    n = min(len(strat_ret), len(bench_ret))
    if n < 10:
        return 1.0, 0.0
    s = strat_ret[-n:]
    b = bench_ret[-n:]
    diff = s - b
    ir = float(np.sqrt(252) * diff.mean() / diff.std()) if diff.std() > 1e-12 else 0.0
    try:
        from scipy import stats

        _, p = stats.ttest_1samp(diff, 0.0, alternative="greater")
        return float(p), ir
    except Exception:
        return 1.0, ir


def main() -> dict:
    t0 = time.time()
    ohlc = _fetch()
    train_mask, val_mask, test_mask = _splits(ohlc.index)
    oos_mask = val_mask | test_mask

    grid = []
    for rvw in RV_WINDOWS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    grid.append(
                        {"rv_window": rvw, "z_window": zw, "entry_scale": es, "vol_target": vt}
                    )

    rows = []
    for p in grid:
        wf = wf_train_sharpe(ohlc, train_mask, p, WF_FOLDS_SELECTION)
        rows.append({**p, "wf_train_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_sharpe"], reverse=True)
    best = rows[0]
    best_params = {k: best[k] for k in ["rv_window", "z_window", "entry_scale", "vol_target"]}

    best_out = run_one(ohlc, best_params)
    bt = best_out["result"]
    train_m = metrics_from(bt, train_mask)
    val_m = metrics_from(bt, val_mask)
    test_m = metrics_from(bt, test_mask)
    oos_m = metrics_from(bt, oos_mask)

    wf_stability = (
        float(best["wf_train_sharpe"] / max(train_m["sharpe"], 1e-9))
        if train_m["sharpe"] > 0
        else 0.0
    )
    worst = worst_regime_sharpe(bt, oos_mask)

    eq_full = pd.Series(bt.equity_curve, index=ohlc.index)
    strat_ret = eq_full.loc[oos_mask.fillna(False)].pct_change().dropna().to_numpy()
    bh = benchmark_buy_hold(ohlc, oos_mask)
    bh_eq = ohlc["Close"].loc[oos_mask.fillna(False)]
    bench_ret = bh_eq.pct_change().dropna().to_numpy()
    bp, ir = benchmark_p_ir(strat_ret, bench_ret)
    pert = perturbation_test(ohlc, best_params, oos_mask)
    mean_exp = float(best_out["signals"][SPY].loc[oos_mask.fillna(False)].mean())
    rand = random_exposure_matched(ohlc, oos_mask, mean_exp, SEED)
    inv = metrics_from(inverse_regime(ohlc, best_params)["result"], oos_mask)

    gates = {
        "sharpe_ge_1": (oos_m["sharpe"] >= 1.0, oos_m["sharpe"]),
        "trades_ge_200": (oos_m["trades"] >= 200, oos_m["trades"]),
        "pf_ge_1_3": (oos_m["profit_factor"] >= 1.3, oos_m["profit_factor"]),
        "maxdd_le_15": (oos_m["max_drawdown"] <= 0.15, oos_m["max_drawdown"]),
        "wf_stability_ge_0_7": (wf_stability >= 0.7, wf_stability),
        "worst_regime_ge_0_3": (worst >= 0.3, worst),
        "benchmark_p_le_0_05_ir_ge_0": (bp <= 0.05 and ir >= 0.0, {"p": bp, "ir": ir}),
        "perturbation_ge_0_5": (pert >= 0.5, pert),
    }
    passed = sum(1 for v in gates.values() if v[0])
    verdict = "ACCEPT" if passed == 8 else "REJECT"

    out = {
        "nf_id": "NF-20261108-06",
        "hypothesis_id": "H143",
        "description": EXPERIMENT_DESC,
        "verdict": verdict,
        "gates_passed": f"{passed}/8",
        "gates": {k: {"pass": bool(v[0]), "value": v[1]} for k, v in gates.items()},
        "selected_params": best_params,
        "selection": {
            "method": "best train-only 4-fold WF mean Sharpe",
            "best_wf_train_sharpe": best["wf_train_sharpe"],
            "top5": rows[:5],
        },
        "metrics": {
            "train": train_m,
            "val": val_m,
            "test": test_m,
            "oos_val_test": oos_m,
            "benchmark_buy_hold_oos": bh,
        },
        "ablations": {
            "random_exposure_matched_oos": rand,
            "inverse_regime_oos": inv,
            "mean_oos_exposure_fraction": mean_exp,
        },
        "data": {
            "symbol": SPY,
            "source": "yfinance",
            "rows": int(len(ohlc)),
            "start": str(ohlc.index.min().date()),
            "end": str(ohlc.index.max().date()),
            "splits": {
                "train": [
                    str(ohlc.index[train_mask].min().date()),
                    str(ohlc.index[train_mask].max().date()),
                ],
                "val": [
                    str(ohlc.index[val_mask].min().date()),
                    str(ohlc.index[val_mask].max().date()),
                ],
                "test": [
                    str(ohlc.index[test_mask].min().date()),
                    str(ohlc.index[test_mask].max().date()),
                ],
            },
        },
        "timing_seconds": round(time.time() - t0, 2),
        "seed": SEED,
        "src_qtr_changed": False,
    }
    run_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261108_06_spy_overnight_gap_rv"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str))
    grid_df = pd.DataFrame(rows)
    grid_df.to_csv(run_dir / "grid.csv", index=False)
    meta = {"description": EXPERIMENT_DESC, "data_start": DATA_START, "data_end": DATA_END}
    (run_dir / "data_meta.json").write_text(json.dumps(meta, indent=2))
    print(
        json.dumps(
            {"verdict": verdict, "gates_passed": f"{passed}/8", "oos": oos_m, "path": str(run_dir)},
            indent=2,
        )
    )
    return out


if __name__ == "__main__":
    main()
