"""NF-20261108-03 / H142 (pre-registered, Cycle 56): SPY timing from
turn-of-quarter window-dressing/rebalancing flows (calendar/auction).

Signal (past-only, ex-ante calendar):
  toq_t = 1 if t is in turn-of-quarter window (last end_days trading days of
         quarter Q and/or first start_days trading days of quarter Q+1),
         else 0 (deterministic from calendar).
When in window (institutional rebalancing/window dressing flows), reduce
vol-targeted long SPY exposure continuously with 1-bar execution delay
(engine signals.shift(1)), long-only.

Repo-relative novelty (honest). Turn-of-month tested as H91 (REJECT 3/9);
quarter-end is a different institutional cycle (quarterly reporting/rebalancing),
not executed as root family. Honest adjacency to H91 statistical form
acknowledged.

Data (free, yfinance): SPY daily Close (auto_adjust), point-in-time.
Splits (pre-registered): Train 2010-01-04->2019-12-31 / Val 2020-01-01->
2021-12-31 / Test (protected) 2022-01-01->2025-01-03.
Grid (bounded): end_days {1,2,3} x start_days {1,2} x entry_scale {1.0,1.5,2.0}
  x vol_target {0.10,0.15} (18 combos). Selection = best train-only 4-fold
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
    "NF-20261108-03/H142: SPY timing from turn-of-quarter window-dressing/rebalancing flows. "
    "Continuous de-risking during ex-ante turn-of-quarter window (last end_days of quarter + "
    "first start_days of next quarter). 1-bar delay. Train-only WF selection; Test protected; OOS Val+Test gates."
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

END_DAYS = [1, 2, 3]
START_DAYS = [1, 2]
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


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)), index=index
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def toq_window(index: pd.DatetimeIndex, end_days: int, start_days: int) -> pd.Series:
    """Deterministic ex-ante turn-of-quarter window (quarter-end + quarter-start)."""
    idx = pd.DatetimeIndex(index)
    q = idx.to_period("Q")
    # position within quarter (0-based) and quarter length
    pos = pd.Series([p.ordinal - q[0].ordinal for p in idx.to_period("Q")], index=idx)
    # simpler: group by quarter
    df = pd.DataFrame({"date": idx, "q": q.astype(str)}, index=idx)
    df["pos"] = df.groupby("q").cumcount()
    df["qlen"] = df.groupby("q")["pos"].transform("max") + 1
    in_end = df["pos"] >= (df["qlen"] - int(end_days))
    in_start = df["pos"] < int(start_days)
    return (in_end | in_start).astype(bool)


def vol_scale(spy_ret: pd.Series, vol_target: float, window: int = 21) -> pd.Series:
    rv = spy_ret.rolling(window).std() * np.sqrt(252)
    scale = (float(vol_target) / rv.replace(0, np.nan)).clip(0.0, 2.0).fillna(1.0)
    return scale


def build_exposure(toq: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    stress = (toq.astype(float) / float(entry_scale)).clip(0.0, 1.0)
    exposure = (1.0 - stress) * float(vol_target)
    return exposure.clip(0.0, MAX_POS)


def run_one(prices: pd.DataFrame, params: dict) -> dict:
    spy_ret = prices[SPY].astype(float).pct_change()
    toq = toq_window(prices.index, int(params["end_days"]), int(params["start_days"]))
    exposure = build_exposure(toq, float(params["entry_scale"]), float(params["vol_target"]))
    vscale = vol_scale(spy_ret, float(params["vol_target"]))
    raw = exposure * vscale
    signals = pd.DataFrame({SPY: raw.clip(0.0, MAX_POS)}, index=prices.index)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    bt = run_backtest(prices[[SPY]], signals, cfg)
    return {"result": bt, "signals": signals}


def metrics_from(bt_result, mask: pd.Series) -> dict:
    eq_full = pd.Series(bt_result.equity_curve, index=mask.index)
    active = mask.fillna(False)
    eq = eq_full.loc[active]
    n = int(active.sum())
    ret = eq.pct_change().dropna().to_numpy()
    if ret.size < 3:
        return {"n": n, "sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    cummax = eq.cummax().replace(0, np.nan)
    neg = cummax - eq
    mdd = float((neg / cummax).max())
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


def wf_train_sharpe(prices: pd.DataFrame, mask: pd.Series, params: dict, folds: int) -> float:
    idx = prices.index[mask.fillna(False)]
    if len(idx) < 200:
        return -99.0
    splits = np.array_split(idx.to_numpy(), folds)
    sharpes = []
    for part in splits:
        part_idx = pd.DatetimeIndex(part)
        pmask = pd.Series(prices.index.isin(part_idx), index=prices.index)
        try:
            out = run_one(prices, params)["result"]
            m = metrics_from(out, pmask)
            sharpes.append(m["sharpe"])
        except Exception:
            continue
    return float(np.mean(sharpes)) if sharpes else -99.0


def perturbation_test(prices: pd.DataFrame, params: dict, mask: pd.Series) -> float:
    base = metrics_from(run_one(prices, params)["result"], mask)["sharpe"]
    if abs(base) < 1e-9:
        return 0.0
    ratios = []
    for ed in [max(1, int(params["end_days"]) - 1), int(params["end_days"]) + 1]:
        for sd in [max(1, int(params["start_days"]) - 1), int(params["start_days"]) + 1]:
            for es in [
                max(0.5, float(params["entry_scale"]) - 0.25),
                float(params["entry_scale"]) + 0.25,
            ]:
                p2 = dict(params)
                p2["end_days"] = ed
                p2["start_days"] = sd
                p2["entry_scale"] = es
                try:
                    s2m = metrics_from(run_one(prices, p2)["result"], mask)["sharpe"]
                    ratios.append(s2m / base if base else 0.0)
                except Exception:
                    continue
    return float(min(ratios)) if ratios else 0.0


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_exposure: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    idx = prices.index
    sig = np.where(rng.random(len(idx)) < mean_exposure, 1.0, 0.0)
    signals = pd.DataFrame({SPY: sig}, index=idx)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=1.0,
        allow_short=False,
    )
    return metrics_from(run_backtest(prices[[SPY]], signals, cfg), mask)


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    """Pre-registered falsifier: invert TOQ de-risking (more exposure in window)."""
    spy_ret = prices[SPY].astype(float).pct_change()
    vscale = vol_scale(spy_ret, float(params["vol_target"]))
    toq = toq_window(prices.index, int(params["end_days"]), int(params["start_days"]))
    stress = (toq.astype(float) / float(params["entry_scale"])).clip(0.0, 1.0)
    exposure = (float(params["vol_target"]) + stress * float(params["vol_target"])).clip(
        0.0, MAX_POS
    )
    raw = exposure * vscale
    signals = pd.DataFrame({SPY: raw.clip(0.0, MAX_POS)}, index=prices.index)
    cfg = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=False,
    )
    return {"result": run_backtest(prices[[SPY]], signals, cfg), "signals": signals}


def main() -> int:
    t0 = time.time()
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos = val | test

    grid = []
    for ed in END_DAYS:
        for sd in START_DAYS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    grid.append(
                        {"end_days": ed, "start_days": sd, "entry_scale": es, "vol_target": vt}
                    )

    scored = []
    for p in grid:
        wf = wf_train_sharpe(prices, train, p, WF_FOLDS_SELECTION)
        scored.append((wf, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_wf, best = scored[0]

    best_run = run_one(prices, best)
    m_train = metrics_from(run_one(prices, best)["result"], train)
    m_val = metrics_from(run_one(prices, best)["result"], val)
    m_test = metrics_from(run_one(prices, best)["result"], test)
    m_oos = metrics_from(best_run["result"], oos)

    bh = BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=1.0,
        allow_short=False,
    )
    bh_sig = pd.DataFrame({SPY: 1.0}, index=prices.index)
    m_bh = metrics_from(run_backtest(prices[[SPY]], bh_sig, bh), oos)

    exp = float(best["vol_target"])
    randm = random_exposure_matched(prices, oos, exp, SEED)
    inv = metrics_from(inverse_regime(prices, best)["result"], oos)
    pert = perturbation_test(prices, best, oos)

    eq = pd.Series(best_run["result"].equity_curve, index=prices.index)
    oos_ret = eq.pct_change()[oos].dropna()
    bh_ret = (
        pd.Series(run_backtest(prices[[SPY]], bh_sig, bh).equity_curve, index=prices.index)
        .pct_change()[oos]
        .dropna()
    )
    ir = (
        float((oos_ret - bh_ret).mean() / (oos_ret - bh_ret).std(ddof=0) * np.sqrt(252))
        if (oos_ret - bh_ret).std(ddof=0) > 1e-12
        else 0.0
    )
    n_boot = 300
    rng = np.random.default_rng(SEED)
    diffs = oos_ret.values - bh_ret.values[: len(oos_ret.values)]
    boot = []
    for _ in range(n_boot):
        s = rng.choice(diffs, size=len(diffs), replace=True)
        boot.append(np.mean(s) / (np.std(s, ddof=0) + 1e-12) * np.sqrt(252))
    pval = float(np.mean(np.array(boot) <= 0.0))

    roll = oos_ret.rolling(252).apply(
        lambda x: sharpe_ratio(x.values) if len(x) > 50 else np.nan, raw=False
    )
    worst_regime = float(roll.min()) if roll.notna().any() else 0.0

    wf_stab = float(m_oos["sharpe"] / m_train["sharpe"]) if abs(m_train["sharpe"]) > 1e-9 else 0.0

    gates = {
        "sharpe_ge_1": m_oos["sharpe"] >= 1.0,
        "trades_ge_200": m_oos["trades"] >= 200,
        "profit_factor_ge_1_3": m_oos["profit_factor"] >= 1.3,
        "max_dd_le_15pct": m_oos["max_drawdown"] <= 0.15,
        "wf_stability_ge_0_7": wf_stab >= 0.7,
        "worst_regime_ge_0_3": worst_regime >= 0.3,
        "benchmark_p_le_0_05_ir_ge_0": (pval <= 0.05 and ir >= 0.0),
        "perturbation_ge_0_5": pert >= 0.5,
    }
    verdict = "ACCEPT" if all(gates.values()) else "REJECT"
    passed = int(sum(1 for v in gates.values() if v))

    out = {
        "nf_id": "NF-20261108-03",
        "h_id": "H142",
        "experiment": EXPERIMENT_DESC,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - t0, 3),
        "data": {
            "rows": int(len(prices)),
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "train_n": int(train.sum()),
            "val_n": int(val.sum()),
            "test_n": int(test.sum()),
        },
        "selection": {
            "best_params": best,
            "best_train_wf_mean_sharpe": best_wf,
            "grid_size": len(grid),
            "top5": [{"wf": w, "params": p} for w, p in scored[:5]],
        },
        "metrics": {"train": m_train, "val": m_val, "test": m_test, "oos_val_test": m_oos},
        "ablations": {
            "buy_hold_spy_oos": m_bh,
            "random_exposure_matched_oos": randm,
            "inverse_regime_oos": inv,
        },
        "benchmark": {"ir_vs_buy_hold_oos": ir, "bootstrap_p_one_sided_oos": pval},
        "perturbation_min_ratio": pert,
        "wf_stability_ratio_oos_to_train": wf_stab,
        "worst_regime_rolling252_sharpe_oos": worst_regime,
        "gates": gates,
        "verdict": verdict,
        "passed_gates": passed,
        "failed_gates": [k for k, v in gates.items() if not v],
        "notes": "Repo-new turn-of-quarter window-dressing/rebalancing calendar observable; honest adjacency to H91 turn-of-month (REJECT 3/9, different institutional cycle). Free PIT yfinance data + deterministic calendar.",
    }

    expdir = ROOT / ".experiments" / "nf_runs" / "nf_20261108_03_spy_toq_window"
    expdir.mkdir(parents=True, exist_ok=True)
    (expdir / "summary.json").write_text(json.dumps(out, indent=2))
    (expdir / "data_meta.json").write_text(
        json.dumps(
            {
                "universe": UNIVERSE,
                "rows": int(len(prices)),
                "start": str(prices.index.min().date()),
                "end": str(prices.index.max().date()),
                "source": "yfinance auto_adjust + deterministic TOQ calendar",
            },
            indent=2,
        )
    )
    pd.DataFrame([{"wf": w, **p} for w, p in scored]).to_csv(expdir / "grid.csv", index=False)
    print(json.dumps({"verdict": verdict, "passed_gates": f"{passed}/8", "oos": m_oos}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
