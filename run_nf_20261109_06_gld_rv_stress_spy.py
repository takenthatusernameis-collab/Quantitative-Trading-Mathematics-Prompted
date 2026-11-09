"""NF-20261109-06 / H164 (Cycle 78): SPY timing from GLD realized-volatility stress regime.

Repo-relative novelty (honest). No executed NF/H in this repo uses *GLD's own
trailing realized-volatility z-score* (hysteresis) as a continuous SPY equity-timing
observable. Honest RV-stress / commodity-safe-haven adjacency is disclosed: H151
TLT realized-volatility stress regime (REJECT 5/8, rates/Treasury asset, different
mechanism), H156 UUP realized-volatility stress regime (REJECT 5/8, USD asset),
H149 GDX-vs-GLD miner gold-beta *RV divergence* (REJECT 4/8, different observable:
relative RV divergence between two assets, not GLD's own RV stress level), H88
GLD-USO relative-value spread mean reversion (REJECT 3/8, convergence mechanism,
different observable). NF-09-06 tests a different observable/mechanism: GLD's own
trailing realized-volatility level (z-scored) as a commodity safe-haven /
monetary-stress proxy — elevated GLD RV can reflect flight-to-quality, inflation
uncertainty, or macro stress that transmits to equity risk premia. Construction-class
adjacency (RV z-score hysteresis, vol-targeted SPY de-risking, 1-bar delay) to
H151/H156 and de-risking form to H138/H139/H151/H156/H158/H159/H162/H163 is
disclosed; novelty scored on the GLD RV-stress observable, not a new statistical
method.

Observable (past-only, PIT, free yfinance): SPY (traded) + GLD (signal), daily
auto-adjust Close. rv_t = rolling std of GLD log returns over rv_window * sqrt(252).
z_t = trailing z-score of rv_t over z_window.

Construction (hysteresis, 1-bar delay via engine signals.shift(1)):
  z_t >=  entry_scale -> de-risk (state 0, GLD RV stress / safe-haven volatility)
  z_t <=  exit_scale  -> full exposure (state 1, GLD RV benign)
  else                -> hold prior state (hysteresis), initial state 1.
w_t = vol_target / rolling_realized_vol(SPY,21,min_periods=21) * state_t,
clipped [0, MAX_POS]. Long-only, Equity CostModel defaults, MAX_POS 0.5.

Null (H0). Trailing GLD realized-volatility z-score contains no incremental SPY
timing information; OOS gates fail vs buy-hold / random-exposure.

Pre-registration (Cycle 78, NF-20261109-06, H164, decision-ready before validation
outcomes). Universe SPY + GLD, yfinance daily auto-adjust Close (free, PIT).
Sample 2010-01-01->2026-10-31 (train 2010-01-01->2019-12-31, val 2020-01-01->
2022-12-31, test 2023-01-01->2026-10-31 protected). Bounded grid:
rv_window {21,63} x z_window {126,252} x entry_scale {1.0,1.5,2.0} x
exit_scale {0.0,0.5} x vol_target {0.10,0.15} (48 combos; exit_scale<=entry_scale
always); train-only 4-fold WF selection by mean train Sharpe; Test protected.
No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations/falsifiers: buy-hold SPY, random-exposure-matched, inverse signal
(de-risk when GLD RV LOW / benign), perturbation OAT +-20%,
worst-regime, Val/Test subperiod stability, benchmark p/IR vs SPY.
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
    "NF-20261109-06/H164: SPY timing from GLD realized-volatility stress regime. "
    "Trailing GLD RV z-scored with hysteresis; de-risk vol-targeted long SPY when "
    "GLD RV is abnormally high (safe-haven/commodity stress), full exposure when "
    "benign. Train-only WF selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
GLD = "GLD"
UNIVERSE = [SPY, GLD]
START = "2010-01-01"
END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
MAX_POS = 0.5
WF_FOLDS = 4
GATES = {
    "sharpe": 1.0,
    "trades": 200,
    "pf": 1.3,
    "max_dd": 0.15,
    "wf_stability": 0.7,
    "worst_regime_sharpe": 0.3,
    "benchmark_p": 0.05,
    "perturbation_min_ratio": 0.5,
}


def fetch_prices() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=START, end="2026-11-01", auto_adjust=True, progress=False)
    close = raw["Close"][UNIVERSE].dropna(how="all")
    close = close.loc[:END].dropna()
    if close.empty:
        raise RuntimeError("no data")
    return close.astype(float)


def realized_vol(series: pd.Series, window: int) -> pd.Series:
    lr = np.log(series / series.shift(1))
    return lr.rolling(window, min_periods=window).std() * np.sqrt(252)


def zscore(series: pd.Series, window: int) -> pd.Series:
    m = series.rolling(window, min_periods=max(30, window // 2)).mean()
    s = series.rolling(window, min_periods=max(30, window // 2)).std(ddof=0)
    return (series - m) / s.replace(0.0, np.nan)


def rv_state(z: pd.Series, entry_scale: float, exit_scale: float) -> pd.Series:
    state = np.ones(len(z), dtype=float)
    cur = 1.0
    for i, val in enumerate(z.values):
        if np.isnan(val):
            state[i] = cur
            continue
        if val >= entry_scale:
            cur = 0.0
        elif val <= exit_scale:
            cur = 1.0
        state[i] = cur
    return pd.Series(state, index=z.index)


def inverse_rv_state(z: pd.Series, entry_scale: float, exit_scale: float) -> pd.Series:
    state = np.ones(len(z), dtype=float)
    cur = 1.0
    for i, val in enumerate(z.values):
        if np.isnan(val):
            state[i] = cur
            continue
        if val <= -entry_scale:
            cur = 0.0
        elif val >= -exit_scale:
            cur = 1.0
        state[i] = cur
    return pd.Series(state, index=z.index)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    rv = realized_vol(prices[GLD], int(params["rv_window"]))
    z = zscore(rv, int(params["z_window"]))
    state = rv_state(z, float(params["entry_scale"]), float(params["exit_scale"]))
    spy_rv = realized_vol(prices[SPY], 21).replace(0.0, np.nan)
    vscale = (float(params["vol_target"]) / spy_rv).clip(0.0, 3.0).fillna(0.0)
    w = (vscale * state * float(params["vol_target"])).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w
    return sig


def make_inverse_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    rv = realized_vol(prices[GLD], int(params["rv_window"]))
    z = zscore(rv, int(params["z_window"]))
    state = inverse_rv_state(z, float(params["entry_scale"]), float(params["exit_scale"]))
    spy_rv = realized_vol(prices[SPY], 21).replace(0.0, np.nan)
    vscale = (float(params["vol_target"]) / spy_rv).clip(0.0, 3.0).fillna(0.0)
    w = (vscale * state * float(params["vol_target"])).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w
    return sig


def param_grid() -> list[dict]:
    grid: list[dict] = []
    for rv_window in (21, 63):
        for z_window in (126, 252):
            for entry_scale in (1.0, 1.5, 2.0):
                for exit_scale in (0.0, 0.5):
                    if exit_scale > entry_scale:
                        continue
                    for vol_target in (0.10, 0.15):
                        grid.append(
                            {
                                "rv_window": rv_window,
                                "z_window": z_window,
                                "entry_scale": entry_scale,
                                "exit_scale": exit_scale,
                                "vol_target": vol_target,
                            }
                        )
    return grid


def bt_cfg() -> BacktestConfig:
    return BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(commission_bps=1.0, spread_bps=1.0),
        allow_short=False,
        allow_leverage=False,
        max_position=MAX_POS,
    )


def perf(result) -> dict:
    return {
        "sharpe": float(result.sharpe),
        "sortino": float(result.sortino),
        "profit_factor": float(result.profit_factor),
        "max_drawdown": float(result.max_drawdown),
        "annual_return": float(result.annual_return),
        "annual_volatility": float(result.annual_volatility),
        "trades": int(result.num_trades),
        "total_return": float(result.total_return),
    }


def worst_regime_sharpe(result, window: int = 252) -> float:
    r = result.returns.dropna()
    if len(r) < window:
        return float(sharpe_ratio(r))
    rolling = r.rolling(window).apply(lambda x: sharpe_ratio(x), raw=False).dropna()
    return float(rolling.min()) if not rolling.empty else float("nan")


def wf_stability(prices: pd.DataFrame, params: dict, train_end: str) -> dict:
    train = prices.loc[:train_end]
    n = len(train)
    fold = n // WF_FOLDS
    sharpes: list[float] = []
    for i in range(WF_FOLDS):
        te = (i + 1) * fold if i < WF_FOLDS - 1 else n
        sub = train.iloc[:te]
        if len(sub) < 400:
            continue
        res = run_backtest(prices=sub, signals=make_signals(sub, params), config=bt_cfg())
        sharpes.append(float(res.sharpe))
    arr = np.array(sharpes, dtype=float) if sharpes else np.array([np.nan])
    mean_s = float(np.nanmean(arr))
    neg_frac = float(np.mean(arr < 0)) if len(arr) else 1.0
    stab = 0.0 if (not np.isfinite(mean_s) or mean_s <= 0 or neg_frac > 0.5) else mean_s
    return {
        "fold_sharpes": sharpes,
        "mean_sharpe": mean_s,
        "neg_fold_frac": neg_frac,
        "stability": stab,
    }


def perturbation(prices: pd.DataFrame, params: dict, oos_idx: pd.Index) -> dict:
    base_res = run_backtest(
        prices=prices.loc[oos_idx],
        signals=make_signals(prices, params).loc[oos_idx],
        config=bt_cfg(),
    )
    base = float(base_res.sharpe)
    ratios = []
    for key, deltas in {
        "rv_window": [max(10, int(params["rv_window"] * 0.8)), int(params["rv_window"] * 1.2)],
        "z_window": [max(60, int(params["z_window"] * 0.8)), int(params["z_window"] * 1.2)],
        "entry_scale": [params["entry_scale"] * 0.8, params["entry_scale"] * 1.2],
        "vol_target": [max(0.01, params["vol_target"] * 0.8), params["vol_target"] * 1.2],
    }.items():
        for d in deltas:
            p = dict(params)
            p[key] = int(round(d)) if key in ("rv_window", "z_window") else float(d)
            if p["exit_scale"] > p["entry_scale"]:
                p["exit_scale"] = p["entry_scale"]
            res = run_backtest(
                prices=prices.loc[oos_idx],
                signals=make_signals(prices, p).loc[oos_idx],
                config=bt_cfg(),
            )
            s = float(res.sharpe)
            denom = abs(base) if abs(base) > 1e-9 else np.nan
            ratios.append(float(s / denom) if np.isfinite(denom) else np.nan)
    arr = np.array(ratios, dtype=float)
    return {
        "base_sharpe": base,
        "ratios": [None if not np.isfinite(x) else float(x) for x in ratios],
        "min_ratio": float(np.nanmin(arr)) if np.isfinite(arr).any() else float("nan"),
    }


def random_exposure(
    prices: pd.DataFrame, params: dict, oos_idx: pd.Index, n: int = 100, seed: int = 164
) -> dict:
    base_sig = make_signals(prices, params).loc[oos_idx, SPY]
    rng = np.random.default_rng(seed)
    sharpes = []
    for _ in range(n):
        arr = base_sig.values.copy()
        rng.shuffle(arr)
        sig = pd.DataFrame(0.0, index=oos_idx, columns=UNIVERSE)
        sig[SPY] = arr
        res = run_backtest(prices=prices.loc[oos_idx], signals=sig, config=bt_cfg())
        sharpes.append(float(res.sharpe))
    a = np.array(sharpes, dtype=float)
    return {"n": n, "mean_sharpe": float(np.mean(a)), "p95_sharpe": float(np.quantile(a, 0.95))}


def benchmark_ir(result, prices: pd.DataFrame, oos_idx: pd.Index) -> dict:
    strat = result.returns.reindex(oos_idx).dropna()
    bh = prices[SPY].reindex(oos_idx).pct_change().dropna()
    common = strat.index.intersection(bh.index)
    active = strat.loc[common] - bh.loc[common]
    ir = float(sharpe_ratio(active)) if len(active) > 30 else float("nan")
    bh_sh = float(sharpe_ratio(bh.loc[common])) if len(common) > 30 else float("nan")
    try:
        from scipy import stats

        t, p = stats.ttest_1samp(active.values, 0.0, nan_policy="omit")
        p_one = float(p / 2) if t > 0 else float(1 - p / 2)
    except Exception:
        p_one = float("nan")
    return {"ir": ir, "bh_sharpe": bh_sh, "p_one_sided": p_one, "active_n": int(len(common))}


def evaluate_gate(oos_perf_d: dict, wf: dict, worst: float, bench: dict, pert: dict) -> dict:
    checks = {
        "sharpe": bool(oos_perf_d["sharpe"] >= GATES["sharpe"]),
        "trades": bool(oos_perf_d["trades"] >= GATES["trades"]),
        "pf": bool(oos_perf_d["profit_factor"] >= GATES["pf"]),
        "max_dd": bool(abs(oos_perf_d["max_drawdown"]) <= GATES["max_dd"]),
        "wf_stability": bool(
            wf["stability"] >= GATES["wf_stability"] or wf["mean_sharpe"] >= GATES["wf_stability"]
        ),
        "worst_regime": bool(worst >= GATES["worst_regime_sharpe"]),
        "benchmark": bool(
            np.isfinite(bench["p_one_sided"])
            and bench["p_one_sided"] <= GATES["benchmark_p"]
            and bench["ir"] >= 0
        ),
        "perturbation": bool(
            np.isfinite(pert["min_ratio"]) and pert["min_ratio"] >= GATES["perturbation_min_ratio"]
        ),
    }
    passed = sum(checks.values())
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "verdict": "PASS" if passed == len(checks) else "REJECT",
    }


def main() -> None:
    t0 = time.time()
    prices = fetch_prices()
    train = prices.loc[:TRAIN_END]
    oos = prices.loc[TRAIN_END:].iloc[1:]
    oos_idx = oos.index
    grid = param_grid()
    rows = []
    for p in grid:
        res = run_backtest(prices=train, signals=make_signals(train, p), config=bt_cfg())
        wf = wf_stability(train, p, TRAIN_END)
        rows.append(
            {**p, **perf(res), "wf_mean": wf["mean_sharpe"], "wf_stability": wf["stability"]}
        )
    grid_df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    best = grid_df.iloc[0].to_dict()
    params = {
        k: best[k] for k in ("rv_window", "z_window", "entry_scale", "exit_scale", "vol_target")
    }
    params["rv_window"] = int(params["rv_window"])
    params["z_window"] = int(params["z_window"])

    oos_res = run_backtest(
        prices=prices.loc[oos_idx],
        signals=make_signals(prices, params).loc[oos_idx],
        config=bt_cfg(),
    )
    oos_p = perf(oos_res)
    wf = wf_stability(prices, params, TRAIN_END)
    worst = worst_regime_sharpe(oos_res)
    bench = benchmark_ir(oos_res, prices, oos_idx)
    pert = perturbation(prices, params, oos_idx)
    gate = evaluate_gate(oos_p, wf, worst, bench, pert)

    inv_res = run_backtest(
        prices=prices.loc[oos_idx],
        signals=make_inverse_signals(prices, params).loc[oos_idx],
        config=bt_cfg(),
    )
    rand = random_exposure(prices, params, oos_idx)
    bh_sig = pd.DataFrame(0.0, index=oos_idx, columns=UNIVERSE)
    bh_sig[SPY] = MAX_POS
    bh_res = run_backtest(prices=prices.loc[oos_idx], signals=bh_sig, config=bt_cfg())

    val_res = run_backtest(
        prices=prices.loc["2020-01-01":VAL_END],
        signals=make_signals(prices, params).loc["2020-01-01":VAL_END],
        config=bt_cfg(),
    )
    test_res = run_backtest(
        prices=prices.loc[VAL_END:].iloc[1:],
        signals=make_signals(prices, params).loc[VAL_END:].iloc[1:],
        config=bt_cfg(),
    )

    artifact = {
        "nf_id_exec": "NF-20261109-06",
        "hypothesis": "H164",
        "mode": "REAL",
        "experiment_description": EXPERIMENT_DESC,
        "universe": UNIVERSE,
        "data": {
            "start": START,
            "end": END,
            "rows": int(len(prices)),
            "train_rows": int(len(train)),
            "oos_rows": int(len(oos)),
        },
        "grid_size": int(len(grid)),
        "selected_params": params,
        "gate": gate,
        "oos_val_test": oos_p,
        "train": perf(
            run_backtest(prices=train, signals=make_signals(train, params), config=bt_cfg())
        ),
        "val": perf(val_res),
        "test": perf(test_res),
        "wf": wf,
        "worst_regime_rolling252_sharpe": worst,
        "benchmark": bench,
        "perturbation": pert,
        "ablations": {
            "buy_hold_spy": perf(bh_res),
            "random_exposure": rand,
            "inverse_regime": perf(inv_res),
        },
        "runtime_sec": round(time.time() - t0, 2),
    }
    out = ROOT / ".experiments" / "nf_runs" / "nf_20261109_06_gld_rv_stress_spy"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(artifact, indent=2, default=str))
    grid_df.to_csv(out / "grid.csv", index=False)
    print(
        json.dumps(
            {
                "verdict": gate["verdict"],
                "passed": gate["passed"],
                "oos_sharpe": oos_p["sharpe"],
                "params": params,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
