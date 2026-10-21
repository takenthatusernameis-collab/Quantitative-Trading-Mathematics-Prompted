"""H51 — `compare_to_benchmark` is container-independent, and the published
`information_ratio` convention split is disclosed.

The defect
----------
`compare_to_benchmark` built the excess series with the *caller's* container:
`excess = strat - bench` stayed a `pandas.Series` when the caller passed a
Series and became an `ndarray` when the caller passed an array, and
`excess.std()` then used `pandas.Series.std()`'s default `ddof=1` (sample)
in the first case and `numpy.ndarray.std()`'s default `ddof=0` (population)
in the second. The information ratio -- the statistic the published
benchmark-significance gate is built on -- therefore depended on *how the
caller stored its data* rather than on the data: the same strategy and
benchmark compared as an array and as a Series produced two different
information ratios, differing by exactly `sqrt(n / (n - 1))`.

The fix
-------
Both sides are reduced to plain float numpy arrays before any statistic is
computed, and every standard deviation carries an explicit `ddof`. The
enforced convention is `ddof=0` (population): it is numpy's default, it is
the convention this module's own `sharpe_ratio` uses, it keeps the larger
set of published numbers unchanged (26 of 48 committed artifacts publish an
`information_ratio` computed that way), and it preserves the repository's
existing `test_runner_metric_agreement` contract, which already pins
`compare_to_benchmark`'s information ratio to numpy's `ddof=0` and requires
it to agree *exactly* with `run_cs_momentum`'s local computation.

The disclosure
--------------
The published record was produced by BOTH conventions: the runners that
pass a `pandas.Series` published a sample-standard-deviation information
ratio and the runners that pass an `ndarray` published a population one.
Every published artifact is re-derived here from its own frozen artifact --
26 on `ddof=0`, 22 on `ddof=1`. The published numbers are NOT rewritten;
the change is disclosed, and the certified families' IRs move by at most
1.7e-3 relative (H23, n = 300) with no sign change and no verdict change.

Nothing here re-runs a grid, re-writes an artifact, or moves a gate.
"""

from __future__ import annotations

import ast
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe  # noqa: E402

from qtr.validation.statistics import (  # noqa: E402
    benchmark_significance_gate,
    compare_to_benchmark,
)

ARTIFACTS = ROOT / ".experiments" / "artifacts"
INITIAL_CAPITAL = 1_000_000.0

LIBRARY_KEYS = (
    "information_ratio",
    "alpha_annualized",
    "beta",
    "alpha_t_stat",
    "alpha_p_value",
    "alpha_p_value_one_sided",
    "win_rate",
    "excess_return_annual",
    "excess_vol_annual",
)

# ---------------------------------------------------------------------------
# The disclosure table.
#
# artifact id -> (family, container at the runner's call site, the ddof the
# published information_ratio was computed with, the published information
# ratio, the published alpha p-value, the number of paired observations).
#
# The convention column was MEASURED, not assumed: every artifact is
# re-derived from its own frozen artifact (see `_artifact_excess`) and the
# ddof that reproduces the published value is recorded here. The three
# families whose runner published `round(information_ratio, 4)` cannot be
# discriminated by the data -- the two conventions differ by ~2e-4 relative
# at n = 1,257 and the published value carries only four decimals -- so for
# those the convention is pinned by the runner's call site instead, and the
# call site is checked statically by
# `test_the_call_sites_pass_the_container_the_published_values_were_made_with`.
# ---------------------------------------------------------------------------
PUBLISHED_INFORMATION_RATIOS = {
    "exp_2026-10-10T20-56-30-507309Z": (
        "H1/H2 ts_momentum",
        "ndarray",
        "ddof=0",
        -0.1241,
        0.78174,
        1257,
    ),
    "exp_2026-10-10T20-57-26-136503Z": (
        "H1/H2 ts_momentum",
        "ndarray",
        "ddof=0",
        -0.1241,
        0.78174,
        1257,
    ),
    "exp_2026-10-10T20-59-28-306148Z": (
        "H3/H4 cs_momentum",
        "ndarray",
        "ddof=0",
        -0.2523,
        0.57342,
        1257,
    ),
    "exp_2026-10-10T21-08-54-188263Z": (
        "H1/H2 ts_momentum",
        "ndarray",
        "ddof=0",
        -0.1241,
        0.78174,
        1257,
    ),
    "exp_2026-10-10T21-09-06-830199Z": (
        "H3/H4 cs_momentum",
        "ndarray",
        "ddof=0",
        -0.2523,
        0.57342,
        1257,
    ),
    "exp_2026-10-10T21-27-13-928282Z": (
        "H5 regime_gated",
        "ndarray",
        "ddof=0",
        -0.8932,
        0.046364,
        1257,
    ),
    "exp_2026-10-10T21-28-20-920399Z": (
        "H5 regime_gated",
        "ndarray",
        "ddof=0",
        -0.8932,
        0.046364,
        1257,
    ),
    "exp_2026-10-10T21-58-28-353634Z": (
        "H4 futures_tsmom",
        "ndarray",
        "ddof=0",
        -0.6399266589647274,
        1.0,
        1258,
    ),
    "exp_2026-10-10T21-59-16-546117Z": (
        "H4 futures_tsmom",
        "ndarray",
        "ddof=0",
        -0.6399266589647274,
        1.0,
        1258,
    ),
    "exp_2026-10-10T22-59-01-182037Z": (
        "H4 futures_tsmom",
        "ndarray",
        "ddof=0",
        0.33150832181222434,
        1.0,
        1258,
    ),
    "exp_2026-10-11T00-26-35-750834Z": (
        "H4 ddcv",
        "ndarray",
        "ddof=0",
        0.3943394550648367,
        0.3786380296798876,
        1258,
    ),
    "exp_2026-10-11T00-34-05-381535Z": (
        "H4 ddcv",
        "ndarray",
        "ddof=0",
        0.3943394550648367,
        0.3786380296798876,
        1258,
    ),
    "exp_2026-10-11T02-44-40-301520Z": (
        "H6 vix_ddcv",
        "ndarray",
        "ddof=0",
        0.35981069144282585,
        0.42177834933464325,
        1258,
    ),
    "exp_2026-10-11T02-46-37-311994Z": (
        "H6 vix_ddcv",
        "ndarray",
        "ddof=0",
        0.35981069144282585,
        0.42177834933464325,
        1258,
    ),
    "exp_2026-10-11T07-18-39-160945Z": (
        "H6 vix_ddcv",
        "ndarray",
        "ddof=0",
        0.35981069144282585,
        0.42177834933464325,
        1258,
    ),
    "exp_2026-10-11T08-02-22-999214Z": (
        "H6 vix_ddcv",
        "ndarray",
        "ddof=0",
        0.35981069144282585,
        0.42177834933464325,
        1258,
    ),
    "exp_2026-10-11T15-21-31-333870Z": (
        "H8 roll_adjusted",
        "ndarray",
        "ddof=0",
        0.5248619387848141,
        0.24132725822205583,
        1258,
    ),
    "exp_2026-10-11T15-54-17-212022Z": (
        "H9 v1 intraday",
        "Series",
        "ddof=1",
        -0.23532720855889727,
        0.11284923875075512,
        11441,
    ),
    "exp_2026-10-11T16-44-06-168529Z": (
        "H9 v2 intraday",
        "Series",
        "ddof=1",
        1.02096576542838,
        6.329465438644181e-12,
        11441,
    ),
    "exp_2026-10-11T16-46-06-466282Z": (
        "H9 v2 intraday",
        "Series",
        "ddof=1",
        1.02096576542838,
        6.329465438644181e-12,
        11441,
    ),
    "exp_2026-10-11T16-52-38-694559Z": (
        "H9 v2 intraday",
        "Series",
        "ddof=1",
        1.02096576542838,
        6.329465438644181e-12,
        11441,
    ),
    "exp_2026-10-11T17-24-14-385352Z": (
        "H10 pfopt",
        "Series",
        "ddof=1",
        1.0172449421222174,
        7.539534140525187e-12,
        11441,
    ),
    "exp_2026-10-11T17-41-18-169363Z": (
        "H10 pfopt",
        "Series",
        "ddof=1",
        0.9247889169803807,
        4.790305556723297e-10,
        11441,
    ),
    "exp_2026-10-13T21-11-45-843908Z": (
        "H16 factor_timing",
        "ndarray",
        "ddof=0",
        -0.47636726658916473,
        0.2083556513192659,
        1760,
    ),
    "exp_2026-10-13T21-13-09-580962Z": (
        "H16 factor_timing",
        "ndarray",
        "ddof=0",
        -0.47636726658916473,
        0.2083556513192659,
        1760,
    ),
    "exp_2026-10-13T21-18-23-178134Z": (
        "H16 factor_timing",
        "ndarray",
        "ddof=0",
        -0.3530817929808074,
        0.3510297076109353,
        1760,
    ),
    "exp_2026-10-13T21-22-02-751156Z": (
        "H16 factor_timing",
        "ndarray",
        "ddof=0",
        -0.3530817929808074,
        0.3510297076109353,
        1760,
    ),
    "exp_2026-10-13T21-51-45-034237Z": (
        "H17 vrp",
        "ndarray",
        "ddof=0",
        -0.23962730807881957,
        0.5338912916185115,
        1700,
    ),
    "exp_2026-10-13T22-40-41-870350Z": (
        "H19 volume_predictive",
        "ndarray",
        "ddof=0",
        -0.8797993277834989,
        0.0026021954893175585,
        2958,
    ),
    "exp_2026-10-13T23-06-33-191710Z": (
        "H20 signed_volume",
        "ndarray",
        "ddof=0",
        -0.7039784403691635,
        0.015948238479977717,
        2958,
    ),
    "exp_2026-10-13T23-27-52-101656Z": (
        "H21 multicontract",
        "Series",
        "ddof=1",
        0.9459483422829976,
        1.914795347616254e-10,
        11441,
    ),
    "exp_2026-10-14T07-12-35-292010Z": (
        "H22 voltarget",
        "Series",
        "ddof=1",
        1.3466905696542812,
        1.3340812548651885e-19,
        11441,
    ),
    "exp_2026-10-14T07-12-59-473353Z": (
        "H22 voltarget",
        "Series",
        "ddof=1",
        1.3466905696542812,
        1.3340812548651885e-19,
        11441,
    ),
    "exp_2026-10-14T07-15-23-322705Z": (
        "H22 voltarget",
        "Series",
        "ddof=1",
        1.3466905696542812,
        1.3340812548651885e-19,
        11441,
    ),
    "exp_2026-10-14T07-32-43-425839Z": (
        "H22 voltarget",
        "Series",
        "ddof=1",
        1.3466905696542812,
        1.3340812548651885e-19,
        11441,
    ),
    "exp_2026-10-14T08-20-39-255883Z": (
        "H9 v2 intraday",
        "Series",
        "ddof=1",
        1.0338737442216517,
        3.2602085788258746e-12,
        11465,
    ),
    "exp_2026-10-14T08-26-18-385545Z": (
        "H1/H2 ts_momentum",
        "ndarray",
        "ddof=0",
        -0.1241,
        0.78174,
        1257,
    ),
    "exp_2026-10-14T08-27-02-650342Z": (
        "H4 futures_tsmom",
        "ndarray",
        "ddof=0",
        0.33150832181222434,
        1.0,
        1258,
    ),
    "exp_2026-10-14T08-48-49-412372Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        0.8001285452997962,
        0.3833571966344182,
        300,
    ),
    "exp_2026-10-14T09-28-59-592390Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        0.8001285452997962,
        0.3833571966344182,
        300,
    ),
    "exp_2026-10-14T09-32-25-959733Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        0.8001285452997962,
        0.3833571966344182,
        300,
    ),
    "exp_2026-10-14T09-39-07-412533Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        0.8001285452997962,
        0.3833571966344182,
        300,
    ),
    "exp_2026-10-14T10-04-52-936640Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        0.8001285452997962,
        0.3833571966344182,
        300,
    ),
    "exp_2026-10-14T11-53-37-996139Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        -3.0738688888576515,
        0.0008995910719803239,
        300,
    ),
    "exp_2026-10-14T18-13-09-457781Z": (
        "H23 crypto",
        "Series",
        "ddof=1",
        -3.0738688888576515,
        0.0008995910719803239,
        300,
    ),
    "exp_2026-10-14T18-52-08-943792Z": (
        "H22 voltarget",
        "Series",
        "ddof=1",
        1.3466905696542812,
        1.3340812548651885e-19,
        11441,
    ),
    "exp_2026-10-14T20-02-45-189859Z": (
        "H25 pfmargin",
        "Series",
        "ddof=1",
        1.3458716250016904,
        1.4028853805082562e-19,
        11441,
    ),
    "exp_2026-10-14T20-08-34-613690Z": (
        "H25 pfmargin",
        "Series",
        "ddof=1",
        1.3458716250016904,
        1.4028853805082562e-19,
        11441,
    ),
}

# The count split the convention choice rests on: enforcing ddof=0 keeps
# these 26 published numbers unchanged and moves the other 22 by a factor
# of sqrt((n - 1) / n).
DDOF_0_ARTIFACTS = 26
DDOF_1_ARTIFACTS = 22

# ---------------------------------------------------------------------------
# How to rebuild each artifact's excess series from the artifact itself.
#
# artifact-id prefix -> (strategy file, strategy is an equity curve,
# benchmark file, benchmark is an equity curve, train_end or None).
#
# An equity curve is inverted to a return series the way the engine builds
# it: `equity = (1 + net_returns).cumprod() * initial_capital`, so the
# first row of the curve already carries the first bar's return and
# `pct_change` alone would lose it.
# ---------------------------------------------------------------------------
RECIPES = {
    "exp_2026-10-10T20-56": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T20-57": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T20-59": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-08": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-09": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-27": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-28": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-58": (
        "ensemble_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T21-59": (
        "ensemble_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-10T22-59": (
        "ensemble_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T00": (
        "best_ddcv_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T02": (
        "best_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T07": (
        "best_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T08": (
        "best_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T15-21": (
        "best_equity_w0.5.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-11T15-54": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-11T16": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-11T17-24": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-11T17-41": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-13T21-11": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2017-12-31",
    ),
    "exp_2026-10-13T21-13": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2017-12-31",
    ),
    "exp_2026-10-13T21-18": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2017-12-31",
    ),
    "exp_2026-10-13T21-22": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2017-12-31",
    ),
    "exp_2026-10-13T21-51": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2019-12-31",
    ),
    "exp_2026-10-13T22-40": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2014-12-31",
    ),
    "exp_2026-10-13T23-06": (
        "best_equity.parquet",
        True,
        "benchmark_returns.parquet",
        False,
        "2014-12-31",
    ),
    "exp_2026-10-13T23-27": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T07-12": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T07-15": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T07-32": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T08-20": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-14T08-26": (
        "selected_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-14T08-27": (
        "ensemble_equity.parquet",
        True,
        "benchmark_equity.parquet",
        True,
        "2019-12-31",
    ),
    "exp_2026-10-14T08-48": ("returns.parquet", False, "benchmark_equity.parquet", True, None),
    "exp_2026-10-14T09-28": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T09-32": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T09-39": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T10-04": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T11-53": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T18-13": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T18-52": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T20-02": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
    "exp_2026-10-14T20-08": ("returns.parquet", False, "benchmark_returns.parquet", False, None),
}

# The container each runner passed to `compare_to_benchmark` when it
# produced its published artifact. H21/H22/H25 reuse H10's `_full_gate_eval`,
# whose call site passes a `pandas.Series`.
RUNNER_CALL_SITE_CONTAINER = {
    "run_ts_momentum_experiment.py": "ndarray",
    "run_cs_momentum_experiment.py": "ndarray",
    "run_regime_gated_momentum_experiment.py": "ndarray",
    "run_futures_tsmom_experiment.py": "ndarray",
    "run_ddcv_experiment.py": "ndarray",
    "run_h6_vix_ddcv_experiment.py": "ndarray",
    "run_h8_rolladjusted_tsmom_experiment.py": "ndarray",
    "run_h16_factor_timing_experiment.py": "ndarray",
    "run_h17_vrp_experiment.py": "ndarray",
    "run_h19_volume_predictive_experiment.py": "ndarray",
    "run_h20_signed_volume_experiment.py": "ndarray",
    "run_h7_intraday_tsmom_experiment.py": "Series",
    "run_h9_intraday_tsmom_experiment.py": "Series",
    "run_h10_intraday_tsmom_pfopt_experiment.py": "Series",
    "run_h18_overnight_intraday_experiment.py": "Series",
    "run_h23_crypto_futures_tsmom.py": "Series",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _published(summary: dict, key: str):
    """The value as published, wherever the runner stored it."""
    for src in (
        summary.get("metrics") or {},
        summary.get("gate_metrics") or {},
        summary.get("alpha_vs_benchmark") or {},
        summary.get("benchmark_comparison") or {},
    ):
        if isinstance(src, dict):
            value = src.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    return None


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


def _recipe(artifact_id: str):
    for prefix, spec in RECIPES.items():
        if artifact_id.startswith(prefix):
            return spec
    raise KeyError(artifact_id)


def _artifact_sides(artifact_id: str) -> tuple[pd.Series, pd.Series]:
    """The published comparison's two sides, rebuilt from the artifact."""
    directory = ARTIFACTS / artifact_id
    sfile, s_is_equity, bfile, b_is_equity, train_end = _recipe(artifact_id)
    strategy = _series(directory / sfile)
    benchmark = _series(directory / bfile)
    if s_is_equity:
        strategy = _returns_from_equity(strategy)
    if b_is_equity:
        benchmark = _returns_from_equity(benchmark)
    if train_end is not None:
        index = strategy.index[strategy.index > pd.Timestamp(train_end)]
        strategy = strategy.reindex(index)
        benchmark = benchmark.reindex(index)
        if b_is_equity:
            benchmark = benchmark.ffill()
    left, right = strategy.align(benchmark, join="inner")
    keep = ~(np.isnan(left.values) | np.isnan(right.values))
    return left[keep], right[keep]


def _artifact_excess(artifact_id: str) -> np.ndarray:
    """The published comparison's excess series, rebuilt from the artifact."""
    left, right = _artifact_sides(artifact_id)
    return left.to_numpy() - right.to_numpy()


def _information_ratio(excess: np.ndarray, ddof: int) -> float:
    std = excess.std(ddof=ddof)
    if std <= 0:
        return 0.0
    return float(excess.mean() / std * math.sqrt(252))


def _pre_h51_information_ratio(strategy, benchmark, periods_per_year: int = 252) -> float:
    """The pre-H51 implementation, reconstructed.

    The excess series kept the caller's container, so ``excess.std()``
    used pandas' sample standard deviation (``ddof=1``) for a Series and
    numpy's population standard deviation (``ddof=0``) for an ndarray.
    """
    if not isinstance(strategy, pd.Series):
        strategy = np.asarray(strategy, dtype=float)
    if not isinstance(benchmark, pd.Series):
        benchmark = np.asarray(benchmark, dtype=float)
    min_len = min(len(strategy), len(benchmark))
    if min_len == 0:
        return float("nan")
    excess = strategy[-min_len:] - benchmark[-min_len:]
    std = excess.std()
    if std <= 0:
        return 0.0
    return float(excess.mean() / std * math.sqrt(periods_per_year))


def _is_rounded(value: float) -> bool:
    """True when the runner published ``round(information_ratio, 4)``."""
    return abs(value - round(value, 4)) < 1e-12


# ---------------------------------------------------------------------------
# 1. the container-independence invariant
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_every_key_is_identical_for_an_array_and_a_series(seed: int) -> None:
    """A Series and an ndarray holding the same numbers give the same nine keys."""
    rng = np.random.default_rng(seed)
    strategy = rng.normal(0.001, 0.01, 512)
    benchmark = rng.normal(0.0005, 0.01, 512)

    from_array = compare_to_benchmark(strategy, benchmark)
    from_series = compare_to_benchmark(pd.Series(strategy), pd.Series(benchmark))

    assert set(from_array) == set(LIBRARY_KEYS)
    for key in LIBRARY_KEYS:
        assert from_array[key] == from_series[key], key


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_mixed_containers_are_identical(seed: int) -> None:
    """One side a Series and the other an array is still the same comparison."""
    rng = np.random.default_rng(seed)
    strategy = rng.normal(0.001, 0.01, 300)
    benchmark = rng.normal(0.0005, 0.01, 300)

    reference = compare_to_benchmark(strategy, benchmark)
    mixed = compare_to_benchmark(pd.Series(strategy), benchmark)
    mixed_other = compare_to_benchmark(strategy, pd.Series(benchmark))

    for key in LIBRARY_KEYS:
        assert reference[key] == mixed[key], key
        assert reference[key] == mixed_other[key], key


def test_a_multi_symbol_benchmark_is_reduced_to_its_equal_weighted_return() -> None:
    """The DataFrame benchmark path agrees with the row-mean series it stands for."""
    rng = np.random.default_rng(7)
    strategy = rng.normal(0.001, 0.01, 400)
    frame = pd.DataFrame(
        {
            "A": rng.normal(0.0, 0.01, 400),
            "B": rng.normal(0.0, 0.01, 400),
        }
    )

    from_frame = compare_to_benchmark(strategy, frame)
    from_mean = compare_to_benchmark(strategy, frame.mean(axis=1))

    for key in LIBRARY_KEYS:
        assert from_frame[key] == from_mean[key], key


def test_a_nan_row_is_dropped_from_both_sides_identically() -> None:
    """The NaN mask is pair-wise, so the result does not depend on the container."""
    rng = np.random.default_rng(11)
    strategy = rng.normal(0.001, 0.01, 200)
    benchmark = rng.normal(0.0005, 0.01, 200)
    strategy[7] = np.nan

    from_array = compare_to_benchmark(strategy, benchmark)
    from_series = compare_to_benchmark(pd.Series(strategy), pd.Series(benchmark))

    for key in LIBRARY_KEYS:
        assert from_array[key] == from_series[key], key


def test_the_enforced_convention_is_the_population_standard_deviation() -> None:
    """The IR is `mean / std(ddof=0)`, and it is NOT the sample deviation."""
    rng = np.random.default_rng(3)
    strategy = rng.normal(0.002, 0.01, 256)
    benchmark = rng.normal(0.0005, 0.01, 256)

    result = compare_to_benchmark(strategy, benchmark)
    excess = strategy - benchmark

    assert result["information_ratio"] == pytest.approx(
        excess.mean() / excess.std(ddof=0) * math.sqrt(252), rel=1e-15
    )
    assert result["excess_vol_annual"] == pytest.approx(
        excess.std(ddof=0) * math.sqrt(252), rel=1e-15
    )

    n = len(excess)
    sample_ir = excess.mean() / excess.std(ddof=1) * math.sqrt(252)
    # the sample deviation is the LARGER of the two, so the sample IR is the
    # SMALLER one: IR_ddof1 = IR_ddof0 * sqrt((n - 1) / n)
    assert result["information_ratio"] == pytest.approx(
        sample_ir * math.sqrt(n / (n - 1)), rel=1e-12
    )
    assert result["information_ratio"] != pytest.approx(sample_ir, rel=1e-6)


# ---------------------------------------------------------------------------
# 2. the disclosure
# ---------------------------------------------------------------------------
def _artifacts_publishing_an_information_ratio() -> set[str]:
    published = set()
    for summary_path in sorted(ARTIFACTS.glob("*/summary.json")):
        summary = json.loads(summary_path.read_text())
        if _published(summary, "information_ratio") is not None:
            published.add(summary_path.parent.name)
    return published


def test_every_published_information_ratio_is_disclosed() -> None:
    """No committed artifact publishes an IR that the disclosure table omits."""
    assert _artifacts_publishing_an_information_ratio() == set(PUBLISHED_INFORMATION_RATIOS)


@pytest.mark.parametrize("artifact_id", sorted(PUBLISHED_INFORMATION_RATIOS))
def test_the_disclosed_published_values_match_the_committed_artifact(artifact_id: str) -> None:
    """The disclosure table is pinned to the artifacts it describes."""
    summary = json.loads((ARTIFACTS / artifact_id / "summary.json").read_text())
    _family, _container, _convention, ir, p_value, n = PUBLISHED_INFORMATION_RATIOS[artifact_id]

    assert _published(summary, "information_ratio") == ir
    published_p = (
        _published(summary, "benchmark_p_value")
        or _published(summary, "p_value")
        or _published(summary, "alpha_p_value")
    )
    assert published_p == p_value
    assert len(_artifact_excess(artifact_id)) == n


def test_the_convention_split_is_pinned() -> None:
    """The count the convention choice rests on cannot drift silently."""
    ddof_0 = [a for a, row in PUBLISHED_INFORMATION_RATIOS.items() if row[2] == "ddof=0"]
    ddof_1 = [a for a, row in PUBLISHED_INFORMATION_RATIOS.items() if row[2] == "ddof=1"]

    assert len(ddof_0) == DDOF_0_ARTIFACTS
    assert len(ddof_1) == DDOF_1_ARTIFACTS
    assert len(ddof_0) + len(ddof_1) == len(PUBLISHED_INFORMATION_RATIOS)


@pytest.mark.parametrize("artifact_id", sorted(PUBLISHED_INFORMATION_RATIOS))
def test_the_published_value_re_derives_under_the_disclosed_convention(artifact_id: str) -> None:
    """Re-derive the published IR from the artifact and check the convention."""
    _family, _container, convention, ir, _p_value, _n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
    excess = _artifact_excess(artifact_id)

    published_ddof = 0 if convention == "ddof=0" else 1
    other_ddof = 1 - published_ddof

    rederived = _information_ratio(excess, published_ddof)
    tolerance = 1e-3 if _is_rounded(ir) else 1e-9
    assert rederived == pytest.approx(ir, rel=tolerance)

    if not _is_rounded(ir):
        # the published value is NOT consistent with the other convention
        assert _information_ratio(excess, other_ddof) != pytest.approx(ir, rel=tolerance)


@pytest.mark.parametrize("artifact_id", sorted(PUBLISHED_INFORMATION_RATIOS))
def test_the_enforced_convention_moves_only_the_documented_amount(artifact_id: str) -> None:
    """The new IR is the published one times sqrt(n / (n - 1)) -- and no more."""
    _family, _container, convention, ir, _p_value, n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
    excess = _artifact_excess(artifact_id)

    if convention == "ddof=1":
        # the published IR is a sample-deviation ratio; the enforced
        # population-deviation ratio is larger by exactly sqrt(n / (n - 1))
        expected = ir * math.sqrt(n / (n - 1))
        assert _information_ratio(excess, 0) == pytest.approx(expected, rel=1e-9)
        relative = abs(expected / ir - 1.0)
        assert relative < 2e-3, artifact_id
        assert (expected > 0) == (ir > 0), artifact_id
    else:
        # a population-deviation ratio is unchanged by the enforced convention
        assert _information_ratio(excess, 0) == pytest.approx(
            ir, rel=1e-3 if _is_rounded(ir) else 1e-9
        )


@pytest.mark.parametrize("artifact_id", sorted(PUBLISHED_INFORMATION_RATIOS))
def test_no_published_verdict_can_move_under_the_new_convention(artifact_id: str) -> None:
    """The direction-aware gate's outcome is invariant under the convention."""
    _family, _container, convention, ir, p_value, _n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
    if p_value is None or p_value >= 1.0:
        pytest.skip("the runner published a default p-value, not a t-test p-value")

    n = PUBLISHED_INFORMATION_RATIOS[artifact_id][5]
    other_ir = (
        ir * math.sqrt(n / (n - 1)) if convention == "ddof=1" else ir * math.sqrt((n - 1) / n)
    )

    assert benchmark_significance_gate(p_value, ir) == benchmark_significance_gate(
        p_value, other_ir
    )


def _is_array_expression(
    expression: ast.AST, assignments: dict[str, list[ast.AST]], seen: frozenset[str] = frozenset()
) -> bool:
    """True when the expression evaluates to an ndarray rather than a Series.

    ``pandas.Series`` exposes no ``.values`` attribute, so an expression
    that reaches a ``.values`` attribute (directly or through the local
    name it was assigned from) hands the library an array.
    """
    if isinstance(expression, ast.Attribute):
        if expression.attr == "values":
            return True
        return _is_array_expression(expression.value, assignments, seen)
    if isinstance(expression, ast.Call):
        return any(
            _is_array_expression(argument, assignments, seen) for argument in expression.args
        )
    if isinstance(expression, ast.IfExp):
        # `s.values if hasattr(s, "values") else s` -- the array branch is
        # the one that runs for a pandas input
        return _is_array_expression(expression.body, assignments, seen) or _is_array_expression(
            expression.orelse, assignments, seen
        )
    if isinstance(expression, ast.Subscript):
        return _is_array_expression(expression.value, assignments, seen)
    if isinstance(expression, ast.Name):
        if expression.id in seen:
            return False
        # a name is an array when ANY of its assignments is one: the runners
        # rebind the same name (`x = s.values` then `x = x[mask]`)
        return any(
            _is_array_expression(assigned, assignments, seen | {expression.id})
            for assigned in assignments.get(expression.id, [])
        )
    return False


def _runner_assignments(tree: ast.Module) -> dict[str, list[ast.AST]]:
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assignments.setdefault(target.id, []).append(node.value)
    return assignments


def test_the_call_sites_pass_the_container_the_published_values_were_made_with() -> None:
    """Static check: the runner's call site fixes the container, hence the ddof."""
    for runner, expected in RUNNER_CALL_SITE_CONTAINER.items():
        tree = ast.parse((ROOT / runner).read_text())
        assignments = _runner_assignments(tree)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "compare_to_benchmark"
        ]
        assert calls, runner
        for call in calls:
            container = "ndarray" if _is_array_expression(call.args[0], assignments) else "Series"
            assert container == expected, runner


def test_the_series_call_sites_belong_to_the_ddof_1_families() -> None:
    """The call-site container and the disclosed convention agree, family by family."""
    series_families = {
        "H9 v1 intraday",
        "H9 v2 intraday",
        "H10 pfopt",
        "H21 multicontract",
        "H22 voltarget",
        "H23 crypto",
        "H25 pfmargin",
    }
    for _artifact_id, (
        family,
        container,
        convention,
        _ir,
        _p,
        _n,
    ) in PUBLISHED_INFORMATION_RATIOS.items():
        if container == "Series":
            assert family in series_families, family
            assert convention == "ddof=1", family
        else:
            assert convention == "ddof=0", family


# ---------------------------------------------------------------------------
# 3. the negative control -- the pre-H51 implementation
# ---------------------------------------------------------------------------
def test_the_pre_h51_implementation_was_container_dependent() -> None:
    """The defect was real: the same data, two containers, two answers."""
    rng = np.random.default_rng(5)
    strategy = rng.normal(0.002, 0.01, 300)
    benchmark = rng.normal(0.0005, 0.01, 300)

    from_array = _pre_h51_information_ratio(strategy, benchmark)
    from_series = _pre_h51_information_ratio(pd.Series(strategy), pd.Series(benchmark))

    assert from_array != from_series
    n = len(strategy)
    assert from_series == pytest.approx(from_array * math.sqrt((n - 1) / n), rel=1e-12)

    # and the fixed library returns ONE answer for both containers
    fixed = compare_to_benchmark(strategy, benchmark)
    assert (
        fixed["information_ratio"]
        == compare_to_benchmark(pd.Series(strategy), pd.Series(benchmark))["information_ratio"]
    )


@pytest.mark.parametrize("artifact_id", sorted(PUBLISHED_INFORMATION_RATIOS))
def test_the_pre_h51_implementation_reproduces_the_published_values(artifact_id: str) -> None:
    """The published record contains BOTH conventions, and the pre-fix code made them."""
    _family, container, convention, ir, _p_value, _n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
    if _is_rounded(ir):
        pytest.skip(
            "the runner published round(information_ratio, 4): the rounding hides the convention"
        )

    left, right = _artifact_sides(artifact_id)

    if container == "Series":
        published_ir = _pre_h51_information_ratio(left, right)
    else:
        published_ir = _pre_h51_information_ratio(left.to_numpy(), right.to_numpy())

    assert published_ir == pytest.approx(ir, rel=1e-9)

    # the OTHER container gives the other convention, and does NOT reproduce it
    if container == "Series":
        other_ir = _pre_h51_information_ratio(left.to_numpy(), right.to_numpy())
    else:
        other_ir = _pre_h51_information_ratio(left, right)
    assert other_ir != pytest.approx(ir, rel=1e-6)


def test_the_library_returns_the_enforced_convention_for_the_certified_families() -> None:
    """The library, called on the certified families' own Series, gives ddof=0.

    The certified families (H10, H21, H22, H25) published a *sample*
    deviation IR. The library now returns the population deviation one for
    the same data -- the disclosed move, measured through the public API
    rather than through a private helper.
    """
    for artifact_id in (
        "exp_2026-10-11T17-41-18-169363Z",
        "exp_2026-10-13T23-27-52-101656Z",
        "exp_2026-10-14T18-52-08-943792Z",
        "exp_2026-10-14T20-08-34-613690Z",
    ):
        _family, container, convention, ir, _p_value, n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
        assert container == "Series"
        assert convention == "ddof=1"

        left, right = _artifact_sides(artifact_id)
        result = compare_to_benchmark(left, right)
        excess = left.to_numpy() - right.to_numpy()

        assert result["information_ratio"] == pytest.approx(
            _information_ratio(excess, 0), rel=1e-12
        )
        assert result["information_ratio"] == pytest.approx(ir * math.sqrt(n / (n - 1)), rel=1e-9)
        assert result["information_ratio"] != pytest.approx(ir, rel=1e-6)


def test_the_certified_h10_value_moves_and_the_move_is_disclosed() -> None:
    """The certified family's published IR is reproduced by the pre-fix code only."""
    artifact_id = "exp_2026-10-11T17-41-18-169363Z"
    _family, container, convention, ir, _p_value, n = PUBLISHED_INFORMATION_RATIOS[artifact_id]
    excess = _artifact_excess(artifact_id)

    assert container == "Series"
    assert convention == "ddof=1"

    # the pre-fix Series path reproduces the published value...
    assert _information_ratio(excess, 1) == pytest.approx(ir, rel=1e-9)
    # ...and the enforced convention moves it by exactly the documented factor
    assert _information_ratio(excess, 0) == pytest.approx(ir * math.sqrt(n / (n - 1)), rel=1e-9)
    assert abs(_information_ratio(excess, 0) / ir - 1.0) < 1e-4
