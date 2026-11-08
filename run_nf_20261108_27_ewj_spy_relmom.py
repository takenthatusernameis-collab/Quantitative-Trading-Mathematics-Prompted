"""NF-20261108-27 / H157 (Cycle 71): SPY timing from EWJ-vs-SPY
relative-momentum regime (Japan/developed-market regional leadership
transmission).

Repo-relative novelty (honest). No executed NF/H in this repo uses *EWJ-vs-SPY
relative-momentum z-score* (ret(EWJ,w) - ret(SPY,w)) as a SPY timing observable.
EWJ appears in the H2 universe specification and in experiment price artifacts,
but never as an executed SPY-timing signal. NF-20261108-22 (EFA-EEM DM/EM
relmom) and NF-20261108-27 were both deferred; NF-27 is selected/executed here
as H157 with NF root verified against executed H-IDs/artifacts.

Honest adjacency. Same z-score / relative-momentum de-risking construction class
as H144 (EEM-SPY relmom, REJECT 3/8, inverse outperformed pre-registered
mapping), H145 (GLD-SPY relmom, REJECT 4/8), and H152 (SLV-GLD relmom→SPY,
REJECT 4/8). Different signal pair and mechanism: EWJ (Japan / developed-market
equity, USD-denominated ETF) vs SPY tests *regional developed-market leadership /
funding-spillover transmission*, not EM leadership (H144), safe-haven/precious
metals (H145/H152), or commodity channels. Distinct from H85 (cross-asset
lead-lag form, REJECT). H139 used IWM-vs-SPY realized-vol divergence (second
moment), not relative momentum. FX/rates/vol/calendar families are different
channels. Novelty is repo-relative on the EWJ-SPY relative-momentum leadership
pair; it is not a wholly new statistical method.

Mechanism (regional leadership / developed-market transmission). EWJ
underperformance vs SPY may proxy Japan/developed ex-US weakness, yen/funding
stress spillovers, or global risk-off leadership rotation that transmits to US
equity risk premia. The pre-registered rule continuously reduces vol-targeted
long SPY exposure as the EWJ-vs-SPY relative-momentum z-score becomes
abnormally negative (EWJ leadership weak). When EWJ keeps up with/outperforms
SPY (z normal/positive), exposure is full. Causal chain: EWJ/SPY closes through
t -> trailing relative momentum and z-score at close t -> exposure weight
applied to return t+1 (engine signals.shift(1)), no look-ahead.

Observable (past-only, PIT, free yfinance): EWJ, SPY daily auto-adjust Close.
`rel_t = cumret(EWJ, mom_window) - cumret(SPY, mom_window)`; `z_t = (rel_t -
rolling_mean(rel, z_window)) / rolling_std(rel, z_window)`.

Null (H0). Trailing EWJ-vs-SPY relative momentum (z-score) contains no
incremental SPY timing information; OOS gates fail vs buy-hold /
random-exposure.

Pre-registration (Cycle 71, decision-ready before validation outcomes).
NF-ID NF-20261108-27. Hypothesis H157. Universe SPY (traded) + EWJ (signal),
yfinance daily auto-adjust Close (free, PIT). Sample 2010-01-04->2025-01-03
(train 2516 / val 505 / test 755, aligned). Signal: z-score of trailing
relative momentum over mom_window, standardized over z_window (past-only);
continuous stress on negative z = ((-z).clip(0)/entry_scale).clip(0,1);
exposure (1-stress)*vol_target*vscale; 1-bar delay via engine signals.shift(1);
Equity CostModel defaults (1bp commission + 1bp spread); long-only, max
exposure scaled to MAX_POS=0.5. Bounded grid: mom_window {21,63} x
z_window {126,252} x entry_scale {1.0,2.0} x vol_target {0.10,0.15}
(16 combos); train-only 4-fold WF selection by mean train Sharpe; Test
protected. No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk when
EWJ outperforms SPY / positive z — pre-registered falsifier).

Falsifiers: random-exposure comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse.
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
    "NF-20261108-27/H157: SPY timing from EWJ-vs-SPY relative-momentum regime "
    "(Japan/developed-market regional leadership transmission). z-score of "
    "trailing ret(EWJ,w)-ret(SPY,w); de-risk vol-targeted long SPY when EWJ "
    "leadership abnormally weak (negative z). 1-bar delay. Train-only WF "
    "selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
EWJ = "EWJ"
UNIVERSE = [SPY, EWJ]
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 157
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

MOM_WINDOWS = [21, 63]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"][UNIVERSE]
    else:
        close = raw[UNIVERSE]
    df = close.dropna().sort_index()
    df = df[(df > 0).all(axis=1)]
    if df.empty:
        raise RuntimeError("empty price data")
    return df


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)),
        index=index,
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def relmom_z(prices: pd.DataFrame, mom_window: int, z_window: int) -> pd.Series:
    rel = prices[EWJ].pct_change(int(mom_window)) - prices[SPY].pct_change(int(mom_window))
    mp = max(30, int(z_window) // 2)
    mu = rel.rolling(int(z_window), min_periods=mp).mean()
    sd = rel.rolling(int(z_window), min_periods=mp).std()
    return (rel - mu) / sd.replace(0.0, np.nan)


def _vol_scale(prices: pd.DataFrame, vol_target: float, lookback: int = 21) -> pd.Series:
    rv = prices[SPY].pct_change().rolling(lookback, min_periods=10).std() * np.sqrt(252)
    scale = (float(vol_target) / rv.replace(0.0, np.nan)).clip(0.0, 3.0)
    return scale.reindex(prices.index).fillna(0.0)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = relmom_z(prices, params["mom_window"], params["z_window"])
    # stress on negative z (EWJ leadership weak vs SPY)
    stress = ((-z).clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame({SPY: expo, EWJ: 0.0}, index=prices.index)
    sig.attrs["z"] = z
    return sig


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        max_position_size=MAX_POS,
        max_leverage=1.0,
        asset_class=AssetClass.EQUITY,
        allow_short=False,
    )


def run_one(prices: pd.DataFrame, params: dict):
    sig = make_signals(prices, params)
    res = run_backtest(prices, sig, _cfg())
    return {"result": res, "signals": sig, "z": sig.attrs["z"]}


def _metrics_from_result(res, mask: pd.Series) -> dict:
    eq = res.equity_curve.loc[res.equity_curve.index.intersection(mask.index[mask])]
    if len(eq) < 30:
        return {
            "n": int(len(eq)),
            "sharpe": float("nan"),
            "profit_factor": float("nan"),
            "max_drawdown": float("nan"),
            "trades": 0,
        }
    ret = eq.pct_change().dropna()
    neg = ret[ret < 0].abs().sum()
    pf = float(ret[ret > 0].sum() / neg) if neg > 1e-12 else float("inf")
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak.replace(0.0, np.nan)).min())
    trades_df = res.trades
    if (
        trades_df is None
        or (hasattr(trades_df, "empty") and trades_df.empty)
        or len(trades_df) == 0
    ):
        ntr = 0
    else:
        td = trades_df
        if "date" in td.columns:
            tmask = pd.to_datetime(td["date"]).isin(eq.index)
            ntr = int(tmask.sum())
        else:
            ntr = int(len(td))
    return {
        "n": int(len(ret)),
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": ntr,
    }


def wf_train_mean_sharpe(prices: pd.DataFrame, params: dict, train_mask: pd.Series) -> float:
    idx = prices.index[train_mask]
    if len(idx) < 400:
        return float("nan")
    splits = np.array_split(np.arange(len(idx)), WF_FOLDS_SELECTION)
    sharpes = []
    for i in range(1, len(splits)):
        fold_idx = idx[splits[i]]
        fmask = pd.Series(prices.index.isin(fold_idx), index=prices.index)
        m = _metrics_from_result(run_one(prices, params)["result"], fmask)
        if np.isfinite(m["sharpe"]):
            sharpes.append(m["sharpe"])
    return float(np.mean(sharpes)) if sharpes else float("nan")


def _worst_regime_sharpe(eq: pd.Series, window: int = 252) -> float:
    ret = eq.pct_change().dropna()
    if len(ret) < window:
        return float("nan")
    roll = ret.rolling(window).apply(lambda x: sharpe_ratio(pd.Series(x)), raw=False)
    return float(roll.min()) if roll.notna().any() else float("nan")


def _perturbation_ratio(prices: pd.DataFrame, params: dict, base_sharpe: float) -> float:
    if not np.isfinite(base_sharpe) or abs(base_sharpe) < 1e-9:
        return 0.0
    candidates = [
        {**params, "entry_scale": float(params["entry_scale"]) * 0.8},
        {**params, "entry_scale": float(params["entry_scale"]) * 1.2},
        {**params, "vol_target": max(0.05, float(params["vol_target"]) - 0.02)},
        {**params, "vol_target": min(0.30, float(params["vol_target"]) + 0.02)},
    ]
    train, val, test = _splits(prices.index)
    oos_m = val | test
    ratios = []
    for p in candidates:
        m = _metrics_from_result(run_one(prices, p)["result"], oos_m)
        if np.isfinite(m["sharpe"]):
            ratios.append(float(m["sharpe"]) / float(base_sharpe))
    return float(min(ratios)) if ratios else 0.0


def benchmark_buy_hold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    eq = (1.0 + prices[SPY].pct_change().fillna(0.0)).cumprod() * INITIAL_CAPITAL
    eq = eq.loc[eq.index.intersection(mask.index[mask])]
    if len(eq) < 30:
        return {
            "n": 0,
            "sharpe": float("nan"),
            "profit_factor": float("nan"),
            "max_drawdown": float("nan"),
            "trades": 1,
        }
    ret = eq.pct_change().dropna()
    neg = ret[ret < 0].abs().sum()
    pf = float(ret[ret > 0].sum() / neg) if neg > 1e-12 else float("inf")
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak.replace(0.0, np.nan)).min())
    return {
        "n": int(len(ret)),
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": 1,
    }


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_expo: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    expo = (
        pd.Series(
            rng.binomial(1, float(np.clip(mean_expo / MAX_POS, 0.01, 0.99)), len(prices)),
            index=prices.index,
        )
        * mean_expo
    )
    sig = pd.DataFrame({SPY: expo.clip(0.0, MAX_POS), EWJ: 0.0}, index=prices.index)
    return _metrics_from_result(run_backtest(prices, sig, _cfg()), mask)


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    z = relmom_z(prices, params["mom_window"], params["z_window"])
    # falsifier: stress on positive z (de-risk when EWJ outperforms SPY)
    stress = (z.clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame({SPY: expo, EWJ: 0.0}, index=prices.index)
    train, val, test = _splits(prices.index)
    return _metrics_from_result(run_backtest(prices, sig, _cfg()), val | test)


def _bootstrap_p(base_ret: pd.Series, bh_ret: pd.Series, n: int = 1000, seed: int = SEED):
    aligned = pd.concat([base_ret, bh_ret], axis=1).dropna()
    if len(aligned) < 50:
        return 1.0, float("nan")
    diff = (aligned.iloc[:, 0] - aligned.iloc[:, 1]).values
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n):
        s = rng.choice(diff, size=len(diff), replace=True)
        means.append(float(np.mean(s)))
    p = float(np.mean(np.array(means) <= 0.0))
    ir = float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-12) * np.sqrt(252))
    return p, ir


def main() -> None:
    t0 = time.time()
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos_m = val | test

    rows = []
    for mom_window in MOM_WINDOWS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    params = {
                        "mom_window": mom_window,
                        "z_window": z_window,
                        "entry_scale": entry_scale,
                        "vol_target": vol_target,
                    }
                    wf = wf_train_mean_sharpe(prices, params, train)
                    rows.append({**params, "wf_train_mean_sharpe": wf})
    grid_df = pd.DataFrame(rows).sort_values("wf_train_mean_sharpe", ascending=False)
    best = grid_df.iloc[0].dropna().to_dict()
    best = {
        k: (int(v) if k in {"mom_window", "z_window"} else float(v))
        for k, v in best.items()
        if k != "wf_train_mean_sharpe"
    }

    out = run_one(prices, best)
    oos_met = _metrics_from_result(out["result"], oos_m)
    train_met = _metrics_from_result(out["result"], train)
    bh = benchmark_buy_hold(prices, oos_m)

    eq_oos = out["result"].equity_curve.loc[
        out["result"].equity_curve.index.intersection(oos_m.index[oos_m])
    ]
    bh_eq = (1.0 + prices[SPY].pct_change().fillna(0.0)).cumprod() * INITIAL_CAPITAL
    bh_eq = bh_eq.loc[bh_eq.index.intersection(eq_oos.index)]
    p_bench, ir = _bootstrap_p(eq_oos.pct_change().dropna(), bh_eq.pct_change().dropna())

    worst = _worst_regime_sharpe(eq_oos)
    wf_stab = (
        float(oos_met["sharpe"] / train_met["sharpe"])
        if np.isfinite(train_met.get("sharpe")) and train_met["sharpe"] not in (0.0, np.nan)
        else 0.0
    )
    pert = _perturbation_ratio(prices, best, oos_met["sharpe"])
    mean_expo = float(out["signals"][SPY].loc[oos_m].mean())

    gates = {
        "sharpe_ge_1": bool(oos_met["sharpe"] >= 1.0),
        "trades_ge_200": bool(oos_met["trades"] >= 200),
        "pf_ge_1_3": bool(
            np.isfinite(oos_met["profit_factor"]) and oos_met["profit_factor"] >= 1.3
        ),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_met["max_drawdown"]) and oos_met["max_drawdown"] >= -0.15
        ),
        "wf_stability_ge_0_7": bool(np.isfinite(wf_stab) and wf_stab >= 0.7),
        "worst_regime_ge_0_3": bool(np.isfinite(worst) and worst >= 0.3),
        "benchmark_p_le_0_05_ir_ge_0": bool(p_bench <= 0.05 and ir >= 0.0),
        "perturbation_ge_0_5": bool(pert >= 0.5),
    }
    passed = int(sum(gates.values()))
    verdict = "REJECT" if passed < 8 else "PASS_CANDIDATE"

    summary = {
        "nf_id_exec": "NF-20261108-27",
        "hypothesis": "H157",
        "verdict": verdict,
        "gates_passed": f"{passed}/{len(gates)}",
        "gates": gates,
        "selected_params": best,
        "selection_wf_train_mean_sharpe": float(grid_df.iloc[0]["wf_train_mean_sharpe"]),
        "oos_val_test": oos_met,
        "train": train_met,
        "wf_stability_ratio": wf_stab,
        "worst_regime_rolling252_sharpe": worst,
        "benchmark_buy_hold_spy_oos": bh,
        "benchmark_p": p_bench,
        "information_ratio_vs_bh": ir,
        "perturbation_min_ratio": pert,
        "ablations": {
            "buy_hold_spy": bh,
            "random_exposure_matched": random_exposure_matched(prices, oos_m, mean_expo, SEED),
            "inverse_regime": inverse_regime(prices, best),
        },
        "timing_seconds": round(time.time() - t0, 2),
        "data": {
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "rows": int(len(prices)),
        },
        "description": EXPERIMENT_DESC,
        "notes": [
            "Repo-new executed EWJ-vs-SPY relative-momentum (regional developed-market/Japan leadership) SPY-timing observable; EWJ present in H2 universe spec/artifacts but never executed as timing signal.",
            "Honest adjacency: relmom/z-score construction class adjacent to H144 EEM-SPY (REJECT 3/8, inverse outperformed), H145 GLD-SPY (REJECT 4/8), H152 SLV-GLD relmom→SPY (REJECT 4/8) — different signal pair/mechanism (regional leadership/funding spillover vs EM/safe-haven/precious metals); distinct from H85 lead-lag form.",
            "Pre-registered: stress on negative z (EWJ leadership weak); inverse falsifier stresses positive z (EWJ outperforms).",
            "src/qtr unchanged; no gate weakening; no published/certified artifact modified.",
        ],
    }

    outdir = ROOT / ".experiments" / "nf_runs" / "nf_20261108_27_ewj_spy_relmom"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid_df.to_csv(outdir / "grid.csv", index=False)
    meta = {
        "universe": UNIVERSE,
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "rows": int(len(prices)),
        "train": int(train.sum()),
        "val": int(val.sum()),
        "test": int(test.sum()),
        "signal_mapping": "stress on negative z of ret(EWJ,w)-ret(SPY,w) (EWJ leadership weak)",
    }
    (outdir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": f"{passed}/{len(gates)}", "oos": oos_met, "best": best},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
