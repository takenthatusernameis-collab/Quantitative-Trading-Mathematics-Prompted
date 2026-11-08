"""NF-20261107-03 / H120 (pre-registered, Cycle 34): SPY short-term time-series
return reversal (single-asset contrarian / overreaction correction).

Signal = SPY trailing `lookback`-day cumulative return (past-only, known at
close). Go vol-targeted long SPY when cumulative return < -threshold (recent
weakness / oversold, contrarian buy); flat otherwise. Optional hysteresis exit
at -exit_threshold (defaults to 0). Engine `signals.shift(1)` gives t->t+1
causality. Weekly-style turnover is naturally bounded by signal persistence but
not forced by a fixed rebalance calendar; trades/costs reported.

Distinct from H119 (NF-20261107-02, REJECT 3/8): H119 trades a 9-sector
cross-sectional *portfolio* ranked by relative weakness (weakest tercile,
multi-asset allocation, relative rank). H120 trades *SPY alone* conditioned on
SPY's own absolute trailing return (single instrument, no cross-sectional rank).
Distinct from H1/H4/H8/H9 TSMOM families (momentum/trend persistence, opposite
predictive direction) and from H87 opening-gap fill (overnight gap observable).
SPY daily adjusted close 2010-01-04..2026-10-30, 4233 rows, 0 non-positive via
DataFetcher/cache. No src/qtr change.
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
from qtr.data.fetcher import DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261107_03_spy_ts_reversal"
EXPERIMENT_DESC = (
    "NF-20261107-03/H120: SPY short-term time-series return reversal. "
    "Vol-targeted long SPY when trailing cumulative return indicates recent "
    "weakness (contrarian), flat otherwise. Train-only WF selection; "
    "Test protected; OOS gates vs buy-hold SPY benchmark."
)

SPY = "SPY"
UNIVERSE = [SPY]
BENCHMARK = SPY

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
MAX_LEVERAGE = 1.0

LOOKBACKS = [2, 3, 5]
ENTRY_THRS = [-0.005, -0.01, -0.02]  # enter long when cumret < threshold
EXIT_THRS = [0.0, -0.005]  # exit (flat) when cumret >= exit_threshold
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4
VOL_WINDOW = 63
VOL_MIN_PERIODS = 21

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
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )


def _align_prices(fetcher: DataFetcher, symbols, start: str, end: str) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    frames = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "adj_close"
            if "adj_close" in df.columns
            else (
                "close"
                if "close" in df.columns
                else ("Close" if "Close" in df.columns else df.columns[0])
            )
        )
        c = df[col].astype(float)
        if (c <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        frames[s] = c.rename(s)
    prices = pd.concat(frames.values(), axis=1).dropna()
    if len(prices) < 500:
        raise RuntimeError(f"Too few aligned rows: {len(prices)}")
    return prices


def _mask(idx: pd.DatetimeIndex, start: str | None, end: str | None) -> pd.Series:
    m = pd.Series(True, index=idx)
    if start:
        m &= idx >= pd.Timestamp(start)
    if end:
        m &= idx <= pd.Timestamp(end)
    return m


def realized_vol(returns: pd.Series) -> pd.Series:
    return returns.rolling(VOL_WINDOW, min_periods=VOL_MIN_PERIODS).std() * np.sqrt(252)


def vol_scale(spy_ret: pd.Series, vol_target: float) -> pd.Series:
    rv = realized_vol(spy_ret).replace(0.0, np.nan)
    return (vol_target / rv).clip(lower=0.0, upper=1.0).fillna(0.0)


def build_exposure(
    spy_ret: pd.Series,
    lookback: int,
    entry_thr: float,
    exit_thr: float,
    vol_target: float,
) -> pd.Series:
    cum = spy_ret.rolling(lookback, min_periods=lookback).sum()
    raw = pd.Series(np.nan, index=spy_ret.index, dtype=float)
    raw[cum < entry_thr] = 1.0
    raw[cum >= exit_thr] = 0.0
    raw = raw.ffill().fillna(0.0)
    scale = vol_scale(spy_ret, vol_target)
    return (raw * scale).clip(0.0, MAX_POS).rename(SPY)


def to_signal(exposure: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({SPY: exposure.astype(float)})


def run_one(prices: pd.DataFrame, params: dict) -> dict:
    cfg = make_equity_config()
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(
        spy_ret,
        int(params["lookback"]),
        float(params["entry_thr"]),
        float(params["exit_thr"]),
        float(params["vol_target"]),
    )
    sig = to_signal(exposure)
    bt = run_backtest(prices[[SPY]], sig, cfg)
    return {"backtest": bt, "exposure": exposure}


def metrics_from(bt, mask: pd.Series, positions: pd.DataFrame | None = None) -> dict:
    r = bt.returns.loc[mask.reindex(bt.returns.index, fill_value=False)]
    n = int(r.shape[0])
    if n == 0:
        return {
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
            "n": 0,
            "total_return": 0.0,
        }
    if positions is not None and SPY in positions.columns:
        p = positions[SPY].loc[r.index].fillna(0.0)
        trades = int((p.diff().abs() > 1e-12).sum())
    else:
        trades = int(bt.metrics.get("num_trades", 0))
    neg = float(r[r < 0].abs().sum())
    pf = float(r[r > 0].sum() / neg) if neg > 1e-12 else 0.0
    eq = bt.equity_curve.loc[r.index]
    dd = float(((eq - eq.cummax()) / eq.cummax()).min()) if len(eq) else 0.0
    tot = float(eq.iloc[-1] / eq.iloc[0] - 1.0) if len(eq) > 1 else 0.0
    return {
        "sharpe": float(sharpe_ratio(r)),
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": trades,
        "n": n,
        "total_return": tot,
    }


def wf_mean_sharpe(prices: pd.DataFrame, params: dict, end: str) -> tuple[float, list[float]]:
    train_idx = prices.index[prices.index <= pd.Timestamp(end)]
    splits = walk_forward_splits(len(train_idx), n_splits=WF_FOLDS_SELECTION)
    sharpes = []
    _res = run_one(prices, params)
    for _tr, te in splits:
        te_idx = train_idx[te]
        if len(te_idx) == 0:
            continue
        tm = _mask(prices.index, str(te_idx.min().date()), str(te_idx.max().date()))
        m = metrics_from(_res["backtest"], tm, _res["backtest"].positions)
        sharpes.append(m["sharpe"])
    return (float(np.mean(sharpes)) if sharpes else 0.0), sharpes


def yearly_regime_sharpes(bt, mask: pd.Series) -> dict:
    r = bt.returns.loc[mask.reindex(bt.returns.index, fill_value=False)]
    out = {}
    for year, g in r.groupby(r.index.year):
        out[str(year)] = float(sharpe_ratio(g)) if len(g) >= 30 else 0.0
    return out


def _bh_metrics(prices: pd.DataFrame, mask: pd.Series) -> dict:
    r = prices[SPY].pct_change().loc[mask.reindex(prices.index, fill_value=False)].dropna()
    neg = float(r[r < 0].abs().sum())
    pf = float(r[r > 0].sum() / neg) if neg > 1e-12 else 0.0
    eq = (1.0 + r).cumprod()
    dd = float(((eq - eq.cummax()) / eq.cummax()).min()) if len(eq) else 0.0
    return {
        "sharpe": float(sharpe_ratio(r)),
        "profit_factor": pf,
        "max_drawdown": dd,
        "trades": 1,
        "n": int(len(r)),
    }


def _ablations(prices: pd.DataFrame, selected: dict, oos_mask: pd.Series) -> dict:
    sel = run_one(prices, selected)
    sel_exp = sel["exposure"].loc[oos_mask.reindex(prices.index, fill_value=False)].fillna(0.0)
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    out = {"buy_hold_spy": _bh_metrics(prices, oos_mask)}

    rng = np.random.default_rng(SEED)
    vals = sel_exp.to_numpy().copy()
    nz = np.where(np.abs(vals) > 1e-12)[0]
    if len(nz):
        vals[nz] = rng.permutation(vals[nz])
    rand_sig = to_signal(pd.Series(vals, index=sel_exp.index, name=SPY))
    rand_bt = run_backtest(prices.loc[sel_exp.index, [SPY]], rand_sig, make_equity_config())
    out["random_exposure_matched"] = metrics_from(
        rand_bt, pd.Series(True, index=sel_exp.index), rand_bt.positions
    )

    inv_exp = (1.0 - (sel["exposure"] > 1e-12).astype(float)) * vol_scale(
        spy_ret, float(selected["vol_target"])
    )
    inv_exp = inv_exp.clip(0.0, MAX_POS)
    inv_bt = run_backtest(prices[[SPY]], to_signal(inv_exp.rename(SPY)), make_equity_config())
    out["inverse_no_reversal_long"] = metrics_from(inv_bt, oos_mask, inv_bt.positions)
    return out


def _perturbation(
    prices: pd.DataFrame, selected: dict, oos_mask: pd.Series, opt_sharpe: float
) -> dict:
    rows = []
    for lb in sorted(
        {
            max(1, int(selected["lookback"]) - 1),
            int(selected["lookback"]),
            int(selected["lookback"]) + 1,
        }
    ):
        for vt in sorted(
            {
                max(0.05, round(float(selected["vol_target"]) * 0.8, 3)),
                float(selected["vol_target"]),
                round(float(selected["vol_target"]) * 1.2, 3),
            }
        ):
            p = {**selected, "lookback": lb, "vol_target": vt}
            _pr = run_one(prices, p)
            m = metrics_from(_pr["backtest"], oos_mask, _pr["backtest"].positions)
            rows.append({"params": p, "oos_sharpe": m["sharpe"]})
    min_s = min((r["oos_sharpe"] for r in rows), default=0.0)
    ratio = float(min_s / opt_sharpe) if abs(opt_sharpe) > 1e-12 else 0.0
    return {"rows": rows, "min_oos_sharpe": float(min_s), "min_ratio_vs_optimum": ratio}


def evaluate_gates(train_m, oos_m, wf_ratio, worst_regime, bench, perturb) -> tuple[bool, dict]:
    gates = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": abs(oos_m["max_drawdown"]) <= GATES["max_drawdown"],
        "wf_stability": wf_ratio >= GATES["min_walkforward_stability"],
        "worst_regime": worst_regime >= GATES["min_worst_regime_sharpe"],
        "benchmark": bench["alpha_p_value"] <= GATES["max_p_value"]
        and bench["information_ratio"] >= GATES["min_information_ratio"],
        "perturbation": perturb["min_ratio_vs_optimum"] >= GATES["min_perturbed_sharpe_ratio"],
    }
    return all(gates.values()), gates


def main() -> int:
    t0 = time.time()
    fetcher = DataFetcher()
    prices = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    print(
        f"Data: {UNIVERSE} aligned {len(prices)} rows {prices.index.min().date()}..{prices.index.max().date()}"
    )

    train_mask = _mask(prices.index, DATA_START, TRAIN_END)
    oos_mask = _mask(prices.index, "2020-01-01", None)

    grid = []
    for lookback in LOOKBACKS:
        for entry_thr in ENTRY_THRS:
            for exit_thr in EXIT_THRS:
                if exit_thr <= entry_thr:
                    continue
                for vol_target in VOL_TARGETS:
                    grid.append(
                        {
                            "lookback": lookback,
                            "entry_thr": entry_thr,
                            "exit_thr": exit_thr,
                            "vol_target": vol_target,
                        }
                    )
    print(f"Grid: {len(grid)} combos")

    rows = []
    for i, params in enumerate(grid, 1):
        wf_mean, wf_folds = wf_mean_sharpe(prices, params, TRAIN_END)
        _tres = run_one(prices, params)
        train_m = metrics_from(_tres["backtest"], train_mask, _tres["backtest"].positions)
        rows.append(
            {
                **params,
                "train_wf_mean_sharpe": wf_mean,
                "train_wf_folds": wf_folds,
                "train_sharpe": train_m["sharpe"],
                "train_trades": train_m["trades"],
            }
        )
        if i % 12 == 0 or i == len(grid):
            print(f"  [{i}/{len(grid)}] wf={wf_mean:.3f} {params}")

    rows.sort(key=lambda r: r["train_wf_mean_sharpe"], reverse=True)
    selected = {k: rows[0][k] for k in ("lookback", "entry_thr", "exit_thr", "vol_target")}
    print(f"Selected (train-only WF): {selected} wf={rows[0]['train_wf_mean_sharpe']:.3f}")

    sel = run_one(prices, selected)
    train_m = metrics_from(sel["backtest"], train_mask, sel["backtest"].positions)
    oos_m = metrics_from(sel["backtest"], oos_mask, sel["backtest"].positions)
    regimes = yearly_regime_sharpes(sel["backtest"], oos_mask)
    worst_regime = min(regimes.values()) if regimes else 0.0
    wf_ratio = float(oos_m["sharpe"] / train_m["sharpe"]) if abs(train_m["sharpe"]) > 1e-12 else 0.0

    spy_ret = prices[SPY].pct_change()
    strat_oos = sel["backtest"].returns.loc[
        oos_mask.reindex(sel["backtest"].returns.index, fill_value=False)
    ]
    bh_oos = spy_ret.loc[strat_oos.index].fillna(0.0)
    bench = compare_to_benchmark(strat_oos, bh_oos)
    bench_out = {
        "benchmark": f"buy_hold_{BENCHMARK}",
        "p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", 0.0)),
    }
    perturb = _perturbation(prices, selected, oos_mask, oos_m["sharpe"])
    passed, gates = evaluate_gates(train_m, oos_m, wf_ratio, worst_regime, bench_out, perturb)
    verdict = "ACCEPT" if passed else "REJECT"

    ablations = _ablations(prices, selected, oos_mask)

    out = {
        "experiment_id": None,
        "hypothesis": "H120",
        "nf_id": "NF-20261107-03",
        "name": EXPERIMENT_NAME,
        "description": EXPERIMENT_DESC,
        "data": {
            "source": "yfinance via DataFetcher/cache",
            "symbols": UNIVERSE,
            "benchmark": BENCHMARK,
            "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date()),
            "rows": int(len(prices)),
            "non_positive_rejected": True,
        },
        "splits": {
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "oos": "2020-01-01..end",
            "holdout_role": "Val+Test OOS gates; Test never selected",
        },
        "grid_rows": rows,
        "selected_params": selected,
        "train": train_m,
        "oos_val_test": oos_m,
        "yearly_regime_oos": regimes,
        "worst_regime_sharpe": float(worst_regime),
        "walk_forward": {
            "train_wf_mean_sharpe": rows[0]["train_wf_mean_sharpe"],
            "train_wf_folds": rows[0]["train_wf_folds"],
            "oos_over_train_ratio": wf_ratio,
        },
        "benchmark": bench_out,
        "perturbation": perturb,
        "ablations": ablations,
        "gates": {"thresholds": GATES, "results": gates, "passed": passed},
        "verdict": verdict,
        "timing_seconds": round(time.time() - t0, 3),
        "src_qtr_changed": False,
    }

    tracker = get_tracker()
    try:
        exp_id = tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    except Exception:
        exp_id = f"exp_manual_{int(time.time())}"
    out["experiment_id"] = exp_id
    try:
        tracker.log_params(
            {
                "nf_id": out["nf_id"],
                "hypothesis": out["hypothesis"],
                "selected_params": selected,
                "gates": GATES,
                "src_qtr_changed": False,
            }
        )
    except Exception:
        pass

    run_dir = Path(__file__).parent / ".experiments" / "nf_runs" / EXPERIMENT_NAME
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str))
    try:
        pd.DataFrame(rows).to_csv(run_dir / "grid.csv", index=False)
    except Exception:
        pass

    tracker.log_metrics(
        {
            "oos_sharpe": oos_m["sharpe"],
            "oos_trades": oos_m["trades"],
            "oos_pf": oos_m["profit_factor"],
            "oos_max_dd": oos_m["max_drawdown"],
            "wf_ratio": wf_ratio,
            "worst_regime": worst_regime,
            "benchmark_p": bench_out["alpha_p_value"],
            "benchmark_ir": bench_out["information_ratio"],
            "perturb_min_ratio": perturb["min_ratio_vs_optimum"],
            "gates_passed": int(passed),
        }
    )
    try:
        tracker.finish_experiment({"verdict": verdict, "gates": gates, "passed": passed})
    except Exception:
        pass

    print(
        json.dumps(
            {
                "experiment_id": exp_id,
                "verdict": verdict,
                "gates": gates,
                "selected": selected,
                "oos": oos_m,
                "benchmark": bench_out,
                "worst_regime": worst_regime,
                "perturb_min_ratio": perturb["min_ratio_vs_optimum"],
                "artifact": str(run_dir / "summary.json"),
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
