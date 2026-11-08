"""NF-20261108-17 / H154 (Cycle 68): SPY timing from short-rate level
regime via SHY (short-Treasury ETF) cumulative-return proxy.

Repo-relative novelty (honest). No executed NF/H in this repo uses a *short-rate
level* (as opposed to a term *spread* or *slope*) as the SPY timing observable.
H141 (NF-20261108-02, REJECT 5/8) tested TLT-vs-SHY Treasury term-spread
momentum (duration-vs-cash relative momentum, a *spread*). H92/H96/H145 used
equity-vs-duration or equity-vs-bond relative momentum / correlation. NF-08-17
was a deferred/incomplete stub (docstring-only, unverified signal mapping);
H154 is the first verified execution of the short-rate-level channel.

Mechanism (short-rate level / monetary-tightness transmission). When the
short-term risk-free rate is abnormally elevated relative to its trailing
history, financial conditions are tight and equity risk premia are compressed;
the pre-registered rule reduces vol-targeted long SPY exposure continuously as
the short-rate-level proxy indicates tightness. Causal chain: SHY cumulative
return at close t -> z-score regime -> exposure weight applied to return t+1
(engine signals.shift(1)), no look-ahead.

Observable (past-only, PIT, free yfinance): SHY (iShares 1-3Y Treasury Bond
ETF, traded proxy for the short end of the curve), SPY. SHY price falls when
yields rise (tight/abnormally high short rate) and rises when yields fall
(loose). `cumret_t = SHY/SHY.shift(shy_window) - 1` (trailing cumulative
return); `z_t = z-score(cumret_t, z_window)` past-only. Pre-registered
mapping (verified/resolved): stress on **negative** z (SHY cumulative return
abnormally weak = yields high/tight) =
`((-z).clip(0)/entry_scale).clip(0,1)`. Exposure `(1-stress)*vol_target*vscale`.

Note on ^IRX: direct 13-week T-bill yield index is NOT used; yfinance ^IRX has
non-positive values (min -0.105, 2020) rejected by engine fail-closed
non-positive-price screen. SHY is clean (3776 rows, 0 non-positive, 2010-2025).

Null (H0). Trailing short-rate level proxy (SHY cumulative-return z-score)
contains no incremental SPY timing information; OOS gates fail vs
buy-hold/random-exposure.

Pre-registration (Cycle 68, decision-ready before validation outcomes).
NF-ID NF-20261108-17 (completing deferred stub). Hypothesis H154. Universe SPY
(traded) + SHY (signal), yfinance daily auto-adjust Close (free, PIT). Sample
2010-01-04->2025-01-03 (train 2516 / val 505 / test 755, aligned). Selection:
train-only 4-fold WF mean Sharpe. Test protected. No src/qtr change.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark p<=0.05
with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-exposure-matched, inverse regime (de-risk
when SHY cumulative return abnormally HIGH / positive z = loose conditions;
pre-registered falsifier).

Falsifiers: random-exposure comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from qtr.config import Settings
from scipy import stats

from qtr.backtest.engine import BacktestConfig, BacktestEngine, CostModel

SPY = "SPY"
SHY = "SHY"
UNIVERSE = [SPY, SHY]
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
MAX_POS = 0.5
WF_FOLDS = 4
REALIZED_VOL_LOOKBACK = 21
TARGET_VOL_SCALE = 0.10
GRID = {
    "shy_window": [21, 63, 126],
    "z_window": [126, 252],
    "entry_scale": [1.0, 2.0],
    "vol_target": [0.10, 0.15],
}
BENCH_GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_pf": 1.3,
    "max_dd": 0.15,
    "min_wf_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_benchmark_p": 0.05,
    "min_perturbation_ratio": 0.5,
}


def _to_series(obj: pd.Series | pd.DataFrame) -> pd.Series:
    if isinstance(obj, pd.DataFrame):
        return obj.iloc[:, 0].astype(float)
    return obj.astype(float)


def fetch_data() -> pd.DataFrame:
    raw = yf.download(
        UNIVERSE,
        start="2010-01-01",
        end="2025-01-05",
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        raise RuntimeError("yfinance returned empty data")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if not isinstance(close, pd.DataFrame):
        close = close.to_frame()
    close = close.dropna(how="all").ffill().dropna()
    missing = [c for c in UNIVERSE if c not in close.columns]
    if missing:
        raise RuntimeError(f"missing columns: {missing}")
    close = close[UNIVERSE]
    if (close <= 0).any().any():
        bad = close.columns[(close <= 0).any()].tolist()
        raise RuntimeError(f"non-positive prices: {bad}")
    return close


def sharpe(returns: pd.Series) -> float:
    r = pd.Series(returns).dropna()
    if len(r) < 20:
        return 0.0
    sd = float(r.std(ddof=1))
    if sd < 1e-12:
        return 0.0
    return float(r.mean() / sd * np.sqrt(252))


def profit_factor(returns: pd.Series) -> float:
    r = pd.Series(returns).dropna()
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    if losses < 1e-12:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def max_drawdown(equity: pd.Series) -> float:
    e = pd.Series(equity).dropna()
    if e.empty:
        return 0.0
    peak = e.cummax()
    dd = (e - peak) / peak.replace(0.0, np.nan)
    return float(dd.min())


def target_vol_scale(spy_close: pd.Series) -> pd.Series:
    rets = spy_close.pct_change(fill_method=None)
    rv = rets.rolling(REALIZED_VOL_LOOKBACK).std() * np.sqrt(252)
    scale = TARGET_VOL_SCALE / rv.replace(0.0, np.nan)
    return scale.clip(0.1, 2.0).fillna(0.1)


def zscore(s: pd.Series, window: int) -> pd.Series:
    m = s.rolling(window, min_periods=max(20, window // 2)).mean()
    sd = s.rolling(window, min_periods=max(20, window // 2)).std()
    return (s - m) / sd.replace(0.0, np.nan)


def _regime_labels(spy_close: pd.Series) -> pd.Series:
    ma = spy_close.rolling(252, min_periods=126).mean()
    ret63 = spy_close.pct_change(63)
    return pd.Series(
        np.select(
            [spy_close > ma, (spy_close <= ma) & (ret63 > 0), (spy_close <= ma) & (ret63 <= 0)],
            ["bull", "sideways", "bear"],
            default="unknown",
        ),
        index=spy_close.index,
    )


def worst_regime_sharpe(returns: pd.Series, spy_close: pd.Series) -> float:
    labels = _regime_labels(spy_close)
    idx = returns.index.intersection(labels.index)
    vals = [
        sharpe(returns.loc[idx][labels.loc[idx] == regime])
        for regime in ["bull", "sideways", "bear"]
        if (labels.loc[idx] == regime).sum() >= 30
    ]
    return float(min(vals)) if vals else 0.0


def make_signals(
    prices: pd.DataFrame,
    *,
    shy_window: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    # SHY falls when yields rise (tight). Positive cumret = loose; negative = tight.
    shy_cumret = prices[SHY] / prices[SHY].shift(shy_window) - 1.0
    z = zscore(shy_cumret, z_window)
    # Pre-registered: stress on negative z (tight/abnormally high short rate).
    stress = ((-z).clip(lower=0.0) / max(entry_scale, 1e-9)).clip(0.0, 1.0)
    vscale = target_vol_scale(prices[SPY]) * (vol_target / TARGET_VOL_SCALE)
    exposure = (1.0 - stress) * vscale
    exposure = exposure.clip(lower=0.0)
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[SPY] = exposure.fillna(0.0)
    return out.clip(-MAX_POS, MAX_POS)


def make_signals_inverse(
    prices: pd.DataFrame,
    *,
    shy_window: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    shy_cumret = prices[SHY] / prices[SHY].shift(shy_window) - 1.0
    z = zscore(shy_cumret, z_window)
    # Inverse falsifier: stress on positive z (loose conditions).
    stress = (z.clip(lower=0.0) / max(entry_scale, 1e-9)).clip(0.0, 1.0)
    vscale = target_vol_scale(prices[SPY]) * (vol_target / TARGET_VOL_SCALE)
    exposure = (1.0 - stress) * vscale
    exposure = exposure.clip(lower=0.0)
    out = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    out[SPY] = exposure.fillna(0.0)
    return out.clip(-MAX_POS, MAX_POS)


def _slice(prices: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    idx = prices.index
    m = pd.Series(True, index=idx)
    if start is not None:
        m &= idx >= pd.Timestamp(start)
    if end is not None:
        m &= idx <= pd.Timestamp(end)
    return prices.loc[m]


def run_bt(prices: pd.DataFrame, signals: pd.DataFrame):
    cfg = BacktestConfig(
        initial_cash=1_000_000.0,
        max_position=MAX_POS,
        max_leverage=1.0,
        cost_model=CostModel(),
    )
    engine = BacktestEngine(config=cfg, settings=Settings(random_seed=42))
    aligned = signals.reindex(prices.index).fillna(0.0)
    return engine.run(prices, aligned)


def wf_train_sharpe(prices: pd.DataFrame, params: dict) -> float:
    train = _slice(prices, None, TRAIN_END)
    n = len(train)
    if n < 500:
        return -9.0
    fold = n // WF_FOLDS
    vals = []
    for i in range(WF_FOLDS):
        te = train.iloc[i * fold : n if i == WF_FOLDS - 1 else (i + 1) * fold]
        if len(te) < 120:
            continue
        sig = make_signals(te, **params)
        res = run_bt(te, sig)
        vals.append(sharpe(res.returns))
    return float(np.mean(vals)) if vals else -9.0


def perturbation_ratio(prices: pd.DataFrame, params: dict, selected_sharpe: float) -> float:
    oos = _slice(prices, "2020-01-01", None)
    if abs(selected_sharpe) < 1e-9:
        return 0.0
    ratios = []
    for key, deltas in [
        ("shy_window", [-1, 1]),
        ("z_window", [-1, 1]),
        ("entry_scale", [-0.2, 0.2]),
    ]:
        base = float(params[key])
        for d in deltas:
            p = dict(params)
            p[key] = type(params[key])(base + d)
            if key != "entry_scale":
                p[key] = int(max(5, p[key]))
            else:
                p[key] = float(max(0.2, p[key]))
            res = run_bt(oos, make_signals(oos, **p))
            s = sharpe(res.returns)
            ratios.append(min(s / selected_sharpe, 2.0))
    return float(np.min(ratios)) if ratios else 0.0


def main() -> None:
    t0 = time.time()
    prices = fetch_data()
    train = _slice(prices, None, TRAIN_END)
    val = _slice(prices, "2020-01-01", VAL_END)
    test = _slice(prices, "2023-01-01", None)
    oos = _slice(prices, "2020-01-01", None)

    rows = []
    for sw in GRID["shy_window"]:
        for zw in GRID["z_window"]:
            if zw < sw:
                continue
            for es in GRID["entry_scale"]:
                for vt in GRID["vol_target"]:
                    params = {
                        "shy_window": sw,
                        "z_window": zw,
                        "entry_scale": es,
                        "vol_target": vt,
                    }
                    wf = wf_train_sharpe(prices, params)
                    tr = run_bt(train, make_signals(train, **params))
                    rows.append(
                        {**params, "wf_train_sharpe": wf, "train_sharpe": sharpe(tr.returns)}
                    )

    grid = pd.DataFrame(rows).sort_values("wf_train_sharpe", ascending=False).reset_index(drop=True)
    best = grid.iloc[0][["shy_window", "z_window", "entry_scale", "vol_target"]].to_dict()
    best = {
        "shy_window": int(best["shy_window"]),
        "z_window": int(best["z_window"]),
        "entry_scale": float(best["entry_scale"]),
        "vol_target": float(best["vol_target"]),
    }

    oos_sig = make_signals(oos, **best)
    oos_res = run_bt(oos, oos_sig)
    oos_ret = oos_res.returns
    spy_oos_ret = oos[SPY].pct_change(fill_method=None).reindex(oos_ret.index).fillna(0.0)
    common = pd.concat([oos_ret.rename("strat"), spy_oos_ret.rename("spy")], axis=1).dropna()
    excess = common["strat"] - common["spy"]
    ir = (
        float(excess.mean() / excess.std(ddof=1) * np.sqrt(252))
        if float(excess.std(ddof=1)) > 1e-12
        else 0.0
    )
    ttest_p = (
        float(stats.ttest_1samp(excess.values, 0.0, alternative="greater").pvalue)
        if len(excess) > 20
        else 1.0
    )

    wf = float(best_row_wf(grid))
    worst = worst_regime_sharpe(oos_ret, oos[SPY])
    sel_oos_sharpe = sharpe(oos_ret)
    pert = perturbation_ratio(prices, best, sel_oos_sharpe)

    # ablations
    bh = oos[SPY].pct_change(fill_method=None).dropna()
    rng = np.random.default_rng(42)
    rand_exp = pd.Series(
        rng.uniform(0.0, oos_sig[SPY].max() if oos_sig[SPY].max() > 0 else 0.15, len(oos)),
        index=oos.index,
    )
    rand_sig = pd.DataFrame(0.0, index=oos.index, columns=oos.columns)
    rand_sig[SPY] = rand_exp
    rand_res = run_bt(oos, rand_sig)
    inv_res = run_bt(oos, make_signals_inverse(oos, **best))

    oos_met = {
        "sharpe": sharpe(oos_ret),
        "profit_factor": profit_factor(oos_ret),
        "max_drawdown": max_drawdown(oos_res.equity_curve),
        "trades": int(oos_res.trade_count),
        "wf_stability": wf / max(float(grid.iloc[0]["train_sharpe"]), 1e-9)
        if float(grid.iloc[0]["train_sharpe"]) > 0
        else 0.0,
        "worst_regime_sharpe": worst,
        "benchmark_p": ttest_p,
        "information_ratio": ir,
        "perturbation_min_ratio": pert,
    }
    # WF stability: OOS-like check vs train; use train sharpe of selected config
    sel_train = run_bt(train, make_signals(train, **best))
    sel_val = run_bt(val, make_signals(val, **best))
    sel_test = run_bt(test, make_signals(test, **best))
    tr_s = sharpe(sel_train.returns)
    oos_fold_s = sharpe(pd.concat([sel_val.returns, sel_test.returns]).dropna())
    oos_met["wf_stability"] = float(oos_fold_s / tr_s) if tr_s > 1e-9 else 0.0

    gates = {
        "sharpe>=1.0": oos_met["sharpe"] >= BENCH_GATES["min_sharpe"],
        "trades>=200": oos_met["trades"] >= BENCH_GATES["min_trades"],
        "profit_factor>=1.3": oos_met["profit_factor"] >= BENCH_GATES["min_pf"],
        "max_dd<=15%": abs(oos_met["max_drawdown"]) <= BENCH_GATES["max_dd"],
        "wf_stability>=0.7": oos_met["wf_stability"] >= BENCH_GATES["min_wf_stability"],
        "worst_regime_sharpe>=0.3": oos_met["worst_regime_sharpe"]
        >= BENCH_GATES["min_worst_regime_sharpe"],
        "benchmark_p<=0.05_IR>=0": (oos_met["benchmark_p"] <= BENCH_GATES["max_benchmark_p"])
        and (oos_met["information_ratio"] >= 0.0),
        "perturbation_min_ratio>=0.5": oos_met["perturbation_min_ratio"]
        >= BENCH_GATES["min_perturbation_ratio"],
    }
    passed = int(sum(gates.values()))
    verdict = f"REJECT {passed}/8" if passed < 8 else f"PASS {passed}/8"

    ablations = {
        "buy_hold_spy": {
            "sharpe": sharpe(bh),
            "pf": profit_factor(bh),
            "max_dd": max_drawdown((1 + bh).cumprod()),
            "trades": 1,
        },
        "random_exposure_matched": {
            "sharpe": sharpe(rand_res.returns),
            "pf": profit_factor(rand_res.returns),
            "max_dd": max_drawdown(rand_res.equity_curve),
            "trades": int(rand_res.trade_count),
        },
        "inverse_regime_tightness_falsifier": {
            "sharpe": sharpe(inv_res.returns),
            "pf": profit_factor(inv_res.returns),
            "max_dd": max_drawdown(inv_res.equity_curve),
            "trades": int(inv_res.trade_count),
        },
    }

    outdir = Path(".experiments/nf_runs/nf_20261108_17_short_rate_level")
    outdir.mkdir(parents=True, exist_ok=True)
    grid.to_csv(outdir / "grid.csv", index=False)
    summary = {
        "hypothesis": "H154",
        "nf_id": "NF-20261108-17",
        "verdict": verdict,
        "gates_passed": passed,
        "gates_total": 8,
        "gate_detail": gates,
        "oos_metrics": oos_met,
        "ablations": ablations,
        "best_params": best,
        "selected_train_sharpe": tr_s,
        "selection_criterion": "max train-only 4-fold walk-forward mean Sharpe",
        "data": {
            "source": "yfinance auto_adjust Close",
            "universe": UNIVERSE,
            "start": "2010-01-04",
            "end": "2025-01-03",
            "rows": int(len(prices)),
            "train_rows": int(len(train)),
            "val_rows": int(len(val)),
            "test_rows": int(len(test)),
        },
        "notes": [
            "NF-08-17 was a deferred/incomplete stub (docstring-only, unverified signal mapping); H154 completes it with verified mapping.",
            "^IRX not used (non-positive values in 2020). SHY used as clean short-rate level proxy.",
            "Pre-registered mapping: stress on negative SHY cumulative-return z (tight/high-rate proxy); inverse falsifier stresses positive z.",
            "Repo-relative novelty honest: short-rate LEVEL vs H141 TLT-SHY spread momentum; rates-domain adjacency disclosed.",
            "src/qtr unchanged; no gate weakening; no published/certified artifact modified.",
        ],
        "runtime_sec": round(time.time() - t0, 2),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    meta = {
        "universe": UNIVERSE,
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "rows": int(len(prices)),
        "train": int(train.index <= pd.Timestamp(TRAIN_END)).sum()
        if hasattr(train.index, "__len__")
        else int(len(train)),
        "val": int(len(val)),
        "test": int(len(test)),
        "signal_mapping": "stress on negative z of SHY trailing cumulative return (tight/high-rate proxy)",
    }
    (outdir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": f"{passed}/{len(gates)}", "oos": oos_met, "best": best},
            indent=2,
            default=str,
        )
    )


def best_row_wf(grid: pd.DataFrame) -> float:
    return float(grid.iloc[0]["wf_train_sharpe"])


if __name__ == "__main__":
    main()
