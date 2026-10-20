"""
H17: Volatility-Risk-Premium Harvesting
    (Term-Structure-Gated, Vol-Targeted Long SVXY).

Implements the pre-registered H17 hypothesis in HYPOTHESIS_SPEC.md:
a term-structure-gated, volatility-targeted long position in SVXY,
selected on Val Sharpe and gate-evaluated on the protected
OOS (Val+Test) window using the PROMPT_V2 evidence gates +
the +/-20% perturbation gate.

Faithfulness notes:
  * Universe: SVXY (traded); ^VIX, ^VIX3M (signal only);
    SPY (secondary reference).  SVXY history starts 2011-10-04.
  * Splits: Train 2011-10-01 -> 2019-12-31 (includes 2018-02
    volmageddon), Val 2020-01-01 -> 2021-12-31 (COVID), Test
    2022-01-01 -> 2026-10-08 (protected).  OOS = Val+Test.
  * Signal (causal; engine applies shift(1), so today's target holds
    next day's return):
      contango_t = ^VIX3M_t / ^VIX_t - 1
      gate_t      = 1{contango_t > gate_thresh}
      vol_t       = rolling-annualized realized vol of SVXY returns
                    (past `vol_window` returns; window from H1 methodology)
      pos_t       = gate_t * clip(target_vol / vol_t, 0, max_pos)
  * Selection: argmax(Val Sharpe) over 60 combos; Test never used.
  * Gates: unchanged PROMPT_V2 set + perturbation gate, on OOS
    (Val+Test).  Benchmark = buy-and-hold SVXY.
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
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "h17_vrp"
EXPERIMENT_DESC = (
    "H17: Term-structure-gated, vol-targeted long SVXY (VRP harvesting); "
    "60-combo grid (gate_thresh x vol_window x target_vol x max_pos), "
    "Val-selected, Test-protected"
)

# Symbols
SVXY_SYMBOL = "SVXY"
VIX_SYMBOL = "^VIX"
VIX3M_SYMBOL = "^VIX3M"
SPY_SYMBOL = "SPY"

# Splits (pre-registered)
DATA_START = "2011-10-01"
DATA_END = "2026-10-08"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"

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

# Grid
GATE_THRESHES = [0.00, 0.02, 0.05]
VOL_WINDOWS = [21, 63]
TARGET_VOLS = [0.05, 0.10, 0.15, 0.25, 0.50]
MAX_POSS = [0.5, 1.0]

WF_FOLDS_SELECTION = 4
WF_FOLDS_STABILITY = 5


def regime_labels(vix_daily: pd.Series) -> pd.Series:
    """VIX regime labels: bull < 20, sideways 20-30, bear > 30."""
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def realized_vol_ann(returns: pd.Series, window: int) -> pd.Series:
    """Annualized realized volatility over rolling window sqrt(252)*std."""
    return returns.rolling(window).std() * np.sqrt(252.0)


def build_targets(
    svxy_close: pd.Series,
    vix_close: pd.Series,
    vix3m_close: pd.Series,
    gate_thresh: float,
    vol_window: int,
    target_vol: float,
    max_pos: float,
) -> pd.DataFrame:
    """
    Build daily target weights for SVXY (long only, [0, max_pos]).
    Causal levels; engine applies shift(1) internally, so a target set
    on date t earns the return of date t+1.
    """
    df = pd.DataFrame(index=svxy_close.index)
    df["svxy_ret"] = svxy_close.pct_change()
    df["vix"] = vix_close.reindex(svxy_close.index)
    df["vix3m"] = vix3m_close.reindex(svxy_close.index)

    contango = (df["vix3m"] / df["vix"]) - 1.0
    vol = realized_vol_ann(df["svxy_ret"], vol_window)
    gate = (contango > gate_thresh).astype(float)

    pos_raw = target_vol / vol
    pos = gate * pos_raw.clip(lower=0.0, upper=max_pos)
    targets = pd.DataFrame(index=svxy_close.index)
    targets["SVXY"] = pos.fillna(0.0)
    return targets


def _splits(prices_idx: pd.Index):
    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)
    val_mask = (prices_idx > pd.Timestamp(TRAIN_END)) & (prices_idx <= pd.Timestamp(VAL_END))
    test_mask = prices_idx > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def _period_metrics(ret: pd.Series, n_trades: int, equity: pd.Series) -> dict:
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
    prices_idx = prices.index
    train_mask = prices_idx <= pd.Timestamp(TRAIN_END)

    oos_ret = result.returns[oos_mask]
    test_ret = result.returns[test_mask]
    oos_eq = result.equity_curve[oos_mask]
    n_oos_trades = _count_in(result.trades, oos_mask, prices)

    oos_m = _period_metrics(oos_ret, n_oos_trades, oos_eq)
    test_m = _period_metrics(
        test_ret,
        _count_in(result.trades, test_mask, prices),
        result.equity_curve[test_mask],
    )

    # Walk-forward stability (full series)
    wf_splits = walk_forward_splits(len(result.returns), n_splits=WF_FOLDS_STABILITY)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].dropna()
        te_r = result.returns.iloc[te_idx].dropna()
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r.values))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r.values))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes)) if np.mean(train_sharpes) != 0 else 0.0
    )

    # Regime sharpes on the OOS window
    regimes = regime_labels(vix.reindex(prices_idx))[oos_mask]
    oos_ret_r = oos_ret  # already masked
    regime_sharpes = {}
    worst = np.inf
    for reg in ["bull", "sideways", "bear"]:
        m = regimes == reg
        r = oos_ret_r[m] if len(m) == len(oos_ret_r) else oos_ret_r.iloc[m.values]
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
    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_m["max_drawdown"]) <= GATES["max_drawdown"]
        if oos_m["max_drawdown"] < 0
        else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "worst": worst >= GATES["min_worst_regime_sharpe"] if worst != np.inf else False,
        "p": benchmark_significance_gate(
            float(bench.get("alpha_p_value", 1.0)),
            float(bench.get("information_ratio", -np.inf)),
            GATES["max_p_value"],
        ),
        "ir": float(bench.get("information_ratio", -np.inf)) > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": oos_m,
        "test_metrics": test_m,
        "train_sharpe": float(sharpe_ratio(result.returns[train_mask].dropna().values))
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": float(sharpe_ratio(result.returns[val_mask].dropna().values))
        if val_mask.sum() > 1
        else 0.0,
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": float(worst) if worst != np.inf else 0.0,
        "regime_sharpes": regime_sharpes,
        "benchmark_p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "benchmark_alpha_annual": float(bench.get("alpha_annualized", 0.0)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def perturbation_eval(
    selected: dict,
    prices: pd.DataFrame,
    vix: pd.Series,
    vix3m: pd.Series,
    oos_mask,
    cfg,
    opt_oos_sharpe: float,
):
    """OAT +/-20% perturbation of numeric selected parameters
    (gate_thresh, vol_window, target_vol, max_pos)."""
    variants = {}
    params = {
        "gate_thresh": selected["gate_thresh"],
        "vol_window": selected["vol_window"],
        "target_vol": selected["target_vol"],
        "max_pos": selected["max_pos"],
    }
    for param, base in params.items():
        for factor in (0.8, 1.2):
            v = base * factor
            if param == "vol_window":
                v = max(1, round(v))
            elif param == "gate_thresh" or param == "target_vol" or param == "max_pos":
                v = round(v, 4)
            if v == base:
                continue
            kw = dict(selected)
            kw[param] = v
            targets = build_targets(
                prices["SVXY"],
                vix,
                vix3m,
                kw["gate_thresh"],
                kw["vol_window"],
                kw["target_vol"],
                kw["max_pos"],
            )
            res = run_backtest(prices=prices, signals=targets, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe) if variants else 0.0
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def make_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=False,
    )


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(GATE_THRESHES) * len(VOL_WINDOWS) * len(TARGET_VOLS) * len(MAX_POSS)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": [SVXY_SYMBOL],
            "signal_symbols": [VIX_SYMBOL, VIX3M_SYMBOL],
            "reference": SPY_SYMBOL,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": ["2011-10-01", TRAIN_END],
                "val": ["2020-01-01", VAL_END],
                "test": ["2022-01-01", DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "gate_thresh": GATE_THRESHES,
                "vol_window": VOL_WINDOWS,
                "target_vol": TARGET_VOLS,
                "max_pos": MAX_POSS,
            },
            "grid_size": grid_size,
            "selection": "argmax Val Sharpe (train-free grid selection; Test protected)",
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": [SVXY_SYMBOL, VIX_SYMBOL, VIX3M_SYMBOL, SPY_SYMBOL],
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[H17] started {exp_id}  grid_size={grid_size}")

    try:
        fetcher = get_data_fetcher()
        data = fetcher.fetch_yahoo(
            [SVXY_SYMBOL, VIX_SYMBOL, VIX3M_SYMBOL, SPY_SYMBOL],
            start=DATA_START,
            end=DATA_END,
            interval="1d",
        )
        svxy_df = data.get(SVXY_SYMBOL, pd.DataFrame())
        if svxy_df.empty:
            raise RuntimeError(f"no data for {SVXY_SYMBOL}")

        # Align all series to SVXY trading days (SVXY is the traded asset)
        common = svxy_df.index
        svxy_close = svxy_df["close"]
        vix = data.get(VIX_SYMBOL, pd.DataFrame())["close"].reindex(common)
        vix3m = data.get(VIX3M_SYMBOL, pd.DataFrame())["close"].reindex(common)
        spy = data.get(SPY_SYMBOL, pd.DataFrame())["close"].reindex(common)

        # Backtest price frame: SVXY only (single traded asset)
        prices = pd.DataFrame({"SVXY": svxy_close.values}, index=common)
        volumes = pd.DataFrame({"SVXY": svxy_df["volume"].values}, index=common)

        train_mask, val_mask, test_mask = _splits(prices.index)
        oos_mask = ~train_mask  # Val + Test
        print(
            f"[H17] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_config()
        svxy_inception = svxy_close.first_valid_index()

        # Benchmark: buy-and-hold SVXY
        bench_signals = pd.DataFrame({"SVXY": 1.0}, index=prices.index)
        bench_result = run_backtest(prices=prices, signals=bench_signals, config=cfg)

        # --- 60-combo grid: selection on Val Sharpe ---
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for gate_thresh in GATE_THRESHES:
            for vol_window in VOL_WINDOWS:
                for target_vol in TARGET_VOLS:
                    for max_pos in MAX_POSS:
                        targets = build_targets(
                            svxy_close,
                            vix,
                            vix3m,
                            gate_thresh,
                            vol_window,
                            target_vol,
                            max_pos,
                        )
                        res = run_backtest(prices=prices, signals=targets, config=cfg)
                        train_r = res.returns[train_mask].dropna()
                        train_sr = float(sharpe_ratio(train_r.values)) if len(train_r) > 1 else 0.0
                        test_r = res.returns[test_mask].dropna()
                        test_sr = float(sharpe_ratio(test_r.values)) if len(test_r) > 1 else 0.0
                        val_r = res.returns[val_mask].dropna()
                        val_sr = float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0
                        oos_r = res.returns[oos_mask].dropna()
                        oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
                        grid_results[(gate_thresh, vol_window, target_vol, max_pos)] = res
                        grid_rows.append(
                            {
                                "gate_thresh": gate_thresh,
                                "vol_window": vol_window,
                                "target_vol": target_vol,
                                "max_pos": max_pos,
                                "train_sharpe": train_sr,
                                "val_sharpe": val_sr,
                                "test_sharpe": test_sr,
                                "oos_sharpe": oos_sr,
                            }
                        )
        grid_df = pd.DataFrame(grid_rows).sort_values("val_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[H17] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; "
            f"best val Sharpe={grid_df.iloc[0]['val_sharpe']:.4f}"
        )

        # --- selection: best Val Sharpe (Test never used) ---
        best_row = grid_df.iloc[0]
        sel_key = (
            float(best_row["gate_thresh"]),
            int(best_row["vol_window"]),
            float(best_row["target_vol"]),
            float(best_row["max_pos"]),
        )
        sel_result = grid_results[sel_key]
        selected = {
            "gate_thresh": sel_key[0],
            "vol_window": sel_key[1],
            "target_vol": sel_key[2],
            "max_pos": sel_key[3],
        }

        # --- full gate evaluation on protected OOS (Val+Test) ---
        gate = full_gate_eval(sel_result, oos_mask, val_mask, test_mask, prices, vix, bench_result)

        # --- perturbation gate (OAT +/-20% on selected params) ---
        pert = perturbation_eval(
            selected,
            prices,
            vix,
            vix3m,
            oos_mask,
            cfg,
            gate["oos_metrics"]["sharpe"],
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"
        gate["passes"]["sharpe"] = gate["oos_metrics"]["sharpe"] >= GATES["min_sharpe"]

        # --- ablations (OOS, not selected) ---
        ablations = {}
        # (a) BH SVXY
        ablations["bh_svxy"] = {
            "oos_metrics": _period_metrics(
                bench_result.returns[oos_mask],
                _count_in(bench_result.trades, oos_mask, prices),
                bench_result.equity_curve[oos_mask],
            ),
        }
        # (b) ungated vol-target (gate_thresh = -inf -> gate always 1)
        ug = dict(selected)
        ug["gate_thresh"] = -1.0
        ug_t = build_targets(
            svxy_close,
            vix,
            vix3m,
            -1.0,
            ug["vol_window"],
            ug["target_vol"],
            ug["max_pos"],
        )
        ug_res = run_backtest(prices=prices, signals=ug_t, config=cfg)
        ug_gate = full_gate_eval(ug_res, oos_mask, val_mask, test_mask, prices, vix, bench_result)
        ablations["ungated_vol_target"] = {"oos_metrics": ug_gate["oos_metrics"]}
        # (c) gate-only (no vol target: target_vol=1.0 effectively full position, max_pos=1.0)
        go_t = build_targets(svxy_close, vix, vix3m, sel_key[0], 21, 1.0, 1.0)
        go_res = run_backtest(prices=prices, signals=go_t, config=cfg)
        go_gate = full_gate_eval(go_res, oos_mask, val_mask, test_mask, prices, vix, bench_result)
        ablations["gate_only_no_vol_target"] = {"oos_metrics": go_gate["oos_metrics"]}
        # (d) BH SPY reference
        if not spy.isna().all():
            spy_eq = pd.Series(
                ((1 + spy.pct_change().fillna(0)).cumprod() * INITIAL_CAPITAL),
                index=common,
            )
            ablations["bh_spy"] = {
                "oos_metrics": _period_metrics(
                    spy.pct_change()[oos_mask].dropna(), 0, spy_eq[oos_mask]
                ),
            }

        # --- artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("vix_close", vix.rename("close").to_frame())
        tracker.log_dataframe("vix3m_close", vix3m.rename("close").to_frame())
        tracker.log_dataframe("spy_close", spy.rename("close").to_frame())
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe("selected_signals", sel_result.positions)
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("benchmark_returns", bench_result.returns.to_frame("returns"))
        for name, ab in ablations.items():
            tracker.log_metrics({f"ablation_{name}_oos_sharpe": ab["oos_metrics"]["sharpe"]})

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "H17",
            "selected_config": selected,
            "selection_rule": (
                "argmax Val Sharpe; Test 2022-2026 protected (never used for selection); "
                "gates on OOS Val+Test"
            ),
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "svxy_inception": str(svxy_inception.date()) if svxy_inception is not None else None,
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
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
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
        print(f"  Benchmark: p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}")
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
