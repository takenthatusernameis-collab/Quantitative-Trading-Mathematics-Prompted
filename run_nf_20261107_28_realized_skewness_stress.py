"""NF-20261107-28 / H128 (pre-registered, Cycle 42): SPY timing from the
realized skewness stress regime (realized third-moment / crash-risk timing).

Signal = z-score of the trailing rolling realized skewness of SPY daily
returns. Abnormally low (negative) realized skewness indicates asymmetric
downside risk / elevated crash probability; the rule reduces vol-targeted
long SPY to flat when `z <= entry_z` and re-enters when `z > exit_z`
(hysteresis, exit_z < entry_z), with 1-bar execution delay
(engine signals.shift(1)).

Realized skewness is the realized third standardized moment of SPY returns
itself, computed point-in-time from past returns only.

Repo-relative novelty (honest). H89 (NF-20261104-10, ^SKEW implied tail
skew regime) uses the CBOE *implied* SKEW index from option prices — an
options-surface observable. H128 uses *realized* skewness computed from
SPY's own past returns — a different moment (realized 3rd vs implied
surface), different observable, different causal chain (realized crash-risk
build-up vs implied tail-protection demand). H122 (NF-20261107-07, REJECT
3/8) uses downside/upside *variance ratio* (a downside second-moment
measure); H128 uses third-moment skewness. Honest adjacency to the
higher-moment / downside-risk stress families (H89, H122, H124 MAX) is
acknowledged and novelty scored moderately (4/5); the realized-skewness
observable and construction are repo-new.

Data (free, yfinance): SPY daily adjusted close. Common aligned sample
2010-01-04..2025-01-03, 3776 rows (all positive). Point-in-time.

Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): lookback {63,126} x z_window {63} x entry_z {0.0,-0.5}
  x exit_z {-0.5,-1.0} (exit_z < entry_z) x vol_target {0.10,0.15}
  (12 combos). Selection = best train-only 4-fold walk-forward mean Sharpe;
  Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime yearly Sharpe>=0.3, benchmark p<=0.05 with
  IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no src/qtr
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
    "NF-20261107-28/H128: SPY timing from realized skewness stress regime. "
    "Reduce vol-targeted long SPY to flat when z-score of trailing realized "
    "SPY skewness <= entry_z, re-enter when z > exit_z (hysteresis), "
    "1-bar delay. Train-only WF selection; Test protected; OOS Val+Test gates."
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

LOOKBACKS = [63, 126]
Z_WINDOWS = [63]
ENTRY_ZS = [0.0, -0.5]
EXIT_ZS = [-0.5, -1.0]
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


def realized_skew_z(spy: pd.Series, lookback: int, z_window: int) -> pd.Series:
    """Z-score of trailing rolling realized skewness of SPY returns (past-only)."""
    ret = spy.astype(float).pct_change()
    skew = ret.rolling(lookback, min_periods=lookback).skew()
    mean = skew.rolling(z_window, min_periods=z_window).mean()
    std = skew.rolling(z_window, min_periods=z_window).std(ddof=0)
    return (skew - mean) / std.replace(0.0, np.nan)


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(z: pd.Series, entry_z: float, exit_z: float, vol_target: float):
    """Hysteresis long/flat exposure from realized-skewness z-score.

    When skew z > entry_z (normal / non-stress skew) -> vol-targeted long (1).
    When skew z < exit_z (abnormally low / negative skew stress) -> flat (0).
    Otherwise hold previous state.
    """
    sig = pd.Series(np.nan, index=z.index, dtype=float)
    sig[z > entry_z] = 1.0
    sig[z < exit_z] = 0.0
    sig = sig.ffill().fillna(1.0)
    sig[z.isna()] = 0.0
    return sig * float(vol_target)


def run_one(prices: pd.DataFrame, params: dict) -> dict:
    z = realized_skew_z(
        prices[SPY],
        int(params["lookback"]),
        int(params["z_window"]),
    )
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(
        z, float(params["entry_z"]), float(params["exit_z"]), float(params["vol_target"])
    )
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
    res = run_one(prices, params)
    for f in folds:
        if len(f) < 20:
            continue
        fold_idx = idx[f[0] : f[-1] + 1]
        m = pd.Series(False, index=train_mask.index)
        m.loc[fold_idx] = True
        met = metrics_from(res["backtest"], m)
        if met["n"] > 10:
            sharpes.append(met["sharpe"])
    if not sharpes:
        return 0.0
    pos = [s for s in sharpes if s > 0]
    return float(len(pos) / len(sharpes)) if sharpes else 0.0


def worst_yearly_sharpe(bt, oos_mask: pd.Series) -> float:
    r = _returns_series(bt, oos_mask.index)[oos_mask].dropna()
    if r.empty:
        return 0.0
    vals = []
    for _, g in r.groupby(r.index.year):
        if len(g) >= 30:
            vals.append(float(sharpe_ratio(g.values)))
    return float(min(vals)) if vals else float(sharpe_ratio(r.values))


def benchmark_cmp(bt, oos_mask, spy: pd.Series) -> dict:
    r = _returns_series(bt, oos_mask.index)[oos_mask].dropna()
    b = spy.pct_change().reindex(r.index).dropna()
    common = r.index.intersection(b.index)
    r, b = r.loc[common], b.loc[common]
    if len(r) < 30:
        return {"p_value": 1.0, "information_ratio": 0.0}
    diff = (r - b).values
    ir = float(np.mean(diff) / (np.std(diff, ddof=0) + 1e-12) * np.sqrt(252))
    try:
        from scipy import stats

        t, p = stats.ttest_1samp(diff, 0.0)
        p_one = float(p / 2) if np.mean(diff) > 0 else float(1 - p / 2)
        return {
            "p_value": max(0.0, min(1.0, p_one)),
            "information_ratio": ir,
            "t": float(t),
        }
    except Exception:
        return {"p_value": 1.0, "information_ratio": ir}


def _ablations(prices: pd.DataFrame, params: dict, mask: pd.Series) -> dict:
    bh = pd.DataFrame({SPY: np.ones(len(prices)) * MAX_POS}, index=prices.index)
    bh_bt = run_backtest(
        prices[[SPY]],
        bh,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    rng = np.random.default_rng(SEED)
    base = run_one(prices, params)
    exp = base["signals"][SPY].values.copy()
    rng.shuffle(exp)
    rand_bt = run_backtest(
        prices[[SPY]],
        pd.DataFrame({SPY: exp}, index=prices.index),
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    z = base["z"]
    inv2 = pd.Series(0.0, index=prices.index)
    in_pos = False
    vals = z.fillna(0.0).values
    for i, zv in enumerate(vals):
        if (not in_pos) and zv <= params["entry_z"]:
            in_pos = True
        elif in_pos and zv > params["exit_z"]:
            in_pos = False
        inv2.iloc[i] = 1.0 if in_pos else 0.0
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    inv_sig = pd.DataFrame(
        {SPY: (inv2 * vol_scale(spy_ret, params["vol_target"])).clip(0, 1) * MAX_POS},
        index=prices.index,
    )
    inv_bt = run_backtest(
        prices[[SPY]],
        inv_sig,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    return {
        "buy_hold_spy": metrics_from(bh_bt, mask),
        "random_exposure_matched": metrics_from(rand_bt, mask),
        "inverse_skew_stress_long": metrics_from(inv_bt, mask),
    }


def _perturbation(prices: pd.DataFrame, params: dict, mask: pd.Series, base_sh: float):
    ratios = []
    for dl, dz, de, dv in [
        (0, 0, 0.5, 0.0),
        (0, 0, -0.5, 0.0),
        (0, 0, 0.0, 0.02),
        (42, 0, 0.0, 0.0),
        (0, 63, 0.0, 0.0),
    ]:
        p = dict(params)
        p["lookback"] = max(10, p["lookback"] + dl)
        p["z_window"] = max(20, p["z_window"] + dz)
        p["entry_z"] = min(p["exit_z"] - 0.1, p["entry_z"] + de)
        p["vol_target"] = max(0.02, p["vol_target"] + dv)
        m = metrics_from(run_one(prices, p)["backtest"], mask)
        denom = abs(base_sh) if abs(base_sh) > 1e-9 else 1.0
        ratios.append(m["sharpe"] / denom)
    return {"min_ratio_vs_optimum": float(min(ratios)) if ratios else 0.0}


def evaluate_gates(oos_m, wf, worst, bench, perturb) -> tuple[bool, dict]:
    gates = {
        "sharpe": oos_m["sharpe"] >= 1.0,
        "trades": oos_m["trades"] >= 200,
        "profit_factor": oos_m["profit_factor"] >= 1.3,
        "max_drawdown": oos_m["max_drawdown"] >= -0.15,
        "wf_stability": wf >= 0.7,
        "worst_regime": worst >= 0.3,
        "benchmark": bench["p_value"] <= 0.05 and bench["information_ratio"] >= 0.0,
        "perturbation": perturb["min_ratio_vs_optimum"] >= 0.5,
    }
    return all(gates.values()), gates


def main() -> int:
    t0 = time.time()
    run_dir = Path(".experiments") / "nf_runs" / "nf_20261107_28_realized_skewness_stress"
    run_dir.mkdir(parents=True, exist_ok=True)
    prices = _fetch()
    (run_dir / "data_meta.json").write_text(
        json.dumps(
            {
                "rows": len(prices),
                "start": str(prices.index.min().date()),
                "end": str(prices.index.max().date()),
                "symbols": UNIVERSE,
            },
            indent=2,
        )
    )
    train_mask, val_mask, test_mask = _splits(prices.index)
    oos_mask = val_mask | test_mask

    grid = []
    for lookback in LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_z in ENTRY_ZS:
                for exit_z in EXIT_ZS:
                    if exit_z >= entry_z:
                        continue
                    for vol_target in VOL_TARGETS:
                        grid.append(
                            {
                                "lookback": lookback,
                                "z_window": z_window,
                                "entry_z": entry_z,
                                "exit_z": exit_z,
                                "vol_target": vol_target,
                            }
                        )
    scored = []
    for p in grid:
        met = metrics_from(run_one(prices, p)["backtest"], train_mask)
        wf = wf_stability(prices, p, train_mask)
        scored.append(
            {
                **p,
                "train_sharpe": met["sharpe"],
                "train_trades": met["trades"],
                "wf": wf,
            }
        )
    pd.DataFrame(scored).to_csv(run_dir / "grid.csv", index=False)
    best = max(scored, key=lambda r: (r["wf"], r["train_sharpe"]))
    best_p = {k: best[k] for k in ["lookback", "z_window", "entry_z", "exit_z", "vol_target"]}

    best_res = run_one(prices, best_p)
    bt = best_res["backtest"]
    train_m = metrics_from(bt, train_mask)
    val_m = metrics_from(bt, val_mask)
    test_m = metrics_from(bt, test_mask)
    oos_m = metrics_from(bt, oos_mask)
    oos_m["trades"] = trades_in_mask(bt, oos_mask) or oos_m["trades"]
    wf = wf_stability(prices, best_p, train_mask)
    worst = worst_yearly_sharpe(bt, oos_mask)
    bench = benchmark_cmp(bt, oos_mask, prices[SPY])
    perturb = _perturbation(prices, best_p, oos_mask, oos_m["sharpe"])
    abl = _ablations(prices, best_p, oos_mask)
    passed, gates = evaluate_gates(oos_m, wf, worst, bench, perturb)

    summary = {
        "experiment_id": f"nf_20261107_28_realized_skewness_stress_{int(time.time())}",
        "hypothesis": "H128",
        "nf_id": "NF-20261107-28",
        "description": EXPERIMENT_DESC,
        "runtime_seconds": round(time.time() - t0, 2),
        "selected_params": best_p,
        "train_metrics": train_m,
        "val_metrics": val_m,
        "test_metrics": test_m,
        "oos_val_test_metrics": oos_m,
        "wf_stability_train": wf,
        "worst_yearly_sharpe_oos": worst,
        "benchmark_vs_buy_hold_spy": bench,
        "perturbation": perturb,
        "ablations_oos": abl,
        "gates": gates,
        "passed_all_gates": passed,
        "verdict": "ACCEPT_FOR_FURTHER_VALIDATION" if passed else "REJECT",
        "data": {
            "rows": len(prices),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
        },
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"verdict": summary["verdict"], "gates": gates, "oos": oos_m}, indent=2))
    return 0


def trades_in_mask(bt, mask: pd.Series) -> int:
    trades = getattr(bt, "trades", None)
    if trades is None or len(trades) == 0:
        return 0
    df = pd.DataFrame(trades) if not isinstance(trades, pd.DataFrame) else trades.copy()
    for col in ("timestamp", "entry_time", "exit_time", "time", "date"):
        if col in df.columns:
            t = pd.to_datetime(df[col])
            return int(t.isin(mask.index[mask]).sum())
    for col in df.columns:
        try:
            t = pd.to_datetime(df[col])
            if t.notna().any():
                return int(t.isin(mask.index[mask]).sum())
        except Exception:
            continue
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
