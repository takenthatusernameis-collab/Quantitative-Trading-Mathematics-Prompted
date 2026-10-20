"""
H16: Cross-Sectional Equity Factor Timing (Value/Momentum/Quality Rotation).

Implements the pre-registered H16 hypothesis in HYPOTHESIS_SPEC.md:
a regime-filtered factor-rotation strategy across 9 liquid factor ETFs
(3 factor families x 3 ETFs), selected on train-only walk-forward
Sharpe and gate-evaluated on the protected OOS (Val+Test) window.

Faithfulness notes (pre-registration -> implementation):
  * Universe: VLUE/IJS/VTV (value), MTUM/QQQ/SPYG (momentum),
    QUAL/SPHQ/USMF (quality). ETFs participate only from their Yahoo
    inception (point-in-time universe; VLUE/MTUM from 2013-04-18,
    QUAL from 2013-07-18, USMF from 2017-06-29). No price is ever
    fabricated before inception.
  * Signal: factor momentum (lookback, skip), top-1 ETF per family,
    families ranked by representative momentum, top-n_factors families
    held at equal weight, total exposure scaled by the VIX regime
    factor (bull/sideways/bear triple from the grid).
  * Monthly rebalance: month-end target held through the next month
    (no look-ahead; the engine applies position_{t-1} to return_t).
  * Selection: mean of 4 train-only walk-forward test-fold Sharpes.
    Test 2021-2024 never enters selection; OOS = Val+Test (gated).
  * Gates: the unchanged PROMPT_V2 set (Sharpe >= 1.0, trades >= 200,
    PF >= 1.3, DD <= 15%, WF stability >= 0.7, worst-regime Sharpe
    >= 0.3, benchmark p < 0.05 and IR > 0) plus the +/-20% OAT
    parameter-perturbation gate (OOS Sharpe >= 0.5 x optimum).
  * Benchmark: equal-weight buy-and-hold of the (point-in-time)
    9-ETF universe.

Cost model, engine, tracker and validation utilities are reused from
src/qtr (no new infrastructure). Data: Yahoo Finance daily, cached.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import get_data_fetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "h16_factor_timing"
EXPERIMENT_DESC = (
    "H16: Cross-sectional equity factor timing (value/momentum/quality "
    "rotation) with VIX-regime exposure filter; 54-combo grid selected on "
    "train-only walk-forward Sharpe; gates on protected OOS (Val+Test)"
)

# --- Pre-registered constants (HYPOTHESIS_SPEC.md H16) -----------------
FACTOR_FAMILIES = {
    "value": ["VLUE", "IJS", "VTV"],
    "momentum": ["MTUM", "QQQ", "SPYG"],
    "quality": ["QUAL", "SPHQ", "USMF"],
}
UNIVERSE = [etf for etfs in FACTOR_FAMILIES.values() for etf in etfs]
VIX_SYMBOL = "^VIX"

DATA_START = "2010-01-01"
DATA_END = "2024-12-31"
TRAIN_END = "2017-12-31"
VAL_END = "2020-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

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

# Pre-registered grid: 3 x 3 x 2 x 3 = 54 combos.
LOOKBACKS = [63, 126, 252]
SKIPS = [1, 5, 21]
REGIME_EXPOSURES = [(1.0, 0.5, 0.25), (1.0, 0.25, 0.10)]
N_FACTORS_OPTS = [1, 2, 3]

WF_FOLDS_SELECTION = 4  # train-only walk-forward folds for selection
WF_FOLDS_STABILITY = 5  # full-series folds for the WF-stability gate


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    """VIX regime labels (same convention as H1-H11): bull < 20,
    sideways 20-30, bear > 30."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def regime_factor_series(vix: pd.Series, exposure: tuple) -> pd.Series:
    """Causal VIX-regime exposure factor on the price index."""
    vix_ff = vix.ffill()
    f = pd.Series(exposure[0], index=vix_ff.index)
    f[vix_ff >= 20] = exposure[1]
    f[vix_ff > 30] = exposure[2]
    return f


def factor_momentum(prices: pd.DataFrame, lookback: int, skip: int) -> pd.DataFrame:
    """Factor momentum, strictly causal at t:
    mom_{i,t} = close_{i,t-skip} / close_{i,t-skip-lookback} - 1.

    With skip >= 1 both inputs are strictly before t. ETFs before their
    inception have NaN momentum and are never selected.
    """
    shifted = prices.shift(skip)
    base = prices.shift(skip + lookback)
    return shifted / base - 1.0


def build_daily_targets(
    prices: pd.DataFrame,
    vix: pd.Series,
    lookback: int,
    skip: int,
    regime_exposure: tuple,
    n_factors: int,
    families: dict[str, list] | None = None,
) -> pd.DataFrame:
    """Daily (pre-rebalance) target weights, causal, point-in-time.

    ``families`` optionally restricts the rotation universe (used
    for the per-family ablations); defaults to all three families.
    """
    fam_map = families if families is not None else FACTOR_FAMILIES
    mom = factor_momentum(prices, lookback, skip)
    rf = regime_factor_series(vix.reindex(prices.index), regime_exposure)

    # Top-1 ETF per family by momentum (point-in-time; NaN family -> None).
    # -inf fill makes all-NA rows argmax-safe; the `valid` mask keeps
    # families with no available momentum (warmup / pre-inception) out
    # of the selection entirely.
    fam_rep = {}
    fam_mom = {}
    for fam, etfs in fam_map.items():
        sub = mom[etfs]
        valid = sub.notna().any(axis=1)
        rep = sub.where(sub.notna(), -np.inf).idxmax(axis=1)
        fam_rep[fam] = rep.where(valid)
        fam_mom[fam] = sub.max(axis=1)

    fam_mom_df = pd.DataFrame(fam_mom)
    # Rank families by representative momentum (best = rank 1); families
    # with no available momentum (all-NaN) are never held.
    fam_rank = fam_mom_df.rank(axis=1, ascending=False, method="first")

    targets = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for fam, etfs in fam_map.items():
        held = (fam_rank[fam] <= n_factors) & fam_mom_df[fam].notna()
        rep = fam_rep[fam]
        for etf in etfs:
            w = pd.Series(0.0, index=prices.index)
            m = held & (rep == etf)
            w[m] = rf[m] / n_factors
            targets[etf] = w
    return targets


def monthly_rebalance(daily_targets: pd.DataFrame) -> pd.DataFrame:
    """Hold the month-end target through the next month (causal).

    The monthly target is anchored on the *actual last trading
    day* of each month (not the calendar month-end, which can be
    a non-trading day): with the engine's internal shift(1), the
    target set at the last trading day of month m earns the
    returns of all trading days of month m+1.
    """
    months = daily_targets.index.to_period("M")
    monthly = daily_targets.groupby(months, sort=True).last()
    # anchor each month's target on its true last trading day
    last_days = pd.Series(daily_targets.index, index=months)
    monthly.index = last_days.groupby(level=0).last().values
    return monthly.reindex(daily_targets.index, method="ffill").fillna(0.0)


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),  # equity defaults: 1bp comm + 1bp spread
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (
        prices.index <= pd.Timestamp(VAL_END)
    )
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
    if len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def train_only_wf_sharpe(
    returns: pd.Series, train_mask, n_splits: int = WF_FOLDS_SELECTION
) -> float:
    """Selection score: mean of test-fold Sharpes over train-only
    walk-forward splits (H1-H3 methodology)."""
    tr = returns[train_mask].dropna()
    if len(tr) < 20:
        return -np.inf
    splits = walk_forward_splits(len(tr), n_splits=n_splits)
    fold_sharpes = []
    for _tr_idx, te_idx in splits:
        if len(te_idx) > 1:
            fold_sharpes.append(sharpe_ratio(tr.iloc[te_idx].values))
    if not fold_sharpes:
        return -np.inf
    return float(np.mean(fold_sharpes))


def full_gate_eval(
    result,
    oos_mask,
    val_mask,
    test_mask,
    prices,
    vix,
    bench_result,
):
    """The 8 pre-registered gates on OOS (Val+Test)."""
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)

    oos_ret = result.returns[oos_mask]
    test_ret = result.returns[test_mask]
    oos_m = _period_metrics(oos_ret, _count_in(result.trades, oos_mask, prices))
    test_m = _period_metrics(test_ret, _count_in(result.trades, test_mask, prices))

    # Walk-forward stability over the full series (H9/H10 convention)
    wf_splits = walk_forward_splits(len(result.returns), n_splits=WF_FOLDS_STABILITY)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].values
        te_r = result.returns.iloc[te_idx].values
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes))
        if np.mean(train_sharpes) != 0
        else 0.0
    )

    # Regime sharpes on the OOS window (VIX labels, daily ffill)
    regimes = regime_labels(vix.reindex(prices.index))[oos_mask]
    regime_sharpes = {}
    worst = np.inf
    for reg in ["bull", "sideways", "bear"]:
        m = regimes == reg
        r = oos_ret[m]
        if len(r) > 1 and r.std() > 0:
            s = float(sharpe_ratio(r.values))
        else:
            s = 0.0
        regime_sharpes[reg] = s
        worst = min(worst, s)

    bench = compare_to_benchmark(
        oos_ret.dropna().values,
        bench_result.returns[oos_mask].dropna().values,
    )
    oos_max_dd = oos_m["max_drawdown"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_max_dd) <= GATES["max_drawdown"] if oos_max_dd < 0 else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "worst": worst >= GATES["min_worst_regime_sharpe"]
        if worst != np.inf
        else False,
        "p": float(bench.get("alpha_p_value_one_sided", 1.0)) < GATES["max_p_value"],
        "ir": float(bench.get("information_ratio", -np.inf))
        > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": oos_m,
        "test_metrics": test_m,
        "train_sharpe": float(sharpe_ratio(result.returns[train_mask].values))
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": float(sharpe_ratio(result.returns[val_mask].dropna().values))
        if val_mask.sum() > 1
        else 0.0,
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
        "regime_sharpes": regime_sharpes,
        "benchmark_p_value": float(bench.get("alpha_p_value_one_sided", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "benchmark_alpha_annual": float(bench.get("alpha_annualized", 0.0)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def perturbation_eval(
    selected: dict,
    prices,
    volumes,
    vix,
    oos_mask,
    cfg,
    opt_oos_sharpe: float,
):
    """OAT +/-20% perturbation of the numeric selected parameters
    (lookback, skip). Returns per-variant OOS Sharpes and the min ratio
    to the optimum (pre-registered gate >= 0.5)."""
    variants = {}
    for param, base in (("lookback", selected["lookback"]), ("skip", selected["skip"])):
        for factor in (0.8, 1.2):
            v = round(base * factor)
            if v == base:
                v = base + (1 if factor > 1 else -1)
            v = max(1, v)
            kw = dict(selected)
            kw[param] = v
            pos = monthly_rebalance(
                build_daily_targets(
                    prices,
                    vix,
                    kw["lookback"],
                    kw["skip"],
                    tuple(kw["regime_exposure"]),
                    kw["n_factors"],
                )
            )
            res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v}"] = (
                float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
            )
    if opt_oos_sharpe > 0:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = (
        len(LOOKBACKS) * len(SKIPS) * len(REGIME_EXPOSURES) * len(N_FACTORS_OPTS)
    )
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "factor_families": FACTOR_FAMILIES,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": ["2010-01-01", TRAIN_END],
                "val": ["2018-01-01", VAL_END],
                "test": ["2021-01-01", DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "lookback": LOOKBACKS,
                "skip": SKIPS,
                "regime_exposure": REGIME_EXPOSURES,
                "n_factors": N_FACTORS_OPTS,
            },
            "grid_size": grid_size,
            "selection": "train-only 4-fold walk-forward Sharpe (mean of test folds)",
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": UNIVERSE,
            "vix": VIX_SYMBOL,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H16] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        data = fetcher.fetch_yahoo(
            UNIVERSE + [VIX_SYMBOL], start=DATA_START, end=DATA_END, interval="1d"
        )
        prices_list, volumes_list = [], []
        for sym in UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                raise RuntimeError(f"no data for universe symbol {sym}")
            prices_list.append(df["close"].rename(sym))
            volumes_list.append(df["volume"].rename(sym))
        # Point-in-time prices: leading NaN before each ETF's inception
        # (never forward-filled across inception).
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index()
        volumes = pd.concat(volumes_list, axis=1, sort=True).sort_index().fillna(0)

        vix_df = data.get(VIX_SYMBOL, pd.DataFrame())
        if len(vix_df) == 0:
            raise RuntimeError("no data for ^VIX")
        vix = vix_df["close"]

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        inception = {s: prices[s].first_valid_index() for s in UNIVERSE}
        print(
            f"[H16] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )
        print(f"[H16] inception dates: {inception}")

        cfg = make_equity_config()

        # Equal-weight buy-and-hold benchmark over the point-in-time universe
        avail = prices.notna().astype(float)
        ew_weights = avail.div(avail.sum(axis=1), axis=0).fillna(0.0)
        bench_result = run_backtest(
            prices=prices, signals=ew_weights, volumes=volumes, config=cfg
        )

        # --- 54-combo grid: selection on train-only walk-forward Sharpe ---
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lookback in LOOKBACKS:
            for skip in SKIPS:
                for regime_exposure in REGIME_EXPOSURES:
                    for n_factors in N_FACTORS_OPTS:
                        daily = build_daily_targets(
                            prices, vix, lookback, skip, regime_exposure, n_factors
                        )
                        pos = monthly_rebalance(daily)
                        res = run_backtest(
                            prices=prices, signals=pos, volumes=volumes, config=cfg
                        )
                        wf_sel = train_only_wf_sharpe(res.returns, train_mask)
                        oos_r = res.returns[oos_mask].dropna()
                        oos_sr = (
                            float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
                        )
                        grid_results[(lookback, skip, regime_exposure, n_factors)] = res
                        grid_rows.append(
                            {
                                "lookback": lookback,
                                "skip": skip,
                                "regime_exposure": str(regime_exposure),
                                "n_factors": n_factors,
                                "train_wf_sharpe": wf_sel,
                                "train_sharpe": float(
                                    sharpe_ratio(
                                        res.returns[train_mask].dropna().values
                                    )
                                )
                                if train_mask.sum() > 1
                                else 0.0,
                                "val_sharpe": float(
                                    sharpe_ratio(res.returns[val_mask].dropna().values)
                                )
                                if val_mask.sum() > 1
                                else 0.0,
                                "test_sharpe": float(
                                    sharpe_ratio(res.returns[test_mask].dropna().values)
                                )
                                if test_mask.sum() > 1
                                else 0.0,
                                "oos_sharpe": oos_sr,
                            }
                        )
        grid_df = pd.DataFrame(grid_rows).sort_values(
            "train_wf_sharpe", ascending=False
        )
        grid_elapsed = time.time() - t_grid
        print(
            f"[H16] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        # --- selection: best train-only WF Sharpe (Test never used) ---
        best_key = grid_df.iloc[0][["lookback", "skip", "regime_exposure", "n_factors"]]
        sel = (
            int(best_key["lookback"]),
            int(best_key["skip"]),
            eval(best_key["regime_exposure"]),
            int(best_key["n_factors"]),
        )
        sel_result = grid_results[sel]
        selected = {
            "lookback": sel[0],
            "skip": sel[1],
            "regime_exposure": list(sel[2]),
            "n_factors": sel[3],
        }

        # --- full gate evaluation on protected OOS (Val+Test) ---
        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
        )

        # --- perturbation gate (OAT +/-20% on lookback, skip) ---
        pert = perturbation_eval(
            selected, prices, volumes, vix, oos_mask, cfg, gate["oos_metrics"]["sharpe"]
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # --- ablations (evaluated on OOS, not selected) ---
        ablations = {}
        # (a) ungated: constant full exposure (regime factor == 1.0)
        ungated_pos = monthly_rebalance(
            build_daily_targets(prices, vix, sel[0], sel[1], (1.0, 1.0, 1.0), sel[3])
        )
        ungated_res = run_backtest(
            prices=prices, signals=ungated_pos, volumes=volumes, config=cfg
        )
        ungated_gate = full_gate_eval(
            ungated_res, oos_mask, val_mask, test_mask, prices, vix, bench_result
        )
        ablations["ungated_full_exposure"] = {
            "oos_metrics": ungated_gate["oos_metrics"],
            "worst_regime_sharpe": ungated_gate["worst_regime_sharpe"],
            "regime_sharpes": ungated_gate["regime_sharpes"],
        }
        # (b) EW benchmark reference
        ablations["ew_benchmark"] = {
            "oos_metrics": _period_metrics(
                bench_result.returns[oos_mask],
                _count_in(bench_result.trades, oos_mask, prices),
            ),
            "train_sharpe": float(
                sharpe_ratio(bench_result.returns[train_mask].dropna().values)
            ),
        }
        # (c) single-factor-family exposure (each family alone,
        # selected lookback/skip/regime, n_factors=1 within family)
        for fam, etfs in FACTOR_FAMILIES.items():
            fam_daily = build_daily_targets(
                prices,
                vix,
                sel[0],
                sel[1],
                sel[2],
                1,
                families={fam: etfs},
            )
            fam_pos = monthly_rebalance(fam_daily)
            fam_res = run_backtest(
                prices=prices, signals=fam_pos, volumes=volumes, config=cfg
            )
            ablations[f"family_{fam}"] = {
                "oos_metrics": _period_metrics(
                    fam_res.returns[oos_mask],
                    _count_in(fam_res.trades, oos_mask, prices),
                )
            }

        # --- family exposure log (root-cause attribution) ---
        sel_daily = build_daily_targets(prices, vix, sel[0], sel[1], sel[2], sel[3])
        sel_pos = monthly_rebalance(sel_daily)
        family_exposure = pd.DataFrame(index=prices.index)
        for fam, etfs in FACTOR_FAMILIES.items():
            family_exposure[fam] = sel_pos[etfs].sum(axis=1)
        tracker.log_dataframe("family_exposure", family_exposure)

        # --- artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.to_frame("close"))
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", sel_pos)
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe(
            "benchmark_equity", bench_result.equity_curve.to_frame("equity")
        )
        tracker.log_dataframe(
            "benchmark_returns", bench_result.returns.to_frame("returns")
        )
        for name, ab in ablations.items():
            tracker.log_metrics(
                {f"ablation_{name}_oos_sharpe": ab["oos_metrics"]["sharpe"]}
            )

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H16",
            "selected_config": selected,
            "selection_rule": (
                "best train-only 4-fold walk-forward Sharpe; "
                "Test 2021-2024 protected (never used for selection); "
                "gates on OOS Val+Test"
            ),
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "inception_dates": {k: str(v.date()) for k, v in inception.items()},
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "worst_regime_sharpe": gate["worst_regime_sharpe"],
                "regime_sharpes": gate["regime_sharpes"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "benchmark_alpha_annual": gate["benchmark_alpha_annual"],
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
                default=lambda x: (
                    float(x) if isinstance(x, (np.integer, np.floating)) else str(x)
                ),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        print(
            f"  sharpe={p['sharpe']} trades={p['trades']} pf={p['pf']} "
            f"dd={p['dd']} stab={p['stab']} worst={p['worst']} "
            f"p={p['p']} ir={p['ir']} perturb={p['perturbation']}"
        )
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} "
            f"DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} "
            f"Test={gate['test_metrics']['sharpe']:.3f} | "
            f"WF stab={gate['wf_stability']:.3f} | worst-regime={gate['worst_regime_sharpe']:.3f}"
        )
        print(
            f"  Benchmark: p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | "
            f"total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:  # noqa: BLE001 -- top-level experiment harness: any failure must finish the tracker and return a verdict
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
