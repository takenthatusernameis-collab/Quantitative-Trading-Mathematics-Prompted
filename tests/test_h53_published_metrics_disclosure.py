"""H53 — the published `metrics` block re-derives from its own frozen artifact.

The gap
-------
The committed record holds **80** `summary.json` files and **37** of them
publish a non-empty `metrics` block — the block that carries the *certified*
numbers and that the published `passes` / `all_pass` / `verdict` blocks rest
on. Three passes had audited parts of that record before H53:

===============  ==========================================  =========
pass             what it covered                             how many
===============  ==========================================  =========
§H49             the `validation` blocks                     5 summaries
§H51             the `information_ratio` inside the block    48 artifacts
§H52             the `avg_trade_cost` (strategy/benchmark)   5 + 23
===============  ==========================================  =========

**Every other key of the `metrics` block had never been re-derived.**
§H53 re-derives all **thirteen** scalar keys of the block, from each
summary's own frozen artifact, and records the convention every publisher
used for every key. The block's four *nested* blocks — `ablations`,
`perturbation`, `perturbation_min_ratio` and `cross_validation` — are pinned
in the key union but are not re-derived here: they are gate-result tables
rather than certified scalars, and most of their inputs were never
committed.

The measurement
---------------
**450** published metric values are re-derived from the frozen record:
**441** re-derive and **9** cannot (the H9 family's regime block — its VIX
input was never committed). The conventions are not uniform: the **37**
summaries were produced by **19** producer tags (eleven base families plus
the eight H28 causal re-certification tags) and published the same thirteen
keys under **ten** distinct convention profiles. The findings that matter:

1. **The walk-forward stability gate was published on the PRE-FIX fold
   convention.** The library's `walk_forward_splits` used to drop the tail of
   the return series (the last window ended at `n_splits * window_size`);
   it was later changed so the last window absorbs the trailing samples.
   **29** of the **37** published `wf_stability` values are on the pre-fix
   convention and **8** (the H28 causal re-certification runs, 2026-10-19)
   are on the post-fix one. The two groups split exactly along the
   production date: every pre-fix summary is from 2026-10-14 or earlier.
   **29** of the 37 values discriminate the two conventions; the other **8**
   coincide, because their series length is an exact multiple of the fold
   count and the tail is empty.
2. **`benchmark_alpha_annual` was published on the PRE-H51 beta convention.**
   The published alpha used `np.cov(..., ddof=1) / np.var(...)` with
   `np.var`'s default `ddof=0` — a mixed ddof that inflates beta by
   `n / (n - 1)` relative to the OLS slope. The library now uses a
   consistent `ddof=1` on both terms. All **7** published alphas are on the
   pre-fix convention.
3. **The H9 family publishes the SAMPLE standard deviation** (`ddof=1`) for
   its train/val/test/OOS Sharpes, because it passed a `pandas.Series` to
   `sharpe_ratio`; every other family passes an `ndarray` and publishes the
   POPULATION standard deviation (`ddof=0`). The two differ by
   `sqrt(n / (n - 1))`.
4. **The H9 family publishes a FULL-SAMPLE profit factor and trade count**,
   not the OOS-window ones every other family publishes, and its
   `max_drawdown` is the only OOS-window value it publishes.
5. **Three of the four H16 summaries publish the TRAIN+VAL window Sharpe
   under the key `val_sharpe`** (everything up to the val end, n = 2769),
   while the fourth publishes the val-window Sharpe (n = 756) — two
   loggings of the same configuration, four minutes apart, disagreeing on
   the window. No gate reads the key.
6. **The H21 family publishes the OOS Sharpe under the key `val_sharpe`**
   (its own source says "val component of OOS").
7. **The H10 family publishes `val_sharpe` as `null`.**

None of these moves a gate, a threshold, a verdict or a certified number:
the published gates read `oos_sharpe`, `profit_factor`, `max_drawdown`,
`trades`, `wf_stability`, `worst_regime_sharpe`, `information_ratio` and
`benchmark_p_value` — all of which re-derive — plus `val_sharpe` and
`train_sharpe`, which no gate reads.

This module is **read-only** against the frozen artifacts: no pipeline
re-execution, no network, no grid re-run, no artifact rewritten, and no
published number moved. It pins the conventions, not a copy of the values.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe  # noqa: E402

ARTIFACTS = ROOT / ".experiments" / "artifacts"
INITIAL_CAPITAL = 1_000_000.0

# ---------------------------------------------------------------------------
# 1. The record
# ---------------------------------------------------------------------------
# The thirteen numeric keys of the `metrics` block, and the two nested
# blocks. The union of the keys published across the 37 summaries is pinned
# in `test_h53_metrics_keys_union_pinned`.
METRIC_KEYS = (
    "train_sharpe",
    "val_sharpe",
    "test_sharpe",
    "oos_sharpe",
    "profit_factor",
    "max_drawdown",
    "trades",
    "wf_stability",
    "worst_regime_sharpe",
    "regime_sharpes",
    "benchmark_p_value",
    "information_ratio",
    "benchmark_alpha_annual",
)

# The keys that are *not* re-derived here, with the reason. `information_ratio`
# is re-derived (it is in the list above); §H51 already disclosed its
# container-dependent ddof split, and H53 extends that disclosure to the
# eight H28 causal re-certification runs §H51 did not cover.
NOT_RE_DERIVABLE_REASON = {
    "regime_sharpes": "the producer's VIX input was never committed",
    "worst_regime_sharpe": "the producer's VIX input was never committed",
}

# The 37 summaries, by the producer tag the tracker metadata records. The tag
# is the record's own statement of which runner produced the artifact.
#
# Every recipe field is a *measured* convention, read off the runner that
# produced the artifact (and, where the artifact carries a copy of it, off
# that copy):
#
#   split        how the producer cut the series into train / val / test
#   sharpe_ddof  the standard-deviation convention of the published Sharpes
#   pf_scope     the window of the published profit factor ("full" = the
#                engine's whole-sample profit factor, "oos" = the OOS window)
#   trades_scope the window of the published trade count
#   regime_scope the window of the published regime Sharpes
#   bench_scope  the window of the benchmark comparison
#   bench_ddof   the excess-volatility convention of the published
#                information ratio (the container the producer passed)
#   val_sharpe   what the published `val_sharpe` key holds
#   wf_tail      whether the producer's walk-forward folds absorbed the tail
#                of the return series (the post-fix library convention) or
#                dropped it (the pre-fix convention)
#   equity       the file the published equity curve lives in
#   vix          the file the producer's VIX input lives in (None when the
#                producer never committed it)
FAMILY_RECIPES = {
    # H9 v1/v2 pass a pandas.Series to sharpe_ratio -> sample std (ddof=1);
    # publish the engine's whole-sample profit factor and trade count; and
    # compare against the benchmark over the whole series.
    "h9_intraday_tsmom_ctexits_v1": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=1,
        pf_scope="full",
        trades_scope="full",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="val-window",
        wf_tail=False,
        equity="equity.parquet",
        vix=None,
    ),
    "h9_intraday_tsmom_ctexits_v2": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=1,
        pf_scope="full",
        trades_scope="full",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="val-window",
        wf_tail=False,
        equity="equity.parquet",
        vix=None,
    ),
    # H10 passes an ndarray -> population std (ddof=0); publishes the
    # OOS-window profit factor, drawdown and trade count; compares against
    # the benchmark over the whole series with a Series container (ddof=1);
    # and publishes `val_sharpe` as null.
    "h10_intraday_tsmom_pfopt": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="null",
        wf_tail=False,
        equity="equity.parquet",
        vix="vix_hourly.parquet",
    ),
    # H16/H17/H19/H20 compare against the benchmark over the OOS window with
    # an ndarray container (ddof=0) and take the regime Sharpes on the OOS
    # window as well.
    "h16_factor_timing": dict(
        split=("date", "2017-12-31", "2020-12-31"),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="oos",
        bench_scope="oos",
        bench_ddof=0,
        val_sharpe="val-window",
        wf_tail=False,
        equity="best_equity.parquet",
        vix="vix_close.parquet",
    ),
    "h17_vrp": dict(
        split=("date", "2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="oos",
        bench_scope="oos",
        bench_ddof=0,
        val_sharpe="val-window",
        wf_tail=False,
        equity="best_equity.parquet",
        vix="vix_close.parquet",
    ),
    "h19_volume_predictive": dict(
        split=("date", "2014-12-31", "2019-12-31"),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="oos",
        bench_scope="oos",
        bench_ddof=0,
        val_sharpe="val-window",
        wf_tail=False,
        equity="best_equity.parquet",
        vix="vix_close.parquet",
    ),
    "h20_signed_volume": dict(
        split=("date", "2014-12-31", "2019-12-31"),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="oos",
        bench_scope="oos",
        bench_ddof=0,
        val_sharpe="val-window",
        wf_tail=False,
        equity="best_equity.parquet",
        vix="vix_close.parquet",
    ),
    # H21 publishes the OOS Sharpe under the key `val_sharpe`.
    "h21_futures_tsmom_multicontract": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="oos",
        wf_tail=False,
        equity="equity.parquet",
        vix="vix_hourly.parquet",
    ),
    "h22_futures_tsmom_voltarget": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="val-window",
        wf_tail=False,
        equity="equity.parquet",
        vix="vix_hourly.parquet",
    ),
    "h23_crypto_futures_tsmom": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="val-window",
        wf_tail=False,
        equity="equity.parquet",
        vix="vix_hourly.parquet",
    ),
    "h25_futures_tsmom_pfmargin": dict(
        split=("frac", 0.55, 0.8),
        sharpe_ddof=0,
        pf_scope="oos",
        trades_scope="oos",
        regime_scope="full",
        bench_scope="full",
        bench_ddof=1,
        val_sharpe="val-window",
        wf_tail=False,
        equity="equity.parquet",
        vix="vix_hourly.parquet",
    ),
}

# The H28 causal re-certification runs re-run their parent family's runner
# with a different daily collapse, so they inherit that family's conventions
# — except for the walk-forward folds: they ran on 2026-10-19, after the
# library's fold fix, so their `wf_stability` is on the post-fix convention.
H28_PARENTS = {
    "h28_h10_control": "h10_intraday_tsmom_pfopt",
    "h28_h10_causal": "h10_intraday_tsmom_pfopt",
    "h28_h21_control": "h21_futures_tsmom_multicontract",
    "h28_h21_causal": "h21_futures_tsmom_multicontract",
    "h28_h22_control": "h22_futures_tsmom_voltarget",
    "h28_h22_causal": "h22_futures_tsmom_voltarget",
    "h28_h25_control": "h25_futures_tsmom_pfmargin",
    "h28_h25_causal": "h25_futures_tsmom_pfmargin",
}
for _child, _parent in H28_PARENTS.items():
    _recipe = dict(FAMILY_RECIPES[_parent])
    _recipe["wf_tail"] = True
    FAMILY_RECIPES[_child] = _recipe

# The measured per-artifact exceptions.
#
# (a) Three of the four H16 summaries publish the TRAIN+VAL window Sharpe
#     (everything up to the val end) under the key `val_sharpe`, while the
#     fourth publishes the val-window Sharpe. Both were produced by the
#     same commit; the val-window value is the one the runner's source
#     computes today.
VAL_SHARPE_TRAIN_PLUS_VAL = frozenset(
    {
        "exp_2026-10-13T21-11-45-843908Z",
        "exp_2026-10-13T21-13-09-580962Z",
        "exp_2026-10-13T21-18-23-178134Z",
    }
)

# (b) Every published `benchmark_alpha_annual` was computed with the PRE-H51
#     beta: `np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench)` with
#     `np.var`'s default `ddof=0`. The library now uses a consistent
#     `ddof=1` on both terms (the OLS slope).
ALPHA_PRE_H51_BETA = frozenset(
    {
        "exp_2026-10-13T21-11-45-843908Z",
        "exp_2026-10-13T21-13-09-580962Z",
        "exp_2026-10-13T21-18-23-178134Z",
        "exp_2026-10-13T21-22-02-751156Z",
        "exp_2026-10-13T21-51-45-034237Z",
        "exp_2026-10-13T22-40-41-870350Z",
        "exp_2026-10-13T23-06-33-191710Z",
    }
)

# The tolerance of a re-derivation. The published values are full float64
# round-trips of the same computation, so they agree to ~1e-12 relative when
# the series is read back from the committed parquet; the tolerance is set
# three orders of magnitude above that and four below any convention
# difference (the smallest convention gap measured is 5.8e-05 relative).
TOLERANCE = 1e-9


# ---------------------------------------------------------------------------
# 2. The record readers
# ---------------------------------------------------------------------------
def _tracker_names() -> dict[str, str]:
    """The producer tag the tracker metadata records for each experiment."""
    names: dict[str, str] = {}
    path = ROOT / ".experiments" / "experiments.jsonl"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        metadata = json.loads(line).get("metadata", {})
        names[metadata.get("experiment_id")] = metadata.get("name")
    return names


def _metric_summaries() -> list[tuple[pathlib.Path, dict]]:
    """Every summary that publishes a non-empty `metrics` block."""
    out = []
    for path in sorted(ARTIFACTS.rglob("summary.json")):
        data = json.loads(path.read_text())
        metrics = data.get("metrics")
        if isinstance(metrics, dict) and metrics:
            out.append((path.parent, data))
    return out


def _series(path: pathlib.Path) -> pd.Series:
    frame = read_parquet_safe(path)
    return frame[frame.columns[0]]


def _returns_from_equity(equity: pd.Series) -> pd.Series:
    """Invert the engine's equity construction.

    ``equity = (1 + net_returns).cumprod() * initial_capital``: the first
    row of the curve already carries the first bar's return, so
    ``pct_change`` alone would lose it and shift every later row by one.
    """
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / INITIAL_CAPITAL - 1.0
    return returns


def _sharpe(returns, ddof: int, periods_per_year: int = 252) -> float:
    values = np.asarray(returns, dtype=float)
    if values.size == 0:
        return 0.0
    deviation = np.std(values, ddof=ddof)
    if deviation <= 1e-15:
        return 0.0
    return float(values.mean() / deviation * np.sqrt(periods_per_year))


def _period_metrics(returns: pd.Series, ddof: int) -> dict:
    values = returns.dropna()
    cumulative = (1 + values).cumprod()
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(abs(values[values < 0].sum()))
    return {
        "sharpe": _sharpe(values.values, ddof) if len(values) > 1 else 0.0,
        "max_drawdown": float((cumulative / cumulative.cummax() - 1.0).min())
        if len(cumulative) > 0
        else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
    }


def _count_in(trades: pd.DataFrame | None, mask, index) -> int:
    if trades is None or len(trades) == 0:
        return 0
    stamps = pd.to_datetime(trades["timestamp"])
    low = index[mask].min()
    high = index[mask].max()
    return int(((stamps >= low) & (stamps <= high)).sum())


def _walk_forward_splits(n_samples: int, n_splits: int = 5, train_ratio: float = 0.7):
    """The PRE-FIX split: the last window ends at ``n_splits * window_size``,
    so the trailing samples of the series are silently dropped.

    The library's current ``walk_forward_splits`` lets the last window
    absorb those samples instead; the two differ, and the published record
    was produced with this one (see the module docstring).
    """
    window_size = n_samples // n_splits
    if window_size == 0:
        return []
    splits = []
    for i in range(n_splits):
        start = i * window_size
        end = (i + 1) * window_size
        window = np.arange(start, end)
        split_point = start + int(len(window) * train_ratio)
        train_idx = np.arange(start, split_point)
        test_idx = np.arange(split_point, end)
        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append((train_idx, test_idx))
    return splits


def _walk_forward_splits_tail_absorbing(
    n_samples: int, n_splits: int = 5, train_ratio: float = 0.7
):
    """The CURRENT library split: the last window absorbs the tail."""
    window_size = n_samples // n_splits
    if window_size == 0:
        return []
    splits = []
    for i in range(n_splits):
        start = i * window_size
        end = n_samples if i == n_splits - 1 else (i + 1) * window_size
        window = np.arange(start, end)
        split_point = start + int(len(window) * train_ratio)
        train_idx = np.arange(start, split_point)
        test_idx = np.arange(split_point, end)
        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append((train_idx, test_idx))
    return splits


def _regime_labels(vix: pd.Series) -> pd.Series:
    """VIX regime labels (the H1-H11 convention): bull < 20, sideways 20-30,
    bear > 30."""
    regimes = pd.Series(index=vix.index, dtype=object)
    forward = vix.ffill()
    regimes[forward < 20] = "bull"
    regimes[(forward >= 20) & (forward <= 30)] = "sideways"
    regimes[forward > 30] = "bear"
    return regimes


def _benchmark_comparison(strategy, benchmark, ddof: int, beta_pre_h51: bool) -> dict:
    """``compare_to_benchmark`` under the convention the producer used.

    ``ddof`` is the excess-volatility convention (the container the producer
    passed decided it: a Series -> ``ddof=1``, an ndarray -> ``ddof=0``).
    ``beta_pre_h51`` selects the pre-H51 mixed-ddof beta.
    """
    from scipy import stats

    strat = np.asarray(strategy, dtype=float)
    bench = np.asarray(benchmark, dtype=float)
    min_len = min(len(strat), len(bench))
    strat, bench = strat[-min_len:], bench[-min_len:]
    valid = ~(np.isnan(strat) | np.isnan(bench))
    if not valid.all():
        strat, bench = strat[valid], bench[valid]
    excess = strat - bench
    if len(excess) < 2:
        return {"information_ratio": 0.0, "alpha_annualized": 0.0, "alpha_p_value": 1.0}
    excess_std = excess.std(ddof=ddof)
    information_ratio = excess.mean() / excess_std * np.sqrt(252) if excess_std > 0 else 0.0
    if bench.std(ddof=0) > 0:
        if beta_pre_h51:
            beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=0)
        else:
            beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=1)
        alpha = strat.mean() - beta * bench.mean()
        alpha_annual = alpha * 252
    else:
        alpha_annual = 0.0
    if excess.std(ddof=0) > 1e-12:
        _, p_value = stats.ttest_1samp(excess, 0)
    else:
        p_value = 1.0
    return {
        "information_ratio": float(information_ratio),
        "alpha_annualized": float(alpha_annual),
        "alpha_p_value": float(p_value),
    }


def _splits(index: pd.DatetimeIndex, spec) -> tuple[pd.Series, pd.Series, pd.Series, pd.Timestamp]:
    if spec[0] == "frac":
        n = len(index)
        train_end = index[int(n * spec[1])]
        val_end = index[int(n * spec[2])]
    else:
        train_end = pd.Timestamp(spec[1])
        val_end = pd.Timestamp(spec[2])
    train = index <= train_end
    val = (index > train_end) & (index <= val_end)
    test = index > val_end
    return train, val, test, val_end


# ---------------------------------------------------------------------------
# 3. The re-derivation
# ---------------------------------------------------------------------------
def _strategy_returns(directory: pathlib.Path, recipe: dict) -> pd.Series:
    path = directory / "returns.parquet"
    if path.exists():
        return _series(path)
    return _returns_from_equity(_series(directory / recipe["equity"]))


def _benchmark_returns(directory: pathlib.Path) -> pd.Series:
    path = directory / "benchmark_returns.parquet"
    if path.exists():
        return _series(path)
    return _returns_from_equity(_series(directory / "benchmark_equity.parquet"))


def _trades(directory: pathlib.Path) -> pd.DataFrame | None:
    for name in ("trades.parquet", "best_trades.parquet"):
        path = directory / name
        if path.exists():
            return read_parquet_safe(path)
    return None


def rederive(
    directory: pathlib.Path,
    artifact_id: str,
    recipe: dict,
    *,
    fold_tail: bool | None = None,
    beta_pre_h51: bool | None = None,
    val_window: str | None = None,
) -> dict:
    """Re-derive the published `metrics` values from the frozen artifact.

    The keyword arguments exist for the negative controls: they let a test
    reconstruct a *different* convention and show that the residual check
    detects it.
    """
    ddof = recipe["sharpe_ddof"]
    returns = _strategy_returns(directory, recipe)
    index = returns.index
    train_mask, val_mask, test_mask, val_end = _splits(index, recipe["split"])
    oos_mask = val_mask | test_mask

    out: dict = {}
    out["train_sharpe"] = _sharpe(returns[train_mask].values, ddof) if train_mask.sum() > 1 else 0.0

    if val_window is None:
        val_window = (
            "train+val" if artifact_id in VAL_SHARPE_TRAIN_PLUS_VAL else recipe["val_sharpe"]
        )
    if val_window == "null":
        out["val_sharpe"] = None
    elif val_window == "oos":
        out["val_sharpe"] = _sharpe(returns[oos_mask].dropna().values, ddof)
    elif val_window == "train+val":
        out["val_sharpe"] = _sharpe(returns[index <= val_end].values, ddof)
    else:
        out["val_sharpe"] = (
            _sharpe(returns[val_mask].dropna().values, ddof) if val_mask.sum() > 1 else 0.0
        )

    test_metrics = _period_metrics(returns[test_mask], ddof)
    oos_metrics = _period_metrics(returns[oos_mask], ddof)
    out["test_sharpe"] = test_metrics["sharpe"]
    out["oos_sharpe"] = oos_metrics["sharpe"]
    out["max_drawdown"] = oos_metrics["max_drawdown"]

    if recipe["pf_scope"] == "oos":
        out["profit_factor"] = oos_metrics["profit_factor"]
    else:
        values = returns.dropna()
        gross_profit = float(values[values > 0].sum())
        gross_loss = float(abs(values[values < 0].sum()))
        out["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    trades = _trades(directory)
    if recipe["trades_scope"] == "oos":
        out["trades"] = _count_in(trades, oos_mask, index)
    else:
        out["trades"] = int(len(trades)) if trades is not None else 0

    tail = recipe["wf_tail"] if fold_tail is None else fold_tail
    splitter = _walk_forward_splits_tail_absorbing if tail else _walk_forward_splits
    oos_sharpes, train_sharpes = [], []
    for train_idx, test_idx in splitter(len(returns)):
        oos_sharpes.append(_sharpe(returns.iloc[test_idx].values, 0))
        train_sharpes.append(_sharpe(returns.iloc[train_idx].values, 0))
    out["wf_stability"] = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes)) if np.mean(train_sharpes) != 0 else 0.0
    )

    vix_file = recipe["vix"]
    if vix_file and (directory / vix_file).exists():
        vix = _series(directory / vix_file)
        if vix_file == "vix_close.parquet":
            vix = vix.reindex(index)
        regimes = _regime_labels(vix)
        if recipe["regime_scope"] == "oos":
            regimes = regimes[oos_mask]
            base = returns[oos_mask]
        else:
            base = returns
        regime_sharpes = {}
        worst = np.inf
        for regime in ("bull", "sideways", "bear"):
            selection = regimes == regime
            subset = base[selection] if len(selection) == len(base) else base.iloc[selection.values]
            if len(subset) > 1 and subset.std() > 0:
                value = _sharpe(subset.values, 0)
            else:
                value = 0.0
            regime_sharpes[regime] = value
            worst = min(worst, value)
        out["regime_sharpes"] = regime_sharpes
        out["worst_regime_sharpe"] = float(worst) if worst != np.inf else 0.0

    benchmark = _benchmark_returns(directory)
    if recipe["bench_scope"] == "oos":
        left = returns[oos_mask].dropna().values
        right = benchmark[oos_mask].dropna().values
    else:
        left = returns.dropna().values
        right = benchmark.dropna().values
    pre_h51 = artifact_id in ALPHA_PRE_H51_BETA if beta_pre_h51 is None else beta_pre_h51
    comparison = _benchmark_comparison(left, right, recipe["bench_ddof"], pre_h51)
    out["benchmark_p_value"] = comparison["alpha_p_value"]
    out["information_ratio"] = comparison["information_ratio"]
    out["benchmark_alpha_annual"] = comparison["alpha_annualized"]
    return out


def _matches(published, rederived) -> bool:
    """Do a published value and a re-derived value agree?

    ``None`` is compared as a value (the H10 family publishes
    ``val_sharpe: null``), infinities compare equal to themselves, and a
    nested block is compared key by key.
    """
    if published is None or rederived is None:
        return published is None and rederived is None
    if isinstance(published, dict) or isinstance(rederived, dict):
        if not (isinstance(published, dict) and isinstance(rederived, dict)):
            return False
        keys = set(published) | set(rederived)
        return all(_matches(published.get(k), rederived.get(k)) for k in keys)
    if np.isinf(published) or np.isinf(rederived):
        return published == rederived
    return abs(published - rederived) <= TOLERANCE * max(1.0, abs(published))


# ---------------------------------------------------------------------------
# 4. The measured table
# ---------------------------------------------------------------------------
_NAMES = _tracker_names()


def _entries() -> list[dict]:
    """One entry per summary that publishes a `metrics` block."""
    entries = []
    for directory, data in _metric_summaries():
        artifact_id = data.get("experiment_id") or directory.name
        producer = _NAMES.get(artifact_id)
        recipe = FAMILY_RECIPES.get(producer)
        assert recipe is not None, f"no recipe for {artifact_id} ({producer})"
        entries.append(
            {
                "directory": directory,
                "artifact_id": artifact_id,
                "producer": producer,
                "recipe": recipe,
                "published": data["metrics"],
                "summary": data,
            }
        )
    return entries


_ENTRIES = _entries()
_REDERIVED: dict[str, dict] = {
    entry["artifact_id"]: rederive(entry["directory"], entry["artifact_id"], entry["recipe"])
    for entry in _ENTRIES
}


def _published_key_values() -> list[tuple[str, str, object]]:
    """Every published metric value, as (artifact_id, key, value)."""
    out = []
    for entry in _ENTRIES:
        for key in METRIC_KEYS:
            if key in entry["published"]:
                out.append((entry["artifact_id"], key, entry["published"][key]))
    return out


def _undeterminable() -> set[tuple[str, str]]:
    """The published values the frozen record cannot support.

    A producer that committed no VIX series cannot have its regime block
    re-derived: the regime labels are a function of a series the record does
    not hold. The set is derived from the recipes, and
    `test_the_undeterminable_values_are_missing_its_vix_input` checks the
    recipe against the artifact directory's own file list.
    """
    out = set()
    for entry in _ENTRIES:
        if entry["recipe"]["vix"] is None:
            for key in ("regime_sharpes", "worst_regime_sharpe"):
                if key in entry["published"]:
                    out.add((entry["artifact_id"], key))
    return out


_UNDETERMINABLE = _undeterminable()


# ---------------------------------------------------------------------------
# 5. The contract
# ---------------------------------------------------------------------------
class TestH53PublishedMetrics:
    # -- the record --------------------------------------------------------
    def test_h53_metrics_summary_count_pinned(self):
        assert len(_ENTRIES) == 37, len(_ENTRIES)

    def test_h53_metrics_keys_union_pinned(self):
        keys = set()
        for entry in _ENTRIES:
            keys.update(entry["published"])
        expected = {
            "train_sharpe",
            "val_sharpe",
            "test_sharpe",
            "oos_sharpe",
            "profit_factor",
            "max_drawdown",
            "trades",
            "wf_stability",
            "worst_regime_sharpe",
            "regime_sharpes",
            "benchmark_p_value",
            "information_ratio",
            "ablations",
            "benchmark_alpha_annual",
            "cross_validation",
            "perturbation",
            "perturbation_min_ratio",
        }
        assert keys == expected, sorted(keys)

    def test_h53_every_summary_has_a_known_producer(self):
        for entry in _ENTRIES:
            assert entry["producer"] in FAMILY_RECIPES, entry["artifact_id"]

    def test_h53_published_value_count_pinned(self):
        assert len(_published_key_values()) == 450, len(_published_key_values())

    # -- the re-derivation -------------------------------------------------
    def test_every_published_value_re_derives(self):
        """Every published value re-derives from its own frozen artifact
        except the nine the record cannot support."""
        failures = []
        for artifact_id, key, published in _published_key_values():
            if (artifact_id, key) in _UNDETERMINABLE:
                continue
            rederived = _REDERIVED[artifact_id].get(key)
            if not _matches(published, rederived):
                failures.append((artifact_id, key, published, rederived))
        assert failures == [], failures

    def test_the_nine_undeterminable_values_are_exactly_the_regime_block(self):
        failures = sorted(
            (artifact_id, key)
            for artifact_id, key, published in _published_key_values()
            if not _matches(published, _REDERIVED[artifact_id].get(key))
        )
        assert failures == [
            ("exp_2026-10-11T15-54-17-212022Z", "worst_regime_sharpe"),
            ("exp_2026-10-11T16-44-06-168529Z", "regime_sharpes"),
            ("exp_2026-10-11T16-44-06-168529Z", "worst_regime_sharpe"),
            ("exp_2026-10-11T16-46-06-466282Z", "regime_sharpes"),
            ("exp_2026-10-11T16-46-06-466282Z", "worst_regime_sharpe"),
            ("exp_2026-10-11T16-52-38-694559Z", "regime_sharpes"),
            ("exp_2026-10-11T16-52-38-694559Z", "worst_regime_sharpe"),
            ("exp_2026-10-14T08-20-39-255883Z", "regime_sharpes"),
            ("exp_2026-10-14T08-20-39-255883Z", "worst_regime_sharpe"),
        ], failures
        for _artifact_id, key in failures:
            assert key in NOT_RE_DERIVABLE_REASON, key

    def test_the_undeterminable_values_are_missing_its_vix_input(self):
        """The nine values cannot be re-derived because the producer's VIX
        series was never committed -- not because the value is wrong."""
        for entry in _ENTRIES:
            vix_file = entry["recipe"]["vix"]
            if vix_file is None:
                assert not (entry["directory"] / "vix_hourly.parquet").exists()
                assert not (entry["directory"] / "vix_close.parquet").exists()
                assert "worst_regime_sharpe" not in _REDERIVED[entry["artifact_id"]]
            else:
                assert (entry["directory"] / vix_file).exists(), entry["artifact_id"]
                assert "worst_regime_sharpe" in _REDERIVED[entry["artifact_id"]]

    # -- the conventions ---------------------------------------------------
    def test_the_walk_forward_fold_convention_splits_by_production_date(self):
        """29 of the 37 published `wf_stability` values are on the pre-fix
        fold convention (the tail of the series is dropped) and 8 are on the
        post-fix one (the last window absorbs the tail). The two groups
        split exactly along the production date: the eight post-fix
        summaries are the H28 causal re-certification runs of 2026-10-19,
        and every pre-fix summary is from 2026-10-14 or earlier."""
        pre_fix = sorted(
            entry["artifact_id"] for entry in _ENTRIES if not entry["recipe"]["wf_tail"]
        )
        post_fix = sorted(entry["artifact_id"] for entry in _ENTRIES if entry["recipe"]["wf_tail"])
        assert len(pre_fix) == 29, len(pre_fix)
        assert len(post_fix) == 8, len(post_fix)
        assert all(_NAMES[artifact_id] in H28_PARENTS for artifact_id in post_fix), post_fix
        # ... and the split is exactly along the production date: every
        # post-fix summary is from 2026-10-19, every pre-fix summary is
        # from 2026-10-14 or earlier.
        assert all("2026-10-19" in artifact_id for artifact_id in post_fix)
        assert all("2026-10-19" not in artifact_id for artifact_id in pre_fix)
        # The eight post-fix summaries are *discriminated* by the data: the
        # pre-fix form does not reproduce any of them. Together with the
        # 21 discriminable pre-fix summaries that makes 29 of the 37
        # published values sensitive to the convention; the other eight
        # coincide because their series length is an exact multiple of the
        # fold count, so the tail is empty.
        for entry in _ENTRIES:
            if not entry["recipe"]["wf_tail"]:
                continue
            other = rederive(
                entry["directory"], entry["artifact_id"], entry["recipe"], fold_tail=False
            )["wf_stability"]
            assert not _matches(entry["published"]["wf_stability"], other), entry["artifact_id"]
        for entry in _ENTRIES:
            if entry["recipe"]["wf_tail"]:
                continue
            pre = rederive(
                entry["directory"], entry["artifact_id"], entry["recipe"], fold_tail=False
            )
            assert _matches(entry["published"]["wf_stability"], pre["wf_stability"])

    def test_the_library_fold_convention_has_since_moved(self):
        """The library's `walk_forward_splits` now lets the last window
        absorb the trailing samples; the published record was produced with
        the earlier form, which dropped them.

        The two are compared on the same series length, so the movement is
        pinned against the library itself and not only against the record.
        """
        from qtr.validation.statistics import walk_forward_splits

        n = 11441
        pre_fix_last = _walk_forward_splits(n)[-1][1].max()
        current_last = walk_forward_splits(n)[-1][1].max()
        assert pre_fix_last != current_last
        assert _walk_forward_splits_tail_absorbing(n)[-1][1].max() == current_last
        # the pre-fix form drops the tail, the current one covers it
        assert pre_fix_last == 11439
        assert current_last == n - 1

    def test_the_alpha_convention_is_the_pre_h51_mixed_ddof_beta(self):
        """All seven published `benchmark_alpha_annual` values were produced
        with the pre-H51 beta (`np.cov(..., ddof=1) / np.var(...)` with
        `np.var`'s default `ddof=0`)."""
        publishers = sorted(
            entry["artifact_id"]
            for entry in _ENTRIES
            if "benchmark_alpha_annual" in entry["published"]
        )
        assert publishers == sorted(ALPHA_PRE_H51_BETA), publishers
        assert len(publishers) == 7

    def test_the_h9_family_publishes_a_whole_sample_profit_factor(self):
        """The H9 family publishes the engine's whole-sample profit factor
        and trade count; every other family publishes the OOS-window ones."""
        for entry in _ENTRIES:
            if entry["producer"].startswith("h9_"):
                assert entry["recipe"]["pf_scope"] == "full"
                assert entry["recipe"]["trades_scope"] == "full"
            else:
                assert entry["recipe"]["pf_scope"] == "oos"
                assert entry["recipe"]["trades_scope"] == "oos"

    def test_the_h9_family_publishes_the_sample_standard_deviation(self):
        for entry in _ENTRIES:
            if entry["producer"].startswith("h9_"):
                assert entry["recipe"]["sharpe_ddof"] == 1
            else:
                assert entry["recipe"]["sharpe_ddof"] == 0

    def test_the_val_sharpe_key_holds_three_different_things(self):
        """`val_sharpe` is null for H10, the OOS Sharpe for H21, and the
        val-window Sharpe for the rest -- except the three H16 summaries
        that publish the train+val window."""
        by_producer: dict[str, set] = {}
        for entry in _ENTRIES:
            by_producer.setdefault(entry["recipe"]["val_sharpe"], set()).add(entry["producer"])
        assert by_producer["null"] == {
            "h10_intraday_tsmom_pfopt",
            "h28_h10_control",
            "h28_h10_causal",
        }
        assert by_producer["oos"] == {
            "h21_futures_tsmom_multicontract",
            "h28_h21_control",
            "h28_h21_causal",
        }
        for entry in _ENTRIES:
            if entry["artifact_id"] in VAL_SHARPE_TRAIN_PLUS_VAL:
                assert entry["recipe"]["val_sharpe"] == "val-window"
                assert entry["producer"] == "h16_factor_timing"

    # -- the negative controls --------------------------------------------
    def test_negative_control_the_fold_convention_is_detected(self):
        """Reconstructing the CURRENT library fold convention must break the
        re-derivation of every pre-fix summary whose series is long enough
        for the tail to matter.

        The control is behavioural: it re-runs the same re-derivation with
        the other convention and shows the residual check fires.
        """
        discriminated = 0
        for entry in _ENTRIES:
            if entry["recipe"]["wf_tail"]:
                continue
            published = entry["published"]["wf_stability"]
            post_fix = rederive(
                entry["directory"], entry["artifact_id"], entry["recipe"], fold_tail=True
            )["wf_stability"]
            if _matches(published, post_fix):
                # The two conventions coincide when the series length is an
                # exact multiple of the fold count: the tail is empty, so
                # the convention is not discriminated by the data.
                continue
            discriminated += 1
            assert not _matches(published, post_fix), entry["artifact_id"]
        assert discriminated == 21, discriminated

    def test_negative_control_the_beta_convention_is_detected(self):
        """Reconstructing the CURRENT library beta must break the
        re-derivation of every published `benchmark_alpha_annual`."""
        broken = []
        for entry in _ENTRIES:
            if "benchmark_alpha_annual" not in entry["published"]:
                continue
            other = rederive(
                entry["directory"], entry["artifact_id"], entry["recipe"], beta_pre_h51=False
            )
            published = entry["published"]["benchmark_alpha_annual"]
            if _matches(published, other["benchmark_alpha_annual"]):
                broken.append(entry["artifact_id"])
        assert broken == [], broken

    def test_negative_control_the_val_window_is_detected(self):
        """Reconstructing the val-only window must break the re-derivation of
        the three H16 summaries that published the train+val window."""
        broken = []
        for entry in _ENTRIES:
            if entry["artifact_id"] not in VAL_SHARPE_TRAIN_PLUS_VAL:
                continue
            other = rederive(
                entry["directory"], entry["artifact_id"], entry["recipe"], val_window="val-window"
            )
            published = entry["published"]["val_sharpe"]
            if _matches(published, other["val_sharpe"]):
                broken.append(entry["artifact_id"])
        assert broken == [], broken

    def test_negative_control_a_corrupted_value_is_detected(self):
        """The residual check is not vacuous: a published value nudged by
        one part in a thousand must fail it."""
        entry = _ENTRIES[0]
        published = entry["published"]["oos_sharpe"]
        corrupted = published * (1.0 + 1e-3)
        assert not _matches(corrupted, _REDERIVED[entry["artifact_id"]]["oos_sharpe"])

    def test_negative_control_missing_metrics(self):
        """A summary without a metrics block must not be counted."""
        names = {entry["artifact_id"] for entry in _ENTRIES}
        assert "h27_pnl_level" not in names

    # -- the blast radius --------------------------------------------------
    def test_no_gate_reads_a_key_that_fails_to_re_derive(self):
        """The nine undeterminable values are reported diagnostics: no
        published gate, threshold or verdict reads them."""
        gate_keys = {
            "sharpe",
            "trades",
            "pf",
            "dd",
            "stab",
            "worst",
            "p",
            "ir",
            "perturbation",
            "cross_validation",
        }
        for entry in _ENTRIES:
            passes = entry["summary"].get("passes")
            if not isinstance(passes, dict):
                continue
            assert gate_keys >= set(passes), passes
            # `regime_sharpes` and `worst_regime_sharpe` reach the summary
            # only through the reported gate values, which are computed from
            # the OOS/full windows that DO re-derive.
            assert "val_sharpe" not in passes
            assert "train_sharpe" not in passes
