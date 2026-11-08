"""NF-20261107-11 / H146 (pre-registered, Cycle 60): SPY timing from
cross-sectional idiosyncratic-volatility (IVOL) spread / dispersion.

Observable (past-only, PIT daily adjusted Close):
  For each non-SPY asset a in a fixed liquid ETF universe, IVOL_a(t) is the
  rolling OLS residual std of asset a's daily returns on SPY's daily returns
  over `ivol_lookback` (computed as sqrt(var(a) - cov(a,spy)^2/var(spy))).
  dispersion(t) = cross-sectional std of IVOL across the 9 non-SPY assets.
  z(t) = (dispersion(t) - rolling_mean(dispersion, z_window)) /
         rolling_std(dispersion, z_window).

Mechanism (cross-sectional volatility decomposition / higher-moment dispersion):
  High cross-sectional IVOL dispersion reflects elevated idiosyncratic
  disagreement/uncertainty across the equity market and predicts increased
  equity risk premia / near-term drawdown risk; low dispersion reflects
  consensus. Continuously de-risk a vol-targeted long SPY position when
  IVOL dispersion z is abnormally high; 1-bar execution delay via engine
  signals.shift(1), long-only.

Repo-relative novelty (honest). No executed NF/H uses *cross-sectional IVOL
dispersion* as the SPY timing observable. H93 tested a single-asset / average
IVOL *level* regime (different observable: level not cross-sectional
dispersion; different mechanism: vol level not disagreement dispersion).
H118/H136/H137 tested cross-sectional return correlation/dispersion (first
moment; different observable). H122 used downside semivariance *level*
(realized-vol level timing). H125/H126 tested IV spread (implied vol level
spread, not realized IVOL dispersion). Honest adjacency to the
z-score/continuous-de-risking/vol-target construction class (H144/H145) is
acknowledged; novelty scored on the repo-new cross-sectional IVOL-dispersion
observable as an executed SPY-timing test, not a wholly new method.

Null (H0). Cross-sectional IVOL dispersion contains no incremental timing
information; OOS gates fail vs buy-hold/random-exposure.

Pre-registration (Cycle 60, decision-ready before validation outcomes).
NF-ID NF-20261107-11 (lineage key preserved from proposal). Hypothesis H146.
Universe: SPY (traded) + QQQ,IWM,EFA,EEM,XLF,XLE,XLV,XLI,XLK (signal only),
yfinance daily auto-adjust Close (free, PIT). All signal ETFs predate 2010,
so the fixed 2010-01-04->2025-01-03 sample is survivorship-free for the
universe used. Sample 2010-01-04->2025-01-03 (train 2516 / val 505 / test 755,
aligned). IVOL lookback {63,126}; dispersion z over z_window {126,252};
continuous stress on high z = (z.clip(0)/entry_scale).clip(0,1);
exposure (1-stress)*vol_target*vscale; 1-bar delay; Equity CostModel defaults
(1bp commission + 1bp spread); long-only, max exposure vol_target scaled to
MAX_POS=0.5. Bounded grid: ivol_lookback {63,126} x z_window {126,252} x
entry_scale {1.0,2.0} x vol_target {0.10,0.15} (16 combos); train-only
4-fold WF selection by mean train Sharpe; Test protected. No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when IVOL dispersion is LOW / negative z — pre-registered falsifier).

Falsifiers: random-exposure comparable or better; inverse not opposite as
expected; benchmark fails; fragile; worst-regime collapse.
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
    "NF-20261107-11/H146: SPY timing from cross-sectional IVOL dispersion. "
    "z-score of rolling cross-sectional std of per-asset IVOL (OLS residual "
    "vol vs SPY); de-risk vol-targeted long SPY when dispersion z is abnormally "
    "high (idiosyncratic disagreement/stress). 1-bar delay. Train-only WF "
    "selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
IVOL_ASSETS = ["QQQ", "IWM", "EFA", "EEM", "XLF", "XLE", "XLV", "XLI", "XLK"]
UNIVERSE = [SPY] + IVOL_ASSETS
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

IVOL_LOOKBACKS = [63, 126]
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
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)), index=index
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def ivol_dispersion(prices: pd.DataFrame, ivol_lookback: int) -> pd.Series:
    """Cross-sectional std of per-asset IVOL (OLS residual vol vs SPY)."""
    lookback = int(ivol_lookback)
    min_p = max(20, lookback // 2)
    rets = prices.pct_change()
    spy = rets[SPY]
    var_s = spy.rolling(lookback, min_periods=min_p).var()
    ivols = {}
    for a in IVOL_ASSETS:
        r_a = rets[a]
        var_a = r_a.rolling(lookback, min_periods=min_p).var()
        cov_as = r_a.rolling(lookback, min_periods=min_p).cov(spy)
        resid_var = var_a - (cov_as**2) / var_s.replace(0.0, np.nan)
        ivols[a] = np.sqrt(np.maximum(resid_var, 0.0))
    ivol_df = pd.DataFrame(ivols, index=rets.index)
    return ivol_df.std(axis=1)


def dispersion_z(dispersion: pd.Series, z_window: int) -> pd.Series:
    window = int(z_window)
    min_p = max(30, window // 2)
    mu = dispersion.rolling(window, min_periods=min_p).mean()
    sd = dispersion.rolling(window, min_periods=min_p).std()
    return (dispersion - mu) / sd.replace(0.0, np.nan)


def build_exposure(z: pd.Series, entry_scale: float, vol_target: float) -> pd.Series:
    # de-risk when cross-sectional IVOL dispersion (idiosyncratic stress) is high
    stress = (z.clip(lower=0.0) / float(entry_scale)).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(vol_target)
    return raw.fillna(float(vol_target)).clip(lower=0.0, upper=float(vol_target))


def _vol_scale(prices: pd.DataFrame, vol_target: float, lookback: int = 21) -> pd.Series:
    rv = prices[SPY].pct_change().rolling(lookback, min_periods=10).std() * np.sqrt(252)
    scale = (float(vol_target) / rv.replace(0.0, np.nan)).clip(0.0, 3.0)
    return scale.reindex(prices.index).fillna(0.0)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    disp = ivol_dispersion(prices, params["ivol_lookback"])
    z = dispersion_z(disp, params["z_window"])
    stress = (z.clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = expo
    sig.attrs["z"] = z
    sig.attrs["dispersion"] = disp
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


def perturbation_ratio(prices: pd.DataFrame, best: dict, oos_mask: pd.Series) -> float:
    base = _metrics_from_result(run_one(prices, best)["result"], oos_mask)["sharpe"]
    if not np.isfinite(base) or abs(base) < 1e-12:
        return float("nan")
    ratios = []
    for k, delta in [
        ("ivol_lookback", 21),
        ("z_window", 21),
        ("entry_scale", 0.25),
        ("vol_target", 0.02),
    ]:
        for sign in (-1, 1):
            p = dict(best)
            alt = p[k] + sign * delta
            if k in ("ivol_lookback", "z_window"):
                alt = int(max(5, round(alt)))
            p[k] = type(best[k])(alt) if not isinstance(best[k], float) else float(alt)
            try:
                s = _metrics_from_result(run_one(prices, p)["result"], oos_mask)["sharpe"]
            except Exception:
                continue
            if np.isfinite(s):
                ratios.append(s / base)
    return float(np.min(ratios)) if ratios else float("nan")


def worst_regime_sharpe(prices: pd.DataFrame, best: dict, oos_mask: pd.Series) -> float:
    res = run_one(prices, best)["result"]
    eq = res.equity_curve.loc[res.equity_curve.index.intersection(prices.index[oos_mask])]
    ret = eq.pct_change().dropna()
    if len(ret) < 252:
        return float("nan")
    vals = [float(sharpe_ratio(ret.iloc[i - 252 : i])) for i in range(252, len(ret) + 1)]
    vals = [v for v in vals if np.isfinite(v)]
    return float(np.min(vals)) if vals else float("nan")


def benchmark_buy_hold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    p = prices.loc[mask, SPY]
    ret = p.pct_change().dropna()
    peak = p.cummax()
    mdd = float(((p - peak) / peak).min())
    neg = ret[ret < 0].abs().sum()
    pf = float(ret[ret > 0].sum() / neg) if neg > 1e-12 else float("inf")
    return {
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": 1,
    }


def random_exposure_matched(
    prices: pd.DataFrame, mask: pd.Series, mean_expo: float, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    p = prices.loc[mask, SPY]
    ret = p.pct_change().dropna()
    expo = pd.Series(rng.uniform(0, 1, len(ret)), index=ret.index)
    expo = expo * (mean_expo / expo.mean()) if expo.mean() > 1e-12 else expo
    expo = expo.clip(0.0, MAX_POS)
    strat = (ret * expo.shift(1).fillna(0.0)).dropna()
    peak = (1 + strat).cumprod().cummax()
    eq = (1 + strat).cumprod()
    mdd = float(((eq - peak) / peak).min())
    neg = strat[strat < 0].abs().sum()
    pf = float(strat[strat > 0].sum() / neg) if neg > 1e-12 else float("inf")
    ntr = int((expo.diff().abs().fillna(0) > 1e-6).sum())
    return {
        "sharpe": float(sharpe_ratio(strat)),
        "profit_factor": pf,
        "max_drawdown": mdd,
        "trades": ntr,
    }


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    disp = ivol_dispersion(prices, params["ivol_lookback"])
    z = dispersion_z(disp, params["z_window"])
    # inverse: de-risk when IVOL dispersion is LOW (negative z, consensus)
    stress = ((-z).clip(lower=0.0) / float(params["entry_scale"])).clip(0.0, 1.0)
    raw = (1.0 - stress) * float(params["vol_target"])
    vscale = _vol_scale(prices, params["vol_target"])
    expo = (raw * vscale).fillna(0.0).clip(lower=0.0, upper=MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = expo
    res = run_backtest(prices, sig, _cfg())
    oos = pd.Series((prices.index > pd.Timestamp(TRAIN_END)), index=prices.index)
    return _metrics_from_result(res, oos)


def main():
    t0 = time.time()
    prices = _fetch()
    train_m, val_m, test_m = _splits(prices.index)
    oos_m = val_m | test_m

    grid = []
    for ivol_lookback in IVOL_LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    p = dict(
                        ivol_lookback=ivol_lookback,
                        z_window=z_window,
                        entry_scale=entry_scale,
                        vol_target=vol_target,
                    )
                    wf = wf_train_mean_sharpe(prices, p, train_m)
                    grid.append({**p, "wf_train_mean_sharpe": wf})
    grid_df = pd.DataFrame(grid).sort_values("wf_train_mean_sharpe", ascending=False)
    best = {
        k: (int(v) if k in ("ivol_lookback", "z_window") else float(v))
        for k, v in grid_df.iloc[0][
            ["ivol_lookback", "z_window", "entry_scale", "vol_target"]
        ].items()
    }

    oos_res = run_one(prices, best)["result"]
    oos_met = _metrics_from_result(oos_res, oos_m)
    bh = benchmark_buy_hold(prices, oos_m)
    eq = oos_res.equity_curve.loc[oos_res.equity_curve.index.intersection(prices.index[oos_m])]
    strat_ret = eq.pct_change().dropna()
    bh_ret = prices.loc[oos_m, SPY].pct_change().reindex(strat_ret.index).dropna()
    common = strat_ret.index.intersection(bh_ret.index)
    diff = (strat_ret.loc[common] - bh_ret.loc[common]).values
    rng = np.random.default_rng(SEED)
    boots = [rng.choice(diff, size=len(diff), replace=True).mean() * 252 for _ in range(2000)]
    ir = float(diff.mean() / (diff.std() + 1e-12) * np.sqrt(252))
    p_bench = float(np.mean(np.array(boots) <= 0.0))
    wf_stab = (
        float(oos_met["sharpe"] / grid_df.iloc[0]["wf_train_mean_sharpe"])
        if np.isfinite(grid_df.iloc[0]["wf_train_mean_sharpe"])
        and abs(grid_df.iloc[0]["wf_train_mean_sharpe"]) > 1e-12
        else float("nan")
    )
    worst = worst_regime_sharpe(prices, best, oos_m)
    pert = perturbation_ratio(prices, best, oos_m)

    gates = {
        "sharpe_ge_1": oos_met["sharpe"] >= 1.0,
        "trades_ge_200": oos_met["trades"] >= 200,
        "pf_ge_1_3": oos_met["profit_factor"] >= 1.3,
        "maxdd_le_15pct": (abs(oos_met["max_drawdown"]) <= 0.15)
        if np.isfinite(oos_met["max_drawdown"])
        else False,
        "wf_stability_ge_0_7": (wf_stab >= 0.7) if np.isfinite(wf_stab) else False,
        "worst_regime_ge_0_3": (worst >= 0.3) if np.isfinite(worst) else False,
        "benchmark_p_le_0_05_ir_ge_0": (p_bench <= 0.05 and ir >= 0.0),
        "perturbation_ge_0_5": (pert >= 0.5) if np.isfinite(pert) else False,
    }
    passed = sum(gates.values())
    verdict = "PASS" if passed == len(gates) else "REJECT"

    mean_expo = float(make_signals(prices, best)[SPY].loc[oos_m].mean())
    summary = {
        "nf_id": "NF-20261107-11",
        "hypothesis": "H146",
        "verdict": verdict,
        "gates_passed": f"{passed}/{len(gates)}",
        "gates": gates,
        "selected_params": best,
        "selection_wf_train_mean_sharpe": float(grid_df.iloc[0]["wf_train_mean_sharpe"]),
        "oos_val_test": oos_met,
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
    }

    outdir = ROOT / ".experiments" / "nf_runs" / "nf_20261107_11_ivol_spread_spy"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    grid_df.to_csv(outdir / "grid.csv", index=False)
    meta = {
        "universe": UNIVERSE,
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "rows": int(len(prices)),
        "train": int(train_m.sum()),
        "val": int(val_m.sum()),
        "test": int(test_m.sum()),
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
