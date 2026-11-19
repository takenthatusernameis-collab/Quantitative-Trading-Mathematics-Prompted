"""NF-20261119-01 / H185 (Cycle 216 pre-registration, Cycle 216 execution).

Broad mechanism category: hedging pressure / speculative positioning measured by
open interest.  Repo-new root family relative to executed H1-H184: no executed
H-ID trades open interest as its primary signal in any market.  H184 (rejected)
trades the relative *price* of two contracts (front/second settlement slope =
inventory carry); H185 trades *contract counts* (total open interest growth and
the front contract's share of open interest).  The two inputs are independent
fields -- a quantity vs a price ratio -- and the train-block cross-sectional
rank correlation between the H185 OI-growth z and the H184 slope z is -0.026
(W=21) / +0.014 (W=63), so this is not a re-skin of carry.  H19/H20 tested
*volume* on US ETFs; open interest counts open positions, not daily turnover.

Mechanism / causal chain.  Open interest measures the stock of open positions.
OI growth measures new capital entering (or leaving) a market: rising hedging
demand must induce speculators onto the other side and the risk transfer earns a
premium (Bessembinder 1992 hedging pressure; Hong & Yogo 2012 show aggregate OI
growth predicts commodity futures returns).  The front contract's OI share
measures near-dated concentration, i.e. roll-cycle crowding.  Null (H0): the
day-t open-interest cross-section has no predictive power for next-period
roll-adjusted returns after CNY costs -- a positioning overlay adds nothing over
a passive front-month long book.

PIT timing.  Each cross-section file is the official settlement record for trade
date t and is knowable at t's settle.  Total OI and front-OI share for day t use
day-t records only; growth windows use strictly earlier trade dates via
``shift(W)`` on the trading calendar.  Positions are formed no earlier than t+1
via the explicit ``shift(1)`` in the shared engine, and they earn the price
change of the contract *known at t-1* (the H184 ``held_returns`` basis), so no
day-t settlement enters the day-t signal and no future contract enters the
day-t return.

Pre-registration (Cycle 216, before any outcome inspection).
NF-ID NF-20261119-01 (H185).  Sample 2016-01-04 -> 2026-11-17.  Train
->2023-06-30; Val 2023-07-01 -> 2024-12-31; Test protected 2025-01-01 ->
2026-11-17.  Universe SHFE RB, CU, AL, ZN, AU, AG (2016-01-04) + INE SC
(2018-03-26); exclude any contract whose delivery month equals the current
month; contracts enter the OI aggregate only when settlement > 0 and open
interest >= OI_FLOOR (100), the same tradable set as the return panel.
Features (cross-sectional z across active products): ``oi_growth_21`` =
ln(total OI_t / total OI_{t-21}); ``oi_growth_63`` = ln(total OI_t /
total OI_{t-63}); ``front_share`` = OI_front,t / total OI_t.  Pre-registered
sign: long top-k / short bottom-k by z (Hong-Yogo / hedging-pressure
direction).  Grid (bounded, 72): feature {oi_growth_21, oi_growth_63,
front_share} x entry_z {0.5, 1.0, 1.5} x exit_z {0.0, 0.5} x k {1, 2} x
vol_target {0.10, 0.15}; train-only 4-fold walk-forward Sharpe selection.
Costs (CNY, explicit, unchanged from H184): commission 2 bps + slippage 3 bps
per one-way side per leg (5 bps one-way per contract traded), roll crossing
1 bps when the held front contract changes; vol targeting delevers only.

Gates (OOS Val+Test, fail-closed, standard 8, unchanged): Sharpe >= 1.0; trades
>= 50; PF >= 1.3; maxDD <= 15%; WF stability >= 0.7; worst-regime rolling-252
Sharpe >= 0.3; benchmark p <= 0.05 (two-sided) with IR >= 0 vs the passive
front-month long book; perturbation min ratio >= 0.5.

Ablations/falsifiers: passive front-month long book; random ranking (same active
leg count, seed 42); inverse-sign signal; OAT +/-20% perturbation.

Implementation constraints: import the parsers/URL builders/cache helper from
scripts/probe_commodity_termstructure_availability.py and the settlement-cache
loader, return basis, backtest engine, gate helpers and benchmark constructors
from run_nf_20261114_01_commodity_termstructure_carry.py (no forked copy); only
the OI feature construction is new code.  Reuses the warm resumable cache under
.cache/commodity_settlements/.  Artifact under
.experiments/nf_runs/<experiment>_<timestamp>/summary.json + grid.csv.
``src/qtr`` unchanged; free/public real data only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

# Reuse the executed H184 runner for the cached cross-section loader, the
# contract-known-at-t-1 return basis, the backtest engine, metrics, gate
# helpers and benchmark constructors.  Nothing here forks a second copy.
_H184_PATH = ROOT / "run_nf_20261114_01_commodity_termstructure_carry.py"
_h184_spec = importlib.util.spec_from_file_location("h184_termstructure", _H184_PATH)
assert _h184_spec is not None and _h184_spec.loader is not None
h184 = importlib.util.module_from_spec(_h184_spec)  # type: ignore[arg-type]
sys.modules[_h184_spec.name] = h184
_h184_spec.loader.exec_module(h184)

EXPERIMENT = "nf_20261119_01_commodity_oi_positioning"
NF_ID = "NF-20261119-01"
HYPOTHESIS = "H185"

START = h184.START
END = h184.END
TRAIN_END = h184.TRAIN_END
VAL_END = h184.VAL_END
UNIVERSE = h184.UNIVERSE
FIRST_DATE = h184.FIRST_DATE
OI_FLOOR = h184.OI_FLOOR
COST_ONE_WAY_BPS = h184.COST_ONE_WAY_BPS
ROLL_CROSS_BPS = h184.ROLL_CROSS_BPS
SEED = h184.SEED
WORKERS = h184.WORKERS
GATES = dict(h184.GATES)

# Declared feature set and growth windows (trading days on the bdate calendar).
OI_GROWTH_WINDOW = {"oi_growth_21": 21, "oi_growth_63": 63}
FRONT_SHARE = "front_share"
FEATURES = [*OI_GROWTH_WINDOW, FRONT_SHARE]

GRID = {
    "feature": list(FEATURES),
    "entry_z": [0.5, 1.0, 1.5],
    "exit_z": [0.0, 0.5],
    "k": [1, 2],
    "vol_target": [0.10, 0.15],
}


# ---------------------------------------------------------------------------
# Open-interest features (the only new signal code)
# ---------------------------------------------------------------------------


def total_open_interest(panel: dict[str, pd.DataFrame], floor: float = OI_FLOOR) -> pd.Series:
    """Open interest summed over every non-delivery, tradable contract each day.

    A contract counts only when its settlement is positive and its open interest
    clears ``floor`` -- the same tradable set used to pick the front contract for
    the return basis, so the OI panel and the return panel agree.
    """
    oi, settle = panel["oi"], panel["settle"]
    mask = (settle > 0) & (oi >= floor)
    return oi.where(mask).sum(axis=1, min_count=1)


def front_share_series(
    panel: dict[str, pd.DataFrame], term: pd.DataFrame, floor: float = OI_FLOOR
) -> pd.Series:
    """Front-contract share of total open interest (roll-cycle crowding)."""
    oi = panel["oi"]
    total = total_open_interest(panel, floor)
    values = []
    for day in oi.index:
        front = term.at[day, "front"]
        if isinstance(front, str) and front in oi.columns:
            front_oi = oi.at[day, front]
            values.append(float(front_oi) if pd.notna(front_oi) else np.nan)
        else:
            values.append(np.nan)
    front_oi = pd.Series(values, index=oi.index, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        share = front_oi / total.where(total > 0)
    return share.where((share >= 0.0) & (share <= 1.0))


def feature_panel(
    panels: dict[str, dict[str, pd.DataFrame]],
    terms: dict[str, pd.DataFrame],
    calendar: pd.DatetimeIndex,
    products: list[str],
) -> dict[str, pd.DataFrame]:
    """All declared H185 features, each a calendar x products frame."""
    totals = pd.DataFrame(
        {product: total_open_interest(panels[product]) for product in products}, index=calendar
    )
    features: dict[str, pd.DataFrame] = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        for name, window in OI_GROWTH_WINDOW.items():
            growth = np.log(totals.where(totals > 0) / totals.shift(window).where(totals > 0))
            features[name] = growth.where(np.isfinite(growth))
    features[FRONT_SHARE] = pd.DataFrame(
        {product: front_share_series(panels[product], terms[product]) for product in products},
        index=calendar,
    )
    return features


def iter_grid():
    for feature in GRID["feature"]:
        for entry_z in GRID["entry_z"]:
            for exit_z in GRID["exit_z"]:
                for k in GRID["k"]:
                    for vol_target in GRID["vol_target"]:
                        yield {
                            "feature": str(feature),
                            "entry_z": float(entry_z),
                            "exit_z": float(exit_z),
                            "k": int(k),
                            "vol_target": float(vol_target),
                        }


def train_collinearity(
    signal: pd.DataFrame, slope: pd.DataFrame, train_index: pd.DatetimeIndex
) -> float:
    """Mean cross-sectional Spearman rank corr of the feature z vs the H184 slope z.

    Input-only diagnostic (no returns), computed on the train block so it cannot
    leak OOS information.  Documents that the OI features are not a re-skin of the
    term-structure signal.
    """
    z_signal = h184.cross_sectional_z(signal)
    z_slope = h184.cross_sectional_z(slope)
    values = []
    for day in train_index:
        left, right = z_signal.loc[day], z_slope.loc[day]
        usable = left.notna() & right.notna()
        if int(usable.sum()) >= 3:
            values.append(float(left[usable].corr(right[usable], method="spearman")))
    return float(np.mean(values)) if values else 0.0


def artifact_dir(out: str | None) -> Path:
    if out:
        path = Path(out).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = (Path(".experiments") / "nf_runs" / f"{EXPERIMENT}_{stamp}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def main(
    out: str | None = None,
    universe: list[tuple[str, str]] | None = None,
    workers: int = WORKERS,
    download_only: bool = False,
) -> dict:
    started = time.time()
    universe = universe or UNIVERSE
    calendar = pd.bdate_range(START, END)
    download_provenance = h184.ensure_cached(universe, calendar, workers=workers)
    if download_only:
        print(json.dumps(download_provenance, indent=2))
        return download_provenance

    artifact = artifact_dir(out)
    products = [f"{source}:{code}" for source, code in universe]
    panels = h184.load_product_data(universe, calendar)
    missing = [product for product in products if product not in panels]
    if missing:
        raise RuntimeError(f"no cached data for {missing}")

    terms = {product: h184.term_panel(panels[product], calendar) for product in products}
    held = {
        product: h184.held_returns(panels[product], terms[product], calendar)
        for product in products
    }
    features = feature_panel(panels, terms, calendar, products)
    slope = pd.DataFrame({product: terms[product]["slope"] for product in products}, index=calendar)
    returns = pd.DataFrame(
        {product: held[product]["return"] for product in products}, index=calendar
    )
    rolls = pd.DataFrame({product: held[product]["roll"] for product in products}, index=calendar)
    provenance = []
    for source, code in universe:
        key = f"{source}:{code}"
        active_days = int(terms[key]["active"].sum())
        observed = str(terms[key].index[terms[key]["active"]].min().date()) if active_days else ""
        declared = FIRST_DATE.get((source, code), "")
        provenance.append(
            {
                "source": source,
                "code": code,
                "key": key,
                "declared_first_date": declared,
                "observed_first_date": observed,
                "effective_first_date": max(declared, observed)
                if declared and observed
                else (declared or observed),
                "active_days": active_days,
                "cached_days": int(terms[key]["front"].notna().sum()),
            }
        )

    train_end = pd.Timestamp(TRAIN_END)
    val_end = pd.Timestamp(VAL_END)
    train_index = calendar[calendar <= train_end]
    val_index = calendar[(calendar > train_end) & (calendar <= val_end)]
    test_index = calendar[calendar > val_end]
    oos_index = calendar[calendar > train_end]

    grid_rows = []
    for params in iter_grid():
        signal = features[params["feature"]]
        score = h184.walk_forward_score(signal, params, returns, rolls, products, train_index)
        grid_rows.append({**params, "wf_train_sharpe": score})
    grid = pd.DataFrame(grid_rows).sort_values("wf_train_sharpe", ascending=False)
    grid.to_csv(artifact / "grid.csv", index=False)
    valid = grid[np.isfinite(grid["wf_train_sharpe"])]
    if valid.empty:
        raise RuntimeError("no valid grid rows: train selection produced no finite score")
    best = valid.iloc[0].to_dict()
    selected_feature = str(best["feature"])
    selected = {
        "feature": selected_feature,
        "entry_z": float(best["entry_z"]),
        "exit_z": float(best["exit_z"]),
        "k": int(best["k"]),
        "vol_target": float(best["vol_target"]),
    }
    signal = features[selected_feature]

    weights, _ = h184.scaled_weights(signal, selected, returns, products)
    full = h184.backtest_metrics(weights, returns, rolls)
    train_result = h184.backtest_metrics(
        weights.reindex(train_index).fillna(0.0),
        returns.reindex(train_index).fillna(0.0),
        rolls.reindex(train_index).fillna(0.0),
    )
    train_sharpe = h184.annualized_sharpe(train_result["returns"])
    oos = h184.backtest_metrics(
        weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    oos_metrics = h184.metrics(oos["returns"], oos["equity"], oos["trades"])

    wf_stability = (
        float(oos_metrics["sharpe"] / train_sharpe)
        if np.isfinite(train_sharpe) and train_sharpe != 0
        else (float("inf") if oos_metrics["sharpe"] > 0 else 0.0)
    )

    bench_weights = h184.passive_long_weights(returns, calendar)
    bench_raw = (bench_weights.shift(1).fillna(0.0) * returns).sum(axis=1).fillna(0.0)
    bench_scale = h184.vol_scale(bench_raw, selected["vol_target"])
    bench_sized = bench_weights.mul(bench_scale, axis=0)
    bench_full = h184.backtest_metrics(bench_sized, returns, rolls)
    bench_oos = h184.backtest_metrics(
        bench_sized.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    bench_metrics = h184.metrics(bench_oos["returns"], bench_oos["equity"], bench_oos["trades"])

    comparison = h184.compare_to_benchmark(oos["returns"], bench_oos["returns"])
    p_value = float(comparison["alpha_p_value"])
    information_ratio = float(comparison["information_ratio"])

    random_target = h184.random_weights(
        weights.reindex(oos_index).fillna(0.0), returns.reindex(oos_index)
    )
    random_result = h184.backtest_metrics(
        random_target,
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    random_metrics = h184.metrics(
        random_result["returns"], random_result["equity"], random_result["trades"]
    )

    inverse_weights, _ = h184.scaled_weights(-signal, selected, returns, products)
    inverse_result = h184.backtest_metrics(
        inverse_weights.reindex(oos_index).fillna(0.0),
        returns.reindex(oos_index).fillna(0.0),
        rolls.reindex(oos_index).fillna(0.0),
    )
    inverse_metrics = h184.metrics(
        inverse_result["returns"], inverse_result["equity"], inverse_result["trades"]
    )

    perturbed = [
        value
        for value in h184.perturbation_sharpes(
            signal, selected, returns, rolls, products, oos_index
        )
        if np.isfinite(value)
    ]
    base_sharpe = oos_metrics["sharpe"]
    min_ratio = (
        float(min(perturbed) / base_sharpe)
        if perturbed and np.isfinite(base_sharpe) and base_sharpe != 0
        else 0.0
    )

    gates = {
        "sharpe_ge_1": bool(np.isfinite(base_sharpe) and base_sharpe >= GATES["min_sharpe"]),
        "trades_ge_50": bool(oos_metrics["trades"] >= GATES["min_trades"]),
        "pf_ge_1_3": bool(
            np.isfinite(oos_metrics["profit_factor"])
            and oos_metrics["profit_factor"] >= GATES["min_profit_factor"]
        ),
        "maxdd_le_15pct": bool(
            np.isfinite(oos_metrics["max_drawdown"])
            and oos_metrics["max_drawdown"] >= -GATES["max_drawdown"]
        ),
        "wf_stability_ge_0_7": bool(
            np.isfinite(wf_stability) and wf_stability >= GATES["min_walkforward_stability"]
        ),
        "worst_regime_ge_0_3": bool(
            np.isfinite(oos_metrics["worst_regime_rolling252_sharpe"])
            and oos_metrics["worst_regime_rolling252_sharpe"] >= GATES["min_worst_regime_sharpe"]
        ),
        "benchmark_p_le_0_05_and_ir_ge_0": h184.benchmark_significance_gate(
            p_value, information_ratio, GATES["max_p_value"]
        ),
        "perturbation_min_ratio_ge_0_5": bool(
            np.isfinite(min_ratio) and min_ratio >= GATES["min_perturbed_sharpe_ratio"]
        ),
    }
    gates_passed = int(sum(gates.values()))
    verdict = "ACCEPT" if gates_passed == len(gates) else "REJECT"

    summary = {
        "experiment": EXPERIMENT,
        "nf_id": NF_ID,
        "hypothesis": HYPOTHESIS,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_sec": round(time.time() - started, 3),
        "data": {
            "source": "SHFE/INE public settlement cross-sections (free/key-less/PIT)",
            "universe": [{"source": s, "code": c} for s, c in universe],
            "products": products,
            "start": START,
            "end": END,
            "train_end": TRAIN_END,
            "val_end": VAL_END,
            "train_rows": int(len(train_index)),
            "val_rows": int(len(val_index)),
            "test_rows": int(len(test_index)),
            "oos_rows": int(len(oos_index)),
            "calendar": "business days; 404 holidays/predating dates skipped",
            "download": download_provenance,
        },
        "provenance": provenance,
        "feature_set": list(FEATURES),
        "oi_growth_window": dict(OI_GROWTH_WINDOW),
        "signal": {
            "construction": "cross-sectional z of the declared OI feature",
            "preregistered_sign": "long top-k / short bottom-k (hedging-pressure direction)",
            "pit": "day-t cross-section only; growth windows use earlier trade dates; shift(1)",
        },
        "grid_size": int(len(grid)),
        "selected": selected,
        "wf_train_sharpe": float(valid.iloc[0]["wf_train_sharpe"]),
        "train_selected_sharpe": float(train_sharpe),
        "full_sample": h184.metrics(full["returns"], full["equity"], full["trades"]),
        "oos_val_test": oos_metrics,
        "val": h184.metrics(
            oos["returns"].reindex(val_index).fillna(0.0),
            oos["equity"].reindex(val_index),
            int((oos["returns"].reindex(val_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "test": h184.metrics(
            oos["returns"].reindex(test_index).fillna(0.0),
            oos["equity"].reindex(test_index),
            int((oos["returns"].reindex(test_index).fillna(0.0).ne(0.0)).sum()),
        ),
        "benchmark_passive_front_month_long_oos": bench_metrics,
        "benchmark_comparison": comparison,
        "ablations": {
            "random_ranking_oos": random_metrics,
            "inverse_signal_oos": inverse_metrics,
        },
        "feature_collinearity_vs_h184_slope_train": {
            name: train_collinearity(frame, slope, train_index) for name, frame in features.items()
        },
        "wf_stability_oos_over_train": float(wf_stability)
        if np.isfinite(wf_stability)
        else str(wf_stability),
        "benchmark_pvalue_two_sided": p_value,
        "information_ratio_vs_passive_front_month": information_ratio,
        "perturbation": {
            "min_ratio": float(min_ratio) if np.isfinite(min_ratio) else str(min_ratio),
            "n_points": len(perturbed),
            "min_sharpe": float(min(perturbed)) if perturbed else None,
        },
        "gates": gates,
        "gates_passed": gates_passed,
        "gates_total": len(gates),
        "verdict": verdict,
        "integrity": {
            "src_qtr_unchanged": True,
            "gate_weakening": False,
            "published_artifacts_modified": False,
            "selection_holdout_feedback": False,
            "real_data": True,
            "cost_one_way_bps": COST_ONE_WAY_BPS,
            "roll_cross_bps": ROLL_CROSS_BPS,
            "benchmark_pvalue_statistic": "two-sided (published gate statistic)",
            "reused_engine": "run_nf_20261114_01_commodity_termstructure_carry.py",
        },
    }
    (artifact / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "gates_passed": f"{gates_passed}/{len(gates)}",
                "artifact": str(artifact),
                "selected_feature": selected_feature,
                "oos_sharpe": oos_metrics["sharpe"],
            },
            indent=2,
        )
    )
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=None, help="artifact directory")
    parser.add_argument("--workers", type=int, default=WORKERS, help="concurrent downloads")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="populate the settlement cache and exit (resumable)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = _parse_args()
    main(arguments.out, workers=arguments.workers, download_only=arguments.download_only)
