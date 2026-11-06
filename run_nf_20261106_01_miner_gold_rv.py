"""NF-20261106-01 / H99 (pre-registered): Gold-miner vs gold real-optionality spread
mean-reversion timing.

Mechanism (relative value / producer real-optionality spread): gold miners (GDX)
carry operating leverage and real optionality on the gold price, so the trailing
GDX/GLD return or level spread can become stretched by risk, cost, or sentiment
shocks and mean-revert as the miner-bullion linkage reasserts. A long GDX
position is taken (vol-targeted) when the trailing log(GDX/GLD) spread z-score is
low (miners cheap vs gold / spread depressed), flat when the z-score is high
(miners rich vs gold / spread elevated), with hysteresis and 1-bar execution
delay.

New family dimension (producer real-optionality / miner-bullion spread
convergence), distinct from:
- H88 commodity pair relative-value mean reversion (GLD/SLV/DXY proxy; rejected).
  H99 uses a different economic mechanism/observable: miner operating
  leverage/equity optionality vs bullion, not a pure commodity/FX proxy pair.
- H92 equity/bond relative momentum (first-moment cross-asset momentum, SPY/TLT).
- H96 equity-bond return-correlation regime (second-moment co-movement).
- H97 equity concentration RV (SPY/RSP capitalization-concentration spread).
- H2/H16 cross-sectional own-return momentum (equity-only ranking).

Causality / timing (pre-registered): spread and z-score at close t use prices
through close t only (trailing windows, past-only). The engine applies
signals.shift(1), so the target set at close t earns return t -> t+1 — no
same-day look-ahead.

Data: yfinance daily GDX + GLD (free, cached), 2012-01-01 -> 2026-10-31.
Splits: Train 2012-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout).
Grid: lookback in {60,126,252} x entry_z in {1.0,1.5,2.0} x
exit_z in {0.0,0.5} x vol_target in {0.08,0.12} (36 combos). Selection = best
train-only 4-fold walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1% ADV).
Turnover moderate (slow-moving spread).

Gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe>=1.0, >=200 trades,
PF>=1.3, max DD<=15%, WF stability test>=0.7*train when train>0, worst-regime
rolling-252 Sharpe>=0.3, benchmark p<=0.05 vs buy-hold GDX, IR>=0, perturbation
min ratio>=0.5.
Rejection: OOS Sharpe<0.5, PF<1.1, max DD>15%, <200 trades.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261106_01_miner_gold_rv"
EXPERIMENT_DESC = (
    "NF-20261106-01/H99: gold-miner vs gold real-optionality spread mean-reversion "
    "timing. Long GDX vol-targeted when trailing log(GDX/GLD) spread z-score is low "
    "(miners cheap vs gold), flat when high (miners rich), hysteresis + 1-bar delay. "
    "Net of costs on OOS Val+Test."
)

TRADE_SYM = "GDX"
SIGNAL_SYM = "GLD"
UNIVERSE = [TRADE_SYM, SIGNAL_SYM]
DATA_START = "2012-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

LOOKBACKS = [60, 126, 252]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5]
VOL_TARGETS = [0.08, 0.12]
WF_FOLDS_SELECTION = 4
SEED = 42
MAX_POS = 0.5

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


def make_equity_config(allow_short: bool = False) -> BacktestConfig:
    return BacktestConfig(
        initial_capital=1_000_000.0,
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(
            equity_commission_bps=1.0,
            equity_spread_bps=0.5,
            equity_impact_bps_per_pct_adv=0.1,
        ),
        allow_short=allow_short,
        max_leverage=1.0,
        max_position_size=MAX_POS,
    )


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    minp = max(20, window // 2)
    mu = series.rolling(window, min_periods=minp).mean()
    sd = series.rolling(window, min_periods=minp).std(ddof=0)
    return (series - mu) / sd.replace(0.0, np.nan)


def build_miner_gold_targets(
    prices: pd.DataFrame,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    """Long GDX vol-targeted when log(GDX/GLD) z-score <= exit_z (miners cheap),
    flat when z >= entry_z (miners rich vs gold); hold (hysteresis) between."""
    if TRADE_SYM not in prices.columns or SIGNAL_SYM not in prices.columns:
        return pd.DataFrame({TRADE_SYM: 0.0}, index=prices.index)

    gdx = prices[TRADE_SYM].astype(float)
    gld = prices[SIGNAL_SYM].astype(float)
    spread = np.log(gdx / gld.replace(0.0, np.nan))
    z = _rolling_zscore(spread, lookback)

    ret = gdx.pct_change().replace([np.inf, -np.inf], np.nan)
    vol = ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252)
    raw = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, MAX_POS)

    pos = pd.Series(np.nan, index=prices.index, dtype=float)
    for i in range(len(prices)):
        zi = z.iat[i]
        if np.isnan(zi):
            pos.iat[i] = 0.0
            continue
        prev = pos.iat[i - 1] if i > 0 and not np.isnan(pos.iat[i - 1]) else 0.0
        if zi >= entry_z:
            pos.iat[i] = 0.0
        elif zi <= exit_z:
            ri = raw.iat[i]
            pos.iat[i] = float(ri) if not np.isnan(ri) else 0.0
        else:
            pos.iat[i] = prev

    return pd.DataFrame({TRADE_SYM: pos.fillna(0.0)}, index=prices.index)


def run_one(prices: pd.DataFrame, targets: pd.DataFrame):
    trade = prices[[TRADE_SYM]].copy()
    tgt = targets[[TRADE_SYM]].reindex(trade.index).fillna(0.0)
    cfg = make_equity_config(allow_short=False)
    return run_backtest(trade, tgt, config=cfg)


def compute_metrics(equity: pd.Series) -> dict:
    if equity is None or equity.empty:
        return {
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
            "total_return": 0.0,
        }
    rets = equity.pct_change().dropna()
    sharpe = float(sharpe_ratio(rets.values)) if len(rets) > 1 else 0.0
    gains = rets[rets > 0].sum()
    losses = abs(rets[rets < 0].sum())
    pf = float(gains / losses) if losses > 1e-12 else (10.0 if gains > 0 else 0.0)
    cummax = equity.cummax()
    dd = float(((equity - cummax) / cummax.replace(0.0, np.nan)).min())
    nz = (rets != 0).sum()
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if equity.iloc[0] else 0.0
    return {
        "sharpe": sharpe,
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": int(nz),
        "total_return": total,
    }


def worst_regime_sharpe(equity: pd.Series, window: int = 252) -> float:
    rets = equity.pct_change().dropna()
    if len(rets) < window:
        return float(sharpe_ratio(rets.values)) if len(rets) > 1 else 0.0
    roll = rets.rolling(window).apply(
        lambda x: sharpe_ratio(x.values) if len(x) > 1 else 0.0, raw=False
    )
    return float(roll.min())


def walkforward_sharpes(prices: pd.DataFrame, params: dict, n_folds: int = 4) -> list[float]:
    sharpes: list[float] = []
    for tr_idx, te_idx in walk_forward_splits(prices.index, n_folds=n_folds):
        tr_p = prices.iloc[tr_idx]
        te_p = prices.iloc[te_idx]
        full_p = pd.concat([tr_p, te_p])
        tgt = build_miner_gold_targets(full_p, **params)
        te_tgt = tgt.loc[te_p.index]
        eq = run_one(te_p, te_tgt)["equity"]
        sharpes.append(compute_metrics(eq)["sharpe"])
    return sharpes


def select_best_on_train(train_prices: pd.DataFrame) -> tuple[dict, float, list[dict]]:
    grid = []
    for lb in LOOKBACKS:
        for ez in ENTRY_ZS:
            for xz in EXIT_ZS:
                for vt in VOL_TARGETS:
                    if xz > ez:
                        continue
                    grid.append({"lookback": lb, "entry_z": ez, "exit_z": xz, "vol_target": vt})
    rows = []
    for p in grid:
        wf = walkforward_sharpes(train_prices, p, n_folds=WF_FOLDS_SELECTION)
        mean_wf = float(np.mean(wf)) if wf else 0.0
        tgt = build_miner_gold_targets(train_prices, **p)
        eq = run_one(train_prices, tgt)["equity"]
        m = compute_metrics(eq)
        rows.append({"params": p, "wf_sharpes": wf, "mean_wf_sharpe": mean_wf, **m})
    rows.sort(key=lambda r: r["mean_wf_sharpe"], reverse=True)
    best = rows[0]["params"]
    return best, rows[0]["mean_wf_sharpe"], rows


def compute_gate(
    train_prices: pd.DataFrame,
    oos_prices: pd.DataFrame,
    best: dict,
    oos_equity: pd.Series,
) -> dict:
    oos_m = compute_metrics(oos_equity)
    train_tgt = build_miner_gold_targets(train_prices, **best)
    train_eq = run_one(train_prices, train_tgt)["equity"]
    train_sharpe = compute_metrics(train_eq)["sharpe"]
    test_wf = walkforward_sharpes(oos_prices, best, n_folds=WF_FOLDS_SELECTION)
    test_wf_mean = float(np.mean(test_wf)) if test_wf else 0.0
    wf_stab = (
        test_wf_mean / train_sharpe if train_sharpe > 1e-9 else (1.0 if test_wf_mean >= 0 else 0.0)
    )
    bench = oos_prices[[TRADE_SYM]].pct_change().dropna()[TRADE_SYM]
    strat = oos_equity.pct_change().dropna()
    aligned = pd.concat([strat.rename("s"), bench.rename("b")], axis=1).dropna()
    cmp = (
        compare_to_benchmark(aligned["s"].values, aligned["b"].values) if len(aligned) > 30 else {}
    )
    bench_p = float(cmp.get("alpha_p_value", 1.0))
    ir = float(cmp.get("information_ratio", 0.0))
    worst_regime = worst_regime_sharpe(oos_equity)
    gate = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "p_value": benchmark_significance_gate(bench_p, ir, max_p_value=GATES["max_p_value"]),
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    return {
        "gate": gate,
        "gate_pass_count": int(sum(gate.values())),
        "gate_count": len(gate),
        "oos_metrics": oos_m,
        "train_sharpe": train_sharpe,
        "test_wf_sharpes": test_wf,
        "test_wf_mean": test_wf_mean,
        "walkforward_stability": wf_stab,
        "benchmark_p": bench_p,
        "information_ratio": ir,
        "worst_regime_sharpe": worst_regime,
    }


def perturbation_eval(oos_prices: pd.DataFrame, best: dict) -> dict:
    def _perturb_num(v, frac=0.2):
        if isinstance(v, bool):
            return [v]
        if isinstance(v, int):
            lo = max(1, int(round(v * (1 - frac))))
            hi = max(lo, int(round(v * (1 + frac))))
            return sorted({lo, v, hi})
        if isinstance(v, float):
            lo = round(v * (1 - frac), 10)
            hi = round(v * (1 + frac), 10)
            return sorted({lo, v, hi})
        return [v]

    keys = list(best.keys())
    rows = []
    for k in keys:
        for v in _perturb_num(best[k]):
            p = dict(best)
            p[k] = v
            if p.get("exit_z", 0.0) > p.get("entry_z", 0.0):
                continue
            eq = run_one(oos_prices, build_miner_gold_targets(oos_prices, **p))["equity"]
            rows.append({"perturbed": p, "sharpe": compute_metrics(eq)["sharpe"]})
    base_eq = run_one(oos_prices, build_miner_gold_targets(oos_prices, **best))["equity"]
    base = compute_metrics(base_eq)["sharpe"]
    min_ratio = min((r["sharpe"] / base) if abs(base) > 1e-9 else 0.0 for r in rows)
    return {
        "base_sharpe": base,
        "min_perturbed_sharpe_ratio": float(min_ratio),
        "rows": rows,
    }


def ablation_random_exposure(oos_prices: pd.DataFrame, base_targets: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SEED)
    vals = base_targets[TRADE_SYM].values.copy()
    nz_idx = np.where(np.abs(vals) > 1e-12)[0]
    n_on = len(nz_idx)
    rand = np.zeros(len(vals))
    if n_on > 0:
        chosen = rng.choice(len(vals), size=n_on, replace=False)
        nz_vals = vals[nz_idx]
        rand[chosen] = rng.permutation(nz_vals)
    rand_tgt = pd.DataFrame({TRADE_SYM: rand}, index=oos_prices.index)
    eq = run_one(oos_prices, rand_tgt)["equity"]
    return {"label": "random_exposure_matched", **compute_metrics(eq)}


def ablation_inverse_signal(oos_prices: pd.DataFrame, best: dict) -> dict:
    """Long GDX when miners rich vs gold (inverse) — falsifier for direction."""
    if TRADE_SYM not in oos_prices.columns or SIGNAL_SYM not in oos_prices.columns:
        return {"label": "inverse_signal", "sharpe": 0.0}
    gdx = oos_prices[TRADE_SYM].astype(float)
    gld = oos_prices[SIGNAL_SYM].astype(float)
    spread = np.log(gdx / gld.replace(0.0, np.nan))
    z = _rolling_zscore(spread, best["lookback"])
    ret = gdx.pct_change().replace([np.inf, -np.inf], np.nan)
    vol = ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252)
    raw = (best["vol_target"] / vol.replace(0.0, np.nan)).clip(0.0, MAX_POS)
    pos = pd.Series(np.nan, index=oos_prices.index, dtype=float)
    entry_z, exit_z = best["entry_z"], best["exit_z"]
    for i in range(len(oos_prices)):
        zi = z.iat[i]
        if np.isnan(zi):
            pos.iat[i] = 0.0
            continue
        prev = pos.iat[i - 1] if i > 0 and not np.isnan(pos.iat[i - 1]) else 0.0
        # inverse: long when rich (high z), flat when cheap (low z)
        if zi <= -entry_z:
            pos.iat[i] = 0.0
        elif zi >= -exit_z:
            ri = raw.iat[i]
            pos.iat[i] = float(ri) if not np.isnan(ri) else 0.0
        else:
            pos.iat[i] = prev
    tgt = pd.DataFrame({TRADE_SYM: pos.fillna(0.0)}, index=oos_prices.index)
    eq = run_one(oos_prices, tgt)["equity"]
    return {"label": "inverse_signal_miners_rich", **compute_metrics(eq)}


def main() -> int:
    t0 = time.time()
    out_dir = Path(".experiments") / "nf_runs" / EXPERIMENT_NAME
    out_dir.mkdir(parents=True, exist=True)

    cache = DataCache(cache_dir=".data_cache", max_age_hours=24 * 365)
    fetcher = DataFetcher(cache=cache)
    panel = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END)
    prices = panel.close.copy()
    nonpos = int((prices <= 0).sum().sum())
    prices = prices[(prices > 0).all(axis=1)].dropna()

    train = prices.loc[:TRAIN_END]
    val = prices.loc[TRAIN_END:VAL_END].iloc[1:]
    test = prices.loc[VAL_END:].iloc[1:]
    oos = pd.concat([val, test])

    best, best_wf, grid_rows = select_best_on_train(train)
    oos_tgt = build_miner_gold_targets(oos, **best)
    oos_res = run_one(oos, oos_tgt)
    val_tgt = build_miner_gold_targets(pd.concat([train, val]), **best).loc[val.index]
    val_eq = run_one(val, val_tgt)["equity"]
    test_tgt = build_miner_gold_targets(pd.concat([train, val, test]), **best).loc[test.index]
    test_eq = run_one(test, test_tgt)["equity"]
    gate = compute_gate(train, oos, best, oos_res["equity"])
    perturb = perturbation_eval(oos, best)

    ablations = [
        ablation_random_exposure(oos, oos_tgt),
        ablation_inverse_signal(oos, best),
        {
            "label": "buy_hold_gdx",
            **compute_metrics((1 + oos[TRADE_SYM].pct_change().fillna(0)).cumprod() * 1_000_000),
        },
    ]

    bench = oos[TRADE_SYM].pct_change().dropna()
    strat = oos_res["equity"].pct_change().dropna()
    aligned = pd.concat([strat.rename("s"), bench.rename("b")], axis=1).dropna()
    cmp = (
        compare_to_benchmark(aligned["s"].values, aligned["b"].values) if len(aligned) > 30 else {}
    )
    gate["benchmark_comparison"] = {
        k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in cmp.items()
    }

    gate["perturbation"] = {
        "base_sharpe": perturb["base_sharpe"],
        "min_perturbed_sharpe_ratio": perturb["min_perturbed_sharpe_ratio"],
        "pass": perturb["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"],
    }
    gate["gate"]["perturbation"] = gate["perturbation"]["pass"]
    gate["gate_pass_count"] = int(sum(gate["gate"].values()))
    gate["gate_count"] = len(gate["gate"])

    verdict = "PROMOTE" if gate["gate_pass_count"] == gate["gate_count"] else "REJECT"
    reject_reasons = [k for k, v in gate["gate"].items() if not v]

    summary = {
        "experiment": EXPERIMENT_NAME,
        "hypothesis": "H99",
        "family": "NF-20261106-01",
        "mechanism": "gold-miner vs gold real-optionality spread mean-reversion timing (GDX/GLD log spread z-score, long GDX vol-targeted)",
        "verdict": verdict,
        "reject_reasons": reject_reasons,
        "data": {
            "source": "yfinance",
            "universe": UNIVERSE,
            "start": DATA_START,
            "end": DATA_END,
            "rows": int(len(prices)),
            "non_positive_rows_dropped": nonpos,
            "train_rows": int(len(train)),
            "val_rows": int(len(val)),
            "test_rows": int(len(test)),
        },
        "selection": {
            "method": "train-only 4-fold walk-forward Sharpe",
            "best_params": best,
            "best_train_wf_sharpe": best_wf,
            "grid_size": len(grid_rows),
        },
        "gate_result": gate,
        "perturbation_detail_count": len(perturb["rows"]),
        "subperiod_oos": {
            "val_metrics": compute_metrics(val_eq),
            "test_metrics": compute_metrics(test_eq),
        },
        "ablations": ablations,
        "gates": GATES,
        "runtime_sec": round(time.time() - t0, 2),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")

    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "lookbacks": LOOKBACKS,
            "entry_zs": ENTRY_ZS,
            "exit_zs": EXIT_ZS,
            "vol_targets": VOL_TARGETS,
            "wf_folds": WF_FOLDS_SELECTION,
            "seed": SEED,
        },
        data_sources=[f"yfinance:{s}" for s in UNIVERSE],
        compute_budget="<=2 CPU-h (expected << 1 min)",
        random_seeds=[SEED],
    )
    tracker.log_metrics(
        {
            "oos_sharpe": gate["oos_metrics"]["sharpe"],
            "oos_profit_factor": gate["oos_metrics"]["profit_factor"],
            "oos_max_drawdown": gate["oos_metrics"]["max_drawdown"],
            "oos_trades": float(gate["oos_metrics"]["trades"]),
            "gate_pass_count": float(gate["gate_pass_count"]),
        }
    )
    tracker.log_artifact("summary", out_dir / "summary.json")
    tracker.finish_experiment(status="completed")
    print(
        json.dumps(
            {"exp_id": exp_id, "verdict": verdict, "summary": str(out_dir / "summary.json")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
