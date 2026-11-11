"""NF-20261107-07 / H122 (executed, Cycle 36): SPY realized downside
semivariance-ratio stress regime timing.

NOTE (lineage correction, 2026-11-07): an earlier draft header mislabeled this
mechanism as "Amihud semivariance/semiliquidity". The *executed* implementation
and recorded verdict use a **realized downside/upside variance ratio** signal:
`down_var_20 / up_var_20` (20-bar rolling mean of squared negative/positive
returns), z-scored over `window`; `volume` is fetched but NOT used by the
signal. Numeric results/artifact verdict preserved unchanged.

Signal = z-score of trailing realized downside semivariance ratio. Reduce
vol-targeted long SPY when z > entry_z (downside asymmetry stress), flat
otherwise; hysteresis exit at exit_z. Engine signals.shift(1) gives t->t+1
causality. No src/qtr change.

Distinct from H121 (NF-20261107-04, REJECT 4/8, Amihud |ret|/dollar-volume
liquidity stress): H122 uses price-return asymmetry (downside vs upside realized
variance), no dollar-volume/Amihud component. Distinct from H117/H118
(cross-sectional correlation/dispersion regime), H1/H4/H8/H9/H10 TSMOM,
H18/H87/H90/H91/H119/H120.
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
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261107_07_realized_semivariance"
EXPERIMENT_DESC = (
    "NF-20261107-07/H122: SPY realized downside semivariance-ratio stress timing. "
    "Reduce vol-targeted long SPY when z-score of rolling downside/upside "
    "variance ratio exceeds entry threshold (downside asymmetry stress), flat "
    "otherwise with hysteresis exit. Volume fetched but unused by signal. "
    "Train-only WF selection; Test protected; OOS gates vs buy-hold SPY."
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

WINDOWS = [10, 20, 40]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5, 1.0]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4
VOL_WINDOW = 20
VOL_MIN_PERIODS = 20

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

COST_MODEL = CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0)


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=COST_MODEL,
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )


def _align_prices(
    fetcher: DataFetcher, symbols, start: str, end: str
) -> tuple[pd.DataFrame, pd.Series]:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    frames = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else df.columns[0])
        )
        c = df[col].astype(float)
        if (c <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        frames[s] = c.rename(s)
    prices = pd.concat(frames.values(), axis=1).dropna()
    vol_col = next((c for c in raw[SPY].columns if str(c).lower() == "volume"), None)
    if vol_col is None:
        raise RuntimeError("Volume column missing from fetched data")
    volume = raw[SPY][vol_col].astype(float).reindex(prices.index)
    if len(prices) < 500:
        raise RuntimeError(f"Too few aligned rows: {len(prices)}")
    return prices, volume


def _mask(idx: pd.DatetimeIndex, start: str | None, end: str | None) -> pd.Series:
    m = pd.Series(True, index=idx)
    if start:
        m &= idx >= pd.Timestamp(start)
    if end:
        m &= idx <= pd.Timestamp(end)
    return m


def semivar_series(close: pd.Series) -> pd.Series:
    r = close.pct_change()
    down = r.where(r < 0, 0.0).pow(2)
    up = r.where(r > 0, 0.0).pow(2)
    down_var = down.rolling(20, min_periods=20).mean()
    up_var = up.rolling(20, min_periods=20).mean()
    return (down_var / up_var.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def semivar_z(close, volume=None, window=20) -> pd.Series:
    a = semivar_series(close)
    m = a.rolling(window, min_periods=window).mean()
    s = a.rolling(window, min_periods=window).std(ddof=0)
    return (a - m) / s.replace(0, np.nan)


def build_exposure(
    semivar_z: pd.Series, entry_z: float, exit_z: float, vol_target: float
) -> pd.Series:
    z = semivar_z.fillna(0.0)
    n = len(z)
    exp = np.zeros(n)
    in_pos = False
    for i in range(n):
        if not in_pos:
            if z.iloc[i] <= entry_z:
                in_pos = True
        else:
            if z.iloc[i] > exit_z:
                in_pos = False
        exp[i] = vol_target if in_pos else 0.0
    return pd.Series(exp, index=z.index)


def realized_vol(
    returns: pd.Series, window: int = VOL_WINDOW, min_periods: int = VOL_MIN_PERIODS
) -> pd.Series:
    return returns.rolling(window, min_periods=min_periods).std(ddof=0) * np.sqrt(252)


def vol_scale(spy_ret: pd.Series, vol_target: float) -> pd.Series:
    rv = realized_vol(spy_ret).replace(0.0, np.nan)
    return (vol_target / rv).clip(lower=0.0, upper=1.0).fillna(0.0)


def run_one(prices: pd.DataFrame, volume: pd.Series, params: dict) -> dict:
    cfg = make_equity_config()
    close = prices[SPY]
    z = semivar_z(close, window=int(params["window"]))
    ret = close.pct_change().fillna(0.0)
    base = build_exposure(
        z, float(params["entry_z"]), float(params["exit_z"]), float(params["vol_target"])
    )
    vs = vol_scale(ret, float(params["vol_target"]))
    exposure = (base * vs).clip(0.0, MAX_POS)
    exposure = exposure.shift(1).fillna(0.0)
    sig = pd.DataFrame({SPY: exposure.astype(float)})
    bt = run_backtest(prices[[SPY]], sig, cfg)
    return {"backtest": bt, "exposure": exposure, "z": z}


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


def wf_mean_sharpe(
    prices: pd.DataFrame, volume: pd.Series, params: dict, end: str
) -> tuple[float, list[float]]:
    train_idx = prices.index[prices.index <= pd.Timestamp(end)]
    splits = walk_forward_splits(len(train_idx), n_splits=WF_FOLDS_SELECTION)
    sharpes = []
    _res = run_one(prices, volume, params)
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


def _ablations(
    prices: pd.DataFrame, volume: pd.Series, selected: dict, oos_mask: pd.Series
) -> dict:
    sel = run_one(prices, volume, selected)
    sel_exp = sel["exposure"].loc[oos_mask.reindex(prices.index, fill_value=False)].fillna(0.0)
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    out = {"buy_hold_spy": _bh_metrics(prices, oos_mask)}

    rng = np.random.default_rng(SEED)
    vals = sel_exp.to_numpy().copy()
    nz = np.where(np.abs(vals) > 1e-12)[0]
    if len(nz):
        vals[nz] = rng.permutation(vals[nz])
    rand_sig = pd.DataFrame({SPY: pd.Series(vals, index=sel_exp.index, name=SPY).astype(float)})
    rand_bt = run_backtest(prices.loc[sel_exp.index, [SPY]], rand_sig, make_equity_config())
    out["random_exposure_matched"] = metrics_from(
        rand_bt, pd.Series(True, index=sel_exp.index), rand_bt.positions
    )

    inv_exp = (1.0 - (sel["exposure"] > 1e-12).astype(float)) * vol_scale(
        spy_ret, float(selected["vol_target"])
    )
    inv_exp = inv_exp.clip(0.0, MAX_POS)
    inv_bt = run_backtest(
        prices[[SPY]], pd.DataFrame({SPY: inv_exp.rename(SPY)}), make_equity_config()
    )
    out["inverse_high_semivaruidity_long"] = metrics_from(inv_bt, oos_mask, inv_bt.positions)
    return out


def _perturbation(
    prices: pd.DataFrame, volume: pd.Series, selected: dict, oos_mask: pd.Series, opt_sharpe: float
) -> dict:
    rows = []
    for w in sorted(
        {
            max(1, int(selected["window"]) - 1),
            int(selected["window"]),
            int(selected["window"]) + 1,
        }
    ):
        for ez in sorted(
            {
                max(0.0, round(float(selected["entry_z"]) - 0.5, 2)),
                float(selected["entry_z"]),
                round(float(selected["entry_z"]) + 0.5, 2),
            }
        ):
            for vt in sorted(
                {
                    max(0.05, round(float(selected["vol_target"]) * 0.8, 3)),
                    float(selected["vol_target"]),
                    round(float(selected["vol_target"]) * 1.2, 3),
                }
            ):
                p = {**selected, "window": w, "entry_z": ez, "vol_target": vt}
                _pr = run_one(prices, volume, p)
                m = metrics_from(_pr["backtest"], oos_mask, _pr["backtest"].positions)
                rows.append({"params": p, "oos_sharpe": m["sharpe"]})
    min_s = min((r["oos_sharpe"] for r in rows), default=0.0)
    ratio = float(min_s / opt_sharpe) if abs(opt_sharpe) > 1e-12 else 0.0
    return {"rows": rows, "min_oos_sharpe": float(min_s), "min_ratio_vs_optimum": ratio}


def evaluate_gates(
    train_m, oos_m, wf_ratio, worst_regime, bench_gate, perturb
) -> tuple[bool, dict]:
    gates = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": abs(oos_m["max_drawdown"]) <= GATES["max_drawdown"],
        "wf_stability": wf_ratio >= GATES["min_walkforward_stability"],
        "worst_regime": worst_regime >= GATES["min_worst_regime_sharpe"],
        "benchmark": benchmark_significance_gate(
            bench_gate["p_value"],
            bench_gate["information_ratio"],
            GATES["max_p_value"],
        )
        and bench_gate["information_ratio"] >= GATES["min_information_ratio"],
        "perturbation": perturb["min_ratio_vs_optimum"] >= GATES["min_perturbed_sharpe_ratio"],
    }
    return all(gates.values()), gates


def main() -> int:
    t0 = time.time()
    fetcher = DataFetcher()
    prices, volume = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    print(
        f"Data: {UNIVERSE} aligned {len(prices)} rows {prices.index.min().date()}..{prices.index.max().date()}"
    )

    train_mask = _mask(prices.index, DATA_START, TRAIN_END)
    oos_mask = _mask(prices.index, "2020-01-01", None)

    grid = []
    for window in WINDOWS:
        for entry_z in ENTRY_ZS:
            for exit_z in EXIT_ZS:
                if exit_z >= entry_z:
                    continue
                for vol_target in VOL_TARGETS:
                    grid.append(
                        {
                            "window": window,
                            "entry_z": entry_z,
                            "exit_z": exit_z,
                            "vol_target": vol_target,
                        }
                    )
    print(f"Grid: {len(grid)} combos")

    rows = []
    for i, params in enumerate(grid, 1):
        wf_mean, wf_folds = wf_mean_sharpe(prices, volume, params, TRAIN_END)
        _tres = run_one(prices, volume, params)
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
    selected = {k: rows[0][k] for k in ("window", "entry_z", "exit_z", "vol_target")}
    print(f"Selected (train-only WF): {selected} wf={rows[0]['train_wf_mean_sharpe']:.3f}")

    sel = run_one(prices, volume, selected)
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
    perturb = _perturbation(prices, volume, selected, oos_mask, oos_m["sharpe"])
    passed, gates = evaluate_gates(train_m, oos_m, wf_ratio, worst_regime, bench_out, perturb)
    verdict = "ACCEPT" if passed else "REJECT"

    ablations = _ablations(prices, volume, selected, oos_mask)

    out = {
        "experiment_id": None,
        "hypothesis": "H122",
        "nf_id": "NF-20261107-07",
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
            "benchmark_p": bench_out["p_value"],
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
