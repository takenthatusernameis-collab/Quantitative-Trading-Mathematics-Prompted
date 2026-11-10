"""NF-20261105-15 / H96 (pre-registered): Equity-bond return-correlation regime timing.

Trailing rolling correlation of SPY vs TLT daily returns proxies a
diversification/correlation regime: low trailing correlation (diversification
intact, risk persistence) -> vol-targeted long SPY; high trailing correlation
(diversification breakdown / risk-off co-movement) -> flat. Hysteresis plus a
1-bar execution delay keeps the design strictly causal; evaluated net of costs
on OOS Val+Test.

New family dimension (cross-asset diversification / correlation-regime risk
premium), distinct from:
- H92 equity/bond relative momentum (SPY-vs-TLT relative cumulative return,
  first-moment level, REJECTED 3/9). H96 uses rolling *correlation* (second
  moment / co-movement), a different observable and causal path
  (diversification breakdown vs relative performance).
- H86 VIX term-structure slope and H89 SKEW tail-risk (vol-surface signals on
  SPY only).
- H94 credit flight-to-quality (HYG-IEF credit/default-risk channel on SPY).
No prior repository family uses SPY-TLT return correlation as the timing
observable.

Causality / timing (pre-registered): corr[t] uses only SPY/TLT returns through
close t; z[t] uses only corr through t; the engine applies signals.shift(1), so
the target set at close t earns the return t -> t+1 -- no same-day look-ahead.

Data: yfinance daily SPY + TLT (free, cached), 2010-01-01 -> 2026-10-31.
Splits: Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout, final ~32%).
Grid: lookback {63,126,252} x entry_z {1.0,1.5,2.0} x exit_z {0.0,0.5} x
vol_target {0.10,0.15} (36 combos). Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1%
ADV). Turnover low (slow-moving correlation signal).

Gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe>=1.0, >=200 trades,
PF>=1.3, max DD<=15%, WF stability test>=0.7*train when train>0, worst-regime
rolling-252 Sharpe>=0.3, benchmark p<=0.05 vs buy-hold SPY, IR>=0,
perturbation min ratio>=0.5.
Rejection: OOS Sharpe<0.5, PF<1.1, max DD>15%, <200 trades.
"""

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

EXPERIMENT_NAME = "nf_20261105_15_corr_regime"
EXPERIMENT_DESC = (
    "NF-20261105-15/H96: equity-bond return-correlation regime timing. "
    "Vol-targeted long SPY when trailing SPY-TLT return correlation z-score is "
    "below exit_z (diversification regime), flat when at/above entry_z "
    "(high-correlation risk-off), with hysteresis and 1-bar execution delay. "
    "Grid search on Train/WF; Test protected; gates on OOS Val+Test."
)

SPY = "SPY"
TLT = "TLT"
UNIVERSE = [SPY, TLT]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
ZSCORE_WINDOW = 252

LOOKBACKS = [63, 126, 252]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

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


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    sr = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    if len(prices.index[mask]) == 0:
        return 0
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def build_corr_regime_targets(
    prices: pd.DataFrame,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    """Vol-targeted SPY targets from trailing SPY-TLT correlation z-score.

    corr[t] = rolling correlation of daily SPY vs TLT returns over lookback bars
    ending at close t (past-only). z[t] = rolling z-score of corr over
    ZSCORE_WINDOW (past-only, min_periods=lookback).
    Position: long SPY when z <= exit_z (low correlation / diversification
    intact); flat when z >= entry_z (high correlation / risk-off co-movement);
    hold (hysteresis) when exit_z < z < entry_z. Engine applies signals.shift(1):
    target at close t earns return t -> t+1. No same-day look-ahead.
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SPY])
    if SPY not in prices.columns or TLT not in prices.columns:
        return targets
    lookback = int(max(2, lookback))
    entry_z = float(entry_z)
    exit_z = float(exit_z)
    vol_target = float(max(0.01, vol_target))

    spy_ret = prices[SPY].astype(float).pct_change()
    tlt_ret = prices[TLT].astype(float).pct_change()
    corr = spy_ret.rolling(lookback).corr(tlt_ret)
    mu = corr.rolling(ZSCORE_WINDOW, min_periods=lookback).mean()
    sd = corr.rolling(ZSCORE_WINDOW, min_periods=lookback).std()
    z = (corr - mu) / sd.replace(0, np.nan)

    # Hysteresis: high correlation (z >= entry_z) -> flat; low correlation
    # (z <= exit_z) -> long. Between thresholds: hold previous state.
    state = pd.Series(np.nan, index=idx, dtype=float)
    state[z >= entry_z] = 0.0
    state[z <= exit_z] = 1.0
    side = state.ffill().fillna(0.0)
    side = side.where(z.notna(), 0.0)

    realized = prices[SPY].astype(float).pct_change().rolling(21, min_periods=21).std() * np.sqrt(
        252
    )
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
    targets[SPY] = (side * scale).clip(0.0, MAX_POS)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask, n_splits=WF_FOLDS_SELECTION) -> float:
    train_r = returns[train_mask].dropna()
    if len(train_r) < 120:
        return 0.0
    try:
        splits = walk_forward_splits(len(train_r), n_splits=n_splits)
    except Exception:
        return 0.0
    sharpes = []
    for _, te_idx in splits:
        r = train_r.iloc[te_idx].dropna()
        if len(r) > 20:
            sharpes.append(float(sharpe_ratio(r.values)))
    return float(np.mean(sharpes)) if sharpes else 0.0


def _stability_test_vs_train(train_sharpe: float, test_sharpe: float) -> float:
    if train_sharpe > 0:
        return test_sharpe / train_sharpe
    if train_sharpe == 0:
        return test_sharpe
    return 0.0


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result):
    rets = result.returns
    oos_r = rets[oos_mask].dropna()
    train_r = rets[prices.index <= pd.Timestamp(TRAIN_END)].dropna()
    val_r = rets[val_mask].dropna()
    test_r = rets[test_mask].dropna()

    oos_m = _period_metrics(oos_r, _count_in(result.trades, oos_mask, prices))
    train_m = _period_metrics(
        train_r, _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices)
    )
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))
    wf_stab = _stability_test_vs_train(train_m["sharpe"], test_m["sharpe"])

    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

    if len(oos_r) >= 252:
        roll = oos_r.rolling(252).apply(lambda x: sharpe_ratio(x.values), raw=False)
        worst_regime = float(roll.min()) if roll.notna().any() else 0.0
    else:
        worst_regime = oos_m["sharpe"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "p_value": benchmark_significance_gate(bench_p, ir, GATES["max_p_value"]),
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    return {
        "oos_metrics": oos_m,
        "train_sharpe": train_m["sharpe"],
        "val_sharpe": float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0,
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "worst_regime_sharpe": worst_regime,
        "benchmark_p": bench_p,
        "information_ratio": ir,
        "passes": passes,
        "gate_pass_count": sum(passes.values()),
    }


def main() -> int:
    t0 = time.time()
    run_dir = Path(".experiments") / "nf_runs" / EXPERIMENT_NAME
    run_dir.mkdir(parents=True, exist_ok=True)
    cache = DataCache(cache_dir=run_dir / "cache")
    fetcher = DataFetcher(cache=cache)
    raw = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")

    def _close(df):
        c = df.get("adj_close") if "adj_close" in df.columns else df.get("close")
        if c is None:
            c = df.get("Close")
        if c is None:
            raise KeyError(f"no close column: {df.columns.tolist()}")
        return c.astype(float)

    prices = pd.DataFrame({sym: _close(df) for sym, df in raw.items()}).sort_index()
    prices = prices.ffill().dropna(how="all")

    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    bench_pos = pd.DataFrame({SPY: 1.0}, index=prices.index)
    bench_result = run_backtest(prices[[SPY]], bench_pos, make_equity_config())

    grid = [
        (lb, ez, xz, vt)
        for lb in LOOKBACKS
        for ez in ENTRY_ZS
        for xz in EXIT_ZS
        for vt in VOL_TARGETS
    ]
    rows = []
    best = None
    for lookback, entry_z, exit_z, vol_target in grid:
        pos = build_corr_regime_targets(prices, lookback, entry_z, exit_z, vol_target)
        res = run_backtest(prices[[SPY]], pos[[SPY]], make_equity_config())
        sel = train_only_wf_sharpe(res.returns, train_mask)
        row = {
            "lookback": lookback,
            "entry_z": entry_z,
            "exit_z": exit_z,
            "vol_target": vol_target,
            "train_wf_sharpe": sel,
        }
        rows.append(row)
        if best is None or sel > best[0]:
            best = (sel, row, res)

    if best is None:
        raise RuntimeError("no grid results")
    _, best_row, best_res = best
    gate = full_gate_eval(best_res, oos_mask, val_mask, test_mask, prices, bench_result)

    pert_rows = []
    for lb in sorted({max(2, int(round(best_row["lookback"] * m))) for m in [0.8, 1.2]}):
        pos = build_corr_regime_targets(
            prices, lb, best_row["entry_z"], best_row["exit_z"], best_row["vol_target"]
        )
        res = run_backtest(prices[[SPY]], pos[[SPY]], make_equity_config())
        pm = _period_metrics(
            res.returns[oos_mask].dropna(), _count_in(res.trades, oos_mask, prices)
        )
        pert_rows.append({"lookback": lb, **pm})
    for ez in sorted({round(best_row["entry_z"] * m, 4) for m in [0.8, 1.2]}):
        pos = build_corr_regime_targets(
            prices, best_row["lookback"], ez, best_row["exit_z"], best_row["vol_target"]
        )
        res = run_backtest(prices[[SPY]], pos[[SPY]], make_equity_config())
        pm = _period_metrics(
            res.returns[oos_mask].dropna(), _count_in(res.trades, oos_mask, prices)
        )
        pert_rows.append({"entry_z": ez, **pm})
    for xz in sorted({round(best_row["exit_z"] * m, 4) for m in [0.8, 1.2]}):
        pos = build_corr_regime_targets(
            prices, best_row["lookback"], best_row["entry_z"], xz, best_row["vol_target"]
        )
        res = run_backtest(prices[[SPY]], pos[[SPY]], make_equity_config())
        pm = _period_metrics(
            res.returns[oos_mask].dropna(), _count_in(res.trades, oos_mask, prices)
        )
        pert_rows.append({"exit_z": xz, **pm})
    for vt in sorted({round(best_row["vol_target"] * m, 4) for m in [0.8, 1.2]}):
        pos = build_corr_regime_targets(
            prices, best_row["lookback"], best_row["entry_z"], best_row["exit_z"], vt
        )
        res = run_backtest(prices[[SPY]], pos[[SPY]], make_equity_config())
        pm = _period_metrics(
            res.returns[oos_mask].dropna(), _count_in(res.trades, oos_mask, prices)
        )
        pert_rows.append({"vol_target": vt, **pm})
    opt_sr = gate["oos_metrics"]["sharpe"]
    pert_sharpes = [r["sharpe"] for r in pert_rows]
    min_ratio = (min(pert_sharpes) / opt_sr) if (opt_sr > 0 and pert_sharpes) else 0.0
    gate["passes"]["perturbation"] = min_ratio >= GATES["min_perturbed_sharpe_ratio"]
    gate["gate_pass_count"] = sum(gate["passes"].values())
    gate["perturbation"] = {"rows": pert_rows, "min_sharpe_ratio": min_ratio}

    rng = np.random.default_rng(SEED)
    active = (best_res.positions.abs().sum(axis=1) > 0).astype(float)
    rand_side = pd.Series(
        rng.choice([0.0, 1.0], size=len(prices), p=[0.5, 0.5]), index=prices.index
    )
    rand_pos = pd.DataFrame({SPY: active * rand_side}, index=prices.index)
    rand_res = run_backtest(prices[[SPY]], rand_pos, make_equity_config())
    rand_m = _period_metrics(
        rand_res.returns[oos_mask].dropna(), _count_in(rand_res.trades, oos_mask, prices)
    )
    bench_m = _period_metrics(
        bench_result.returns[oos_mask].dropna(), _count_in(bench_result.trades, oos_mask, prices)
    )
    gate["ablations"] = {"random_exposure_matched": rand_m, "buy_hold_spy": bench_m}

    # Inverse-signal falsifier: long SPY when correlation high (z >= entry_z).
    inv_pos = pd.DataFrame(0.0, index=prices.index, columns=[SPY])
    if SPY in prices.columns and TLT in prices.columns:
        spy_ret = prices[SPY].astype(float).pct_change()
        tlt_ret = prices[TLT].astype(float).pct_change()
        corr = spy_ret.rolling(best_row["lookback"]).corr(tlt_ret)
        mu = corr.rolling(ZSCORE_WINDOW, min_periods=best_row["lookback"]).mean()
        sd = corr.rolling(ZSCORE_WINDOW, min_periods=best_row["lookback"]).std()
        z = (corr - mu) / sd.replace(0, np.nan)
        realized = prices[SPY].astype(float).pct_change().rolling(
            21, min_periods=21
        ).std() * np.sqrt(252)
        scale = (
            (best_row["vol_target"] / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
        )
        inv_side = (z >= best_row["entry_z"]).astype(float)
        inv_side = inv_side.where(z.notna(), 0.0)
        inv_pos[SPY] = (inv_side * scale).clip(0.0, MAX_POS)
    inv_res = run_backtest(prices[[SPY]], inv_pos[[SPY]], make_equity_config())
    inv_m = _period_metrics(
        inv_res.returns[oos_mask].dropna(), _count_in(inv_res.trades, oos_mask, prices)
    )
    gate["ablations"]["inverse_high_corr_long"] = inv_m

    verdict = "PASS" if gate["gate_pass_count"] == len(gate["passes"]) else "REJECT"
    summary = {
        "experiment": EXPERIMENT_NAME,
        "hypothesis": "H96/NF-20261105-15 equity-bond return-correlation regime timing",
        "seed": SEED,
        "data": {
            "start": DATA_START,
            "end": DATA_END,
            "symbols": UNIVERSE,
            "rows": int(len(prices)),
        },
        "splits": {"train_end": TRAIN_END, "val_end": VAL_END},
        "grid_rows": len(grid),
        "selected": best_row,
        "gate_eval_oos_val_test": gate,
        "verdict": verdict,
        "duration_seconds": round(time.time() - t0, 3),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")

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
    tracker.log_artifact("summary", run_dir / "summary.json")
    tracker.finish_experiment(status="completed")
    print(
        json.dumps(
            {"exp_id": exp_id, "verdict": verdict, "summary": str(run_dir / "summary.json")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
