"""
H88 / NF-20261105-06: Gold–Oil Relative-Value Spread Mean Reversion.

Pre-registered in NEW_FAMILY_RESEARCH_REGISTER.md §10–11 and
HYPOTHESIS_SPEC.md §H88. Mechanism: mean reversion of log(GOLD/OIL) spread
dislocations (relative value/convergence). Long spread (long gold, short oil)
when z-score extreme negative; short spread when extreme positive.

Amendment 2026-11-05 (option b, before outcome evaluation): observable
re-specification from GC=F/CL=F futures to GLD/USO ETF proxies after CL=F
non-positive-price feasibility blocker (2020-04 WTI episode). Material
instrument/cost/basis change disclosed in spec/register; splits/holdout
unchanged. Equity cost model applied to ETF legs.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher  # noqa: E402
from qtr.tracking.experiment import get_tracker  # noqa: E402
from qtr.validation.statistics import (  # noqa: E402
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_06_gold_oil_rv"
EXPERIMENT_DESC = (
    "H88/NF-20261105-06 (amended option b): Gold–oil relative-value spread "
    "mean reversion (log GLD/USO z-score, ETF proxy). Long/short spread on "
    "extreme dislocations, vol-targeted; Train/Val/Test 2010-2018/2019-2022/"
    "2023-2026; Test protected; gates on OOS Val+Test."
)

GOLD = "GLD"
OIL = "USO"
UNIVERSE = [GOLD, OIL]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2018-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 30,
    "min_profit_factor": 1.1,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}

LOOKBACKS = [60, 120, 252]
ENTRY_ZS = [1.5, 2.0, 2.5]
EXIT_ZS = [0.5, 0.75]
VOL_TARGET = 0.10
MAX_LEG = 0.5  # per leg, dollar-neutral spread

WF_FOLDS_SELECTION = 4


def make_etf_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_LEG,
        max_leverage=2.0,
        allow_short=True,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    if len(r) > 1:
        sr = float(sharpe_ratio(r.values))
    else:
        sr = 0.0
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


def spread_series(prices: pd.DataFrame) -> pd.Series:
    """Log spread s_t = log(GOLD_t) - log(OIL_t), point-in-time."""
    gold = prices[GOLD].astype(float)
    oil = prices[OIL].astype(float)
    valid = (gold > 0) & (oil > 0)
    s = pd.Series(np.nan, index=prices.index)
    s[valid] = np.log(gold[valid]) - np.log(oil[valid])
    return s


def spread_zscore(s: pd.Series, lookback: int) -> pd.Series:
    min_p = int(max(21, lookback // 3))
    mu = s.rolling(lookback, min_periods=min_p).mean()
    sd = s.rolling(lookback, min_periods=min_p).std()
    sd = sd.replace(0, np.nan)
    z = (s - mu) / sd
    return z


def _stationarity_diagnostic(s: pd.Series) -> dict:
    """Simple autocorrelation diagnostic (no statsmodels dependency required)."""
    x = s.dropna()
    if len(x) < 30:
        return {"n": int(len(x)), "acf1": None, "ar1_coef": None}
    x0 = x.values
    xdm = x0 - x0.mean()
    denom = float(np.dot(xdm, xdm))
    acf1 = float(np.dot(xdm[1:], xdm[:-1]) / denom) if denom > 0 else None
    # AR(1) via OLS on demeaned series
    y = xdm[1:]
    xlag = xdm[:-1]
    xx = float(np.dot(xlag, xlag))
    ar1 = float(np.dot(xlag, y) / xx) if xx > 0 else None
    return {"n": int(len(x)), "acf1": acf1, "ar1_coef": ar1}


def build_spread_targets(
    prices: pd.DataFrame,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float = VOL_TARGET,
) -> tuple[pd.DataFrame, pd.Series]:
    """Daily target weights for GOLD and OIL (spread legs), strictly causal.

    Returns (targets DataFrame with GOLD/OIL columns, spread_position series in {-1,0,1}).
    """
    targets = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
    if GOLD not in prices.columns or OIL not in prices.columns:
        return targets, pd.Series(0.0, index=prices.index)

    s = spread_series(prices)
    z = spread_zscore(s, lookback)

    # State machine: position decided from z at t (known at close t), applied t+1 via shift
    pos = pd.Series(0.0, index=prices.index)
    current = 0.0
    for i in range(len(prices.index)):
        zi = z.iloc[i]
        if not np.isfinite(zi):
            pos.iloc[i] = current
            continue
        if current == 0.0:
            if zi <= -entry_z:
                current = 1.0  # long spread: long GOLD, short OIL
            elif zi >= entry_z:
                current = -1.0  # short spread
        elif current == 1.0:
            if zi >= -exit_z or zi >= entry_z:
                if zi >= entry_z:
                    current = -1.0
                elif zi >= -exit_z:
                    current = 0.0
        elif current == -1.0:
            if zi <= exit_z or zi <= -entry_z:
                if zi <= -entry_z:
                    current = 1.0
                elif zi <= exit_z:
                    current = 0.0
        pos.iloc[i] = current

    # Apply with 1-bar delay (signal at close t -> position t+1)
    pos_delayed = pos.shift(1).fillna(0.0)

    # Vol targeting on spread returns (causal, trailing)
    gold_ret = prices[GOLD].pct_change()
    oil_ret = prices[OIL].pct_change()
    # Unit spread return proxy: 0.5*(gold_ret - oil_ret) per leg notionally
    spread_ret = 0.5 * (gold_ret - oil_ret)
    rolling_vol = spread_ret.rolling(63, min_periods=21).std() * np.sqrt(252)
    rolling_vol = rolling_vol.replace(0, np.nan).ffill().fillna(0.15)
    scale = (vol_target / rolling_vol).clip(lower=0.0, upper=1.0)

    leg = (MAX_LEG * scale * pos_delayed).fillna(0.0)
    targets[GOLD] = leg
    targets[OIL] = -leg
    return targets, pos_delayed


def _count_entries(pos: pd.Series, mask) -> int:
    p = pos.reindex(mask.index if hasattr(mask, "index") else pos.index)
    if hasattr(mask, "dtype") and mask.dtype == bool:
        p = pos[mask]
    changes = p.fillna(0.0).diff().fillna(p.fillna(0.0))
    entries = ((p != 0) & (changes != 0)) | ((p != 0) & (p.shift(1).fillna(0.0) == 0.0))
    return int(entries.sum())


def train_only_wf_sharpe(returns: pd.Series, train_mask: pd.Series) -> float:
    r = returns.copy()
    r.index = pd.to_datetime(r.index)
    try:
        splits = walk_forward_splits(r, n_folds=WF_FOLDS_SELECTION, embargo_days=5)
    except Exception:
        train_r = r[train_mask].dropna()
        if len(train_r) > 1:
            return float(sharpe_ratio(train_r.values))
        return 0.0
    sharpes = []
    for tr, _ in splits:
        tr_mask = r.index.isin(tr)
        if tr_mask.sum() < 30:
            continue
        tr_r = r[tr_mask].dropna()
        if len(tr_r) > 1:
            s = sharpe_ratio(tr_r.values)
            if np.isfinite(s):
                sharpes.append(float(s))
    if sharpes:
        return float(np.mean(sharpes))
    train_r = r[train_mask].dropna()
    if len(train_r) > 1:
        return float(sharpe_ratio(train_r.values))
    return 0.0


def full_gate_eval(result, oos_mask, val_mask, test_mask, train_mask, prices, bench_result):
    oos_ret = result.returns[oos_mask].dropna()
    val_ret = result.returns[val_mask].dropna()
    test_ret = result.returns[test_mask].dropna()
    train_ret = result.returns[train_mask].dropna()

    oos_sr = float(sharpe_ratio(oos_ret.values)) if len(oos_ret) > 1 else 0.0
    val_sr = float(sharpe_ratio(val_ret.values)) if len(val_ret) > 1 else 0.0
    test_sr = float(sharpe_ratio(test_ret.values)) if len(test_ret) > 1 else 0.0
    train_sr = float(sharpe_ratio(train_ret.values)) if len(train_ret) > 1 else 0.0

    oos_trades = _count_in(result.trades, oos_mask, prices)
    cum = (1 + oos_ret).cumprod()
    oos_dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(oos_ret[oos_ret > 0].sum())
    gl = float(abs(oos_ret[oos_ret < 0].sum()))
    oos_pf = gp / gl if gl > 0 else float("inf")

    wf_stab = float(test_sr / train_sr) if train_sr > 0 and np.isfinite(train_sr) else 0.0

    bench_cmp = compare_to_benchmark(result.returns, bench_result.returns)
    bench_p = float(bench_cmp.get("alpha_p_value", 1.0))
    ir = float(bench_cmp.get("information_ratio", 0.0))

    regime_sharpes = []
    for m in [train_mask, val_mask, test_mask]:
        r = result.returns[m].dropna()
        if len(r) > 10:
            regime_sharpes.append(float(sharpe_ratio(r.values)))
    worst_regime = float(min(regime_sharpes)) if regime_sharpes else -np.inf

    passes = {
        "sharpe": oos_sr >= GATES["min_sharpe"],
        "trades": oos_trades >= GATES["min_trades"],
        "profit_factor": oos_pf >= GATES["min_profit_factor"],
        "drawdown": oos_dd >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "benchmark_significance": benchmark_significance_gate(bench_p, ir),
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    test_cum = (1 + test_ret).cumprod() if len(test_ret) > 0 else pd.Series([1.0])
    test_dd = float((test_cum / test_cum.cummax() - 1.0).min()) if len(test_cum) > 0 else 0.0
    return {
        "passes": passes,
        "oos_metrics": {
            "sharpe": oos_sr,
            "profit_factor": oos_pf,
            "max_drawdown": oos_dd,
            "trades": oos_trades,
        },
        "train_sharpe": train_sr,
        "val_sharpe": val_sr,
        "test_metrics": {"sharpe": test_sr, "max_drawdown": test_dd},
        "wf_stability": wf_stab,
        "benchmark_p_value": bench_p,
        "information_ratio": ir,
        "worst_regime_sharpe": worst_regime,
    }


def perturbation_eval(selected, prices, oos_mask, cfg, baseline_sharpe):
    """OAT perturbation ±20% on lookback and entry_z."""
    variants = {}
    for param in ["lookback", "entry_z"]:
        base = selected[param]
        for factor in [0.8, 1.2]:
            v = base * factor
            if abs(v - base) < 1e-12:
                v = base + (0.1 if factor > 1 else -0.1)
            kw = dict(selected)
            if param == "lookback":
                kw[param] = int(max(20, round(v)))
            else:
                kw[param] = float(max(0.5, v))
            tgt, _ = build_spread_targets(prices, kw["lookback"], kw["entry_z"], kw["exit_z"])
            try:
                res = run_backtest(prices=prices[UNIVERSE], signals=tgt, volumes=None, config=cfg)
                r = res.returns[oos_mask].dropna()
                variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            except Exception:
                variants[f"{param}={v:.3f}"] = 0.0
    if baseline_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / baseline_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main() -> int:
    start_time = time.time()
    tracker = get_tracker()
    grid_size = len(LOOKBACKS) * len(ENTRY_ZS) * len(EXIT_ZS)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "lookbacks": LOOKBACKS,
            "entry_zs": ENTRY_ZS,
            "exit_zs": EXIT_ZS,
            "vol_target": VOL_TARGET,
            "splits": {
                "train": f"<={TRAIN_END}",
                "val": f"{TRAIN_END}->{VAL_END}",
                "test": f">{VAL_END}",
            },
            "grid_size": grid_size,
        },
        data_sources={
            "source": "yahoo_daily_cached_isolated",
            "symbols": UNIVERSE,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 1.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H88] started {exp_id} grid={grid_size}")

    exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    isolated_cache = exp_dir / "cache"
    isolated_cache.mkdir(parents=True, exist_ok=True)
    fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))

    try:
        data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END, interval="1d")
        parts = []
        for sym in UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                raise RuntimeError(f"no data for {sym}")
            parts.append(df["close"].rename(sym))
        prices = pd.concat(parts, axis=1, sort=True).sort_index().dropna(how="any")

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[H88] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        stat_diag = _stationarity_diagnostic(spread_series(prices))
        print(
            f"[H88] spread diagnostic acf1={stat_diag.get('acf1')} ar1={stat_diag.get('ar1_coef')}"
        )

        cfg = make_etf_config()

        # Benchmark: equal-weight buy-hold GOLD+OIL (ETF proxy)
        bench_w = pd.DataFrame(0.5, index=prices.index, columns=UNIVERSE)
        bench_result = run_backtest(
            prices=prices[UNIVERSE], signals=bench_w, volumes=None, config=cfg
        )

        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lb in LOOKBACKS:
            for ez in ENTRY_ZS:
                for xz in EXIT_ZS:
                    if xz >= ez:
                        continue
                    tgt, pos = build_spread_targets(prices, lb, ez, xz)
                    res = run_backtest(
                        prices=prices[UNIVERSE], signals=tgt, volumes=None, config=cfg
                    )
                    wf_train = train_only_wf_sharpe(res.returns, train_mask)
                    oos_r = res.returns[oos_mask].dropna()
                    oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
                    key = (lb, ez, xz)
                    grid_results[key] = (res, pos)
                    grid_rows.append(
                        {
                            "lookback": lb,
                            "entry_z": ez,
                            "exit_z": xz,
                            "train_wf_sharpe": wf_train,
                            "oos_sharpe": oos_sr,
                            "trades_total": int(len(res.trades)) if res.trades is not None else 0,
                        }
                    )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        if grid_df.empty:
            raise RuntimeError("empty grid")
        print(
            f"[H88] grid done {grid_elapsed:.1f}s; best train-WF={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        best = grid_df.iloc[0]
        sel = {
            "lookback": int(best["lookback"]),
            "entry_z": float(best["entry_z"]),
            "exit_z": float(best["exit_z"]),
        }
        sel_result, base_pos = grid_results[(sel["lookback"], sel["entry_z"], sel["exit_z"])]

        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, train_mask, prices, bench_result
        )
        pert = perturbation_eval(sel, prices, oos_mask, cfg, gate["oos_metrics"]["sharpe"])
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        ablations = {}
        try:
            rng_ab = np.random.default_rng(SEED)
            rand_pos = base_pos.copy()
            rand_pos[:] = rng_ab.choice([-1.0, 0.0, 1.0], size=len(rand_pos))
            rand_pos = rand_pos.shift(1).fillna(0.0)
            rt = pd.DataFrame(0.0, index=prices.index, columns=UNIVERSE)
            rt[GOLD] = MAX_LEG * rand_pos
            rt[OIL] = -MAX_LEG * rand_pos
            rr = run_backtest(prices=prices[UNIVERSE], signals=rt, volumes=None, config=cfg)
            ablations["random_entry"] = _period_metrics(
                rr.returns[oos_mask], _count_in(rr.trades, oos_mask, prices)
            )
        except Exception:
            ablations["random_entry"] = {"error": "failed"}
        ablations["gold_oil_equal_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, prices)
        )

        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", build_spread_targets(prices, **sel)[0])
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))

        total_elapsed = time.time() - start_time
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H88",
            "temporary_id": "NF-20261105-06",
            "selected_config": sel,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "spread_diagnostic": stat_diag,
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
                "perturbation": pert,
                "ablations": ablations,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }
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
        print(f"  Selected: {sel}")
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        traceback.print_exc()
        try:
            tracker.finish_experiment(status="failed", error=str(e))
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
