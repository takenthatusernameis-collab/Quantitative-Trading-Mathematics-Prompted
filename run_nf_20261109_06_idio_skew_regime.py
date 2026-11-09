"""NF-20261109-06 / H164 (Cycle 78): SPY timing from cross-sectional
idiosyncratic-skewness (lottery-demand) regime.

Repo-relative novelty (honest). No executed NF/H in this repo times SPY from
the *cross-sectional mean of idiosyncratic skewness* of liquid ETF residuals
vs SPY. Honest adjacency disclosed: H112 MAX/lottery (same 15-asset universe,
max-daily-return *level* observable, REJECT 2/8) and H128 realized skewness
(SPY's own *time-series* realized third moment, REJECT 2/8) are higher-moment
families but different observables/constructions; H93 is idiosyncratic
*volatility* (second moment, REJECT 2/9). H164 is repo-new on the
cross-sectional idiosyncratic-skewness observable, not a wholly new statistical
method.

Mechanism (investor attention / lottery-demand transmission). Idiosyncratic
skewness (third standardized moment of residuals from a rolling asset-on-SPY
regression) proxies lottery-demand / crash-risk sentiment in the cross-section.
Abnormally *high* cross-sectional mean idiosyncratic skewness signals
lottery overheating and elevated crash risk; de-risk vol-targeted long SPY.
Abnormally low skewness supports full exposure. Trailing z-score of the
cross-sectional mean provides a PIT regime signal.

Observable (past-only, PIT, free yfinance): SPY (traded) + 15 liquid ETFs
(QQQ,IWM,EFA,EEM,XLE,XLF,XLV,XLI,XLB,XLP,XLU,XLY,XLK,GLD,TLT) daily
auto-adjust Close. beta_i,t = rolling Cov(ret_i, ret_SPY)/rolling Var(ret_SPY)
over lookback (past-only); res_i,t = ret_i,t - beta_i,t*ret_SPY,t;
skew_i,t = rolling skew of res_i over lookback; S_t = cross-sectional mean of
skew_i,t; z_t = trailing z-score of S_t over z_window.

Construction (hysteresis, 1-bar delay via engine signals.shift(1)):
  z_t >= entry_z   -> de-risk (state 0, lottery overheating)
  z_t <= exit_z    -> full exposure (state 1)
  else             -> hold prior state, initial state 1
w_t = vol_target / rolling realized SPY vol(21) * state, clipped [0, MAX_POS],
long-only, Equity CostModel (1bp commission + 1bp spread).

Null (H0). Cross-sectional idiosyncratic skewness contains no incremental SPY
timing information; OOS gates fail vs buy-hold / random-exposure.

Pre-registration (Cycle 78, decision-ready before validation outcomes).
Universe SPY + 15 ETFs, yfinance daily auto-adjust Close (free, PIT).
Sample 2010-01-01->2026-11-01 (train 2010-01-01->2019-12-31,
val 2020-01-01->2022-12-31, test 2023-01-01->2026-10-31 protected).
Bounded grid: lookback {63,126,252} x z_window {126,252} x entry_z {1.0,1.5,2.0}
x exit_z {0.0,0.5} (exit_z < entry_z) x vol_target {0.10,0.15} (108 combos);
train-only 4-fold WF selection by mean train Sharpe; Test protected. No
src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations/falsifiers: buy-hold SPY, random-exposure-matched, inverse regime
(de-risk on LOW skewness / risk-on high skewness), perturbation OAT +-20%,
worst-regime, Val/Test subperiods, benchmark p/IR vs SPY.
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
    "NF-20261109-06/H164: SPY timing from cross-sectional idiosyncratic "
    "skewness (lottery-demand) regime. Cross-sectional mean of rolling "
    "idiosyncratic skewness (residuals vs SPY) z-scored with hysteresis; "
    "vol-targeted long SPY de-risked on high skewness, 1-bar delay. Train-only "
    "WF selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
SKEW_ASSETS = [
    "QQQ",
    "IWM",
    "EFA",
    "EEM",
    "XLE",
    "XLF",
    "XLV",
    "XLI",
    "XLB",
    "XLP",
    "XLU",
    "XLY",
    "XLK",
    "GLD",
    "TLT",
]
UNIVERSE = [SPY] + SKEW_ASSETS
DATA_START = "2010-01-01"
DATA_END = "2026-11-01"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 164
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

LOOKBACKS = [63, 126, 252]
Z_WINDOWS = [126, 252]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5]
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


def _beta_residuals(rets: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Rolling idiosyncratic residuals of each asset vs SPY, past-only."""
    spy_ret = rets[SPY]
    mp = max(10, int(lookback) // 2)
    spy_var = spy_ret.rolling(int(lookback), min_periods=mp).var().replace(0.0, np.nan)
    resids = {}
    for a in SKEW_ASSETS:
        cov = rets[a].rolling(int(lookback), min_periods=mp).cov(spy_ret)
        beta = cov / spy_var
        resids[a] = rets[a] - beta * spy_ret
    return pd.DataFrame(resids, index=rets.index)


def idiosyncratic_skew_cross_section_mean(prices: pd.DataFrame, lookback: int) -> pd.Series:
    """Cross-sectional mean of rolling idiosyncratic skewness vs SPY."""
    rets = prices.pct_change()
    resids = _beta_residuals(rets, lookback)
    mp = max(30, int(lookback) // 2)
    skew = resids.rolling(int(lookback), min_periods=mp).skew()
    return skew.mean(axis=1)


def skew_z_score(skew_cs: pd.Series, z_window: int) -> pd.Series:
    mp = max(30, int(z_window) // 2)
    mu = skew_cs.rolling(int(z_window), min_periods=mp).mean()
    sd = skew_cs.rolling(int(z_window), min_periods=mp).std()
    return (skew_cs - mu) / sd.replace(0.0, np.nan)


def _vol_scale(prices: pd.DataFrame, vol_target: float, lookback: int = 21) -> pd.Series:
    rv = prices[SPY].pct_change().rolling(lookback, min_periods=10).std() * np.sqrt(252.0)
    scale = (float(vol_target) / rv.replace(0.0, np.nan)).clip(0.0, 3.0)
    return scale.reindex(prices.index).fillna(0.0)


def hysteresis_state(z: pd.Series, entry_z: float, exit_z: float) -> pd.Series:
    """Hysteresis: z >= entry_z => de-risk (0); z <= exit_z => full (1); hold."""
    state = np.empty(len(z), dtype=float)
    s = 1.0  # initial long per spec
    zv = z.to_numpy(dtype=float)
    for i, v in enumerate(zv):
        if np.isfinite(v):
            if v >= float(entry_z):
                s = 0.0
            elif v <= float(exit_z):
                s = 1.0
        state[i] = s
    return pd.Series(state, index=z.index)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    skew_cs = idiosyncratic_skew_cross_section_mean(prices, params["lookback"])
    z = skew_z_score(skew_cs, params["z_window"])
    state = hysteresis_state(z, params["entry_z"], params["exit_z"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (vscale * state * float(params["vol_target"])).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame({SPY: expo}, index=prices.index)
    for a in SKEW_ASSETS:
        sig[a] = 0.0
    sig.attrs["z"] = z
    sig.attrs["skew_cs"] = skew_cs
    sig.attrs["state"] = state
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
        {**params, "lookback": max(21, int(params["lookback"]) * 4 // 5)},
        {**params, "lookback": int(params["lookback"]) * 6 // 5},
        {**params, "z_window": max(63, int(params["z_window"]) * 4 // 5)},
        {**params, "z_window": int(params["z_window"]) * 6 // 5},
        {**params, "entry_z": float(params["entry_z"]) * 0.8},
        {**params, "entry_z": float(params["entry_z"]) * 1.2},
        {**params, "exit_z": max(0.0, float(params["exit_z"]) - 0.2)},
        {**params, "exit_z": min(1.5, float(params["exit_z"]) + 0.2)},
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
    sig = pd.DataFrame({SPY: expo.clip(0.0, MAX_POS)}, index=prices.index)
    for a in SKEW_ASSETS:
        sig[a] = 0.0
    return _metrics_from_result(run_backtest(prices, sig, _cfg()), mask)


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    """Falsifier: de-risk on LOW skewness (risk-on when lottery overheating)."""
    skew_cs = idiosyncratic_skew_cross_section_mean(prices, params["lookback"])
    z = skew_z_score(skew_cs, params["z_window"])
    state = np.empty(len(z), dtype=float)
    s = 1.0
    zv = z.to_numpy(dtype=float)
    for i, v in enumerate(zv):
        if np.isfinite(v):
            if v <= -float(params["entry_z"]):
                s = 0.0
            elif v >= -float(params["exit_z"]):
                s = 1.0
        state[i] = s
    state_s = pd.Series(state, index=z.index)
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (vscale * state_s * float(params["vol_target"])).fillna(0.0).clip(0.0, MAX_POS)
    sig = pd.DataFrame({SPY: expo}, index=prices.index)
    for a in SKEW_ASSETS:
        sig[a] = 0.0
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
    ir = float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-12) * np.sqrt(252.0))
    return p, ir


def main() -> None:
    t0 = time.time()
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos_m = val | test

    rows = []
    for lookback in LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_z in ENTRY_ZS:
                for exit_z in EXIT_ZS:
                    if exit_z >= entry_z:
                        continue
                    for vol_target in VOL_TARGETS:
                        params = {
                            "lookback": lookback,
                            "z_window": z_window,
                            "entry_z": entry_z,
                            "exit_z": exit_z,
                            "vol_target": vol_target,
                        }
                        wf = wf_train_mean_sharpe(prices, params, train)
                        rows.append({**params, "wf_train_mean_sharpe": wf})
    grid_df = pd.DataFrame(rows).sort_values("wf_train_mean_sharpe", ascending=False)
    best = grid_df.iloc[0].dropna().to_dict()
    best = {
        k: (int(v) if k in ("lookback", "z_window") else float(v))
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
        "nf_id_exec": "NF-20261109-06",
        "hypothesis": "H164",
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
            "Repo-new executed cross-sectional idiosyncratic-skewness SPY-timing observable.",
            "Honest adjacency: H112 MAX/lottery (same universe, max-return level observable, REJECT 2/8), H128 SPY realized skewness (single-asset time-series third moment, REJECT 2/8), H93 idiosyncratic volatility (second moment, REJECT 2/9).",
            "Signal: cross-sectional mean of rolling idiosyncratic skewness (residuals vs SPY over lookback), z-scored over z_window; de-risk on z >= entry_z (lottery overheating).",
            "Pre-registered: hysteresis de-risks on high skewness; inverse falsifier de-risks on low skewness.",
            "src/qtr unchanged; no gate weakening; no published/certified artifact modified.",
        ],
    }

    outdir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_06_idio_skew_regime"
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
        "signal_mapping": "hysteresis: z>=entry_z de-risk, z<=exit_z full exposure; cross-sectional mean idiosyncratic skewness vs SPY",
        "grid_combos": int(len(grid_df)),
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
