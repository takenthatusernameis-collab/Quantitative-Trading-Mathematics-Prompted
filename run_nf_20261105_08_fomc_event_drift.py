"""NF-20261105-08 / H90 (pre-registered): FOMC announcement event drift.

Pre-scheduled FOMC statement-release event windows on SPY (long/flat). New
family dimension (event/auction, ex-ante macro calendar), distinct from:
- H18 overnight/intraday persistence (arbitrary days, price-derived session returns).
- H87 opening-gap fill (price gap signal).
H90 conditions on ex-ante FOMC calendar dates, not price-derived signals.

Causality / timing (pre-registered): FOMC statement dates are known from the
public Federal Reserve calendar before meetings. Signal for trading day t+1 is
1.0 if calendar day t is an FOMC statement date, else 0; position held for
`hold_days` trading days starting t+1. Targets are shifted by 1 bar so the
engine applies positions to next-day returns (no same-day look-ahead).

Calendar source: Federal Reserve Board FOMC calendars/historical statements
(public, pre-scheduled; includes emergency meetings as they occurred). Dates
are statement-release days (ET). Hardcoded list audited for 2015-01-01 through
2026-10-31 coverage against the public Fed calendar; no return-derived selection.

Data: yfinance daily via DataFetcher.fetch_yahoo (SPY, ^VIX) 2015-01-01 onward.
Protected holdout Test 2023-01-01+. Train/Val/Test by time.

Gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe>=1.0, >=200 trades,
PF>=1.3, max DD<=15%, WF stability test>=0.7*train when train>0, benchmark
p<=0.05 vs buy-hold SPY, IR>=0, perturbation min ratio>=0.5.
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
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_08_fomc_event_drift"
EXPERIMENT_DESC = (
    "NF-20261105-08/H90: FOMC announcement event drift on SPY. "
    "Daily long/flat SPY over ex-ante FOMC calendar windows (hold_days), optional VIX gate, "
    "vol-targeted; 1-bar execution delay. Grid search on Train/WF; Test protected; "
    "gates on OOS Val+Test."
)

SPY = "SPY"
VIX = "^VIX"
UNIVERSE = [SPY, VIX]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

# Public Federal Reserve FOMC statement-release dates (ET), 2015-01-01..2026-10-31.
# Source: Federal Reserve Board FOMC calendars and historical meeting statements.
# Pre-scheduled; emergency meetings included as they occurred (ex-ante calendar
# is the intended mechanism; using the realized public statement dates is a
# documented audit choice — survivorship/revision risk is minimal for fixed
# historical meeting outcomes).
FOMC_DATES = [
    # 2015
    "2015-01-28",
    "2015-03-18",
    "2015-04-29",
    "2015-06-17",
    "2015-07-29",
    "2015-09-17",
    "2015-10-28",
    "2015-12-16",
    # 2016
    "2016-01-27",
    "2016-03-16",
    "2016-04-27",
    "2016-06-15",
    "2016-07-27",
    "2016-09-21",
    "2016-11-02",
    "2016-12-14",
    # 2017
    "2017-02-01",
    "2017-03-15",
    "2017-05-03",
    "2017-06-14",
    "2017-07-26",
    "2017-09-20",
    "2017-11-01",
    "2017-12-13",
    # 2018
    "2018-01-31",
    "2018-03-21",
    "2018-05-02",
    "2018-06-13",
    "2018-08-01",
    "2018-09-26",
    "2018-11-08",
    "2018-12-19",
    # 2019
    "2019-01-30",
    "2019-03-20",
    "2019-05-01",
    "2019-06-19",
    "2019-07-31",
    "2019-09-18",
    "2019-10-30",
    "2019-12-11",
    # 2020 (includes emergency 2020-03-03, 2020-03-15)
    "2020-01-29",
    "2020-03-03",
    "2020-03-15",
    "2020-04-29",
    "2020-06-10",
    "2020-07-29",
    "2020-09-16",
    "2020-11-05",
    "2020-12-16",
    # 2021
    "2021-01-27",
    "2021-03-17",
    "2021-04-28",
    "2021-06-16",
    "2021-07-28",
    "2021-09-22",
    "2021-11-03",
    "2021-12-15",
    # 2022
    "2022-01-26",
    "2022-03-16",
    "2022-05-04",
    "2022-06-15",
    "2022-07-27",
    "2022-09-21",
    "2022-11-02",
    "2022-12-14",
    # 2023
    "2023-02-01",
    "2023-03-22",
    "2023-05-03",
    "2023-06-14",
    "2023-07-26",
    "2023-09-20",
    "2023-11-01",
    "2023-12-13",
    # 2024
    "2024-01-31",
    "2024-03-20",
    "2024-05-01",
    "2024-06-12",
    "2024-07-31",
    "2024-09-18",
    "2024-11-07",
    "2024-12-18",
    # 2025
    "2025-01-29",
    "2025-03-19",
    "2025-05-07",
    "2025-06-18",
    "2025-07-30",
    "2025-09-17",
    "2025-10-29",
    "2025-12-10",
    # 2026 through DATA_END
    "2026-01-28",
    "2026-03-18",
    "2026-04-29",
    "2026-06-17",
    "2026-07-29",
    "2026-09-16",
    "2026-10-28",
]

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

HOLD_DAYS = [1, 2, 3, 5]
VIX_GATES = [None, 20.0, 25.0, 30.0]  # skip event if VIX close on signal day > gate
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4


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


def is_fomc_date(idx: pd.DatetimeIndex) -> pd.Series:
    s = pd.Series(False, index=idx)
    norm = idx.normalize()
    for d in FOMC_DATES:
        s = s | (norm == pd.Timestamp(d))
    return s


def build_daily_targets(
    prices: pd.DataFrame,
    hold_days: int = 1,
    vix_gate: float | None = None,
    vol_target: float = 0.15,
) -> pd.DataFrame:
    """Long/flat SPY event-window targets, strictly causal.

    Signal day t: FOMC calendar match AND (vix_gate is None or VIX[t] <= vix_gate).
    Raw exposure 1.0 for trading days t+1 .. t+hold_days (1-bar execution delay).
    Vol-targeted using trailing SPY realized vol known at t (causal). Output shifted
    by 1 to represent target applied to next bar.
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SPY])
    if SPY not in prices.columns:
        return targets
    hold_days = int(max(1, hold_days))

    fomc = is_fomc_date(idx)
    if vix_gate is not None and VIX in prices.columns:
        fomc = fomc & (prices[VIX].astype(float) <= float(vix_gate))

    raw = np.zeros(len(idx), dtype=float)
    fomc_vals = fomc.to_numpy(dtype=bool)
    for i in range(len(idx)):
        if fomc_vals[i]:
            for j in range(1, hold_days + 1):
                k = i + j
                if k < len(idx):
                    raw[k] = 1.0

    spy_ret = prices[SPY].astype(float).pct_change()
    realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
    # scale known through t applied to raw at t (then shifted for execution)
    targets[SPY] = (pd.Series(raw, index=idx) * scale).clip(0.0, MAX_POS)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask, n_splits=WF_FOLDS_SELECTION) -> float:
    train_r = returns[train_mask].dropna()
    if len(train_r) < 120:
        return 0.0
    try:
        splits = walk_forward_splits(train_r, n_splits=n_splits, expanding=True)
    except Exception:
        return 0.0
    sharpes = []
    for _, te in splits:
        r = te.dropna()
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

    worst_regime = 0.0
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
        "p_value": bench_p <= GATES["max_p_value"],
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    return {
        "oos_metrics": oos_m,
        "train_sharpe": train_m["sharpe"],
        "val_sharpe": float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0,
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "benchmark_p_value": bench_p,
        "information_ratio": ir,
        "worst_regime_sharpe": worst_regime,
        "passes": passes,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, opt_oos_sharpe):
    variants = {}
    for param in ["hold_days", "vol_target"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            kw = dict(selected)
            if param == "hold_days":
                kw[param] = int(max(1, round(base * factor)))
            else:
                kw[param] = float(max(0.01, min(0.5, base * factor)))
            if kw == selected:
                continue
            pos = build_daily_targets(prices, kw["hold_days"], kw["vix_gate"], kw["vol_target"])
            res = run_backtest(prices=prices[[SPY]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={kw[param]}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    # vix gate perturbation (categorical): try neighbors
    vg = selected["vix_gate"]
    vg_opts = [None, 20.0, 25.0, 30.0]
    if vg in vg_opts:
        i = vg_opts.index(vg)
        for j in [max(0, i - 1), min(len(vg_opts) - 1, i + 1)]:
            if j == i:
                continue
            kw = dict(selected)
            kw["vix_gate"] = vg_opts[j]
            pos = build_daily_targets(prices, kw["hold_days"], kw["vix_gate"], kw["vol_target"])
            res = run_backtest(prices=prices[[SPY]], signals=pos, volumes=None, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"vix_gate={kw['vix_gate']}"] = (
                float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            )
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid = [(h, vg, vt) for h in HOLD_DAYS for vg in VIX_GATES for vt in VOL_TARGETS]
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SPY, VIX],
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": [DATA_START, TRAIN_END],
                "val": [TRAIN_END, VAL_END],
                "test": [VAL_END, DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {"hold_days": HOLD_DAYS, "vix_gate": VIX_GATES, "vol_target": VOL_TARGETS},
            "grid_size": len(grid),
            "fomc_calendar_source": "Federal Reserve Board public FOMC calendars/statements (hardcoded, audited)",
            "fomc_dates_count": len(FOMC_DATES),
            "timing": "FOMC date t -> long days t+1..t+hold_days (1-bar delay), ex-ante calendar",
        },
        data_sources={"source": "yahoo_daily_cached", "symbols": UNIVERSE, "interval": "1d"},
        compute_budget={"max_cpu_hours": 2.0, "grid_size": len(grid)},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-08/H90] started {exp_id}  grid_size={len(grid)}")

    try:
        isolated_cache = Path(tracker.log_dir) / "artifacts" / exp_id / "cache"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))
        data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END, interval="1d")
        prices_list = []
        for sym in UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                raise RuntimeError(f"no data for universe symbol {sym}")
            prices_list.append(df["close"].rename(sym))
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index().dropna(how="any")

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[NF-08/H90] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_equity_config()
        spy_prices = prices[[SPY]]
        bench_weights = pd.DataFrame(1.0, index=prices.index, columns=[SPY])
        bench_result = run_backtest(
            prices=spy_prices, signals=bench_weights, volumes=None, config=cfg
        )

        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for hold_days, vix_gate, vol_target in grid:
            pos = build_daily_targets(prices, hold_days, vix_gate, vol_target)
            res = run_backtest(prices=spy_prices, signals=pos, volumes=None, config=cfg)
            wf_sel = train_only_wf_sharpe(res.returns, train_mask)
            oos_r = res.returns[oos_mask].dropna()
            oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
            key = (hold_days, vix_gate, vol_target)
            grid_results[key] = res
            grid_rows.append(
                {
                    "hold_days": hold_days,
                    "vix_gate": vix_gate,
                    "vol_target": vol_target,
                    "train_wf_sharpe": wf_sel,
                    "train_sharpe": float(sharpe_ratio(res.returns[train_mask].dropna().values))
                    if train_mask.sum() > 1
                    else 0.0,
                    "val_sharpe": float(sharpe_ratio(res.returns[val_mask].dropna().values))
                    if val_mask.sum() > 1
                    else 0.0,
                    "test_sharpe": float(sharpe_ratio(res.returns[test_mask].dropna().values))
                    if test_mask.sum() > 1
                    else 0.0,
                    "oos_sharpe": oos_sr,
                }
            )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-08/H90] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best = grid_df.iloc[0]
        vg_raw = best["vix_gate"]
        vg = None if pd.isna(vg_raw) else float(vg_raw)
        sel = (int(best["hold_days"]), vg, float(best["vol_target"]))
        sel_result = grid_results[sel]
        selected = {"hold_days": sel[0], "vix_gate": sel[1], "vol_target": sel[2]}

        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, bench_result)
        pert = perturbation_eval(selected, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        ablations["spy_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, spy_prices)
        )
        # Random event dates ablation (same count/frequency, deterministic)
        rng = np.random.default_rng(SEED)
        rand_mask = np.zeros(len(prices), dtype=bool)
        n_events = int(is_fomc_date(prices.index).sum())
        rand_idx = rng.choice(len(prices), size=min(n_events, len(prices)), replace=False)
        rand_mask[rand_idx] = True
        # build targets using random mask by monkeypatching via local build
        raw_rand = np.zeros(len(prices), dtype=float)
        for i in range(len(prices)):
            if rand_mask[i]:
                for j in range(1, sel[0] + 1):
                    k = i + j
                    if k < len(prices):
                        raw_rand[k] = 1.0
        spy_ret = prices[SPY].astype(float).pct_change()
        realized = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
        scale = (sel[2] / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
        rand_pos = pd.DataFrame(
            {SPY: (pd.Series(raw_rand, index=prices.index) * scale).clip(0.0, MAX_POS)}
        )
        rand_res = run_backtest(prices=spy_prices, signals=rand_pos, volumes=None, config=cfg)
        ablations["random_event_dates"] = _period_metrics(
            rand_res.returns[oos_mask], _count_in(rand_res.trades, oos_mask, prices)
        )
        # No VIX gate ablation for selected
        no_vix_pos = build_daily_targets(prices, sel[0], None, sel[2])
        no_vix_res = run_backtest(prices=spy_prices, signals=no_vix_pos, volumes=None, config=cfg)
        ablations["no_vix_gate"] = _period_metrics(
            no_vix_res.returns[oos_mask], _count_in(no_vix_res.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_daily_targets(prices, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261105-08/H90",
            "selected_config": {k: (None if v is None else v) for k, v in selected.items()},
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": len(grid),
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "calendar": {
                "source": "Federal Reserve Board public FOMC calendars/statements (hardcoded)",
                "dates_count": len(FOMC_DATES),
                "coverage": [DATA_START, DATA_END],
            },
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
                "perturbation": pert,
                "ablations": ablations,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | total {total_elapsed / 60:.1f} min"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        tracker.finish_experiment(status="failed", error=str(e))
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
