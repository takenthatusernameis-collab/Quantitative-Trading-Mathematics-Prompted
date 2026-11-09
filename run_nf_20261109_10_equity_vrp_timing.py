"""NF-20261109-10 / H167 (Cycle 81): equity volatility risk premium SPY timing (SPY realized vol vs VIX implied vol spread z-score).

Repo-relative novelty (honest). H17 (NF-20261105-02 equivalent VRP, REJECT) trades SVXY
directly to harvest the volatility risk premium; H100 (NF-20261106-02, REJECT 5/9) uses
ICE BofA MOVE *rates* implied volatility; H165 (NF-20261109-08, REJECT 4/8) uses the
SPY--VIX *realized correlation* (second moment, not a vol spread). H167 uses the equity
*VRP spread* (VIX implied vol minus trailing SPY realized vol, z-scored) as continuous
SPY equity timing — repo-relative distinct observable, not a new statistical method.
Honest adjacency disclosed: H17/H100 (vol-risk-premium family, different instrument/market),
H165 (SPY--VIX correlation, different observable/construction class).

Mechanism (equity volatility risk premium). Implied volatility (VIX) embeds forward-looking
fear/protection demand; realized volatility (SPY RV) is backward-looking. When VIX >> SPY RV
(positive VRP spread), options are rich relative to realized turbulence — a fear/stress
regime that coincides with or precedes equity drawdowns — so reduce equity exposure. When the
VRP spread is low/benign (complacency or cheap protection), allow targeted long exposure.
`rv_t = rolling_std(ret(SPY), rv_window)*sqrt(252)`; `vrp_t = VIX_t - rv_t`;
`z_t = rolling z-score of vrp over z_window` (past-only). Stress on positive z =
`(z.clip(0)/entry_scale).clip(0,1)`; exposure applied to return t+1 (engine `signals.shift(1)`),
no look-ahead. Vol target scales by trailing SPY RV, clipped to `MAX_POS=0.5`.

Observable (past-only, PIT, free yfinance): SPY (traded), ^VIX (signal), daily auto-adjust Close.

Null (H0). Trailing SPY realized volatility vs VIX implied volatility spread contains no
incremental SPY timing information; OOS gates fail vs buy-hold / random-exposure.

Pre-registration (Cycle 81, decision-ready before validation outcomes). NF-ID NF-20261109-10
(verified unused). Hypothesis H167 (next unused after H166; H24/H68-H73/H76-H79 unassigned, not
recycled). Universe SPY (traded) + ^VIX (signal), yfinance daily auto-adjust Close (free, PIT).
Sample 2010-01-01->2026-10-31 (train 2010-01-01->2019-12-31, val 2020-01-01->2022-12-31, test
2023-01-01->2026-10-31 protected). Signal: z-score of trailing VRP spread over z_window
(past-only); continuous stress on positive z (VIX far above realized = fear/stress); exposure
(1-stress)*vol_target*vscale; 1-bar delay; Equity CostModel defaults (1bp commission + 1bp
spread); long-only, max exposure scaled to MAX_POS=0.5. Bounded grid: rv_window {21,63} x
z_window {126,252} x entry_scale {1.0,1.5,2.0} x vol_target {0.10,0.15} (24 combos);
train-only 4-fold WF selection by mean train Sharpe; Test protected. No src/qtr change.
All gates fail-closed on pre-registered OOS Val+Test.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%, WF stability>=0.7,
worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk when VRP abnormally
*NEGATIVE*/complacent — pre-registered falsifier).

Falsifiers: random-exposure comparable or better; inverse outperforms; benchmark fails;
worst-regime collapse; fragile perturbation.
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
    "NF-20261109-10/H167 (Cycle 81): equity volatility risk premium SPY timing "
    "(SPY realized vol vs VIX implied vol spread z-score). De-risk vol-targeted long SPY "
    "when VIX far above realized SPY vol. 1-bar delay. Train-only WF selection; Test "
    "protected; OOS Val+Test gates."
)

SPY = "SPY"
VIX = "^VIX"
UNIVERSE = [SPY, VIX]
DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 167
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

RV_WINDOWS = [21, 63]
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


def equity_vrp_spread_z(prices: pd.DataFrame, rv_window: int, z_window: int) -> pd.Series:
    ret = prices[SPY].pct_change()
    rv = ret.rolling(rv_window, min_periods=rv_window).std(ddof=0) * np.sqrt(252.0)
    vrp = prices[VIX] - rv
    mean = vrp.rolling(z_window, min_periods=z_window).mean()
    std = vrp.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0.0, np.nan)
    return (vrp - mean) / std


def _vol_scale(prices: pd.DataFrame, vol_target: float) -> pd.Series:
    ret = prices[SPY].pct_change()
    rv = ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252.0)
    return (vol_target / rv.replace(0.0, np.nan)).clip(0.0, 1.0)


def make_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = equity_vrp_spread_z(prices, params["rv_window"], params["z_window"])
    stress = (z.clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0)
    vscale = _vol_scale(prices, params["vol_target"])
    w = ((1.0 - stress) * params["vol_target"] * vscale).clip(0.0, MAX_POS)
    sig = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    sig[SPY] = w.fillna(0.0)
    return sig


def make_inverse_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = equity_vrp_spread_z(prices, params["rv_window"], params["z_window"])
    stress = ((-z).clip(lower=0.0) / params["entry_scale"]).clip(0.0, 1.0)
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
    for rv_window in RV_WINDOWS:
        for z_window in Z_WINDOWS:
            for entry_scale in ENTRY_SCALES:
                for vol_target in VOL_TARGETS:
                    params = {
                        "rv_window": rv_window,
                        "z_window": z_window,
                        "entry_scale": entry_scale,
                        "vol_target": vol_target,
                    }
                    wf = _wf_selection_mean(prices, train_mask, params)
                    rows.append({**params, "wf_train_mean_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_mean_sharpe"], reverse=True)
    best = {k: rows[0][k] for k in ("rv_window", "z_window", "entry_scale", "vol_target")}
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
    for drw, dz, de, dv in [
        (0, 0, 0.25, 0.0),
        (0, 0, -0.25, 0.0),
        (0, 0, 0.0, 0.02),
        (0, 0, 0.0, -0.02),
        (21, 0, 0.0, 0.0),
        (-21, 0, 0.0, 0.0),
        (0, 63, 0.0, 0.0),
    ]:
        p = {
            "rv_window": int(np.clip(best["rv_window"] + drw, 10, 252)),
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
        "nf_id": "NF-20261109-10",
        "h_id": "H167",
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
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_10_equity_vrp_timing"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    pd.DataFrame(grid_rows).to_csv(out_dir / "grid.csv", index=False)
    meta = {
        "nf_id": "NF-20261109-10",
        "h_id": "H167",
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
