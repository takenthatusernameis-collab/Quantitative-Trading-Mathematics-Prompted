"""NF-20261107-10 / H125 (pre-registered, Cycle 39): SPY timing from the
cross-asset equity-vs-rates implied volatility spread (^VIX minus ^MOVE).

Signal = z-score of the trailing *relative* implied-vol spread `VIX - MOVE`
(equity implied volatility minus rates implied volatility). Elevated spread means
equity fear/stress is high relative to rates volatility — a cross-asset vol
transmission / risk-appetite stress signal. Rule reduces vol-targeted long SPY
to flat when `z > entry_z` and re-enters when `z < exit_z` (hysteresis), with
1-bar execution delay (engine signals.shift(1)).

Repo-relative novelty (honest). H100 (NF-20261106-02, REJECT 4/9) tested ^MOVE
*rates-vol level* alone as a stress signal on SPY — a single-asset rates-vol
observable. H125 uses the *cross-asset relative* spread `VIX - MOVE` (equity vs
rates implied vol transmission), a different observable and causal channel than
MOVE level. H86/H123 tested VIX term-structure shape (VIX3M/VIX slope, VIX9D/VIX
front-end spread), different maturity/within-equity-vol observables. H104 tested
VVIX (vol-of-vol), H17 VRP. H125 is a cross-asset vol-transmission timing
family; adjacency to H100 is acknowledged and novelty scored moderately.

Data (free, yfinance): ^VIX (4235 rows), ^MOVE (4149 rows), SPY (4233 rows).
Common aligned sample 2010-01-04..2024-12-30, 3692 rows (all positive). Point-in-
time; no paid data.

Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2024-12-31.
Grid (bounded): window {21,63} x entry_z {1.0,1.5,2.0} x exit_z {0.0,0.5}
  x vol_target {0.10,0.15} (24 combos; exit_z < entry_z enforced).
Selection = best train-only 4-fold walk-forward mean Sharpe; Test protected.
Gates on OOS Val+Test: Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
  WF stability>=0.7, worst-regime yearly Sharpe>=0.3, benchmark p<=0.05 with
  IR>=0, perturbation min ratio>=0.5. Equity CostModel defaults; no src/qtr change.
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
    "NF-20261107-10/H125: SPY timing from the cross-asset VIX-MOVE implied-vol "
    "spread. Reduce vol-targeted long SPY to flat when z-score of trailing "
    "(VIX - MOVE) > entry_z, re-enter when z < exit_z (hysteresis), 1-bar delay. "
    "Train-only WF selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
VIX = "^VIX"
MOVE = "^MOVE"
UNIVERSE = [SPY, VIX, MOVE]
DATA_START = "2010-01-01"
DATA_END = "2024-12-31"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

WINDOWS = [21, 63]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5]
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


def spread_z(vix: pd.Series, move: pd.Series, window: int) -> pd.Series:
    """Z-score of the cross-asset vol spread VIX - MOVE (past-only)."""
    spread = vix.astype(float) - move.astype(float)
    mean = spread.rolling(window, min_periods=window).mean()
    std = spread.rolling(window, min_periods=window).std(ddof=0)
    return (spread - mean) / std.replace(0.0, np.nan)


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(z: pd.Series, entry_z: float, exit_z: float, vol_target: float) -> pd.Series:
    """Hysteresis long/flat exposure from cross-asset vol spread z-score.

    in_pos starts True. Exit to flat when z > entry_z (equity stress high relative
    to rates vol). Re-enter long when z < exit_z.
    """
    assert exit_z < entry_z
    in_pos = True
    out = []
    vals = z.fillna(0.0).values
    for zv in vals:
        if in_pos and zv > entry_z:
            in_pos = False
        elif (not in_pos) and zv < exit_z:
            in_pos = True
        out.append(1.0 if in_pos else 0.0)
    base = pd.Series(out, index=z.index, dtype=float)
    return (base * vol_target).clip(lower=0.0, upper=vol_target)


def run_one(prices: pd.DataFrame, params: dict):
    z = spread_z(prices[VIX], prices[MOVE], params["window"])
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    scale = vol_scale(spy_ret, params["vol_target"])
    base = build_exposure(z, params["entry_z"], params["exit_z"], 1.0)
    exposure = (base * scale).clip(0.0, 1.0) * MAX_POS
    signals = pd.DataFrame({SPY: exposure}, index=prices.index)
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
    )
    bt = run_backtest(prices[[SPY]], signals, config=config)
    return {"backtest": bt, "z": z, "signals": signals}


def _returns_series(bt, index: pd.Index) -> pd.Series:
    r = bt.returns
    if isinstance(r, pd.Series):
        return r.reindex(index).fillna(0.0)
    return pd.Series(np.asarray(r, dtype=float), index=index).fillna(0.0)


def metrics_from(bt, mask: pd.Series) -> dict:
    idx = mask.index
    r = _returns_series(bt, idx)[mask].dropna()
    if len(r) < 2:
        return {
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
            "n": int(len(r)),
        }
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 0 else (float("inf") if pos > 0 else 0.0)
    eq = (1 + r).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    trades = 0
    t = getattr(bt, "trades", None)
    if t is not None and len(t):
        try:
            if "timestamp" in t.columns:
                ts = pd.to_datetime(t["timestamp"])
                trades = int(mask.reindex(ts).fillna(False).sum())
            else:
                trades = int(len(t))
        except Exception:
            trades = int(len(t))
    if trades == 0 and isinstance(getattr(bt, "metrics", None), dict):
        trades = int(bt.metrics.get("n_trades", bt.metrics.get("num_trades", 0)) or 0)
    return {
        "sharpe": float(sharpe_ratio(r.values)),
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": trades,
        "n": int(len(r)),
    }


def wf_stability(prices: pd.DataFrame, params: dict, train_mask) -> float:
    idx = prices.index[train_mask]
    n = len(idx)
    fold = n // WF_FOLDS_SELECTION
    sharpes = []
    for i in range(WF_FOLDS_SELECTION):
        s = i * fold
        e = n if i == WF_FOLDS_SELECTION - 1 else (i + 1) * fold
        m = pd.Series(False, index=prices.index)
        m.loc[idx[s:e]] = True
        met = metrics_from(run_one(prices, params)["backtest"], m)
        if met["n"] > 20:
            sharpes.append(met["sharpe"])
    if len(sharpes) < 2:
        return 0.0
    arr = np.array(sharpes)
    neg = (arr < 0).mean()
    mean = float(arr.mean())
    if mean <= 0:
        return 0.0
    return float(max(0.0, mean / (np.std(arr, ddof=0) + 1e-9)) * (1 - neg))


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
        return {"p_value": max(0.0, min(1.0, p_one)), "information_ratio": ir, "t": float(t)}
    except Exception:
        return {"p_value": 1.0, "information_ratio": ir}


def _ablations(prices: pd.DataFrame, params: dict, mask: pd.Series) -> dict:
    # buy-hold SPY
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
    # random exposure-matched
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
    # inverse: long when z > entry_z (high equity-vs-rates stress) — opposite
    z = base["z"]
    inv = pd.Series(0.0, index=prices.index)
    in_pos = False
    for i, zv in enumerate(z.fillna(0.0).values):
        if (not in_pos) and zv > params["entry_z"]:
            in_pos = True
        elif in_pos and zv < params["exit_z"]:
            in_pos = False
        inv.iloc[i] = 1.0 if in_pos else 0.0
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    inv_sig = pd.DataFrame(
        {SPY: (inv * vol_scale(spy_ret, params["vol_target"])).clip(0, 1) * MAX_POS},
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
        "inverse_stress_long": metrics_from(inv_bt, mask),
    }


def _perturbation(prices: pd.DataFrame, params: dict, mask: pd.Series, base_sh: float):
    ratios = []
    for dw, de, dx, dv in [
        (-0, 0.5, 0.0, 0.0),
        (0, -0.5, 0.0, 0.0),
        (0, 0.0, 0.0, 0.02),
        (42, 0.0, 0.0, 0.0),
    ]:
        p = dict(params)
        p["window"] = max(5, p["window"] + dw)
        p["entry_z"] = max(p["exit_z"] + 0.1, p["entry_z"] + de)
        p["exit_z"] = max(0.0, min(p["entry_z"] - 0.1, p["exit_z"] + dx))
        p["vol_target"] = max(0.02, p["vol_target"] + dv)
        m = metrics_from(run_one(prices, p)["backtest"], mask)
        denom = abs(base_sh) if abs(base_sh) > 1e-9 else 1.0
        ratios.append(m["sharpe"] / denom)
    return {"min_ratio_vs_optimum": float(min(ratios)) if ratios else 0.0}


def evaluate_gates(train_m, oos_m, wf, worst, bench, perturb) -> tuple[bool, dict]:
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
    run_dir = Path(".experiments") / "nf_runs" / "nf_20261107_10_vix_move_spread"
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
    for window in WINDOWS:
        for entry_z in ENTRY_ZS:
            for exit_z in EXIT_ZS:
                if exit_z >= entry_z:
                    continue
                for vol_target in VOL_TARGETS:
                    grid.append(
                        {
                            "window": window,
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
            {**p, "train_sharpe": met["sharpe"], "train_trades": met["trades"], "train_wf": wf}
        )
    scored.sort(key=lambda x: (x["train_wf"], x["train_sharpe"]), reverse=True)
    best = {k: scored[0][k] for k in ["window", "entry_z", "exit_z", "vol_target"]}
    best_res = run_one(prices, best)
    train_m = metrics_from(best_res["backtest"], train_mask)
    val_m = metrics_from(best_res["backtest"], val_mask)
    test_m = metrics_from(best_res["backtest"], test_mask)
    oos_m = metrics_from(best_res["backtest"], oos_mask)
    wf = wf_stability(prices, best, train_mask)
    worst = worst_yearly_sharpe(best_res["backtest"], oos_mask)
    bench = benchmark_cmp(best_res["backtest"], oos_mask, prices[SPY])
    perturb = _perturbation(prices, best, oos_mask, oos_m["sharpe"])
    passed, gates = evaluate_gates(train_m, oos_m, wf, worst, bench, perturb)
    ablations = _ablations(prices, best, oos_mask)

    verdict = "ACCEPT" if passed else "REJECT"
    summary = {
        "experiment": "nf_20261107_10_vix_move_spread",
        "nf_id": "NF-20261107-10",
        "h_id": "H125",
        "description": EXPERIMENT_DESC,
        "verdict": verdict,
        "gate_pass": passed,
        "gates": gates,
        "selected_params": best,
        "train_metrics": train_m,
        "val_metrics": val_m,
        "test_metrics": test_m,
        "oos_val_test_metrics": oos_m,
        "wf_stability": wf,
        "worst_regime_yearly_sharpe": worst,
        "benchmark": bench,
        "perturbation": perturb,
        "ablations": ablations,
        "grid_top5": scored[:5],
        "data": {
            "rows": len(prices),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
        },
        "timing_seconds": round(time.time() - t0, 2),
        "cost_model": "CostModel(equity 1+1bp)",
        "seed": SEED,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gate_pass": passed,
                "gates": gates,
                "oos": oos_m,
                "selected": best,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
