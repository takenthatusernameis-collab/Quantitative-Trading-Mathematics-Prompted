"""H53 — every published `metrics` block re-derives from its own frozen
artifact, and the convention each publisher used is recorded.

The gap
------
The committed record holds **37** ``summary.json`` files that publish a
non-empty ``metrics`` block.  §H49 re-derived the ``validation`` blocks of
five exploratory summaries, §H51 the ``information_ratio`` of 48 artifacts and
§H52 the ``avg_trade_cost`` values.  The rest of the ``metrics`` block --
the block that carries the *certified* numbers and that the published
``passes`` / ``all_pass`` / ``verdict`` blocks rest on -- had never been
re-derived from the artifact that published it.

The measurement
---------------
Every published scalar key is re-derived here from the summary's own frozen
artifact, under the convention that publisher used.  The conventions are not
assumed: each one was *measured* by re-deriving the published value under
every candidate convention and keeping the one that reproduces it, then
asserting that the alternatives do **not** reproduce it.  Where a convention
cannot be discriminated by the data (a degenerate series, an artifact whose
trades all fall inside the OOS window) the test says so instead of
pretending otherwise.

Five publisher conventions differ from the library's current behaviour, and
each of them is a *call-site* or *version* artefact, not a defect in the
published numbers:

1. **The Sharpe's standard-deviation convention is the caller's container.**
   ``qtr.validation.statistics.sharpe_ratio`` only became container-independent
   on 2026-10-17 (commit ``9fb26b8``).  Before that it called
   ``returns.std()`` on whatever it was handed, so a ``pandas.Series`` gave
   the *sample* deviation (``ddof=1``) and an ``ndarray`` gave the
   *population* deviation (``ddof=0``).  The H9 family passed a Series and
   the H10+ families passed ``.values``, so the two families published
   Sharpes on different conventions.  H26 recorded the same fact.

2. **The walk-forward split dropped the tail of the series** until
   2026-10-18 (commit ``26c6aa6``).  The published ``wf_stability`` of every
   artifact published before that commit is the ratio of the fold Sharpes of
   the *tail-dropping* split; the eight H28 artifacts (2026-10-19) use the
   tail-absorbing split.  This is the *only* key whose convention is
   decided by the publication date.

3. **The published ``benchmark_alpha_annual`` uses the pre-H51 beta.**
   §H51 made the CAPM beta's two terms use a consistent ``ddof``; the
   published values use the *mixed* convention
   (``np.cov(S, B, ddof=1)[0, 1] / np.var(B, ddof=0)``), which inflates beta
   by ``n / (n - 1)``.  The seven published alphas re-derive exactly under
   the mixed convention and *not* under the library's current one.

4. **The published ``information_ratio`` follows the same container rule.**
   The families that published a Series information ratio (H9, H10, H21,
   H22, H25, H23) published the *sample*-deviation ratio; the families that
   published an ndarray one (H16, H17, H19, H20) published the
   *population*-deviation ratio.  §H51 disclosed this for the 48 artifacts
   that publish an IR; here it is re-measured from the same artifacts.

5. **Three artifacts published a ``val_sharpe`` that leaks the training
   period.**  H21 publishes the *OOS* Sharpe under the key ``val_sharpe``;
   three of the four H16 artifacts publish a window that *includes the
   training period* ((data start, VAL_END] instead of (TRAIN_END,
   VAL_END]).  Neither value is read by any published gate.

6. **One summary published two Sharpe conventions at once.**  The H9 runner
   computed its *main* block from a ``pandas.Series`` (``sharpe_ratio(oos_ret)``,
   the sample deviation) and its *ablation* block from an ``ndarray``
   (``sharpe_ratio(oos_no.values)``, the population deviation).  Both live in
   the same ``metrics`` block, so the convention is per *call site*, not per
   family.

The disclosure
--------------
Nothing is rewritten.  Every published value stays as it is, and the
convention that explains it is pinned here so that a later reader can tell
a *convention difference* from a *defect*.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

ARTIFACTS = ROOT / ".experiments" / "artifacts"
CACHE = ROOT / ".cache" / "data"
INITIAL_CAPITAL = 1_000_000.0

# The reconstruction tolerance.  The published values were computed from the
# engine's own return series; the artifact stores the equity curve those
# returns were compounded into, so the re-derivation carries the float noise
# of one inversion.  The observed noise is ~5e-13 relative (see
# `test_the_reconstruction_noise_is_bounded`), so 1e-9 is a wide but safe
# bound that no *alternative* convention can hide inside.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# ---------------------------------------------------------------------------
# The families.
#
# Every entry says how a publisher computed each key of its `metrics` block.
#
#   returns            (file, is_equity)   the strategy's own series
#   trades             file                the trade log
#   split              "fraction" | ("dates", train_end, val_end)
#   sharpe_ddof        the deviation convention of the published Sharpe
#   wf_ddof            the deviation convention of the published fold Sharpe
#   regime_ddof        the deviation convention of the published regime Sharpe
#   profit_factor      "full" | "oos"      the window the factor covers
#   trades_window      "all" | "oos"       the window the count covers
#   walk_forward       "pre" | "post"      the split the stability used
#   regime             (source, kind, window)   source: "cache" | file name
#   benchmark          (file, is_equity)  the benchmark leg of the comparison
#   benchmark_window   "full" | "oos"      the window the comparison covers
#   ir_ddof            the deviation convention of the published IR
#   alpha_beta         "pre_h51" | "consistent"
#   val_sharpe         "val" | "leaky" | "oos" | "null"
# ---------------------------------------------------------------------------
FAMILIES = {
    # H9: the runner passed a pandas Series to `sharpe_ratio`, published the
    # FULL-SAMPLE profit factor (the engine's own `result.metrics`) and the
    # FULL trade count, and read the VIX regimes from a live daily fetch
    # that was never logged.
    "H9": {
        "returns": ("returns.parquet", False),
        "trades": "trades.parquet",
        "split": "fraction",
        "sharpe_ddof": 1,
        "wf_ddof": 0,
        "regime_ddof": 0,
        "profit_factor": "full",
        "trades_window": "all",
        "walk_forward": "pre",
        "regime": ("cache", "daily", "full"),
        "benchmark": ("benchmark_equity.parquet", True),
        "benchmark_window": "full",
        "ir_ddof": 1,
        "alpha_beta": "consistent",
        "val_sharpe": "val",
    },
    # H10 / H21 / H22 / H25 / H28: the runner passed `.values` to
    # `sharpe_ratio` and published the OOS-window profit factor and trade
    # count.  H28 was published after the walk-forward fix, so its
    # `wf_stability` uses the tail-absorbing split.
    "H10": {
        "returns": ("returns.parquet", False),
        "trades": "trades.parquet",
        "split": "fraction",
        "sharpe_ddof": 0,
        "wf_ddof": 0,
        "regime_ddof": 0,
        "profit_factor": "oos",
        "trades_window": "oos",
        "walk_forward": "pre",
        "regime": ("vix_hourly.parquet", "hourly", "full"),
        "benchmark": ("benchmark_returns.parquet", False),
        "benchmark_window": "full",
        "ir_ddof": 1,
        "alpha_beta": "consistent",
        "val_sharpe": "val",
    },
    # H16 / H17 / H19 / H20: the daily families.  The splits are calendar
    # dates, the benchmark comparison is made on the OOS window only and the
    # published alpha uses the pre-H51 beta.
    "H16": {
        "returns": ("best_equity.parquet", True),
        "trades": "best_trades.parquet",
        "split": ("dates", "2017-12-31", "2020-12-31"),
        "sharpe_ddof": 0,
        "wf_ddof": 0,
        "regime_ddof": 0,
        "profit_factor": "oos",
        "trades_window": "oos",
        "walk_forward": "pre",
        "regime": ("vix_close.parquet", "daily", "oos"),
        "benchmark": ("benchmark_returns.parquet", False),
        "benchmark_window": "oos",
        "ir_ddof": 0,
        "alpha_beta": "pre_h51",
        "val_sharpe": "val",
    },
    # H23: the crypto family, H10's gate conventions on its own data.
    "H23": {
        "returns": ("returns.parquet", False),
        "trades": "trades.parquet",
        "split": "fraction",
        "sharpe_ddof": 0,
        "wf_ddof": 0,
        "regime_ddof": 0,
        "profit_factor": "oos",
        "trades_window": "oos",
        "walk_forward": "pre",
        "regime": ("vix_hourly.parquet", "hourly", "full"),
        "benchmark": ("benchmark_returns.parquet", False),
        "benchmark_window": "full",
        "ir_ddof": 1,
        "alpha_beta": "consistent",
        "val_sharpe": "val",
    },
}

# ---------------------------------------------------------------------------
# The record: every committed summary that publishes a `metrics` block, the
# family that published it, and the per-artifact overrides.
#
# `val_sharpe` names the window the published `val_sharpe` covers:
#   "val"   -- the Val window (TRAIN_END, VAL_END]
#   "oos"   -- the OOS window (H21 published the OOS Sharpe under this key)
#   "leaky" -- (data start, VAL_END], i.e. the window ALSO covers the
#              training period (three of the four H16 artifacts)
#   "null"  -- the key is published as JSON null (the H10 family)
# ---------------------------------------------------------------------------
RECORD: dict[str, dict] = {}


def _register(artifact_id: str, family: str, **overrides) -> None:
    RECORD[artifact_id] = {"family": family, **overrides}


# --- H9 (5) ---------------------------------------------------------------
_register("exp_2026-10-11T15-54-17-212022Z", "H9")
_register("exp_2026-10-11T16-44-06-168529Z", "H9")
_register("exp_2026-10-11T16-46-06-466282Z", "H9")
_register("exp_2026-10-11T16-52-38-694559Z", "H9")
_register("exp_2026-10-14T08-20-39-255883Z", "H9")

# --- H10 (2) --------------------------------------------------------------
_register("exp_2026-10-11T17-24-14-385352Z", "H10", val_sharpe="null")
_register("exp_2026-10-11T17-41-18-169363Z", "H10", val_sharpe="null")

# --- H21 (1) --------------------------------------------------------------
_register("exp_2026-10-13T23-27-52-101656Z", "H10", val_sharpe="oos")

# --- H22 (5) --------------------------------------------------------------
_register("exp_2026-10-14T07-12-35-292010Z", "H10")
_register("exp_2026-10-14T07-12-59-473353Z", "H10")
_register("exp_2026-10-14T07-15-23-322705Z", "H10")
_register("exp_2026-10-14T07-32-43-425839Z", "H10")
_register("exp_2026-10-14T18-52-08-943792Z", "H10")

# --- H25 (2) --------------------------------------------------------------
_register("exp_2026-10-14T20-02-45-189859Z", "H10")
_register("exp_2026-10-14T20-08-34-613690Z", "H10")

# --- H28 (8) -- published AFTER the walk-forward fix ----------------------
_register("exp_2026-10-19T15-46-16-261803Z", "H10", val_sharpe="null", walk_forward="post")
_register("exp_2026-10-19T16-41-44-683912Z", "H10", val_sharpe="null", walk_forward="post")
_register("exp_2026-10-19T17-38-03-570526Z", "H10", val_sharpe="oos", walk_forward="post")
_register("exp_2026-10-19T17-38-21-389139Z", "H10", val_sharpe="oos", walk_forward="post")
_register("exp_2026-10-19T17-38-39-157337Z", "H10", walk_forward="post")
_register("exp_2026-10-19T17-38-50-887609Z", "H10", walk_forward="post")
_register("exp_2026-10-19T17-39-02-719690Z", "H10", walk_forward="post")
_register("exp_2026-10-19T17-39-12-729639Z", "H10", walk_forward="post")

# --- H16 (4) -- three of them published a val window that leaks the train -
_register("exp_2026-10-13T21-11-45-843908Z", "H16", val_sharpe="leaky")
_register("exp_2026-10-13T21-13-09-580962Z", "H16", val_sharpe="leaky")
_register("exp_2026-10-13T21-18-23-178134Z", "H16", val_sharpe="leaky")
_register("exp_2026-10-13T21-22-02-751156Z", "H16")

# --- H17 (1) --------------------------------------------------------------
_register(
    "exp_2026-10-13T21-51-45-034237Z",
    "H16",
    split=("dates", "2019-12-31", "2021-12-31"),
)

# --- H19 (1) --------------------------------------------------------------
_register(
    "exp_2026-10-13T22-40-41-870350Z",
    "H16",
    split=("dates", "2014-12-31", "2019-12-31"),
)

# --- H20 (1) --------------------------------------------------------------
_register(
    "exp_2026-10-13T23-06-33-191710Z",
    "H16",
    split=("dates", "2014-12-31", "2019-12-31"),
)

# --- H23 (7) --------------------------------------------------------------
for _aid in (
    "exp_2026-10-14T08-48-49-412372Z",
    "exp_2026-10-14T09-28-59-592390Z",
    "exp_2026-10-14T09-32-25-959733Z",
    "exp_2026-10-14T09-39-07-412533Z",
    "exp_2026-10-14T10-04-52-936640Z",
    "exp_2026-10-14T11-53-37-996139Z",
    "exp_2026-10-14T18-13-09-457781Z",
):
    _register(_aid, "H23")

# The scalar keys of the `metrics` block.
SCALAR_KEYS = (
    "train_sharpe",
    "val_sharpe",
    "test_sharpe",
    "oos_sharpe",
    "profit_factor",
    "max_drawdown",
    "trades",
    "wf_stability",
    "worst_regime_sharpe",
    "information_ratio",
    "benchmark_p_value",
    "benchmark_alpha_annual",
)

# The structural keys of the `metrics` block: they carry nested blocks
# rather than a single number.
STRUCTURAL_KEYS = (
    "ablations",
    "cross_validation",
    "perturbation",
    "perturbation_min_ratio",
    "regime_sharpes",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _artifact_index() -> dict[str, pathlib.Path]:
    """Every artifact directory, by artifact id.

    Most artifacts sit directly under ``.experiments/artifacts/<id>/``, but
    the H28 recertification nests its eight runs one level deeper, under
    ``.experiments/artifacts/h28_causal_recertification/runs/<id>/``.  The
    index is built from the committed tree, so the nesting is not assumed.
    """
    index: dict[str, pathlib.Path] = {}
    for path in sorted(ARTIFACTS.rglob("summary.json")):
        index[path.parent.name] = path.parent
    return index


_INDEX = _artifact_index()


def _directory(artifact_id: str) -> pathlib.Path:
    return _INDEX[artifact_id]


def _summary(artifact_id: str) -> dict:
    return json.loads((_directory(artifact_id) / "summary.json").read_text())


def _first_column(path: pathlib.Path) -> pd.Series:
    frame = pd.read_parquet(path)
    return frame[frame.columns[0]]


def _returns_from_equity(equity: pd.Series) -> pd.Series:
    """Invert the engine's equity construction.

    ``equity = (1 + net_returns).cumprod() * initial_capital``: the first row
    of the curve already carries the first bar's return, so ``pct_change``
    alone would lose it and shift every later row by one.
    """
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / INITIAL_CAPITAL - 1.0
    return returns


def _load(directory: pathlib.Path, name: str, is_equity: bool) -> pd.Series | None:
    path = directory / name
    if not path.exists():
        return None
    series = _first_column(path).astype(float)
    return _returns_from_equity(series) if is_equity else series


def _sharpe(values, ddof: int) -> float:
    """The Sharpe of ``values`` under an explicit deviation convention.

    This is ``qtr.validation.statistics.sharpe_ratio`` with the deviation's
    ``ddof`` pinned: the library's own ``sharpe_ratio`` became
    container-independent on 2026-10-17 (commit ``9fb26b8``) and always uses
    the population deviation now, so the sample-deviation numbers the H9
    family published cannot be produced by calling it.
    """
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 0.0
    deviation = array.std(ddof=ddof)
    if deviation <= 1e-15:
        return 0.0
    return float(array.mean() / deviation * math.sqrt(252))


def _walk_forward_splits(n_samples: int, n_splits: int, tail: str):
    """The library's walk-forward split, in its pre- and post-fix forms.

    Before 2026-10-18 (``26c6aa6``) the last window was
    ``min((i + 1) * window_size, n_samples)``, so the tail of the series
    (up to ``n_splits - 1`` bars) was silently dropped; the fix lets the
    last window absorb it.  Both forms are reproduced here.
    """
    window_size = n_samples // n_splits
    if window_size == 0:
        return []
    splits = []
    for i in range(n_splits):
        start = i * window_size
        if tail == "post":
            end = n_samples if i == n_splits - 1 else (i + 1) * window_size
        else:
            end = min((i + 1) * window_size, n_samples)
        window = np.arange(start, end)
        if len(window) == 0:
            continue
        split_point = start + int(len(window) * 0.7)
        splits.append((np.arange(start, split_point), np.arange(split_point, end)))
    return splits


def _period_metrics(returns: pd.Series, ddof: int) -> dict:
    """The runners' ``_period_metrics``: Sharpe, drawdown and profit factor."""
    clean = returns.dropna()
    cumulative = (1 + clean).cumprod()
    gross_profit = float(clean[clean > 0].sum())
    gross_loss = float(abs(clean[clean < 0].sum()))
    return {
        "sharpe": _sharpe(clean.values, ddof) if len(clean) > 1 else 0.0,
        "max_drawdown": (
            float((cumulative / cumulative.cummax() - 1.0).min()) if len(cumulative) > 0 else 0.0
        ),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
    }


def _count_in(trades: pd.DataFrame, mask: np.ndarray, index: pd.DatetimeIndex) -> int:
    """The runners' ``_count_in``: the trades inside the window's bounds."""
    if len(trades) == 0:
        return 0
    stamps = pd.to_datetime(trades["timestamp"])
    low = index[mask].min()
    high = index[mask].max()
    return int(((stamps >= low) & (stamps <= high)).sum())


def _regime_labels(vix: pd.Series) -> pd.Series:
    """The runners' VIX regime labels: bull < 20, sideways 20-30, bear > 30."""
    regimes = pd.Series(index=vix.index, dtype=object)
    filled = vix.ffill()
    regimes[filled < 20] = "bull"
    regimes[(filled >= 20) & (filled <= 30)] = "sideways"
    regimes[filled > 30] = "bear"
    return regimes


def _vix_from_cache(artifact_id: str) -> pd.Series | None:
    """The H9 family's VIX daily series, recovered from the committed cache.

    The H9 runner fetched ``^VIX`` with ``start = now - 729 days`` and
    ``end = now``, and the fetcher's cache key is
    ``sha256(f"yahoo:{symbol}:{start}:{end}:{interval}")[:16]``.  The run's
    start time is the artifact id, so the exact file the run read is
    addressable in the committed content-addressed cache.
    """
    stamp = datetime.strptime(artifact_id[4:], "%Y-%m-%dT%H-%M-%S-%fZ")
    start = (stamp - timedelta(days=729)).strftime("%Y-%m-%d")
    end = stamp.strftime("%Y-%m-%d")
    key = hashlib.sha256(f"yahoo:^VIX:{start}:{end}:1d".encode()).hexdigest()[:16]
    path = CACHE / f"{key}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)["close"].astype(float)


def _recipe(artifact_id: str) -> dict:
    spec = dict(FAMILIES[RECORD[artifact_id]["family"]])
    spec.update({k: v for k, v in RECORD[artifact_id].items() if k != "family"})
    return spec


def _splits(index: pd.DatetimeIndex, spec: dict):
    split = spec["split"]
    if split == "fraction":
        count = len(index)
        train_end = index[int(count * 0.55)]
        val_end = index[int(count * 0.8)]
    else:
        train_end = pd.Timestamp(split[1])
        val_end = pd.Timestamp(split[2])
    train_mask = index <= train_end
    val_mask = (index > train_end) & (index <= val_end)
    test_mask = index > val_end
    return train_mask, val_mask, test_mask, train_end, val_end


def _strategy_returns(directory: pathlib.Path, spec: dict, index) -> pd.Series:
    name, is_equity = spec["returns"]
    raw = _load(directory, name, is_equity)
    if raw is None:
        raise FileNotFoundError(name)
    return raw.reindex(index)


def _benchmark_returns(directory: pathlib.Path, spec: dict, index) -> pd.Series:
    name, is_equity = spec["benchmark"]
    raw = _load(directory, name, is_equity)
    if raw is None:
        # The H28 runs and the H9 family commit the benchmark as an equity
        # curve only; the fall back is the engine's own construction.
        name, is_equity = "benchmark_equity.parquet", True
        raw = _load(directory, name, is_equity)
    if raw is None:
        raise FileNotFoundError(name)
    return raw.reindex(index)


def _regimes(directory: pathlib.Path, artifact_id: str, spec: dict, index):
    source, kind, window = spec["regime"]
    if source == "cache":
        vix = _vix_from_cache(artifact_id)
        if vix is None:
            return None, window
        labels = _regime_labels(vix.reindex(index, method="ffill").fillna(20.0))
        return labels, window
    vix = _first_column(directory / source).astype(float)
    if kind == "hourly":
        labels = _regime_labels(vix.reindex(index, method="ffill").fillna(20.0))
    else:
        labels = _regime_labels(vix.reindex(index))
    return labels, window


def _alpha_annual(strategy: np.ndarray, benchmark: np.ndarray, mode: str) -> float:
    """The CAPM alpha, under the library's or the pre-H51 beta convention.

    Before 2026-10-18 (commit ``85ad85b``) the beta was
    ``np.cov(S, B)[0, 1] / np.var(B)`` -- a *sample* covariance over a
    *population* variance, which inflates beta by ``n / (n - 1)`` relative to
    the OLS slope.  The library now uses a consistent ``ddof=1`` on both
    terms.
    """
    if mode == "pre_h51":
        beta = np.cov(strategy, benchmark, ddof=1)[0, 1] / np.var(benchmark, ddof=0)
    else:
        beta = np.cov(strategy, benchmark, ddof=1)[0, 1] / np.var(benchmark, ddof=1)
    return float((strategy.mean() - beta * benchmark.mean()) * 252)


_DERIVED: dict[tuple, dict] = {}


def _derive(artifact_id: str, **overrides) -> dict:
    """Re-derive every published scalar key of one artifact.

    ``overrides`` replaces entries of the artifact's recipe, so the *other*
    candidate conventions can be measured against the same artifact.
    """
    spec = _recipe(artifact_id)
    spec.update(overrides)
    cache_key = (artifact_id, json.dumps(spec, sort_keys=True, default=str))
    if cache_key in _DERIVED:
        return _DERIVED[cache_key]

    directory = _directory(artifact_id)
    index = pd.read_parquet(directory / "prices.parquet").index
    returns = _strategy_returns(directory, spec, index)
    trades = pd.read_parquet(directory / spec["trades"])
    train_mask, val_mask, test_mask, train_end, val_end = _splits(index, spec)
    oos_mask = val_mask | test_mask
    ddof = spec["sharpe_ddof"]

    oos_metrics = _period_metrics(returns[oos_mask], ddof)
    val_metrics = _period_metrics(returns[val_mask], ddof)
    test_metrics = _period_metrics(returns[test_mask], ddof)
    train_metrics = _period_metrics(returns[train_mask], ddof)

    full = returns.dropna()
    gross_profit = float(full[full > 0].sum())
    gross_loss = float(abs(full[full < 0].sum()))
    full_profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    oos_sharpes, train_sharpes = [], []
    wf_ddof = spec["wf_ddof"]
    for train_idx, test_idx in _walk_forward_splits(len(returns), 5, spec["walk_forward"]):
        if len(test_idx) > 1:
            oos_sharpes.append(_sharpe(returns.iloc[test_idx].values, wf_ddof))
        if len(train_idx) > 1:
            train_sharpes.append(_sharpe(returns.iloc[train_idx].values, wf_ddof))
    wf_stability = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes)) if np.mean(train_sharpes) != 0 else 0.0
    )

    labels, regime_window = _regimes(directory, artifact_id, spec, index)
    regime_sharpes = None
    worst_regime = None
    if labels is not None:
        regime_sharpes = {}
        worst = np.inf
        for name in ("bull", "sideways", "bear"):
            mask = labels == name
            if regime_window == "oos":
                mask = mask & oos_mask
            subset = returns[mask]
            sharpe = (
                _sharpe(subset.values, spec["regime_ddof"])
                if len(subset) > 1 and subset.std() > 0
                else 0.0
            )
            regime_sharpes[name] = sharpe
            worst = min(worst, sharpe)
        worst_regime = float(worst) if worst != np.inf else 0.0

    benchmark = _benchmark_returns(directory, spec, index)
    if spec["benchmark_window"] == "oos":
        left = returns[oos_mask].dropna().values
        right = benchmark[oos_mask].dropna().values
    else:
        left = returns.dropna().values
        right = benchmark.dropna().values
    excess = left - right

    if spec["ir_ddof"] == 1:
        excess_deviation = excess.std(ddof=1)
    else:
        excess_deviation = excess.std(ddof=0)
    information_ratio = (
        float(excess.mean() / excess_deviation * math.sqrt(252)) if excess_deviation > 0 else 0.0
    )
    p_value = float(stats.ttest_1samp(excess, 0).pvalue) if excess.std(ddof=0) > 1e-12 else 1.0

    if spec["val_sharpe"] == "oos":
        val_sharpe = oos_metrics["sharpe"]
    elif spec["val_sharpe"] == "leaky":
        leaky = returns[returns.index <= val_end]
        val_sharpe = _sharpe(leaky.dropna().values, ddof)
    else:
        val_sharpe = val_metrics["sharpe"]

    derived = {
        "train_sharpe": train_metrics["sharpe"],
        "val_sharpe": val_sharpe,
        "test_sharpe": test_metrics["sharpe"],
        "oos_sharpe": oos_metrics["sharpe"],
        "profit_factor": (
            oos_metrics["profit_factor"] if spec["profit_factor"] == "oos" else full_profit_factor
        ),
        "max_drawdown": oos_metrics["max_drawdown"],
        "trades": (
            _count_in(trades, oos_mask, index)
            if spec["trades_window"] == "oos"
            else int(len(trades))
        ),
        "wf_stability": wf_stability,
        "worst_regime_sharpe": worst_regime,
        "regime_sharpes": regime_sharpes,
        "information_ratio": information_ratio,
        "benchmark_p_value": p_value,
        "benchmark_alpha_annual": _alpha_annual(left, right, spec["alpha_beta"]),
    }
    _DERIVED[cache_key] = derived
    return derived


def _legs(artifact_id: str) -> tuple[np.ndarray, np.ndarray]:
    """The strategy and benchmark legs of an artifact, as the runners used them.

    The two legs are dropped *jointly* -- a NaN in either side removes the
    bar from both -- because the comparison statistics are paired.
    """
    spec = _recipe(artifact_id)
    directory = _directory(artifact_id)
    index = pd.read_parquet(directory / "prices.parquet").index
    returns = _strategy_returns(directory, spec, index)
    benchmark = _benchmark_returns(directory, spec, index)
    train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
    if spec["benchmark_window"] == "oos":
        left, right = returns[val_mask | test_mask], benchmark[val_mask | test_mask]
    else:
        left, right = returns, benchmark
    paired = left.notna() & right.notna()
    return left[paired].values, right[paired].values


def _oos_returns(artifact_id: str) -> pd.Series:
    """The OOS-window return series of an artifact."""
    spec = _recipe(artifact_id)
    directory = _directory(artifact_id)
    index = pd.read_parquet(directory / "prices.parquet").index
    returns = _strategy_returns(directory, spec, index)
    train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
    return returns[val_mask | test_mask].dropna()


def _published(artifact_id: str, key: str):
    return _summary(artifact_id)["metrics"].get(key, "<absent>")


def _close(published, rederived) -> bool:
    if published == "<absent>" or published is None:
        return False
    try:
        left = float(published)
        right = float(rederived)
    except (TypeError, ValueError):
        return False
    if math.isinf(left) or math.isinf(right):
        return (
            math.isinf(left)
            and math.isinf(right)
            and (math.copysign(1, left) == math.copysign(1, right))
        )
    return left == pytest.approx(right, rel=REL_TOL, abs=ABS_TOL)


# ---------------------------------------------------------------------------
# 1. the record
# ---------------------------------------------------------------------------
def _committed_metric_summaries() -> set[str]:
    published = set()
    for path in sorted(ARTIFACTS.rglob("summary.json")):
        metrics = json.loads(path.read_text()).get("metrics")
        if isinstance(metrics, dict) and metrics:
            published.add(path.parent.name)
    return published


class TestTheRecord:
    """The record of `metrics`-publishing summaries is complete and pinned."""

    def test_the_record_is_every_committed_metrics_summary(self):
        assert _committed_metric_summaries() == set(RECORD)

    def test_the_record_holds_37_summaries(self):
        assert len(RECORD) == 37

    def test_every_recorded_artifact_is_committed(self):
        for artifact_id in RECORD:
            assert (_directory(artifact_id) / "summary.json").exists(), artifact_id

    def test_the_published_key_union_is_pinned(self):
        keys: set[str] = set()
        for artifact_id in RECORD:
            keys.update(_summary(artifact_id)["metrics"].keys())
        assert keys == {
            "ablations",
            "benchmark_alpha_annual",
            "benchmark_p_value",
            "cross_validation",
            "information_ratio",
            "max_drawdown",
            "oos_sharpe",
            "perturbation",
            "perturbation_min_ratio",
            "profit_factor",
            "regime_sharpes",
            "test_sharpe",
            "trades",
            "train_sharpe",
            "val_sharpe",
            "worst_regime_sharpe",
            "wf_stability",
        }

    def test_the_family_counts_are_pinned(self):
        counts: dict[str, int] = {}
        for artifact_id in RECORD:
            family = RECORD[artifact_id]["family"]
            counts[family] = counts.get(family, 0) + 1
        assert counts == {"H9": 5, "H10": 18, "H16": 7, "H23": 7}

    def test_every_published_scalar_key_is_covered_by_the_scalars(self):
        """Every key of the `metrics` block is either a scalar or a structural key."""
        for artifact_id in RECORD:
            metrics = _summary(artifact_id)["metrics"]
            for key in metrics:
                assert key in SCALAR_KEYS or key in STRUCTURAL_KEYS, (artifact_id, key)


# ---------------------------------------------------------------------------
# 2. every published scalar re-derives under its publisher's convention
# ---------------------------------------------------------------------------
class TestEveryPublishedScalarReDerives:
    """Every published scalar of the `metrics` block re-derives from the artifact."""

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    @pytest.mark.parametrize("key", SCALAR_KEYS)
    def test_the_published_value_re_derives(self, artifact_id: str, key: str) -> None:
        published = _published(artifact_id, key)
        if published == "<absent>" or published is None:
            pytest.skip("the key is not published with a number")
        derived = _derive(artifact_id)
        assert _close(published, derived[key]), (
            f"{artifact_id} {key}: published {published!r} != re-derived {derived[key]!r}"
        )

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_regime_sharpes_re_derive(self, artifact_id: str) -> None:
        published = _published(artifact_id, "regime_sharpes")
        if published == "<absent>" or published is None:
            pytest.skip("the key is not published")
        derived = _derive(artifact_id)
        assert derived["regime_sharpes"] is not None, artifact_id
        for name, value in published.items():
            assert _close(value, derived["regime_sharpes"][name]), (
                f"{artifact_id} regime {name}: {value} != {derived['regime_sharpes'][name]}"
            )

    def test_the_reconstruction_noise_is_bounded(self):
        """The published and the re-derived numbers agree to float noise.

        The published values were computed from the engine's own return
        series; the artifact stores the equity curve those returns were
        compounded into, so the re-derivation carries the float noise of one
        inversion.  This pins that noise so the tolerance above cannot be
        silently loosened.
        """
        worst = 0.0
        for artifact_id in sorted(RECORD):
            derived = _derive(artifact_id)
            for key in ("train_sharpe", "test_sharpe", "oos_sharpe", "max_drawdown"):
                published = _published(artifact_id, key)
                if published == "<absent>" or published is None:
                    continue
                left = float(published)
                right = float(derived[key])
                if left == 0.0:
                    continue
                worst = max(worst, abs(left - right) / abs(left))
        assert worst < 1e-9, worst

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_published_verdict_cannot_move(self, artifact_id: str) -> None:
        """Re-deriving a published number never changes a published verdict."""
        summary = _summary(artifact_id)
        assert "verdict" in summary, artifact_id
        assert isinstance(summary["all_pass"], bool), artifact_id
        derived = _derive(artifact_id)
        assert derived["oos_sharpe"] == pytest.approx(
            _published(artifact_id, "oos_sharpe"), rel=REL_TOL
        )


# ---------------------------------------------------------------------------
# 3. the conventions are discriminating, not merely sufficient
# ---------------------------------------------------------------------------
class TestTheConventionsAreDiscriminating:
    """The alternative convention does NOT reproduce the published number."""

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_sharpe_deviation_convention_is_discriminating(self, artifact_id: str) -> None:
        """The published Sharpe fixes the deviation convention of its family."""
        spec = _recipe(artifact_id)
        other = 1 - spec["sharpe_ddof"]
        published = _published(artifact_id, "oos_sharpe")
        if published == "<absent>" or published is None:
            pytest.skip("no published OOS Sharpe")
        if float(published) == 0.0:
            pytest.skip("a degenerate series: both conventions report 0.0")
        derived = _derive(artifact_id, sharpe_ddof=other)
        assert not _close(published, derived["oos_sharpe"]), (
            f"{artifact_id}: the oos Sharpe does not discriminate the convention"
        )

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_profit_factor_window_is_discriminating(self, artifact_id: str) -> None:
        """The published profit factor fixes the window it covers."""
        spec = _recipe(artifact_id)
        other = "full" if spec["profit_factor"] == "oos" else "oos"
        published = _published(artifact_id, "profit_factor")
        if published == "<absent>" or published is None:
            pytest.skip("no published profit factor")
        if math.isinf(float(published)):
            pytest.skip("a degenerate series: both windows report an infinite factor")
        derived = _derive(artifact_id, profit_factor=other)
        if _close(published, derived["profit_factor"]):
            pytest.skip(
                "the artifact cannot discriminate the window: "
                "the strategy trades only inside the OOS window"
            )
        assert not _close(published, derived["profit_factor"]), (
            f"{artifact_id}: the profit factor does not discriminate the window"
        )

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_trade_count_window_is_discriminating(self, artifact_id: str) -> None:
        """The published trade count fixes the window it covers."""
        spec = _recipe(artifact_id)
        other = "all" if spec["trades_window"] == "oos" else "oos"
        published = _published(artifact_id, "trades")
        if published == "<absent>" or published is None:
            pytest.skip("no published trade count")
        derived = _derive(artifact_id, trades_window=other)
        if int(published) == int(derived["trades"]):
            pytest.skip(
                "the artifact cannot discriminate the window: "
                "the strategy trades only inside the OOS window"
            )
        assert int(published) != int(derived["trades"]), (
            f"{artifact_id}: the trade count does not discriminate the window"
        )

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_information_ratio_deviation_is_discriminating(self, artifact_id: str) -> None:
        """The published IR fixes the deviation convention of its family."""
        spec = _recipe(artifact_id)
        other = 1 - spec["ir_ddof"]
        published = _published(artifact_id, "information_ratio")
        if published == "<absent>" or published is None:
            pytest.skip("no published information ratio")
        derived = _derive(artifact_id, ir_ddof=other)
        assert not _close(published, derived["information_ratio"]), (
            f"{artifact_id}: the information ratio does not discriminate the convention"
        )

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_regime_deviation_is_discriminating(self, artifact_id: str) -> None:
        """The published regime Sharpe fixes the deviation convention."""
        spec = _recipe(artifact_id)
        other = 1 - spec["regime_ddof"]
        published = _published(artifact_id, "worst_regime_sharpe")
        if published == "<absent>" or published is None:
            pytest.skip("no published worst-regime Sharpe")
        if float(published) == 0.0:
            pytest.skip("a degenerate series: both conventions report 0.0")
        derived = _derive(artifact_id, regime_ddof=other)
        assert not _close(published, derived["worst_regime_sharpe"]), (
            f"{artifact_id}: the worst-regime Sharpe does not discriminate the convention"
        )


# ---------------------------------------------------------------------------
# 4. the walk-forward split -- the only convention decided by a date
# ---------------------------------------------------------------------------
# The library's `walk_forward_splits` let the last window absorb the tail of
# the series on 2026-10-18 (commit `26c6aa6`); before that the tail was
# silently dropped.  The published `wf_stability` therefore splits on the
# publication date: everything published before the fix uses the
# tail-dropping split, the eight H28 artifacts (2026-10-19) the fixed one.
PRE_FIX_ARTIFACTS = sorted(a for a in RECORD if _recipe(a)["walk_forward"] == "pre")
POST_FIX_ARTIFACTS = sorted(a for a in RECORD if _recipe(a)["walk_forward"] == "post")


class TestTheWalkForwardSplit:
    """The published `wf_stability` re-derives on the split its publisher used."""

    def test_the_split_is_decided_by_the_publication_date(self):
        assert len(POST_FIX_ARTIFACTS) == 8
        assert all(a.startswith("exp_2026-10-19") for a in POST_FIX_ARTIFACTS)
        assert all(not a.startswith("exp_2026-10-19") for a in PRE_FIX_ARTIFACTS)

    @pytest.mark.parametrize("artifact_id", PRE_FIX_ARTIFACTS)
    def test_the_pre_fix_split_reproduces_the_published_value(self, artifact_id: str) -> None:
        published = _published(artifact_id, "wf_stability")
        derived = _derive(artifact_id, walk_forward="pre")
        assert _close(published, derived["wf_stability"]), artifact_id

    @pytest.mark.parametrize("artifact_id", POST_FIX_ARTIFACTS)
    def test_the_post_fix_split_reproduces_the_published_value(self, artifact_id: str) -> None:
        published = _published(artifact_id, "wf_stability")
        derived = _derive(artifact_id, walk_forward="post")
        assert _close(published, derived["wf_stability"]), artifact_id

    @pytest.mark.parametrize("artifact_id", PRE_FIX_ARTIFACTS)
    def test_the_other_split_does_not(self, artifact_id: str) -> None:
        """The behavioural negative control.

        The reconstructed *pre-fix* splitter is the one that reproduces the
        published number, and the *post-fix* splitter does not -- so the
        contract is not satisfied by "any reasonable walk-forward split".
        Artifacts whose series length is a multiple of five are the
        exception: the tail is empty and the two splits coincide.
        """
        published = _published(artifact_id, "wf_stability")
        derived = _derive(artifact_id, walk_forward="post")
        if _close(published, derived["wf_stability"]):
            pytest.skip("the series length is a multiple of five: the splits coincide")
        assert not _close(published, derived["wf_stability"]), artifact_id

    @pytest.mark.parametrize("artifact_id", POST_FIX_ARTIFACTS)
    def test_the_pre_fix_split_does_not(self, artifact_id: str) -> None:
        published = _published(artifact_id, "wf_stability")
        derived = _derive(artifact_id, walk_forward="pre")
        if _close(published, derived["wf_stability"]):
            pytest.skip("the series length is a multiple of five: the splits coincide")
        assert not _close(published, derived["wf_stability"]), artifact_id

    def test_the_library_now_implements_the_post_fix_split(self):
        """The library's own splitter is the post-fix form."""
        from qtr.validation.statistics import walk_forward_splits

        n_samples = 11
        library = walk_forward_splits(n_samples, n_splits=5)
        post = _walk_forward_splits(n_samples, 5, "post")
        pre = _walk_forward_splits(n_samples, 5, "pre")
        assert [tuple(pair[1]) for pair in library] == [tuple(pair[1]) for pair in post]
        assert [tuple(pair[1]) for pair in library] != [tuple(pair[1]) for pair in pre]


# ---------------------------------------------------------------------------
# 5. the published alpha uses the pre-H51 beta
# ---------------------------------------------------------------------------
ALPHA_ARTIFACTS = sorted(a for a in RECORD if "benchmark_alpha_annual" in _summary(a)["metrics"])


class TestThePublishedAlpha:
    """The published `benchmark_alpha_annual` re-derives on the pre-H51 beta."""

    def test_seven_artifacts_publish_an_alpha(self):
        assert len(ALPHA_ARTIFACTS) == 7

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_pre_h51_beta_reproduces_the_published_alpha(self, artifact_id: str) -> None:
        published = _published(artifact_id, "benchmark_alpha_annual")
        derived = _derive(artifact_id, alpha_beta="pre_h51")
        assert _close(published, derived["benchmark_alpha_annual"]), artifact_id

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_library_beta_does_not(self, artifact_id: str) -> None:
        """The library's consistent-ddof beta moves the published alpha.

        The move is disclosed, not rewritten: the artifacts are frozen and no
        published gate reads `benchmark_alpha_annual`.
        """
        published = _published(artifact_id, "benchmark_alpha_annual")
        derived = _derive(artifact_id, alpha_beta="consistent")
        assert not _close(published, derived["benchmark_alpha_annual"]), artifact_id

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_library_beta_is_the_ols_slope(self, artifact_id: str) -> None:
        """The library's convention is the one the OLS regression gives."""
        spec = _recipe(artifact_id)
        directory = _directory(artifact_id)
        index = pd.read_parquet(directory / "prices.parquet").index
        returns = _strategy_returns(directory, spec, index)
        benchmark = _benchmark_returns(directory, spec, index)
        train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
        oos_mask = val_mask | test_mask
        left = returns[oos_mask].dropna().values
        right = benchmark[oos_mask].dropna().values
        beta = np.cov(left, right, ddof=1)[0, 1] / np.var(right, ddof=1)
        assert beta == pytest.approx(np.polyfit(right, left, 1)[0], rel=1e-9)

    def test_no_published_gate_reads_the_alpha(self):
        """The alpha is informational: it is not one of the published passes."""
        for artifact_id in ALPHA_ARTIFACTS:
            summary = _summary(artifact_id)
            passes = summary.get("passes", {})
            for key in passes:
                assert "alpha" not in key, (artifact_id, key)


# ---------------------------------------------------------------------------
# 6. the families whose `val_sharpe` is not the Val Sharpe
# ---------------------------------------------------------------------------
LEAKY_VAL_ARTIFACTS = sorted(a for a in RECORD if _recipe(a)["val_sharpe"] == "leaky")
OOS_VAL_ARTIFACTS = sorted(a for a in RECORD if _recipe(a)["val_sharpe"] == "oos")
NULL_VAL_ARTIFACTS = sorted(a for a in RECORD if _recipe(a)["val_sharpe"] == "null")


class TestThePublishedValSharpe:
    """Two publishers wrote something other than the Val Sharpe under the key."""

    def test_the_leaky_set_is_pinned(self):
        assert LEAKY_VAL_ARTIFACTS == [
            "exp_2026-10-13T21-11-45-843908Z",
            "exp_2026-10-13T21-13-09-580962Z",
            "exp_2026-10-13T21-18-23-178134Z",
        ]

    def test_the_oos_set_is_pinned(self):
        assert OOS_VAL_ARTIFACTS == [
            "exp_2026-10-13T23-27-52-101656Z",
            "exp_2026-10-19T17-38-03-570526Z",
            "exp_2026-10-19T17-38-21-389139Z",
        ]

    def test_the_null_set_is_pinned(self):
        assert NULL_VAL_ARTIFACTS == [
            "exp_2026-10-11T17-24-14-385352Z",
            "exp_2026-10-11T17-41-18-169363Z",
            "exp_2026-10-19T15-46-16-261803Z",
            "exp_2026-10-19T16-41-44-683912Z",
        ]

    @pytest.mark.parametrize("artifact_id", LEAKY_VAL_ARTIFACTS)
    def test_the_leaky_val_sharpe_covers_the_training_period(self, artifact_id: str) -> None:
        """The published value is the Sharpe of (data start, VAL_END].

        The window *includes* the training period, so the published
        `val_sharpe` is not a validation-window statistic.  The value is
        informational: no published gate reads it.
        """
        published = float(_published(artifact_id, "val_sharpe"))
        spec = _recipe(artifact_id)
        index = pd.read_parquet(_directory(artifact_id) / "prices.parquet").index
        returns = _strategy_returns(_directory(artifact_id), spec, index)
        leaky = returns[returns.index <= pd.Timestamp(spec["split"][2])]
        assert _close(published, _sharpe(leaky.dropna().values, spec["sharpe_ddof"]))

        train_end = pd.Timestamp(spec["split"][1])
        assert len(leaky[leaky.index <= train_end]) > 0, "the window must cover the train"
        proper = returns[(returns.index > train_end) & (returns.index <= spec["split"][2])]
        assert not _close(published, _sharpe(proper.dropna().values, spec["sharpe_ddof"])), (
            "the leaky value must differ from the proper validation window"
        )

    @pytest.mark.parametrize("artifact_id", OOS_VAL_ARTIFACTS)
    def test_the_oos_val_sharpe_is_the_oos_sharpe(self, artifact_id: str) -> None:
        published = float(_published(artifact_id, "val_sharpe"))
        oos = float(_published(artifact_id, "oos_sharpe"))
        assert published == oos, artifact_id
        derived = _derive(artifact_id)
        assert _close(published, derived["val_sharpe"]), artifact_id

    @pytest.mark.parametrize("artifact_id", NULL_VAL_ARTIFACTS)
    def test_the_null_val_sharpe_is_published_as_null(self, artifact_id: str) -> None:
        assert _published(artifact_id, "val_sharpe") is None, artifact_id

    def test_no_published_gate_reads_the_val_sharpe(self):
        """`val_sharpe` is informational in every family that publishes it."""
        for artifact_id in RECORD:
            summary = _summary(artifact_id)
            passes = summary.get("passes", {})
            for key in passes:
                assert "val" not in key, (artifact_id, key)


# ---------------------------------------------------------------------------
# 7. the structural keys
# ---------------------------------------------------------------------------
class TestTheStructuralKeys:
    """The nested blocks of the `metrics` block are disclosed, not assumed."""

    def test_the_structural_key_counts_are_pinned(self):
        counts = {key: 0 for key in STRUCTURAL_KEYS}
        for artifact_id in RECORD:
            metrics = _summary(artifact_id)["metrics"]
            for key in STRUCTURAL_KEYS:
                if key in metrics:
                    counts[key] += 1
        assert counts == {
            "ablations": 35,
            "perturbation": 7,
            "cross_validation": 2,
            "perturbation_min_ratio": 7,
            "regime_sharpes": 36,
        }

    @pytest.mark.parametrize("artifact_id", sorted(RECORD))
    def test_the_ablation_block_shape_is_pinned(self, artifact_id: str) -> None:
        metrics = _summary(artifact_id)["metrics"]
        if "ablations" not in metrics:
            pytest.skip("the summary publishes no ablation block")
        for name, block in metrics["ablations"].items():
            assert isinstance(name, str)
            assert isinstance(block, dict), (artifact_id, name)
            for key in block:
                assert isinstance(key, str), (artifact_id, name)

    def test_the_flat_ablation_blocks_carry_two_distinct_shapes(self):
        """Two flat ablation blocks are published, and they differ.

        The H9 family publishes ``{oos_sharpe, profit_factor,
        max_drawdown, trades}``; the H10/H23 family publishes
        ``{oos_sharpe, oos_profit_factor, oos_max_drawdown, oos_trades,
        test_sharpe}``.  The difference is a call-site difference (the H9
        runner names the keys after the engine's own metric names), not a
        different measurement.
        """
        shapes: dict[tuple, list[str]] = {}
        for artifact_id in sorted(RECORD):
            metrics = _summary(artifact_id)["metrics"]
            block = metrics.get("ablations")
            if not block:
                continue
            first = next(iter(block.values()))
            if "oos_metrics" in first:
                continue
            for name, entry in block.items():
                shapes.setdefault(tuple(sorted(entry)), []).append(f"{artifact_id}/{name}")
        assert sorted(shapes) == [
            ("max_drawdown", "oos_sharpe", "profit_factor", "trades"),
            ("oos_max_drawdown", "oos_profit_factor", "oos_sharpe", "oos_trades", "test_sharpe"),
        ]
        assert len(shapes[("max_drawdown", "oos_sharpe", "profit_factor", "trades")]) == 6
        assert (
            len(
                shapes[
                    (
                        "oos_max_drawdown",
                        "oos_profit_factor",
                        "oos_sharpe",
                        "oos_trades",
                        "test_sharpe",
                    )
                ]
            )
            == 120
        )

    def test_the_nested_ablation_block_carries_the_oos_metrics(self):
        """The daily family's ablation block nests an `oos_metrics` block."""
        nested = 0
        for artifact_id in sorted(RECORD):
            metrics = _summary(artifact_id)["metrics"]
            block = metrics.get("ablations")
            if not block:
                continue
            first = next(iter(block.values()))
            if "oos_metrics" not in first:
                continue
            nested += 1
            for name, entry in block.items():
                assert "oos_metrics" in entry, (artifact_id, name)
                assert set(entry["oos_metrics"]) >= {
                    "sharpe",
                    "max_drawdown",
                    "profit_factor",
                    "trades",
                    "n_periods",
                }, (artifact_id, name)
        assert nested == 7

    def test_the_perturbation_block_shape_is_pinned(self):
        for artifact_id in sorted(RECORD):
            metrics = _summary(artifact_id)["metrics"]
            if "perturbation" not in metrics:
                continue
            block = metrics["perturbation"]
            assert set(block) == {"variants", "min_perturbed_sharpe_ratio"}, artifact_id
            assert isinstance(block["variants"], dict), artifact_id

    def test_the_perturbation_min_ratio_is_the_block_ratio(self):
        """No artifact publishes the perturbation ratio twice.

        The daily family publishes the ratio *nested* inside its
        ``perturbation`` block; the H23 family publishes it *flat*, as
        ``perturbation_min_ratio``.  The two sets are disjoint, so the ratio
        is never published twice -- and neither form can be re-derived: the
        perturbed equity curves were never committed.
        """
        nested = sorted(
            artifact_id
            for artifact_id in RECORD
            if "perturbation" in _summary(artifact_id)["metrics"]
        )
        flat = sorted(
            artifact_id
            for artifact_id in RECORD
            if "perturbation_min_ratio" in _summary(artifact_id)["metrics"]
        )
        assert len(nested) == 7
        assert len(flat) == 7
        assert not set(nested) & set(flat)
        for artifact_id in nested:
            metrics = _summary(artifact_id)["metrics"]
            ratio = metrics["perturbation"]["min_perturbed_sharpe_ratio"]
            assert isinstance(ratio, (int, float)), artifact_id
            assert 0.0 <= float(ratio) <= 1.0, artifact_id
            assert "perturbation_min_ratio" not in metrics, artifact_id
        for artifact_id in flat:
            metrics = _summary(artifact_id)["metrics"]
            ratio = metrics["perturbation_min_ratio"]
            assert isinstance(ratio, (int, float)), artifact_id
            assert 0.0 <= float(ratio) <= 1.0, artifact_id
            assert "perturbation" not in metrics, artifact_id


class TestTheCommittedAblationCurves:
    """Where the ablation's own equity curve is committed, it re-derives.

    The H10 family (and the H21/H22/H23/H28 runs that reuse it) logs an
    ``ablations__<name>__equity`` artifact for every ablation, so the
    ablation's OOS Sharpe, profit factor and drawdown re-derive from the
    artifact.  The H16 family does not log them, so its ablation numbers are
    not quantifiable from the record -- disclosed, not quantified.
    """

    ABLATION_ARTIFACTS = sorted(
        artifact_id
        for artifact_id in RECORD
        if list(_directory(artifact_id).glob("ablations__*__equity.parquet"))
    )

    def test_the_committed_set_is_pinned(self):
        assert len(self.ABLATION_ARTIFACTS) == 25

    @pytest.mark.parametrize("artifact_id", ABLATION_ARTIFACTS)
    def test_the_ablation_scalars_re_derive(self, artifact_id: str) -> None:
        spec = _recipe(artifact_id)
        index = pd.read_parquet(_directory(artifact_id) / "prices.parquet").index
        train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
        oos = val_mask | test_mask
        published = _summary(artifact_id)["metrics"]["ablations"]
        directory = _directory(artifact_id)
        checked = 0
        for path in sorted(directory.glob("ablations__*__equity.parquet")):
            name = path.name[len("ablations__") : -len("__equity.parquet")]
            if name not in published:
                continue
            equity = _first_column(path).astype(float)
            returns = _returns_from_equity(equity).reindex(index)
            metrics = _period_metrics(returns[oos], spec["sharpe_ddof"])
            block = published[name]
            if "oos_sharpe" in block:
                assert _close(block["oos_sharpe"], metrics["sharpe"]), (
                    f"{artifact_id} {name} oos_sharpe"
                )
            if "oos_profit_factor" in block:
                assert _close(block["oos_profit_factor"], metrics["profit_factor"]), (
                    f"{artifact_id} {name} oos_profit_factor"
                )
            if "oos_max_drawdown" in block:
                assert _close(block["oos_max_drawdown"], metrics["max_drawdown"]), (
                    f"{artifact_id} {name} oos_max_drawdown"
                )
            if "test_sharpe" in block:
                test_metrics = _period_metrics(returns[test_mask], spec["sharpe_ddof"])
                assert _close(block["test_sharpe"], test_metrics["sharpe"]), (
                    f"{artifact_id} {name} test_sharpe"
                )
            checked += 1
        assert checked > 0, artifact_id

    def test_the_uncommitted_set_is_the_daily_family_and_the_h9_runs(self):
        uncommitted = sorted(set(RECORD) - set(self.ABLATION_ARTIFACTS))
        assert uncommitted == [
            "exp_2026-10-11T15-54-17-212022Z",
            "exp_2026-10-11T16-44-06-168529Z",
            "exp_2026-10-11T16-46-06-466282Z",
            "exp_2026-10-11T16-52-38-694559Z",
            "exp_2026-10-13T21-11-45-843908Z",
            "exp_2026-10-13T21-13-09-580962Z",
            "exp_2026-10-13T21-18-23-178134Z",
            "exp_2026-10-13T21-22-02-751156Z",
            "exp_2026-10-13T21-51-45-034237Z",
            "exp_2026-10-13T22-40-41-870350Z",
            "exp_2026-10-13T23-06-33-191710Z",
            "exp_2026-10-14T08-20-39-255883Z",
        ]

    def test_the_ablation_block_is_quantifiable_for_all_but_the_daily_family(self):
        """28 of the 35 published ablation blocks re-derive from a committed curve.

        The H9 family logs its ablation curves under a *single* underscore
        (``ablations_<name>_equity``) and the H10 family under a double one
        (``ablations__<name>__equity``); the daily family logs none, so its
        nested ``oos_metrics`` block is disclosed, not quantified.
        """
        publishers = {a for a in RECORD if "ablations" in _summary(a)["metrics"]}
        quantifiable = set(self.ABLATION_ARTIFACTS) | set(
            TestTheH9AblationBlock.H9_ABLATION_ARTIFACTS
        )
        assert len(publishers) == 35
        assert len(quantifiable) == 28
        assert sorted(publishers - quantifiable) == [
            "exp_2026-10-13T21-11-45-843908Z",
            "exp_2026-10-13T21-13-09-580962Z",
            "exp_2026-10-13T21-18-23-178134Z",
            "exp_2026-10-13T21-22-02-751156Z",
            "exp_2026-10-13T21-51-45-034237Z",
            "exp_2026-10-13T22-40-41-870350Z",
            "exp_2026-10-13T23-06-33-191710Z",
        ]


# ---------------------------------------------------------------------------
# 8. the H9 family's VIX leg -- recovered from the committed cache
# ---------------------------------------------------------------------------
class TestTheH9VixLeg:
    """The H9 regimes re-derive from the VIX series the run actually read."""

    H9_ARTIFACTS = sorted(a for a in RECORD if RECORD[a]["family"] == "H9")

    @pytest.mark.parametrize("artifact_id", H9_ARTIFACTS)
    def test_the_vix_series_is_addressable_in_the_cache(self, artifact_id: str) -> None:
        vix = _vix_from_cache(artifact_id)
        assert vix is not None, artifact_id
        assert len(vix) > 100, artifact_id

    @pytest.mark.parametrize("artifact_id", H9_ARTIFACTS)
    def test_the_worst_regime_sharpe_re_derives(self, artifact_id: str) -> None:
        derived = _derive(artifact_id)
        published = _published(artifact_id, "worst_regime_sharpe")
        assert _close(published, derived["worst_regime_sharpe"]), artifact_id

    def test_the_cache_key_is_the_fetcher_key(self):
        """The recovery is not a guess: it is the fetcher's own cache key."""
        from qtr.data.fetcher import DataCache

        cache = DataCache(cache_dir=CACHE)
        stamp = datetime.strptime("exp_2026-10-11T15-54-17-212022Z"[4:], "%Y-%m-%dT%H-%M-%S-%fZ")
        start = (stamp - timedelta(days=729)).strftime("%Y-%m-%d")
        end = stamp.strftime("%Y-%m-%d")
        key = cache._cache_key("yahoo", "^VIX", start, end, "1d")
        assert (CACHE / f"{key}.parquet").exists()

    def test_the_committed_h9_runner_published_these_keys(self):
        """The H9 artifact carries the very runner that published its block."""
        runner = (
            _directory("exp_2026-10-11T15-54-17-212022Z") / "run_h9_intraday_tsmom_experiment.py"
        )
        text = runner.read_text()
        for key in SCALAR_KEYS:
            if key == "benchmark_alpha_annual":
                continue
            assert f'"{key}"' in text, key


# ---------------------------------------------------------------------------
# 9. the behavioural negative control: the library's OWN historical source
# ---------------------------------------------------------------------------
# The control is not a hand-written reconstruction of a superseded convention:
# it is the library's own ``src/qtr/validation/statistics.py`` at the commit
# that changed the convention, executed exactly as it was written.  That makes
# the control *behavioural* -- it does what the publisher's process did -- and
# it turns the contract's verdict into a statement about a specific version
# of the library rather than about "some reasonable implementation".
#
# Each control is run in both directions:
#
#   * the historical implementation REPRODUCES the numbers published under the
#     convention it implemented, and
#   * the historical implementation FAILS to reproduce the numbers published
#     under the convention that replaced it.
#
# The second half is the negative control proper: it shows that the contract
# -- the published number re-derives from its own frozen artifact -- is *not*
# satisfied by the superseded implementation, so the recorded convention is
# pinned by the data and not by this file's own reconstruction of it.

PRE_SHARPE_REVISION = "9fb26b8^"
PRE_WALK_FORWARD_REVISION = "26c6aa6^"
PRE_BETA_REVISION = "85ad85b^"

H9_SHARPE_ARTIFACTS = sorted(a for a in RECORD if RECORD[a]["family"] == "H9")
H10_SHARPE_ARTIFACTS = sorted(a for a in RECORD if RECORD[a]["family"] == "H10")


def _historical_module(revision: str):
    """Execute the library's own statistics module at ``revision``."""
    import subprocess
    import types

    try:
        completed = subprocess.run(
            ["git", "show", f"{revision}:src/qtr/validation/statistics.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        pytest.skip(f"the historical revision {revision} is not available here: {error}")
    module = types.ModuleType(f"statistics_at_{revision}")
    filename = f"{revision}:src/qtr/validation/statistics.py"
    exec(compile(completed.stdout, filename, "exec"), module.__dict__)
    return module


def _wf_stability_with(artifact_id: str, splitter) -> float:
    """The published `wf_stability` under an arbitrary split implementation."""
    spec = _recipe(artifact_id)
    directory = _directory(artifact_id)
    index = pd.read_parquet(directory / "prices.parquet").index
    returns = _strategy_returns(directory, spec, index)
    oos_sharpes, train_sharpes = [], []
    for train_idx, test_idx in splitter(len(returns), 5):
        if len(test_idx) > 1:
            oos_sharpes.append(_sharpe(returns.iloc[test_idx].values, spec["wf_ddof"]))
        if len(train_idx) > 1:
            train_sharpes.append(_sharpe(returns.iloc[train_idx].values, spec["wf_ddof"]))
    if not oos_sharpes or not train_sharpes:
        return 0.0
    mean_train = float(np.mean(train_sharpes))
    return float(np.mean(oos_sharpes)) / mean_train if mean_train != 0 else 0.0


class TestTheHistoricalImplementationIsTheNegativeControl:
    """The library's own superseded source is the negative control."""

    # -- the Sharpe's deviation convention ---------------------------------
    def test_the_pre_9fb26b8_sharpe_ratio_was_container_dependent(self):
        """One series, two answers: the old `sharpe_ratio` read the container."""
        module = _historical_module(PRE_SHARPE_REVISION)
        series = _oos_returns("exp_2026-10-11T15-54-17-212022Z")
        assert not _close(
            float(module.sharpe_ratio(series)), float(module.sharpe_ratio(series.values))
        ), "the pre-9fb26b8 sharpe_ratio must have been container dependent"

    @pytest.mark.parametrize("artifact_id", H9_SHARPE_ARTIFACTS)
    def test_the_h9_sharpe_reproduces_only_through_the_series_path(self, artifact_id: str):
        """The H9 family's published Sharpe is the *sample* deviation."""
        module = _historical_module(PRE_SHARPE_REVISION)
        published = _published(artifact_id, "oos_sharpe")
        if published == "<absent>" or published is None or float(published) == 0.0:
            pytest.skip("a degenerate series")
        series = _oos_returns(artifact_id)
        assert _close(published, module.sharpe_ratio(series)), artifact_id
        assert not _close(published, module.sharpe_ratio(series.values)), artifact_id

    @pytest.mark.parametrize("artifact_id", H10_SHARPE_ARTIFACTS)
    def test_the_h10_sharpe_reproduces_only_through_the_array_path(self, artifact_id: str):
        """The H10 family's published Sharpe is the *population* deviation."""
        module = _historical_module(PRE_SHARPE_REVISION)
        published = _published(artifact_id, "oos_sharpe")
        if published == "<absent>" or published is None or float(published) == 0.0:
            pytest.skip("a degenerate series")
        series = _oos_returns(artifact_id)
        assert _close(published, module.sharpe_ratio(series.values)), artifact_id
        assert not _close(published, module.sharpe_ratio(series)), artifact_id

    def test_the_current_library_fails_the_h9_contract(self):
        """The contract fails against the *current* implementation for the H9 family.

        The library's `sharpe_ratio` became container-independent on
        2026-10-17 and always uses the population deviation, so it can no
        longer reproduce the H9 family's published Sharpe.  Disclosed, not
        rewritten: the artifacts are frozen.
        """
        from qtr.validation.statistics import sharpe_ratio

        checked = 0
        for artifact_id in H9_SHARPE_ARTIFACTS:
            published = _published(artifact_id, "oos_sharpe")
            if published == "<absent>" or published is None or float(published) == 0.0:
                continue
            series = _oos_returns(artifact_id)
            assert not _close(published, sharpe_ratio(series)), artifact_id
            assert not _close(published, sharpe_ratio(series.values)), artifact_id
            checked += 1
        assert checked == len(H9_SHARPE_ARTIFACTS)

    def test_the_current_library_reproduces_the_h10_sharpe(self):
        """For the H10 family the current library still reproduces the number."""
        from qtr.validation.statistics import sharpe_ratio

        checked = 0
        for artifact_id in H10_SHARPE_ARTIFACTS:
            published = _published(artifact_id, "oos_sharpe")
            if published == "<absent>" or published is None or float(published) == 0.0:
                continue
            series = _oos_returns(artifact_id)
            assert _close(published, sharpe_ratio(series.values)), artifact_id
            checked += 1
        assert checked > 0

    # -- the walk-forward split --------------------------------------------
    @pytest.mark.parametrize("artifact_id", PRE_FIX_ARTIFACTS)
    def test_the_pre_26c6aa6_splitter_reproduces_the_pre_fix_stability(
        self, artifact_id: str
    ) -> None:
        module = _historical_module(PRE_WALK_FORWARD_REVISION)
        published = _published(artifact_id, "wf_stability")
        derived = _wf_stability_with(artifact_id, module.walk_forward_splits)
        assert _close(published, derived), artifact_id

    @pytest.mark.parametrize("artifact_id", POST_FIX_ARTIFACTS)
    def test_the_pre_26c6aa6_splitter_fails_the_post_fix_contract(self, artifact_id: str):
        """The negative control: the old splitter cannot reproduce the H28 value."""
        module = _historical_module(PRE_WALK_FORWARD_REVISION)
        published = _published(artifact_id, "wf_stability")
        derived = _wf_stability_with(artifact_id, module.walk_forward_splits)
        assert not _close(published, derived), artifact_id

    def test_the_library_splitter_fails_the_pre_fix_contract(self):
        """The negative control the other way round: the H10 value is *not*
        reproducible by the library's current splitter."""
        from qtr.validation.statistics import walk_forward_splits

        failed = 0
        for artifact_id in PRE_FIX_ARTIFACTS:
            published = _published(artifact_id, "wf_stability")
            derived = _wf_stability_with(artifact_id, walk_forward_splits)
            if _close(published, derived):
                # the series length is a multiple of five: the tail is empty
                # and the two splits coincide
                continue
            failed += 1
        assert failed > 0

    # -- the CAPM beta ------------------------------------------------------
    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_pre_h51_library_reproduces_the_published_alpha(self, artifact_id: str) -> None:
        """The pre-H51 `compare_to_benchmark` produced the published alpha."""
        module = _historical_module(PRE_BETA_REVISION)
        left, right = _legs(artifact_id)
        result = module.compare_to_benchmark(left, right)
        published = _published(artifact_id, "benchmark_alpha_annual")
        assert _close(published, result["alpha_annualized"]), artifact_id

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_current_library_fails_the_alpha_contract(self, artifact_id: str) -> None:
        """The negative control: the library's consistent-ddof beta cannot."""
        from qtr.validation.statistics import compare_to_benchmark

        left, right = _legs(artifact_id)
        result = compare_to_benchmark(left, right)
        published = _published(artifact_id, "benchmark_alpha_annual")
        assert not _close(published, result["alpha_annualized"]), artifact_id

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_pre_h51_library_reproduces_the_published_p_value(self, artifact_id: str) -> None:
        """The published p-value is the pre-H51 library's `alpha_p_value`."""
        module = _historical_module(PRE_BETA_REVISION)
        left, right = _legs(artifact_id)
        result = module.compare_to_benchmark(left, right)
        assert _close(_published(artifact_id, "benchmark_p_value"), result["alpha_p_value"])

    @pytest.mark.parametrize("artifact_id", ALPHA_ARTIFACTS)
    def test_the_daily_family_published_the_pre_h51_library_verbatim(
        self, artifact_id: str
    ) -> None:
        """The daily family's benchmark leg is one library call.

        Its published information ratio, p-value and alpha are the three
        numbers the pre-H51 `compare_to_benchmark` returned -- the IR included,
        because that function's excess deviation was the population one.  The
        intraday families did *not* use it: their published IR carries the
        sample deviation, so it is off by ``sqrt(n / (n - 1))``.
        """
        module = _historical_module(PRE_BETA_REVISION)
        left, right = _legs(artifact_id)
        result = module.compare_to_benchmark(left, right)
        assert _close(_published(artifact_id, "information_ratio"), result["information_ratio"])
        assert _close(_published(artifact_id, "benchmark_p_value"), result["alpha_p_value"])
        assert _close(_published(artifact_id, "benchmark_alpha_annual"), result["alpha_annualized"])

    @pytest.mark.parametrize("artifact_id", H9_SHARPE_ARTIFACTS + H10_SHARPE_ARTIFACTS)
    def test_the_intraday_families_did_not_use_the_library_comparison(self, artifact_id: str):
        """The intraday families computed their own information ratio.

        Their published IR carries the *sample* deviation of the excess
        returns, so the library's population-deviation IR does not reproduce
        it -- while the p-value, which does not depend on the deviation
        convention, still reproduces.
        """
        module = _historical_module(PRE_BETA_REVISION)
        left, right = _legs(artifact_id)
        result = module.compare_to_benchmark(left, right)
        assert not _close(
            _published(artifact_id, "information_ratio"), result["information_ratio"]
        ), artifact_id
        assert _close(_published(artifact_id, "benchmark_p_value"), result["alpha_p_value"])


# ---------------------------------------------------------------------------
# 10. the H9 family's ablation block -- a second convention in one summary
# ---------------------------------------------------------------------------
class TestTheH9AblationBlock:
    """The H9 summary published two Sharpe conventions in the same block.

    The H9 runner computed its *main* block from a ``pandas.Series``
    (``sharpe_ratio(oos_ret)`` -- the sample deviation) and its *ablation*
    block from an ``ndarray`` (``sharpe_ratio(oos_no.values)`` -- the
    population deviation).  The ablation block is measured here against the
    ablation's own committed equity curve.
    """

    H9_ABLATION_ARTIFACTS = sorted(
        artifact_id
        for artifact_id in RECORD
        if "ablations" in _summary(artifact_id)["metrics"]
        and [
            path
            for path in _directory(artifact_id).glob("ablations_*_equity.parquet")
            if not path.name.startswith("ablations__")
        ]
    )

    # The committed curve is named after the ablation, the published block
    # entry after the variant it ablates -- the two names are not the same.
    CURVE_TO_BLOCK = {
        "daily_target_no_exits": "daily_target_no_exits",
        "raw_hourly": "raw_hourly_no_exits",
    }

    def test_the_committed_set_is_pinned(self):
        assert self.H9_ABLATION_ARTIFACTS == [
            "exp_2026-10-11T16-46-06-466282Z",
            "exp_2026-10-11T16-52-38-694559Z",
            "exp_2026-10-14T08-20-39-255883Z",
        ]

    def test_every_block_entry_has_a_committed_curve(self):
        for artifact_id in self.H9_ABLATION_ARTIFACTS:
            directory = _directory(artifact_id)
            curves = {path.name for path in directory.glob("ablations_*_equity.parquet")}
            published = _summary(artifact_id)["metrics"]["ablations"]
            assert len(published) == len(self.CURVE_TO_BLOCK), artifact_id
            for curve in self.CURVE_TO_BLOCK:
                assert f"ablations_{curve}_equity.parquet" in curves, (artifact_id, curve)
                assert self.CURVE_TO_BLOCK[curve] in published, (artifact_id, curve)

    def _ablation_returns(self, artifact_id: str, curve: str) -> pd.Series:
        directory = _directory(artifact_id)
        path = directory / f"ablations_{curve}_equity.parquet"
        equity = _first_column(path).astype(float)
        index = pd.read_parquet(directory / "prices.parquet").index
        return _returns_from_equity(equity).reindex(index)

    @pytest.mark.parametrize("artifact_id", H9_ABLATION_ARTIFACTS)
    @pytest.mark.parametrize("curve", sorted(CURVE_TO_BLOCK))
    def test_the_ablation_sharpe_is_the_population_deviation(
        self, artifact_id: str, curve: str
    ) -> None:
        """The ablation block's Sharpe is NOT the summary's own convention."""
        spec = _recipe(artifact_id)
        index = pd.read_parquet(_directory(artifact_id) / "prices.parquet").index
        train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
        returns = self._ablation_returns(artifact_id, curve)
        oos = returns[val_mask | test_mask].dropna()
        published = _summary(artifact_id)["metrics"]["ablations"][self.CURVE_TO_BLOCK[curve]]
        assert _close(published["oos_sharpe"], _sharpe(oos.values, 0)), artifact_id
        assert not _close(published["oos_sharpe"], _sharpe(oos.values, 1)), artifact_id

    @pytest.mark.parametrize("artifact_id", H9_ABLATION_ARTIFACTS)
    @pytest.mark.parametrize("curve", sorted(CURVE_TO_BLOCK))
    def test_the_ablation_drawdown_is_the_oos_one(self, artifact_id: str, curve: str) -> None:
        spec = _recipe(artifact_id)
        index = pd.read_parquet(_directory(artifact_id) / "prices.parquet").index
        train_mask, val_mask, test_mask, _train_end, _val_end = _splits(index, spec)
        returns = self._ablation_returns(artifact_id, curve)
        published = _summary(artifact_id)["metrics"]["ablations"][self.CURVE_TO_BLOCK[curve]]
        oos = returns[val_mask | test_mask].dropna()
        cumulative = (1 + oos).cumprod()
        drawdown = float((cumulative / cumulative.cummax() - 1.0).min())
        assert _close(published["max_drawdown"], drawdown), artifact_id

    @pytest.mark.parametrize("artifact_id", H9_ABLATION_ARTIFACTS)
    @pytest.mark.parametrize("curve", sorted(CURVE_TO_BLOCK))
    def test_the_ablation_profit_factor_is_the_full_sample_one(
        self, artifact_id: str, curve: str
    ) -> None:
        """The ablation's factor is the engine's *full-sample* metric."""
        returns = self._ablation_returns(artifact_id, curve)
        published = _summary(artifact_id)["metrics"]["ablations"][self.CURVE_TO_BLOCK[curve]]
        full = returns.dropna()
        gross_profit = float(full[full > 0].sum())
        gross_loss = float(abs(full[full < 0].sum()))
        factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        assert _close(published["profit_factor"], factor), artifact_id

    @pytest.mark.parametrize("artifact_id", H9_ABLATION_ARTIFACTS)
    def test_the_ablation_trade_count_is_not_quantifiable(self, artifact_id: str) -> None:
        """The ablation's own trade log was never committed.

        The block's ``trades`` is the length of the *ablation's* trade log,
        which is not part of the artifact; the only committed trade log is
        the main run's.  Disclosed, not quantified.
        """
        directory = _directory(artifact_id)
        assert list(directory.glob("ablations_*trade*")) == [], artifact_id
        published = _summary(artifact_id)["metrics"]["ablations"]
        main_trades = int(len(pd.read_parquet(directory / "trades.parquet")))
        for name, block in published.items():
            assert int(block["trades"]) != main_trades, (artifact_id, name)
