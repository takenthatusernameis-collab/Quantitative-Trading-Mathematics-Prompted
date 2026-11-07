"""NF-20261107-30 / H130 (pre-registered, Cycle 44): SPY timing from the
cross-sectional average idiosyncratic-volatility (IVOL) regime.

Signal = z-score of trailing cross-sectional mean IVOL across liquid sector
ETFs vs SPY. IVOL for each sector is the rolling std of residual returns from
a trailing beta regression on SPY (past-only). Abnormally high aggregate IVOL
proxies elevated stock/sector-specific risk and fragile risk appetite; the
rule continuously reduces vol-targeted long SPY exposure as the IVOL z-score
rises (linear stress), with 1-bar execution delay (engine signals.shift(1)).

Repo-relative novelty (honest). H93 (NF-20261105-13, REJECT 2/9) ranks ETFs by
*IVOL level* cross-sectionally (bottom/top quintiles, monthly rebalance, long
low-IVOL / short high-IVOL) — a different construction, objective, and
trade structure. H130 tests a *market-wide aggregate IVOL regime* z-score as a
continuous SPY de-risking overlay (no cross-sectional ranking portfolio), using
sector ETFs as the IVOL panel. H117/H129 test sector co-movement/beta
statistics (correlation, beta) — different observable (residual dispersion) and
different mechanism (idiosyncratic/dispersion stress vs systematic
co-movement/beta expansion). Honest adjacency to H93 (IVOL concept) and the
sector-stat construction class is acknowledged; novelty scored moderately.

Data (free, yfinance): SPY + XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY daily adjusted
close (9 sectors; XLC/XLRE excluded for 2010+ history, same feasibility as
H117/H129). Common aligned sample 2010-01-04..2025-01-03, 3776 rows (all
positive). Point-in-time.

Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): beta_window {21,63} x z_window {126} x entry_scale {1.0,1.5,2.0}
  x vol_target {0.10,0.15} (12 combos). Selection = best train-only 4-fold
  walk-forward mean Sharpe; Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
  with IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no src/qtr
  change.
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
    "NF-20261107-30/H130: SPY timing from cross-sectional average sector IVOL "
    "regime. Continuous de-risking when z-score of trailing mean sector IVOL "
    "vs SPY is elevated; 1-bar delay. Train-only WF selection; Test protected; "
    "OOS Val+Test gates."
)

SPY = "SPY"
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
UNIVERSE = [SPY] + SECTORS
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

BETA_WINDOWS = [21, 63]
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


def avg_ivol_z(prices: pd.DataFrame, beta_window: int, z_window: int) -> pd.Series:
    """Z-score of cross-sectional mean sector IVOL vs SPY (past-only)."""
    ret = prices.astype(float).pct_change()
    spy_ret = ret[SPY]
    var_spy = spy_ret.rolling(beta_window, min_periods=beta_window).var(ddof=0)
    ivols = {}
    for sec in SECTORS:
        cov = ret[sec].rolling(beta_window, min_periods=beta_window).cov(spy_ret)
        beta = cov / var_spy.replace(0.0, np.nan)
        resid = ret[sec] - beta * spy_ret
        ivols[sec] = resid.rolling(beta_window, min_periods=beta_window).std(ddof=0) * np.sqrt(252)
    avg = pd.DataFrame(ivols).mean(axis=1)
    mean = avg.rolling(z_window, min_periods=z_window).mean()
    std = avg.rolling(z_window, min_periods=z_window).std(ddof=0)
    return (avg - mean) / std.replace(0.0, np.nan)


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    """Continuous de-risking: exposure falls linearly as IVOL z rises above 0."""
    stress = (z.clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    exposure = exposure.where(z.notna(), 0.0)
    return exposure.clip(0.0, float(vol_target))


def run_one(prices: pd.DataFrame, params: dict) -> dict:
    z = avg_ivol_z(prices, int(params["beta_window"]), int(params["z_window"]))
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
        "n": int(len(r)),
        "total_return": float(eq.iloc[-1] - 1.0),
    }


def wf_stability(prices: pd.DataFrame, params: dict, train_mask: pd.Series) -> float:
    idx = train_mask.index[train_mask]
    if len(idx) < 80:
        return 0.0
    folds = np.array_split(np.arange(len(idx)), WF_FOLDS_SELECTION)
    sharpes = []
    for part in folds:
        if len(part) < 30:
            continue
        fold_mask = pd.Series(False, index=prices.index)
        fold_mask.loc[idx[part[0]] : idx[part[-1]]] = True
        fold_mask &= train_mask
        res = run_one(prices, params)
        sharpes.append(metrics_from(res["backtest"], fold_mask)["sharpe"])
    if not sharpes:
        return 0.0
    arr = np.array(sharpes)
    pos = arr[arr > 0]
    return float(len(pos) / len(arr))


def worst_regime_sharpe(bt, mask: pd.Series, window: int = 252) -> float:
    r = _returns_series(bt, mask.index)[mask].dropna()
    if len(r) < window:
        return float(sharpe_ratio(r.values)) if len(r) else 0.0
    vals = []
    for i in range(window, len(r) + 1):
        vals.append(float(sharpe_ratio(r.iloc[i - window : i].values)))
    return float(min(vals)) if vals else 0.0


def perturbation_ratio(prices: pd.DataFrame, params: dict, oos_mask: pd.Series) -> float:
    base = metrics_from(run_one(prices, params)["backtest"], oos_mask)["sharpe"]
    if abs(base) < 1e-12:
        return 0.0
    ratios = []
    for bw in [max(10, params["beta_window"] - 10), params["beta_window"] + 10]:
        for es in [max(0.5, params["entry_scale"] - 0.25), params["entry_scale"] + 0.25]:
            p = dict(params)
            p["beta_window"] = bw
            p["entry_scale"] = es
            s = metrics_from(run_one(prices, p)["backtest"], oos_mask)["sharpe"]
            if base > 0:
                ratios.append(s / base)
            else:
                ratios.append(base / s if abs(s) > 1e-12 else 0.0)
    return float(min(ratios)) if ratios else 0.0


def random_exposure_matched(
    spy_ret: pd.Series, exposure: pd.Series, mask: pd.Series, seed: int = SEED
) -> dict:
    rng = np.random.default_rng(seed)
    on = (exposure > 1e-9).astype(int).values
    n_on = int(on.sum())
    idx = np.arange(len(on))
    rng.shuffle(idx)
    rand_on = np.zeros_like(on)
    rand_on[idx[:n_on]] = 1
    avg = float(exposure[exposure > 1e-9].mean()) if n_on else 0.0
    r = spy_ret.values * rand_on * avg
    rs = pd.Series(r, index=spy_ret.index)[mask].dropna()
    if rs.empty:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": n_on}
    sh = float(sharpe_ratio(rs.values))
    pos = rs[rs > 0].sum()
    neg = -rs[rs < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + rs).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    return {"sharpe": sh, "profit_factor": pf, "max_drawdown": dd, "trades": n_on}


def benchmark_pvalue(strategy_r: pd.Series, bench_r: pd.Series) -> tuple[float, float]:
    diff = (strategy_r - bench_r).dropna()
    if len(diff) < 30:
        return 1.0, 0.0
    ir = float(diff.mean() / diff.std(ddof=0) * np.sqrt(252)) if diff.std(ddof=0) > 1e-12 else 0.0
    from math import erf, sqrt

    z = (
        float(diff.mean() / (diff.std(ddof=0) / sqrt(len(diff))))
        if diff.std(ddof=0) > 1e-12
        else 0.0
    )
    p = float(1.0 - 0.5 * (1.0 + erf(z / sqrt(2.0))))
    return p, ir


def main() -> dict:
    t0 = time.time()
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos = val | test
    grid = []
    best = None
    for bw in BETA_WINDOWS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {
                        "beta_window": bw,
                        "z_window": zw,
                        "entry_scale": es,
                        "vol_target": vt,
                    }
                    tr_res = run_one(prices, params)
                    tr_m = metrics_from(tr_res["backtest"], train)
                    wf = wf_stability(prices, params, train)
                    score = tr_m["sharpe"]
                    grid.append(
                        {**params, "train_sharpe": tr_m["sharpe"], "wf_stability_train": wf}
                    )
                    if best is None or score > best[0]:
                        best = (score, params)
    assert best is not None
    sel = best[1]
    res = run_one(prices, sel)
    oos_m = metrics_from(res["backtest"], oos)
    tr_m = metrics_from(res["backtest"], train)
    wf = wf_stability(prices, sel, train)
    worst = worst_regime_sharpe(res["backtest"], oos)
    pert = perturbation_ratio(prices, sel, oos)

    spy_ret = prices[SPY].pct_change().fillna(0.0)
    strat_r = _returns_series(res["backtest"], prices.index)
    bench_r = (spy_ret * (vol_scale(spy_ret, sel["vol_target"]) > 0).astype(float)).fillna(0.0)
    bench_r = bench_r * MAX_POS
    bp, ir = benchmark_pvalue(strat_r[oos], bench_r[oos])
    rnd = random_exposure_matched(spy_ret, res["signals"][SPY], oos)
    buyhold = metrics_from(run_one(prices, {**sel, "entry_scale": 999.0})["backtest"], oos)
    inv_params = dict(sel)
    inv_res = run_one(prices, inv_params)
    inv_exp = (float(sel["vol_target"]) - res["signals"][SPY]).clip(0.0, float(sel["vol_target"]))
    inv_bt = run_backtest(
        prices[[SPY]],
        pd.DataFrame({SPY: inv_exp * MAX_POS / float(sel["vol_target"])}, index=prices.index),
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    inv_m = metrics_from(inv_bt, oos)

    gates = {
        "sharpe_ge_1": oos_m["sharpe"] >= 1.0,
        "trades_ge_200": oos_m["trades"] >= 200,
        "pf_ge_1_3": oos_m["profit_factor"] >= 1.3,
        "max_dd_le_15pct": oos_m["max_drawdown"] >= -0.15,
        "wf_stability_ge_0_7": wf >= 0.7,
        "worst_regime_ge_0_3": worst >= 0.3,
        "benchmark_p_le_0_05_ir_ge_0": bp <= 0.05 and ir >= 0.0,
        "perturbation_ge_0_5": pert >= 0.5,
    }
    verdict = "ACCEPT" if all(gates.values()) else "REJECT"

    out = {
        "experiment": "nf_20261107_30_avg_ivol_regime",
        "hypothesis": "H130",
        "nf_id": "NF-20261107-30",
        "description": EXPERIMENT_DESC,
        "data": {
            "source": "yfinance auto_adjust=True",
            "universe": UNIVERSE,
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "rows": int(len(prices)),
        },
        "selected_params": sel,
        "train": tr_m,
        "oos_val_test": oos_m,
        "wf_stability": wf,
        "worst_regime_rolling252_sharpe": worst,
        "benchmark": {"p_value": bp, "information_ratio": ir},
        "perturbation_min_ratio": pert,
        "ablations": {
            "buy_hold_spy": buyhold,
            "random_exposure_matched": rnd,
            "inverse_ivol_regime": inv_m,
        },
        "gates": gates,
        "gates_passed": int(sum(gates.values())),
        "gates_total": len(gates),
        "verdict": f"{verdict} ({sum(gates.values())}/{len(gates)})",
        "grid_top5": sorted(grid, key=lambda x: x["train_sharpe"], reverse=True)[:5],
        "runtime_sec": round(time.time() - t0, 2),
    }
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261107_30_avg_ivol_regime"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
    (out_dir / "grid.csv").write_text(pd.DataFrame(grid).to_csv(index=False))
    meta = {
        "start": str(prices.index.min().date()),
        "end": str(prices.index.max().date()),
        "rows": int(len(prices)),
        "universe": UNIVERSE,
    }
    (out_dir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"verdict": out["verdict"], "oos": oos_m, "selected": sel}, indent=2))
    return out


if __name__ == "__main__":
    main()
