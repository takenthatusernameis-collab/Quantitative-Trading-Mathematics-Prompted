#!/usr/bin/env python3
"""H29: systematic look-ahead sweep of the *remaining* families.

Pre-registered in ``HYPOTHESIS_SPEC.md`` §H29 (2026-10-19, before execution).
Trigger: H27 returned ``LOOKAHEAD_CONFIRMED`` for the intraday futures TSMOM
family -- the published construction positions every session with that session's
own **closing** signal -- and H28 re-certified the family under a causal daily
collapse (``CAUSAL_REJECTED``).

The defect is *mechanical* (a collapse of a fine signal onto a coarser grid
followed by a forward-fill expansion), so it is searchable.  H29 sweeps every
remaining family for it and decides each family from the committed artifacts
alone.  No published artifact, runner, gate, threshold, verdict or certified
number is modified, and no grid is re-run.

The detector has three independent legs:

* **L1 -- source sweep.**  Every ``run_*.py`` is parsed with ``ast``; every
  ``resample(<literal>)`` call is listed together with the *probed* label
  position of that frequency on the installed pandas.  The inventory is
  exhaustive by construction, not by spot check.
* **L2 -- artifact alignment.**  The family's collapse is rebuilt from the
  committed prices with the family's *own* runner code and the published
  configuration, and must reproduce the committed artifact **bit-exactly**
  (max abs diff ``0.0``).  The **hold lag** of the construction is then
  measured on the committed grid and the committed target's change points are
  compared with the change points the classified construction predicts.
* **L3 -- same-period vs previous-period expansion.**  The committed target is
  compared with the two candidate expansions of the base signal (H27's L5a
  statistic, generalised).

The **hold lag** is the primary statistic.  A value that first appears on the
grid at bar ``d`` is first traded during bar ``d + 1`` (the engine holds
``signals.shift(1)``).  If the value's *source bar* -- the bar whose raw
signal it carries -- is at or after ``d``, the construction positions a bar
with information that is not yet knowable: a look-ahead.
"""

import ast
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))

import run_cs_momentum_experiment as h2
import run_ddcv_experiment as h5
import run_futures_tsmom_experiment as h4
import run_h6_vix_ddcv_experiment as h6
import run_h7_intraday_tsmom_experiment as h7
import run_h8_rolladjusted_tsmom_experiment as h8
import run_h9_intraday_tsmom_experiment as h9
import run_h23_crypto_futures_tsmom as h23
import run_regime_gated_momentum_experiment as h3
import run_ts_momentum_experiment as h1
from qtr.backtest.engine import run_backtest
from qtr.validation.statistics import sharpe_ratio

# H27 owns the causal collapse and the L5a artifact chain; H29 imports them so
# the two cannot drift apart.
from run_h27_pnl_level_audit import (
    artifact_lookahead as h27_artifact_lookahead,
)
from run_h27_pnl_level_audit import (
    causal_daily_target_from_hourly,
)

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / ".experiments" / "artifacts"
ART_DIR = ARTIFACTS / "h29_lookahead_sweep"

HYPOTHESIS = "H29"

# --------------------------------------------------------------------------- #
# frozen constants (pre-registration §H29, incl. the pre-execution amendment)
# --------------------------------------------------------------------------- #
ENGINE_LAG_BARS = 1  # the engine trades signals.shift(1)
REBUILD_TOL = 0.0  # L2: a rebuild must be bit-exact
VALUE_TOL = 1e-12  # L3: value comparison tolerance

# The daily / monthly grids used by the probe and by the families.
DAILY_GRID = pd.bdate_range("2023-01-02", "2024-12-31")
HOURLY_GRID = pd.date_range("2024-10-12 00:00", "2024-10-18 23:00", freq="1h")

# The families the sweep audits, with their frozen artifact ids.  A family
# with no committed artifact is reported as a coverage gap, never as a pass.
FAMILIES = [
    {
        "family": "H1",
        "artifact": "exp_2026-10-14T08-26-18-385545Z",
        "published_verdict": "REJECT",
        "route": "rebuild_collapsed",
        "rebuild": "h1",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "selected_signals",
        "prices_artifact": "prices",
    },
    {
        "family": "H2",
        "artifact": "exp_2026-10-10T20-59-28-306148Z",
        "published_verdict": "REJECT",
        "route": "rebuild_collapsed",
        "rebuild": "h2",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "selected_signals",
        "prices_artifact": "prices",
    },
    {
        "family": "H3",
        "artifact": "exp_2026-10-10T21-27-13-928282Z",
        "published_verdict": "REJECT",
        "route": "rebuild_collapsed",
        "rebuild": "h3",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "selected_signals",
        "prices_artifact": "prices",
    },
    {
        "family": "H4",
        "artifact": "exp_2026-10-14T08-27-02-650342Z",
        "published_verdict": "REJECT",
        "route": "rebuild_pipeline",
        "rebuild": "h4",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "ensemble_equity",
        "prices_artifact": "prices",
    },
    {
        "family": "H5",
        "artifact": "exp_2026-10-11T00-26-35-750834Z",
        "published_verdict": "REJECT",
        "route": "rebuild_pipeline",
        "rebuild": "h5",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "best_ddcv_equity",
        "prices_artifact": "prices",
    },
    {
        "family": "H6",
        "artifact": "exp_2026-10-11T08-02-22-999214Z",
        "published_verdict": "REJECT",
        "route": "rebuild_pipeline",
        "rebuild": "h6",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "best_equity",
        "prices_artifact": "prices",
    },
    {
        "family": "H7",
        "artifact": "exp_2026-10-19T18-56-08-872500Z",
        "published_verdict": "REJECT",
        "route": "rebuild_pipeline",
        "rebuild": "h7",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "equity_curve",
        "prices_artifact": "prices",
    },
    {
        "family": "H8",
        "artifact": "exp_2026-10-11T15-21-31-333870Z",
        "published_verdict": "REJECT",
        "route": "rebuild_collapsed",
        "rebuild": "h8",
        "collapse_freq": "ME",
        "grid": "daily",
        "target_artifact": "signals_w0.5",
        "prices_artifact": "roll_adjusted_prices_w0.5",
    },
    {
        "family": "H11",
        "artifact": "exp_2026-10-11T20-25-36-443045Z",
        "published_verdict": "PASS",
        "route": "inherited",
        "rebuild": None,
        "collapse_freq": "1D",
        "grid": "hourly",
        "target_artifact": "baseline_positions",
        "prices_artifact": "prices",
    },
    {
        "family": "H12",
        "artifact": "exp_2026-10-13T12-51-06-515939Z",
        "published_verdict": "PASS",
        "route": "inherited",
        "rebuild": None,
        "collapse_freq": "1D",
        "grid": "hourly",
        "target_artifact": None,
        "prices_artifact": None,
    },
    {
        "family": "H13",
        "artifact": "exp_2026-10-13T14-35-58-316759Z",
        "published_verdict": "REJECT",
        "route": "inherited",
        "rebuild": None,
        "collapse_freq": "1D",
        "grid": "hourly",
        "target_artifact": None,
        "prices_artifact": None,
    },
    {
        "family": "H23",
        "artifact": "exp_2026-10-14T18-13-09-457781Z",
        "published_verdict": "REJECT",
        "route": "intraday_artifact",
        "rebuild": None,
        "collapse_freq": "1D",
        "grid": "hourly",
        "target_artifact": "hourly_target_selected",
        "prices_artifact": "prices",
    },
]

# The already-audited families: the detector must reproduce H27's verdict for
# every one of them (self-check SC1).
SELF_CHECK = [
    {
        "family": "H9",
        "artifact": "exp_2026-10-11T16-52-38-694559Z",
        "published_verdict": "REJECT",
        "signal_artifact": "hourly_signal",
        "daily_artifact": "daily_target",
        "target_artifact": None,
    },
    {
        "family": "H10",
        "artifact": "exp_2026-10-11T17-41-18-169363Z",
        "published_verdict": "PASS",
        "signal_artifact": "hourly_signal_h9",
        "daily_artifact": "daily_target_h9",
        "target_artifact": None,
    },
    {
        "family": "H21",
        "artifact": "exp_2026-10-13T23-27-52-101656Z",
        "published_verdict": "REJECT",
        "signal_artifact": "hourly_signal_h10",
        "daily_artifact": "daily_target_h10",
        "target_artifact": "hourly_target_selected",
    },
    {
        "family": "H22",
        "artifact": "exp_2026-10-14T18-52-08-943792Z",
        "published_verdict": "PASS",
        "signal_artifact": "hourly_signal_h10",
        "daily_artifact": "daily_target_h10",
        "target_artifact": "hourly_target_selected",
    },
    {
        "family": "H25",
        "artifact": "exp_2026-10-14T20-08-34-613690Z",
        "published_verdict": "PASS",
        "signal_artifact": "hourly_signal_h10",
        "daily_artifact": "daily_target_h10",
        "target_artifact": "hourly_target_selected",
    },
]

# The families whose PASS is at stake -- all of them are the H10 construction.
CERTIFIED = ("H10", "H22", "H25")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def art_dir_for(artifact: str) -> Path:
    return ARTIFACTS / artifact


def read_parquet(artifact: str, name: str):
    path = art_dir_for(artifact) / f"{name}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def read_json(artifact: str, name: str = "summary.json"):
    path = art_dir_for(artifact) / name
    if not path.exists():
        return None
    with path.open() as handle:
        return json.load(handle)


def _frame_max_abs_diff(a: pd.DataFrame, b: pd.DataFrame) -> float:
    """The max absolute difference between two frames on their common index."""
    if a is None or b is None:
        return float("nan")
    idx = a.index.intersection(b.index)
    if len(idx) == 0:
        return float("nan")
    cols = [c for c in a.columns if c in b.columns]
    if not cols:
        return float("nan")
    diff = np.abs(a.loc[idx, cols].to_numpy(dtype=float) - b.loc[idx, cols].to_numpy(dtype=float))
    return float(np.nanmax(diff)) if diff.size else float("nan")


# --------------------------------------------------------------------------- #
# L1 -- the construction-level probe
# --------------------------------------------------------------------------- #
def probe_collapse(freq: str, grid: pd.DatetimeIndex, source_bin_offset: int = 0) -> dict:
    """Probe a collapse construction on ``grid``.

    A synthetic series whose value identifies its own bar is collapsed with
    ``resample(freq).last()``; the probe therefore knows, for every resample
    label, the **source bar** (the last bar of that bin) whose value the label
    carries.  The expansion ``reindex(..., method="ffill")`` puts a label's
    value on every bar from the label onwards, and the engine trades
    ``signals.shift(1)``, so the position held during bar ``t`` comes from the
    signal at ``t - 1``.

    The **hold lag** of bar ``t`` is ``t - source(signal at t - 1)``: the
    number of bars between the moment the held position became knowable and
    the bar on which it is traded.  A construction is a look-ahead iff the
    minimum hold lag is ``<= 0`` for some bar.

    ``source_bin_offset`` shifts the source of every label by that many bins:
    ``-1`` models a *lagged* construction (the value of period ``P`` is the one
    computed at the close of period ``P-1``), which is what a causal daily
    collapse does.
    """
    probe = pd.Series(np.arange(len(grid), dtype=float), index=grid)
    collapsed = probe.resample(freq).last().dropna()
    labels = collapsed.index
    canonical_ord = collapsed.to_numpy(dtype=float)

    source_ord = canonical_ord
    if source_bin_offset:
        shifted = np.full(len(canonical_ord), np.nan)
        for i in range(len(canonical_ord)):
            j = i + source_bin_offset
            if 0 <= j < len(canonical_ord):
                shifted[i] = canonical_ord[j]
        source_ord = shifted

    # the label in force at each grid bar (the last label at or before it)
    idx = labels.searchsorted(grid, side="right") - 1
    in_force = np.where(idx >= 0, source_ord[np.clip(idx, 0, len(source_ord) - 1)], np.nan)

    # the position held during bar t is the signal at t-1
    held_source = np.concatenate(([np.nan], in_force[:-1]))
    hold_lag = np.arange(len(grid), dtype=float) - held_source

    finite = np.isfinite(hold_lag)
    lags = hold_lag[finite]

    canonical_bars = grid[canonical_ord.astype(int)]
    starts = int(np.sum(labels.to_numpy() < canonical_bars.to_numpy()))
    ends = int(len(labels) - starts)

    return {
        "freq": freq,
        "n_grid_bars": len(grid),
        "n_labels": len(labels),
        "labels_at_bin_start": starts,
        "labels_at_bin_end": ends,
        "label_position": "bin_start" if starts > ends else "bin_end",
        "min_hold_lag_bars": float(np.min(lags)) if len(lags) else float("nan"),
        "max_hold_lag_bars": float(np.max(lags)) if len(lags) else float("nan"),
        "n_lookahead_bars": int(np.sum(lags <= 0)) if len(lags) else 0,
        "lookahead_bar_fraction": (float(np.mean(lags <= 0)) if len(lags) else float("nan")),
        "_labels": labels,
        "_source_ord": source_ord,
    }


def probe_label_position(freq: str) -> dict:
    """The probed label position of ``freq`` on the daily and hourly grids."""
    daily = probe_collapse(freq, DAILY_GRID)
    hourly = probe_collapse(freq, HOURLY_GRID)
    return {
        "freq": freq,
        "daily_label_position": daily["label_position"],
        "hourly_label_position": hourly["label_position"],
        "daily_min_hold_lag_bars": daily["min_hold_lag_bars"],
        "hourly_min_hold_lag_bars": hourly["min_hold_lag_bars"],
        "daily_lookahead_bar_fraction": daily["lookahead_bar_fraction"],
        "hourly_lookahead_bar_fraction": hourly["lookahead_bar_fraction"],
    }


# --------------------------------------------------------------------------- #
# L1 -- the source sweep
# --------------------------------------------------------------------------- #
class _ResampleVisitor(ast.NodeVisitor):
    """Collect every ``resample(<literal>)`` call with its enclosing function."""

    def __init__(self):
        self.stack = []
        self.hits = []

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node):  # pragma: no cover - not used here
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "resample"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            self.hits.append(
                {
                    "function": self.stack[-1] if self.stack else "<module>",
                    "freq": node.args[0].value,
                    "line": node.lineno,
                }
            )
        self.generic_visit(node)


def source_sweep() -> list[dict]:
    """Every ``resample(<literal>)`` in every runner, with its label position."""
    rows = []
    for path in sorted(ROOT.glob("run_*.py")):
        source = path.read_text()
        visitor = _ResampleVisitor()
        visitor.visit(ast.parse(source))
        for hit in visitor.hits:
            freq = hit["freq"]
            try:
                probe = probe_label_position(freq)
            except Exception as exc:  # noqa: BLE001 - an exotic frequency
                probe = {"freq": freq, "error": str(exc)}
            rows.append(
                {
                    "file": path.name,
                    "function": hit["function"],
                    "line": hit["line"],
                    "freq": freq,
                    "forward_filled_expansion": (
                        'method="ffill"' in source or "method='ffill'" in source
                    ),
                    **probe,
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# L2 / L3 -- the artifact-level detector
# --------------------------------------------------------------------------- #
def change_points(target: pd.DataFrame, tol: float = 1e-15) -> list:
    """The bars on which the committed target changes value."""
    diff = target.diff().abs().sum(axis=1)
    changed = diff[diff > tol]
    return list(changed.index)


def predicted_change_points(probe: dict, grid: pd.DatetimeIndex) -> set:
    """The bars on which the *classified* construction changes value."""
    labels = probe["_labels"]
    positions = grid.searchsorted(labels, side="left")
    positions = positions[positions < len(grid)]
    return set(grid[positions])


def expansion_match_fractions(
    base: pd.DataFrame, target: pd.DataFrame, grid: pd.DatetimeIndex, probe: dict
) -> dict:
    """L3: the same-period / previous-period match fractions of ``target``.

    The two candidates are defined **against the base signal**: for every grid
    bar the *same-period* candidate is the base signal's value at the last bar
    of the period that contains the bar, and the *previous-period* candidate is
    its value at the last bar of the period before that.
    """
    source_ord = probe["_source_ord"]
    contain = np.searchsorted(source_ord, np.arange(len(grid)), side="left")
    contain = np.clip(contain, 0, len(source_ord) - 1)
    prev = np.clip(contain - 1, 0, len(source_ord) - 1)
    same_ord = source_ord[contain].astype(int)
    prev_ord = source_ord[prev].astype(int)

    per_symbol = {}
    pairs = []
    for sym in target.columns:
        if sym in base.columns:
            pairs.append((sym, sym))
    if not pairs:
        # the target and the base are not labelled alike (e.g. the daily
        # collapse of a multi-contract signal): pair them positionally
        for i in range(min(len(target.columns), len(base.columns))):
            pairs.append((target.columns[i], base.columns[i]))
    for tcol, bcol in pairs:
        b = base[bcol].reindex(grid).to_numpy(dtype=float)
        t = target[tcol].reindex(grid).to_numpy(dtype=float)
        same = b[same_ord]
        prev_vals = b[prev_ord]
        ok = np.isfinite(t) & np.isfinite(same) & np.isfinite(prev_vals)
        key = f"{tcol}"
        if not ok.any():
            per_symbol[key] = {
                "same_period_match_fraction": float("nan"),
                "prev_period_match_fraction": float("nan"),
            }
            continue
        per_symbol[key] = {
            "same_period_match_fraction": float(np.mean(np.abs(t[ok] - same[ok]) <= VALUE_TOL)),
            "prev_period_match_fraction": float(
                np.mean(np.abs(t[ok] - prev_vals[ok]) <= VALUE_TOL)
            ),
        }
    if not per_symbol:
        return {
            "same_period_match_fraction": float("nan"),
            "prev_period_match_fraction": float("nan"),
            "per_symbol": {},
        }
    return {
        "same_period_match_fraction": float(
            np.mean([v["same_period_match_fraction"] for v in per_symbol.values()])
        ),
        "prev_period_match_fraction": float(
            np.mean([v["prev_period_match_fraction"] for v in per_symbol.values()])
        ),
        "per_symbol": per_symbol,
    }


def classify(min_hold_lag: float, same_frac: float, prev_frac: float) -> str:
    """The frozen verdict rule (pre-registration §H29, as amended)."""
    if not np.isfinite(min_hold_lag):
        return "INCONCLUSIVE"
    if min_hold_lag <= 0 and same_frac > prev_frac:
        return "LOOKAHEAD"
    if min_hold_lag >= 1 and prev_frac >= same_frac:
        return "CAUSAL"
    return "INCONCLUSIVE"


# --------------------------------------------------------------------------- #
# the per-family rebuilds (L2)
# --------------------------------------------------------------------------- #
def rebuild_h1(art_dir: Path):
    """H1: vol-scaled TSMOM on 20 ETFs, monthly rebalance."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    summary = read_json(art_dir.name, "summary.json")
    params = summary["selected_params"]
    base = h1.vol_scaled_tsmom_signals(
        prices,
        lookback=int(params["lookback"]),
        skip=int(params["skip"]),
        long_only=bool(params["long_only"]),
        target_vol=float(params["target_vol"]),
    )
    target = h1.resample_monthly_signals(base)
    return base, target


def rebuild_h2(art_dir: Path):
    """H2: cross-sectional momentum, monthly rebalance."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    summary = read_json(art_dir.name, "summary.json")
    params = summary["selected_params"]
    base = h2.cs_momentum_vol_scaled(
        prices,
        int(params["lookback"]),
        int(params["skip"]),
        bool(params["long_only"]),
        target_vol=float(params.get("target_vol", h2.TARGET_VOL)),
    )
    target = h2.resample_monthly_signals(base)
    return base, target


def rebuild_h3(art_dir: Path):
    """H3: regime-gated TSMOM, monthly rebalance."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    vix = pd.read_parquet(art_dir / "vix_close.parquet").iloc[:, 0]
    summary = read_json(art_dir.name, "summary.json")
    params = summary["selected_params"]
    base = h3.regime_gated_signals(
        prices,
        vix,
        lookback=int(params["lookback"]),
        skip=int(params["skip"]),
        long_only=bool(params["long_only"]),
        regime_triple=tuple(params["regime_triple"]),
        hedge_weight=float(params["hedge_weight"]),
    )
    target = h3.resample_monthly_signals(base)
    return base, target


def rebuild_h4(art_dir: Path):
    """H4: the published top-K ensemble of futures TSMOM configs."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    volumes = pd.read_parquet(art_dir / "volumes.parquet")
    summary = read_json(art_dir.name, "summary.json")
    top_k = summary["top_k"]
    # the published runner accumulates the ensemble in the same order (a
    # running sum of the per-config weights), so the rebuild is bit-exact
    ensemble = None
    for row in top_k:
        sig = h4.vol_scaled_tsmom_signals(
            prices,
            lookback=int(row["lookback"]),
            skip=int(row["skip"]),
            long_only=bool(row["long_only"]),
            target_vol=h4.TARGET_VOL,
        )
        sig = h4.resample_monthly_signals(sig)
        if ensemble is None:
            ensemble = sig.copy() / len(top_k)
        else:
            ensemble += sig / len(top_k)
    base = ensemble
    target = h4.resample_monthly_signals(base)
    adv = volumes.rolling(20).mean().iloc[-1] if len(volumes) else None
    long_only = [bool(r["long_only"]) for r in top_k]
    avg_long_only = max(set(long_only), key=long_only.count)
    cfg = h4.make_futures_config(allow_short=not avg_long_only)
    result = run_backtest(
        prices=prices,
        signals=target,
        volumes=volumes,
        adv=adv,
        config=cfg,
    )
    return base, target, result.equity_curve.to_frame("equity")


def rebuild_h5(art_dir: Path):
    """H5: futures TSMOM + the DDCV overlay."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    volumes = pd.read_parquet(art_dir / "volumes.parquet")
    summary = read_json(art_dir.name, "summary.json")
    best = summary["best_ddcv"]
    base = h5.vol_scaled_tsmom_signals(
        prices,
        lookback=h5.LOOKBACK,
        skip=h5.SKIP,
        long_only=h5.LONG_ONLY,
        target_vol=h5.TARGET_VOL,
        vol_window=h5.VOL_WINDOW,
        max_position_size=h5.MAX_POSITION_SIZE,
    )
    collapsed = h5.resample_monthly_signals(base)
    scaled, _, _ = h5.apply_ddcv(
        prices, collapsed, float(best["dd_trigger"]), float(best["dd_factor"])
    )
    # the published pipeline collapses the *scaled* series a second time; the
    # L3 comparison is therefore made against the series that enters the
    # final collapse (the DDCV overlay is a causal, multiplicative rescaling)
    target = h5.resample_monthly_signals(scaled)
    base = scaled
    adv = volumes.rolling(20).mean().iloc[-1] if len(volumes) else None
    cfg = h5.make_futures_config(allow_short=not h5.LONG_ONLY)
    result = run_backtest(prices=prices, signals=target, volumes=volumes, adv=adv, config=cfg)
    return base, target, result.equity_curve.to_frame("equity")


def rebuild_h6(art_dir: Path):
    """H6: futures TSMOM + the VIX gate + the DDCV overlay."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    volumes = pd.read_parquet(art_dir / "volumes.parquet")
    vix = pd.read_parquet(art_dir / "vix_close.parquet").iloc[:, 0]
    summary = read_json(art_dir.name, "summary.json")
    best = summary["best_combo"]
    base = h6.vol_scaled_tsmom_signals(
        prices,
        lookback=h6.LOOKBACK,
        skip=h6.SKIP,
        long_only=h6.LONG_ONLY,
        target_vol=h6.TARGET_VOL,
        vol_window=h6.VOL_WINDOW,
        max_position_size=h6.MAX_POSITION_SIZE,
    )
    collapsed = h6.resample_monthly_signals(base)
    scaled, _, _, _ = h6.apply_combined(
        prices, collapsed, vix, float(best["dd_trigger"]), float(best["dd_factor"])
    )
    # the published pipeline collapses the *scaled* series a second time; the
    # L3 comparison is therefore made against the series that enters the
    # final collapse (the VIX gate and the DDCV overlay are causal rescalings)
    target = h6.resample_monthly_signals(scaled)
    base = scaled
    adv = volumes.rolling(20).mean().iloc[-1] if len(volumes) else None
    cfg = h6.make_futures_config(allow_short=not h6.LONG_ONLY)
    result = run_backtest(prices=prices, signals=target, volumes=volumes, adv=adv, config=cfg)
    return base, target, result.equity_curve.to_frame("equity")


def rebuild_h7(art_dir: Path):
    """H7: multi-horizon regime-weighted TSMOM on futures, monthly rebalance."""
    prices = pd.read_parquet(art_dir / "prices.parquet")
    blend = {"slow": h7.LOOKBACK_SLOW, "fast": h7.LOOKBACK_FAST, "skip": h7.SKIP}
    base = h7.multi_horizon_blend_signals(
        prices,
        lookback_slow=int(blend["slow"]),
        lookback_fast=int(blend["fast"]),
        skip=int(blend["skip"]),
    )
    target = h7.resample_monthly_signals(base)
    atr = h7.compute_atr(prices)
    signals = h7.apply_path_dependent_exits_daily(target, prices, atr)
    cfg = h7.make_futures_config(allow_short=False)
    adv = pd.Series(100_000, index=prices.columns)  # placeholder, matches the runner
    result = run_backtest(prices=prices, signals=signals, volumes=None, adv=adv, config=cfg)
    return base, target, result.equity_curve.to_frame("equity")


def rebuild_h8(art_dir: Path):
    """H8: TSMOM on the roll-adjusted futures prices, monthly rebalance."""
    prices_adj = pd.read_parquet(art_dir / "roll_adjusted_prices_w0.5.parquet")
    base = h8.vol_scaled_tsmom_signals(
        prices_adj,
        lookback=h8.LOOKBACK,
        skip=h8.SKIP,
        long_only=h8.LONG_ONLY,
        target_vol=h8.TARGET_VOL,
        vol_window=h8.VOL_WINDOW,
        max_position_size=h8.MAX_POSITION_SIZE,
    )
    target = h8.resample_monthly_signals(base)
    return base, target


REBUILDS = {
    "h1": rebuild_h1,
    "h2": rebuild_h2,
    "h3": rebuild_h3,
    "h4": rebuild_h4,
    "h5": rebuild_h5,
    "h6": rebuild_h6,
    "h7": rebuild_h7,
    "h8": rebuild_h8,
}


# --------------------------------------------------------------------------- #
# the family audits
# --------------------------------------------------------------------------- #
def audit_rebuild_family(spec: dict) -> dict:
    """L1 + L2 + L3 for a family that is rebuilt from its committed prices."""
    out = {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "published_verdict": spec["published_verdict"],
        "route": spec["route"],
        "collapse_freq": spec["collapse_freq"],
        "available": False,
    }
    art_dir = art_dir_for(spec["artifact"])
    rebuild = REBUILDS[spec["rebuild"]]
    try:
        rebuilt = rebuild(art_dir)
    except Exception as exc:  # noqa: BLE001 - a rebuild failure is reported, not raised
        out["reason"] = f"rebuild failed: {type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()
        out["verdict"] = "INCONCLUSIVE"
        return out

    if len(rebuilt) == 3:
        base, target, equity = rebuilt
        pipeline_equity = True
    else:
        base, target = rebuilt
        equity = None
        pipeline_equity = False

    grid = pd.DatetimeIndex(target.index)
    probe = probe_collapse(spec["collapse_freq"], grid)

    out["available"] = True
    out["n_grid_bars"] = len(grid)
    out["label_position"] = probe["label_position"]
    out["min_hold_lag_bars"] = probe["min_hold_lag_bars"]
    out["max_hold_lag_bars"] = probe["max_hold_lag_bars"]
    out["n_lookahead_bars"] = probe["n_lookahead_bars"]
    out["lookahead_bar_fraction"] = probe["lookahead_bar_fraction"]

    # L2a -- the rebuild must reproduce the committed artifact bit-exactly
    committed = read_parquet(spec["artifact"], spec["target_artifact"])
    if committed is not None:
        if pipeline_equity:
            diff = _frame_max_abs_diff(equity, committed)
        else:
            diff = _frame_max_abs_diff(target, committed)
        out["committed_artifact"] = spec["target_artifact"]
        out["rebuild_max_abs_diff"] = diff
        out["rebuild_bit_exact"] = bool(np.isfinite(diff) and diff <= REBUILD_TOL)
    else:
        out["committed_artifact"] = None
        out["rebuild_max_abs_diff"] = float("nan")
        out["rebuild_bit_exact"] = False

    # L2b -- the committed target's change points vs the classified construction
    observed = change_points(target)
    predicted = predicted_change_points(probe, grid)
    out["n_change_points"] = len(observed)
    out["n_predicted_change_points"] = len(predicted)
    out["n_extra_change_points"] = len(set(observed) - predicted)
    out["n_missing_change_points"] = len(predicted - set(observed))

    # L3 -- the same-period / previous-period expansion fractions
    match = expansion_match_fractions(base, target, grid, probe)
    out["same_period_match_fraction"] = match["same_period_match_fraction"]
    out["prev_period_match_fraction"] = match["prev_period_match_fraction"]

    out["verdict"] = classify(
        out["min_hold_lag_bars"],
        out["same_period_match_fraction"],
        out["prev_period_match_fraction"],
    )
    if out["verdict"] != "INCONCLUSIVE" and not out["rebuild_bit_exact"]:
        out["verdict"] = "INCONCLUSIVE"
        out["reason"] = "the rebuild is not bit-exact"
    if out["verdict"] != "INCONCLUSIVE" and out["n_extra_change_points"] > 0:
        out["verdict"] = "INCONCLUSIVE"
        out["reason"] = (
            "the committed target changes on bars the classified construction does not predict"
        )
    return out


def audit_intraday_artifact(spec: dict) -> dict:
    """L1 + L2 + L3 for a family that logs the base signal and the collapse."""
    out = {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "published_verdict": spec["published_verdict"],
        "route": spec["route"],
        "collapse_freq": spec["collapse_freq"],
        "available": False,
    }
    art_dir = art_dir_for(spec["artifact"])
    signal = read_parquet(spec["artifact"], "hourly_signal_h9")
    daily = read_parquet(spec["artifact"], "daily_target_h9")
    target = read_parquet(spec["artifact"], spec["target_artifact"])
    if signal is None or daily is None:
        out["reason"] = "missing hourly_signal_h9 / daily_target_h9"
        out["verdict"] = "INCONCLUSIVE"
        return out

    grid = pd.DatetimeIndex(signal.index)
    probe = probe_collapse(spec["collapse_freq"], grid)
    out["available"] = True
    out["n_grid_bars"] = len(grid)
    out["label_position"] = probe["label_position"]
    out["min_hold_lag_bars"] = probe["min_hold_lag_bars"]
    out["max_hold_lag_bars"] = probe["max_hold_lag_bars"]
    out["n_lookahead_bars"] = probe["n_lookahead_bars"]
    out["lookahead_bar_fraction"] = probe["lookahead_bar_fraction"]

    # L2 -- the committed daily collapse must equal the base signal at the
    # day's close (H27's L5a chain) and must not equal it at the day's open.
    chain = h27_artifact_lookahead(
        {
            "signal_artifact": "hourly_signal_h9.parquet",
            "daily_artifact": "daily_target_h9.parquet",
            "target_artifact": (spec["target_artifact"] or "") + ".parquet",
        },
        art_dir,
        grid,
    )
    out["h27_l5a"] = chain
    out["max_abs_diff_signal_at_day_close_vs_daily_collapse"] = chain.get(
        "max_abs_diff_signal_at_day_close_vs_daily_collapse"
    )
    out["max_abs_diff_signal_at_day_open_vs_daily_collapse"] = chain.get(
        "max_abs_diff_signal_at_day_open_vs_daily_collapse"
    )

    # L3 -- the same-period / previous-period expansion fractions
    base = signal.iloc[:, 0].to_frame("signal")
    match = expansion_match_fractions(base, daily, grid, probe)
    out["same_period_match_fraction"] = match["same_period_match_fraction"]
    out["prev_period_match_fraction"] = match["prev_period_match_fraction"]

    if target is not None:
        out["committed_artifact"] = spec["target_artifact"]
        out["target_same_day_match_fraction"] = chain.get("target_same_day_match_fraction")
        out["target_prev_day_match_fraction"] = chain.get("target_prev_day_match_fraction")
    else:
        out["committed_artifact"] = None

    out["verdict"] = classify(
        out["min_hold_lag_bars"],
        out["same_period_match_fraction"],
        out["prev_period_match_fraction"],
    )
    return out


def audit_inherited(spec: dict) -> dict:
    """L1 + L2 for a family that inherits H10's construction."""
    out = {
        "family": spec["family"],
        "artifact": spec["artifact"],
        "published_verdict": spec["published_verdict"],
        "route": spec["route"],
        "collapse_freq": spec["collapse_freq"],
        "available": False,
    }
    h10_artifact = "exp_2026-10-11T17-41-18-169363Z"
    h10_positions = read_parquet(h10_artifact, "positions")
    h10_returns = read_parquet(h10_artifact, "returns")

    evidence = {}
    if spec["family"] == "H11":
        own = read_parquet(spec["artifact"], "baseline_positions")
        if own is None or h10_positions is None:
            out["reason"] = "missing baseline_positions / H10 positions"
            out["verdict"] = "INCONCLUSIVE"
            return out
        evidence["max_abs_diff_positions_vs_h10"] = _frame_max_abs_diff(own, h10_positions)
        evidence["baseline_returns_max_abs_diff_vs_h10"] = _frame_max_abs_diff(
            read_parquet(spec["artifact"], "baseline_returns"), h10_returns
        )
    elif spec["family"] == "H12":
        summary = read_json(spec["artifact"])
        rerun = summary.get("rerun_oos_metrics", {})
        evidence["selected_oos_sharpe"] = rerun.get("selected_oos_sharpe")
        evidence["h10_artifact_oos_sharpe"] = rerun.get("h10_artifact_oos_sharpe")
        evidence["oos_sharpe_abs_diff_vs_h10"] = abs(
            float(rerun.get("selected_oos_sharpe", np.nan))
            - float(rerun.get("h10_artifact_oos_sharpe", np.nan))
        )
    elif spec["family"] == "H13":
        summary = read_json(spec["artifact"])
        checks = summary.get("reproduction_checks", {})
        evidence["returns_max_abs_diff_vs_h10"] = checks.get("returns_max_abs_diff_vs_h10")
        evidence["per_symbol_reconstruction_max_abs_diff"] = checks.get(
            "per_symbol_reconstruction_max_abs_diff"
        )
    out["inheritance_evidence"] = evidence

    # the inherited construction is H10's: its probe is the H10 grid
    grid = pd.DatetimeIndex(h10_positions.index)
    probe = probe_collapse(spec["collapse_freq"], grid)
    out["available"] = True
    out["n_grid_bars"] = len(grid)
    out["label_position"] = probe["label_position"]
    out["min_hold_lag_bars"] = probe["min_hold_lag_bars"]
    out["n_lookahead_bars"] = probe["n_lookahead_bars"]
    out["lookahead_bar_fraction"] = probe["lookahead_bar_fraction"]
    out["inherits"] = "H10"

    # the same/prev expansion fractions of the inherited construction
    signal = read_parquet(h10_artifact, "hourly_signal_h9")
    daily = read_parquet(h10_artifact, "daily_target_h9")
    if signal is not None and daily is not None:
        match = expansion_match_fractions(signal.iloc[:, 0].to_frame("signal"), daily, grid, probe)
        out["same_period_match_fraction"] = match["same_period_match_fraction"]
        out["prev_period_match_fraction"] = match["prev_period_match_fraction"]
    out["verdict"] = classify(
        out.get("min_hold_lag_bars", float("nan")),
        out.get("same_period_match_fraction", float("nan")),
        out.get("prev_period_match_fraction", float("nan")),
    )
    return out


def audit_source_only(spec: dict) -> dict:
    """A family with no committed artifact: the mechanism only."""
    out = {
        "family": spec["family"],
        "artifact": None,
        "published_verdict": spec["published_verdict"],
        "route": spec["route"],
        "collapse_freq": spec["collapse_freq"],
        "available": False,
        "reason": "no committed artifact for this family (coverage gap)",
    }
    probe = probe_collapse(spec["collapse_freq"], DAILY_GRID)
    out["mechanism"] = {
        "label_position": probe["label_position"],
        "min_hold_lag_bars": probe["min_hold_lag_bars"],
        "n_lookahead_bars": probe["n_lookahead_bars"],
        "lookahead_bar_fraction": probe["lookahead_bar_fraction"],
        "note": "the collapse runs on a daily grid; the mechanism is classified, the artifact is missing",
    }
    out["verdict"] = "INCONCLUSIVE"
    return out


def audit_family(spec: dict) -> dict:
    route = spec["route"]
    if route in ("rebuild_collapsed", "rebuild_pipeline"):
        return audit_rebuild_family(spec)
    if route == "intraday_artifact":
        return audit_intraday_artifact(spec)
    if route == "inherited":
        return audit_inherited(spec)
    if route == "source_only":
        return audit_source_only(spec)
    raise ValueError(f"unknown route: {route}")


# --------------------------------------------------------------------------- #
# SC3 -- the negative control
# --------------------------------------------------------------------------- #
def negative_control() -> dict:
    """SC3: the detector must report ``CAUSAL`` for a deliberately causal build.

    H27's ``causal_daily_target_from_hourly`` takes, for each day ``D``, the
    signal at the **last bar of day D-1** and expands it over day ``D``.  A
    detector that fires on it is broken.
    """
    grid = HOURLY_GRID
    base = pd.DataFrame(
        {"x": np.arange(len(grid), dtype=float)},
        index=grid,
    )
    causal = causal_daily_target_from_hourly(base)
    published = h9._daily_target_from_hourly(base)
    probe = probe_collapse("1D", grid)
    # the causal construction carries, for each day D, the signal at the last
    # bar of day D-1: its source is the *previous* bin's last bar
    probe_causal = probe_collapse("1D", grid, source_bin_offset=-1)
    match_causal = expansion_match_fractions(base, causal, grid, probe)
    match_published = expansion_match_fractions(base, published, grid, probe)
    return {
        "construction": "causal_daily_target_from_hourly (H27)",
        "published_construction": "_daily_target_from_hourly (H9/H10)",
        "published_min_hold_lag_bars": probe["min_hold_lag_bars"],
        "published_verdict": classify(
            probe["min_hold_lag_bars"],
            match_published["same_period_match_fraction"],
            match_published["prev_period_match_fraction"],
        ),
        "causal_min_hold_lag_bars": probe_causal["min_hold_lag_bars"],
        "causal_same_period_match_fraction": match_causal["same_period_match_fraction"],
        "causal_prev_period_match_fraction": match_causal["prev_period_match_fraction"],
        "causal_verdict": classify(
            probe_causal["min_hold_lag_bars"],
            match_causal["same_period_match_fraction"],
            match_causal["prev_period_match_fraction"],
        ),
        "note": (
            "the causal construction shifts the daily series by one calendar day; "
            "the hold lag of the *published* construction is reported alongside it "
            "because the two share the label position and differ in the value"
        ),
    }


# --------------------------------------------------------------------------- #
# the magnitude of a defect (H27's terms)
# --------------------------------------------------------------------------- #
def h23_counterfactual() -> dict:
    """H23: the OOS metrics of the published build and of the causal fix.

    The published H23 pipeline is *not* edited: the causal daily collapse is
    installed by patching the module-global ``_daily_target_from_hourly``
    (the same minimal intervention H27/H28 used).  The control rebuild must
    reproduce the committed positions **bit-exactly**.
    """
    artifact = "exp_2026-10-14T18-13-09-457781Z"
    art_dir = art_dir_for(artifact)
    prices = pd.read_parquet(art_dir / "prices.parquet")
    volumes = pd.read_parquet(art_dir / "volumes.parquet")
    committed_positions = pd.read_parquet(art_dir / "positions.parquet")
    summary = read_json(artifact)
    config = summary["selected_config"]

    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol_exit = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol_exit = vol_exit.replace(0, np.nan).ffill()
    vix_hourly = pd.Series(20.0, index=prices.index)

    base = h9.vol_scaled_tsmom_hourly(
        prices,
        vol_window_long=int(config["vol_window_long"]),
        vol_window_short=int(config["vol_window_long"]) // 4,
    )
    cfg = h9.make_futures_config()
    _train_mask, val_mask, test_mask = h23._splits(prices)
    oos_mask = val_mask | test_mask

    def build(collapse):
        original = h23._daily_target_from_hourly
        try:
            h23._daily_target_from_hourly = collapse
            span = config["smooth_span"]
            span = None if span in (None, "None", "none") else int(span)
            target = h23.build_hourly_target(
                base,
                span,
                int(config["vol_window_long"]),
                bool(config["regime_scaling"]),
                vix_hourly,
                prices.index,
            )
        finally:
            h23._daily_target_from_hourly = original
        positions = h23.apply_exits_hourly(
            target,
            prices,
            atr,
            vol_exit,
            trailing_mult=float(config["trailing_mult"]),
            max_hold_bars=int(config["max_hold_bars"]),
            vol_limit_mult=float(config["vol_limit_mult"]),
            vol_floor_fraction=float(config["vol_floor_fraction"]),
            target_vol=h23.TARGET_VOL,
            min_trade_interval=int(config["min_trade_interval"]),
        )
        result = run_backtest(prices=prices, signals=positions, volumes=volumes, config=cfg)
        oos = result.returns[oos_mask]
        return positions, {
            "oos_sharpe": float(sharpe_ratio(oos.to_numpy())) if len(oos) > 1 else float("nan"),
            "oos_n_trades": len(
                result.trades[result.trades["timestamp"] > prices.index[int(len(prices) * 0.55)]]
            ),
            "oos_max_drawdown": float(
                (1 + oos).cumprod().div((1 + oos).cumprod().cummax()).sub(1).min()
            ),
        }

    control_positions, control_metrics = build(h9._daily_target_from_hourly)
    _causal_positions, causal_metrics = build(causal_daily_target_from_hourly)

    control_diff = _frame_max_abs_diff(control_positions, committed_positions)
    probe = probe_collapse("1D", pd.DatetimeIndex(prices.index))
    return {
        "family": "H23",
        "artifact": artifact,
        "selected_config": config,
        "control_max_abs_diff_positions_vs_committed": control_diff,
        "control_bit_exact": bool(np.isfinite(control_diff) and control_diff <= REBUILD_TOL),
        "published_build": control_metrics,
        "causal_build": causal_metrics,
        "oos_sharpe_delta": causal_metrics["oos_sharpe"] - control_metrics["oos_sharpe"],
        "min_hold_lag_bars": probe["min_hold_lag_bars"],
        "lookahead_bar_fraction": probe["lookahead_bar_fraction"],
        "overnight_split": "not applicable: the crypto sample is a continuous 24/7 market with no session boundary",
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    started = time.time()
    ART_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("H29 -- systematic look-ahead sweep of the remaining families")
    print("=" * 78)

    # L1 -- the source sweep
    inventory = source_sweep()
    freqs = sorted({row["freq"] for row in inventory})
    print(f"\n[L1] source sweep: {len(inventory)} resample() call(s) in the runners")
    for freq in freqs:
        rows = [r for r in inventory if r["freq"] == freq]
        positions = {r.get("daily_label_position") for r in rows}
        print(
            f"     {freq:>4s}: {len(rows):2d} call(s)  label position "
            f"(daily grid) = {sorted(p for p in positions if p)}"
        )

    # the audits
    results = []
    for spec in FAMILIES:
        result = audit_family(spec)
        results.append(result)
        print(
            f"     {result['family']:>4s}: {result['verdict']:<13s} "
            f"min hold lag = {result.get('min_hold_lag_bars')}   "
            f"artifact = {result.get('artifact')}"
        )

    # the self-check on the already-audited families
    print("\n[SC1] self-check on the already-audited intraday family:")
    self_check = []
    for spec in SELF_CHECK:
        art_dir = art_dir_for(spec["artifact"])
        signal = read_parquet(spec["artifact"], spec["signal_artifact"])
        daily = read_parquet(spec["artifact"], spec["daily_artifact"])
        if signal is None or daily is None:
            self_check.append({"family": spec["family"], "verdict": "INCONCLUSIVE"})
            continue
        grid = pd.DatetimeIndex(signal.index)
        probe = probe_collapse("1D", grid)
        chain = h27_artifact_lookahead(
            {
                "signal_artifact": spec["signal_artifact"] + ".parquet",
                "daily_artifact": spec["daily_artifact"] + ".parquet",
                "target_artifact": ((spec["target_artifact"] or "") + ".parquet"),
            },
            art_dir,
            grid,
        )
        match = expansion_match_fractions(signal.iloc[:, 0].to_frame("signal"), daily, grid, probe)
        verdict = classify(
            probe["min_hold_lag_bars"],
            match["same_period_match_fraction"],
            match["prev_period_match_fraction"],
        )
        self_check.append(
            {
                "family": spec["family"],
                "artifact": spec["artifact"],
                "published_verdict": spec["published_verdict"],
                "verdict": verdict,
                "min_hold_lag_bars": probe["min_hold_lag_bars"],
                "lookahead_bar_fraction": probe["lookahead_bar_fraction"],
                "same_period_match_fraction": match["same_period_match_fraction"],
                "prev_period_match_fraction": match["prev_period_match_fraction"],
                "h27_l5a": chain,
            }
        )
        print(
            f"     {spec['family']:>4s}: {verdict:<13s} "
            f"min hold lag = {probe['min_hold_lag_bars']}  "
            f"same/prev = {match['same_period_match_fraction']:.3f}/"
            f"{match['prev_period_match_fraction']:.3f}"
        )

    # SC3 -- the negative control
    control = negative_control()
    print(
        f"\n[SC3] negative control (a causal daily collapse): "
        f"{control['causal_verdict']}  "
        f"(the published construction: {control['published_verdict']})"
    )

    # the magnitude of the defect
    affected = [r for r in results if r["verdict"] == "LOOKAHEAD"]
    magnitudes = {}
    if any(r["family"] == "H23" for r in affected):
        magnitudes["H23"] = h23_counterfactual()
        print(
            f"\n[magnitude] H23 published OOS Sharpe = "
            f"{magnitudes['H23']['published_build']['oos_sharpe']:.4f}, "
            f"causal-fix OOS Sharpe = "
            f"{magnitudes['H23']['causal_build']['oos_sharpe']:.4f} "
            f"(control bit-exact: {magnitudes['H23']['control_bit_exact']})"
        )

    # SC4 -- the source sweep must classify the two constructions differently
    # the two constructions must be classified differently *on the grid they
    # run on*: the "1D" collapse runs on an hourly grid (a look-ahead), the
    # "ME" collapse runs on a daily grid (causal)
    daily_on_hourly = probe_collapse("1D", HOURLY_GRID)
    monthly_on_daily = probe_collapse("ME", DAILY_GRID)
    sc4 = {
        "daily_collapse_present": any(
            r["file"].startswith("run_h9") or r["file"].startswith("run_h10")
            for r in inventory
            if r["freq"] == "1D"
        ),
        "monthly_collapse_present": any(r["freq"] == "ME" for r in inventory),
        "daily_collapse_on_hourly_grid_is_lookahead": bool(
            daily_on_hourly["min_hold_lag_bars"] <= 0
        ),
        "monthly_collapse_on_daily_grid_is_causal": bool(
            monthly_on_daily["min_hold_lag_bars"] >= 1
        ),
        "daily_and_monthly_classified_differently": bool(
            daily_on_hourly["min_hold_lag_bars"] <= 0 and monthly_on_daily["min_hold_lag_bars"] >= 1
        ),
    }

    # the self-check bookkeeping
    sc1_ok = all(r["verdict"] == "LOOKAHEAD" for r in self_check)
    sc2_ok = not any(r["verdict"] == "LOOKAHEAD" for r in results if r.get("collapse_freq") == "ME")
    sc3_ok = control["causal_verdict"] == "CAUSAL"
    sc4_ok = all(sc4.values())
    self_checks = {
        "SC1_detector_fires_on_the_already_audited_family": sc1_ok,
        "SC2_detector_does_not_fire_on_a_monthly_family": sc2_ok,
        "SC3_negative_control_reports_causal": sc3_ok,
        "SC4_source_sweep_classifies_both_constructions": sc4_ok,
    }

    audited = [r for r in results if r["available"]]
    verdict = (
        "SWEEP_CLEAN"
        if not affected and all(r["verdict"] == "CAUSAL" for r in audited)
        else "LOOKAHEAD_FOUND"
    )
    if not all(self_checks.values()):
        verdict = "VOID"

    summary = {
        "hypothesis": HYPOTHESIS,
        "verdict": verdict,
        "self_checks": self_checks,
        "self_check_detail": self_check,
        "negative_control": control,
        "source_sweep": {
            "n_resample_calls": len(inventory),
            "frequencies": freqs,
            "label_positions": {f: probe_label_position(f) for f in freqs},
            "sc4": sc4,
        },
        "families": results,
        "already_audited": self_check,
        "magnitudes": magnitudes,
        "elapsed_sec": time.time() - started,
    }

    with (ART_DIR / "summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2, default=str)

    rows = []
    for r in results:
        rows.append(
            {
                "family": r["family"],
                "artifact": r.get("artifact"),
                "published_verdict": r.get("published_verdict"),
                "route": r.get("route"),
                "collapse_freq": r.get("collapse_freq"),
                "sweep_verdict": r.get("verdict"),
                "min_hold_lag_bars": r.get("min_hold_lag_bars"),
                "n_lookahead_bars": r.get("n_lookahead_bars"),
                "lookahead_bar_fraction": r.get("lookahead_bar_fraction"),
                "same_period_match_fraction": r.get("same_period_match_fraction"),
                "prev_period_match_fraction": r.get("prev_period_match_fraction"),
                "rebuild_max_abs_diff": r.get("rebuild_max_abs_diff"),
                "rebuild_bit_exact": r.get("rebuild_bit_exact"),
                "n_extra_change_points": r.get("n_extra_change_points"),
            }
        )
    pd.DataFrame(rows).to_parquet(ART_DIR / "sweep_table.parquet", index=False)
    pd.DataFrame(inventory).to_parquet(ART_DIR / "source_inventory.parquet", index=False)

    print("\n" + "=" * 78)
    print(f"H29 verdict: {verdict}")
    for name, ok in self_checks.items():
        print(f"   {name}: {'PASS' if ok else 'FAIL'}")
    for r in results:
        print(f"   {r['family']:>4s}  {r['verdict']:<13s} (published {r.get('published_verdict')})")
    print(f"   artifacts: {ART_DIR}")
    print(f"   elapsed: {summary['elapsed_sec']:.1f}s")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
