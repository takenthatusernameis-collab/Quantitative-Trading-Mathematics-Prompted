"""NF-20261109-09 / H166 (Cycle 80): SPY timing from KRE--XLF regional-bank
vs broad-financial intermediation-stress spread (relative-momentum regime).

Repo-relative novelty (honest). H107 (NF-20261106-16, REJECT 4/8) used KRE's
*own* trailing momentum z-score as a banking-stress proxy for SPY timing — a
single-asset observable confounded by broad financials/market beta. NF-06-03 in
the research register proposed a KRE/XLF regional-bank-vs-broad-financials
intermediation stress spread as a distinct candidate and it was never executed.
H166 uses the *KRE/XLF ratio trailing relative-momentum z-score* (KRE vs XLF)
to isolate regional-bank-specific intermediation/funding stress from broad
financial-sector moves. Honest adjacency to H107 (same KRE asset, different
observable: spread vs own level; mechanism emphasis differs) and to H94/H108
(credit spreads, different channel) is disclosed; novelty scored repo-relative
on the KRE/XLF spread observable, not a new statistical method.

Mechanism (financial intermediation / regional-bank liquidity-stress
transmission). KRE underperformance relative to broad financials (XLF) can
reflect regional-bank-specific funding/liquidity stress, deposit/credit
impairment, or balance-sheet risk beyond the broad financial sector. Regional-
bank intermediation stress may tighten financial conditions and transmit to
equity risk premia. `ratio_t = KRE_t / XLF_t`; `mom_t = pct_change(ratio,
lookback)`; `z_t = (mom_t - rolling_mean(mom, z_window)) / rolling_std(mom,
z_window)` (past-only). Stress when KRE underperforms XLF (negative z) =
`((-z).clip(0)/entry_scale).clip(0,1)`; exposure `(1-stress)*vol_target*vscale`
applied to return t+1 (engine `signals.shift(1)`), no look-ahead. Vol target
scales by trailing 21-day realized SPY vol, clipped to MAX_POS=0.5.

Observable (past-only, PIT, free yfinance): SPY (traded), KRE, XLF daily
auto-adjust Close.

Null (H0). Trailing KRE/XLF intermediation-stress spread contains no
incremental SPY timing information; OOS gates fail vs buy-hold /
random-exposure.

Pre-registration (Cycle 80, decision-ready before validation outcomes).
NF-ID NF-20261109-09 (verified unused: no executed NF/H/runner/artifact).
Hypothesis H166 (next unused after H165; H24/H68-H73/H76-H79 unassigned, not
recycled). Universe SPY (traded) + KRE,XLF (signal), yfinance daily
auto-adjust Close (free, PIT). Sample 2010-01-01->2026-10-31 (train
2010-01-01->2019-12-31, val 2020-01-01->2022-12-31, test 2023-01-01->2026-10-31
protected). Signal: z-score of trailing KRE/XLF ratio momentum over lookback,
standardized over z_window (past-only); continuous stress on negative z
(KRE underperforms XLF); exposure (1-stress)*vol_target*vscale; 1-bar delay;
Equity CostModel defaults (1bp commission + 1bp spread); long-only, max
exposure scaled to MAX_POS=0.5. Bounded grid: lookback {63,126} x z_window
{126,252} x entry_scale {1.0,1.5,2.0} x vol_target {0.10,0.15} (24 combos);
train-only 4-fold WF selection by mean train Sharpe; Test protected. No src/qtr
change. All gates fail-closed on pre-registered OOS Val+Test.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when KRE *outperforms* XLF, positive z — pre-registered falsifier).

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
    "NF-20261109-09/H166 (Cycle 80): SPY timing from KRE/XLF regional-bank vs "
    "broad-financial intermediation-stress spread (relative-momentum z-score). "
    "De-risk vol-targeted long SPY when KRE underperforms XLF. 1-bar delay. "
    "Train-only WF selection; Test protected; OOS Val+Test gates."
)

SPY = "SPY"
KRE = "KRE"
XLF = "XLF"
UNIVERSE = [SPY, KRE, XLF]
DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 166
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

LOOKBACKS = [63, 126]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
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


def kre_xlf_spread_z(prices: pd.DataFrame, lookback: int, z_window: int) -> pd.Series:
    ratio = prices[KRE] / prices[XLF]
    mom = ratio.pct_change(lookback)
    mean = mom.rolling(z_window, min_periods=z_window).mean()
    std = mom.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0.0, np.nan)
    return (mom - mean) / std


def _vol_scale(prices: pd.DataFrame, vol_target: float) -> pd.Series:
    ret = prices[SPY].pct_change()
    rv = ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252.0)
    return (vol_target / rv.replace(0.0, np.nan)).clip(0.0, 1.0)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = kre_xlf_spread_z(prices, params["lookback"], params["z_window"])
    stress = ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0)
    vscale = _vol_scale(prices, params["vol_target"])
    w = ((1.0 - stress) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return sig


def make_inverse_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = kre_xlf_spread_z(prices, params["lookback"], params["z_window"])
    stress = (z.clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0)
    vscale = _vol_scale(prices, params["vol_target"])
    w = ((1.0 - stress) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return sig


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
    )


def _pf(returns: pd.Series) -> float:
    r = returns.dropna()
    gain = r[r > 0].sum()
    loss = -r[r < 0].sum()
    if loss <= 0:
        return float("inf") if gain > 0 else 0.0
    return float(gain / loss)


def _maxdd(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())


def evaluate(prices: pd.DataFrame, signals: pd.DataFrame, mask: pd.Series) -> dict:
    p = prices.loc[mask]
    s = signals.loc[mask]
    if len(p) < 60 or s[SPY].abs().sum() < 1e-12:
        return {"sharpe": float("nan"), "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0}
    res = run_backtest(p, s, _cfg())
    eq = res.equity_curve
    ret = eq.pct_change().dropna()
    trades = res.trades
    ntr = 0
    if trades is not None and len(trades) > 0:
        if hasattr(trades, "empty") and not trades.empty:
            if "date" in trades.columns:
                ntr = int(pd.to_datetime(trades["date"]).isin(eq.index).sum())
            else:
                ntr = int(len(trades))
        elif not hasattr(trades, "empty"):
            ntr = int(len(trades))
    return {
        "sharpe": float(sharpe_ratio(ret)),
        "profit_factor": _pf(ret),
        "max_drawdown": _maxdd(eq),
        "trades": ntr,
    }


def benchmark_buy_hold(prices: pd.DataFrame, mask: pd.Series) -> dict:
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = 1.0
    return evaluate(prices, sig, mask)


def _wf_selection_mean(prices: pd.DataFrame, train_mask: pd.Series, params: dict) -> float:
    train_idx = prices.index[train_mask]
    if len(train_idx) < WF_FOLDS_SELECTION * 252:
        ev = evaluate(prices, make_signals(prices, params), train_mask)
        return ev["sharpe"] if np.isfinite(ev["sharpe"]) else float("-inf")
    fold = len(train_idx) // WF_FOLDS_SELECTION
    sharpes = []
    for i in range(WF_FOLDS_SELECTION):
        end = (i + 1) * fold if i < WF_FOLDS_SELECTION - 1 else len(train_idx)
        idx = train_idx[:end]
        if len(idx) < 252:
            continue
        m = pd.Series(False, index=prices.index)
        m.loc[idx] = True
        ev = evaluate(prices, make_signals(prices, params), m)
        if np.isfinite(ev["sharpe"]):
            sharpes.append(ev["sharpe"])
    return float(np.mean(sharpes)) if sharpes else float("-inf")


def select_params(prices: pd.DataFrame, train_mask: pd.Series) -> tuple[dict, list[dict]]:
    rows = []
    for lookback in LOOKBACKS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    params = {
                        "lookback": lookback,
                        "z_window": z_window,
                        "entry_scale": entry_scale,
                        "vol_target": vol_target,
                    }
                    wf = _wf_selection_mean(prices, train_mask, params)
                    rows.append({**params, "wf_train_mean_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_mean_sharpe"], reverse=True)
    best = {k: rows[0][k] for k in ("lookback", "z_window", "entry_scale", "vol_target")}
    return best, rows


def worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    r = returns.dropna()
    if len(r) < window:
        return float(sharpe_ratio(r))
    roll = r.rolling(window).apply(lambda x: float(sharpe_ratio(x)), raw=False)
    return float(roll.min())


def perturbation_ratio(prices: pd.DataFrame, oos_mask: pd.Series, best: dict) -> float:
    base = evaluate(prices, make_signals(prices, best), oos_mask)["sharpe"]
    if not np.isfinite(base) or abs(base) < 1e-12:
        return 0.0
    ratios = []
    for dlb, dz, de, dv in [
        (0, 0, 0.25, 0.0),
        (0, 0, -0.25, 0.0),
        (0, 0, 0.0, 0.02),
        (0, 0, 0.0, -0.02),
        (21, 0, 0.0, 0.0),
        (-21, 0, 0.0, 0.0),
        (0, 63, 0.0, 0.0),
    ]:
        p = {
            "lookback": int(np.clip(best["lookback"] + dlb, 21, 252)),
            "z_window": int(np.clip(best["z_window"] + dz, 63, 504)),
            "entry_scale": float(np.clip(best["entry_scale"] + de, 0.5, 4.0)),
            "vol_target": float(np.clip(best["vol_target"] + dv, 0.05, 0.30)),
        }
        s = evaluate(prices, make_signals(prices, p), oos_mask)["sharpe"]
        if np.isfinite(s):
            ratios.append(s / base)
    return float(min(ratios)) if ratios else 0.0


def random_exposure(prices: pd.DataFrame, base_sig: pd.DataFrame, mask: pd.Series) -> dict:
    rng = np.random.default_rng(SEED)
    m = mask[mask].index
    vals = base_sig.loc[m, SPY].to_numpy().copy()
    rng.shuffle(vals)
    sig = base_sig.copy()
    sig.loc[m, SPY] = vals
    return evaluate(prices, sig, mask)


def inverse_regime(prices: pd.DataFrame, params: dict) -> dict:
    _, _, test = _splits(prices.index)
    _, val, _ = _splits(prices.index)
    oos = val | test
    return evaluate(prices, make_inverse_signals(prices, params), oos)


def _oos_returns(prices: pd.DataFrame, signals: pd.DataFrame, mask: pd.Series) -> pd.Series:
    res = run_backtest(prices.loc[mask], signals.loc[mask], _cfg())
    return res.equity_curve.pct_change().dropna()


def _benchmark_compare(strat_ret: pd.Series, bench_ret: pd.Series) -> tuple[float, float]:
    a = pd.concat([strat_ret.rename("s"), bench_ret.rename("b")], axis=1).dropna()
    if len(a) < 30:
        return 1.0, 0.0
    diff = a["s"] - a["b"]
    ir = float(diff.mean() / diff.std(ddof=0) * np.sqrt(252.0)) if diff.std(ddof=0) > 0 else 0.0
    rng = np.random.default_rng(SEED)
    obs = diff.mean()
    count = 0
    n = len(diff)
    vals = diff.to_numpy()
    for _ in range(2000):
        signs = rng.choice([-1.0, 1.0], size=n)
        if float((vals * signs).mean()) >= obs:
            count += 1
    p = (count + 1) / 2001
    return float(p), ir


def main() -> None:
    t0 = time.time()
    print(f"[{EXPERIMENT_DESC}]")
    prices = _fetch()
    train, val, test = _splits(prices.index)
    oos = val | test
    best, grid_rows = select_params(prices, train)
    sig = make_signals(prices, best)
    oos_ev = evaluate(prices, sig, oos)
    train_ev = evaluate(prices, sig, train)
    wf_stab = (
        float(oos_ev["sharpe"] / train_ev["sharpe"])
        if np.isfinite(train_ev["sharpe"]) and abs(train_ev["sharpe"]) > 1e-12
        else 0.0
    )
    strat_ret = _oos_returns(prices, sig, oos)
    bench_sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    bench_sig[SPY] = 1.0
    bench_ret = _oos_returns(prices, bench_sig, oos)
    bench_p, ir = _benchmark_compare(strat_ret, bench_ret)
    pert = perturbation_ratio(prices, oos, best)
    oos_ev["wf_stability"] = wf_stab
    oos_ev["worst_regime_sharpe"] = worst_regime_sharpe(strat_ret)
    oos_ev["benchmark_p"] = bench_p
    oos_ev["information_ratio"] = ir
    oos_ev["perturbation_ratio"] = pert
    oos_ev["n"] = int(oos.sum())
    gates = {
        "sharpe_ge_1": oos_ev["sharpe"] >= 1.0,
        "trades_ge_200": oos_ev["trades"] >= 200,
        "pf_ge_1_3": oos_ev["profit_factor"] >= 1.3,
        "maxdd_le_15pct": oos_ev["max_drawdown"] >= -0.15,
        "wf_stability_ge_0_7": wf_stab >= 0.7,
        "worst_regime_ge_0_3": oos_ev["worst_regime_sharpe"] >= 0.3,
        "benchmark_p_le_0_05_ir_ge_0": bench_p <= 0.05 and ir >= 0.0,
        "perturbation_ge_0_5": pert >= 0.5,
    }
    pass_count = sum(1 for v in gates.values() if v)
    verdict = "PASS" if pass_count == 8 else "REJECT"
    out = {
        "nf_id": "NF-20261109-09",
        "h_id": "H166",
        "verdict": verdict,
        "gates": f"{pass_count}/8",
        "gate_detail": gates,
        "best": best,
        "train": train_ev,
        "oos": oos_ev,
        "ablations": {
            "buy_hold_spy": benchmark_buy_hold(prices, oos),
            "random_exposure_matched": random_exposure(prices, sig, oos),
            "inverse_regime": inverse_regime(prices, best),
        },
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_09_kre_xlf_stress_spy"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    pd.DataFrame(grid_rows).to_csv(out_dir / "grid.csv", index=False)
    meta = {
        "nf_id": "NF-20261109-09",
        "h_id": "H166",
        "universe": UNIVERSE,
        "data_start": DATA_START,
        "data_end": DATA_END,
        "rows": int(len(prices)),
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "seed": SEED,
        "grid_n": len(grid_rows),
        "selection": "best train-only 4-fold WF mean Sharpe; gates on OOS Val+Test",
    }
    (out_dir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": out["gates"], "oos": oos_ev, "best": best},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
