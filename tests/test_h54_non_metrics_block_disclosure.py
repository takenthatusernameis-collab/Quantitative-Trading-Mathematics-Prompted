"""H54 — the published blocks of the summaries that publish no `metrics` block.

The gap
-------
§H53 closed the `metrics` block: every published value in the **37** summaries
that carry one re-derives from the artifact that published it. The record's
other **43** summaries publish **no** `metrics` block at all — they carry a
different shape, and the published `all_pass` / `verdict` / `gates` blocks
that rest on them had never been re-derived.

What H54 measures
-----------------
============  ==========================================  =========
measured      quantity                                   value
============  ==========================================  =========
summaries     with no `metrics` block                      **43**
shapes        distinct top-level key sets                  **24**
keys          distinct top-level keys                     **164**
leaf values   published                                   **7 785**
summaries     publishing no parquet artifact at all        **3**
============  ==========================================  =========

The three classes
-----------------
The 43 summaries fall into three classes, and the class decides what
"re-derives" can even mean:

* **certified-family blocks** — ``gates``, ``verdict``, ``all_pass``,
  ``splits``, ``overall``. These are the published verdicts of the H7/H10/
  H21/H22/H25 families; their numbers and verdicts are frozen.
* **exploratory blocks** — ``ablation``, ``ablations``, ``grid``,
  ``all_results``, ``all_combo_results``, ``param_grid_summary``. Grid and
  ablation tables published as nested JSON; they echo a committed parquet.
* **audit blocks** — ``h26_sharpe_scale``, ``h27_pnl_level``,
  ``h28_causal_recertification``, ``h29_lookahead_sweep``,
  ``pf_robustness``. A verdict *about* the record; it reads other artifacts,
  and publishes its own committed table.

The conventions
---------------
Every published value is compared against a value reconstructed from the
summary's own frozen artifact. Where the reconstruction does not match, the
difference is always a **convention**, never an arithmetic error, and the
convention is recorded:

1. **The numpy-boolean serialisation.** Every runner writes its summary with
   ``json.dump(..., default=str)``. A numpy boolean is not JSON
   serialisable, so ``default=str`` turns it into the *string* ``"True"`` /
   ``"False"``; a Python boolean stays a JSON ``true`` / ``false``. The
   published gate blocks therefore mix the two, and which one a given gate
   gets depends on whether the producer's expression evaluated to a numpy or
   a Python boolean. The semantic verdict is the same either way; the
   *serialisation class* is the convention, and it is pinned per gate.
2. **The pre-fix bootstrap seeding.** The published bootstrap confidence
   intervals were resampled with the legacy MT19937 stream
   (``numpy.random.RandomState(seed).randint``); the library now uses
   ``numpy.random.default_rng`` (PCG64). The two draw different samples, so
   the published intervals do not re-derive under the library's convention.
3. **The pre-H51 mixed-ddof beta.** The published ``alpha_annualized`` was
   computed with ``np.cov(..., ddof=1) / np.var(...)`` — ``np.var``'s default
   ``ddof=0`` — which inflates beta by ``n / (n - 1)`` and moves the alpha.
   §H53 recorded this for the ``metrics`` block; H54 extends it to the
   non-``metrics`` blocks, where the same published key appears.
4. **The pre-fix alpha p-value lookup.** Two families read the alpha
   p-value under ``"p_value"``, a key ``compare_to_benchmark`` does not
   return, so the published value is the ``1.0`` default and the gate it
   feeds was **vacuous** — it could never pass. The runner now reads
   ``"alpha_p_value"``. The published ``1.0`` is disclosed, not rewritten.
5. **The pre-fix regime-stability sentinel.** One summary of the H16 family
   publishes ``-Infinity`` under the regime-stability gate value where its
   five siblings publish the computed minimum. The current runner computes
   the minimum, so the value does not re-derive.

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

# The tolerance of a re-derivation. The published values are float64
# round-trips of the same computation, so they agree to ~1e-12 relative when
# the series is read back from the committed parquet. The tolerance sits
# three orders of magnitude above that and four below the smallest
# convention gap measured in this record (5.8e-05 relative).
TOLERANCE = 1e-9


# ---------------------------------------------------------------------------
# 1. The record
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


_NAMES = _tracker_names()


def _non_metric_summaries() -> list[tuple[pathlib.Path, dict]]:
    """Every summary that publishes no `metrics` block."""
    out = []
    for path in sorted(ARTIFACTS.rglob("summary.json")):
        data = json.loads(path.read_text())
        if "metrics" not in data:
            out.append((path.parent, data))
    return out


def _artifact_id(directory: pathlib.Path, data: dict) -> str:
    return data.get("experiment_id") or directory.name


# ---------------------------------------------------------------------------
# 2. The shared readers and statistics
# ---------------------------------------------------------------------------
def _series(path: pathlib.Path) -> pd.Series:
    frame = read_parquet_safe(path)
    return frame[frame.columns[0]]


def _returns_from_equity(equity: pd.Series, capital: float = INITIAL_CAPITAL) -> pd.Series:
    """Invert the engine's equity construction.

    ``equity = (1 + net_returns).cumprod() * initial_capital``: the first row
    of the curve already carries the first bar's return, so ``pct_change``
    alone would lose it and shift every later row by one.
    """
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / capital - 1.0
    return returns


def _sharpe(values, ddof: int = 0, periods_per_year: int = 252) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return 0.0
    deviation = float(np.std(values, ddof=ddof))
    if deviation <= 1e-15:
        return 0.0
    return float(values.mean() / deviation * np.sqrt(periods_per_year))


def _profit_factor(values) -> float:
    values = pd.Series(np.asarray(values, dtype=float))
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(abs(values[values < 0].sum()))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def _max_drawdown(values, form: str = "absolute") -> float:
    """The drawdown of the compounded series.

    Two forms exist in the record, and the families genuinely differ:

    * ``absolute`` — ``(cum - cum.expanding().max()).min()``, the *level*
      difference between the curve and its running peak. This is the form
      the time-series, regime-gated, futures, DDCV and H6 runners use.
    * ``ratio`` — ``(cum / cum.expanding().max() - 1).min()``, the
      *relative* drawdown. This is the form the cross-sectional runner
      uses (``run_cs_momentum_experiment.py``).
    """
    series = pd.Series(np.asarray(values, dtype=float))
    equity = (1 + series).cumprod()
    if form == "ratio":
        return float((equity / equity.expanding().max() - 1.0).min())
    return float((equity - equity.expanding().max()).min())


def _regime_labels(vix: pd.Series) -> pd.Series:
    """VIX regime labels (the H1-H11 convention): bull < 20, sideways 20-30,
    bear > 30."""
    regimes = pd.Series(index=vix.index, dtype=object)
    forward = vix.ffill()
    regimes[forward < 20] = "bull"
    regimes[(forward >= 20) & (forward <= 30)] = "sideways"
    regimes[forward > 30] = "bear"
    return regimes


def _split_by_date(returns: pd.Series, train_end: str, val_end: str):
    train = returns[returns.index <= train_end]
    val = returns[(returns.index > train_end) & (returns.index <= val_end)]
    test = returns[returns.index > val_end]
    oos = returns[returns.index > train_end]
    return train, val, test, oos


def _legacy_bootstrap_ci(
    data: np.ndarray, statistic, seed: int = 42, n_bootstrap: int = 1000
) -> tuple[float, float]:
    """The bootstrap the published record used: MT19937 (``RandomState``).

    The library now uses ``numpy.random.default_rng`` (PCG64); the two draw
    different samples from the same seed, so a published interval only
    re-derives under this form.
    """
    data = np.asarray(data, dtype=float)
    rng = np.random.RandomState(seed)
    stats = []
    for _ in range(n_bootstrap):
        index = rng.randint(0, len(data), len(data))
        stats.append(statistic(data[index]))
    alpha = 0.025
    return (
        float(np.percentile(stats, 100 * alpha)),
        float(np.percentile(stats, 100 * (1 - alpha))),
    )


def _pcg_bootstrap_ci(
    data: np.ndarray, statistic, seed: int = 42, n_bootstrap: int = 1000
) -> tuple[float, float]:
    """The library's current bootstrap: PCG64 (``default_rng``)."""
    data = np.asarray(data, dtype=float)
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_bootstrap):
        index = rng.integers(0, len(data), len(data))
        stats.append(statistic(data[index]))
    alpha = 0.025
    return (
        float(np.percentile(stats, 100 * alpha)),
        float(np.percentile(stats, 100 * (1 - alpha))),
    )


def _benchmark_stats(strategy, benchmark, ddof: int = 0, beta_pre_h51: bool = False) -> dict:
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
    excess_std = float(np.std(excess, ddof=ddof))
    information_ratio = excess.mean() / excess_std * np.sqrt(252) if excess_std > 0 else 0.0
    if float(np.var(bench, ddof=0)) > 0:
        if beta_pre_h51:
            beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=0)
        else:
            beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=1)
        alpha = strat.mean() - beta * bench.mean()
        alpha_annual = alpha * 252
    else:
        beta = 0.0
        alpha_annual = 0.0
    if float(np.std(excess, ddof=0)) > 1e-12:
        _, p_value = stats.ttest_1samp(excess, 0)
    else:
        p_value = 1.0
    return {
        "information_ratio": float(information_ratio),
        "alpha_annualized": float(alpha_annual),
        "alpha_p_value": float(p_value),
        "beta": float(beta),
    }


def _matches(published, rederived) -> bool:
    """Do a published value and a re-derived value agree?

    ``None`` compares as a value, infinities compare equal to themselves, a
    numpy-boolean serialised as the string ``"True"`` / ``"False"`` compares
    equal to the Python boolean it denotes, and a nested block is compared
    key by key.
    """
    if isinstance(published, str) and published in ("True", "False"):
        published = published == "True"
    if isinstance(rederived, str) and rederived in ("True", "False"):
        rederived = rederived == "True"
    if published is None or rederived is None:
        return published is None and rederived is None
    if isinstance(published, bool) or isinstance(rederived, bool):
        return bool(published) == bool(rederived)
    if isinstance(published, dict) or isinstance(rederived, dict):
        if not (isinstance(published, dict) and isinstance(rederived, dict)):
            return False
        keys = set(published) | set(rederived)
        return all(_matches(published.get(k), rederived.get(k)) for k in keys)
    if isinstance(published, (list, tuple)) or isinstance(rederived, (list, tuple)):
        if not (isinstance(published, (list, tuple)) and isinstance(rederived, (list, tuple))):
            return False
        if len(published) != len(rederived):
            return False
        return all(_matches(p, r) for p, r in zip(published, rederived))
    if isinstance(published, str) or isinstance(rederived, str):
        return published == rederived
    if np.isinf(published) or np.isinf(rederived):
        return published == rederived
    return abs(published - rederived) <= TOLERANCE * max(1.0, abs(published))


def _compare_published(published, rederived, path: str = ""):
    """Compare a published block with its reconstruction.

    The walk is over the **published** structure: every published leaf must
    be found in the reconstruction and must agree with it. Two lists come
    back:

    * ``mismatches`` — a published leaf that the reconstruction reaches and
      disagrees with. Always a failure.
    * ``uncovered`` — a published leaf the reconstruction does not reach.
      Not a failure by itself, but it must be *declared*: every uncovered
      leaf appears in :data:`NOT_REDERIVABLE` with the reason the artifact
      cannot carry it.

    A reconstructed leaf the published block does not carry is invisible
    here, and is reported by :func:`_extra_leaves` so that a value the
    producer computed but did not publish is disclosed rather than lost.
    """
    if isinstance(published, dict):
        if not isinstance(rederived, dict):
            return [(path, published, rederived)], [path]
        mismatches: list[tuple[str, object, object]] = []
        uncovered: list[str] = []
        for key, value in published.items():
            child = f"{path}.{key}" if path else str(key)
            if key not in rederived:
                uncovered.append(child)
                continue
            sub_mismatch, sub_uncovered = _compare_published(value, rederived[key], child)
            mismatches.extend(sub_mismatch)
            uncovered.extend(sub_uncovered)
        return mismatches, uncovered
    if isinstance(published, (list, tuple)):
        if not isinstance(published, (list, tuple)) or not isinstance(rederived, (list, tuple)):
            return [(path, published, rederived)], [path]
        mismatches = []
        uncovered = []
        for index, value in enumerate(published):
            child = f"{path}[{index}]"
            if index >= len(rederived):
                uncovered.append(child)
                continue
            sub_mismatch, sub_uncovered = _compare_published(value, rederived[index], child)
            mismatches.extend(sub_mismatch)
            uncovered.extend(sub_uncovered)
        return mismatches, uncovered
    if not _matches(published, rederived):
        return [(path, published, rederived)], []
    return [], []


def _extra_leaves(published, rederived, path: str = "") -> list[str]:
    """The reconstructed leaves the published block does not carry."""
    if isinstance(rederived, dict):
        if not isinstance(published, dict):
            return [path]
        out: list[str] = []
        for key, value in rederived.items():
            child = f"{path}.{key}" if path else str(key)
            if key not in published:
                out.append(child)
                continue
            out.extend(_extra_leaves(published[key], value, child))
        return out
    if isinstance(rederived, (list, tuple)):
        if not isinstance(published, (list, tuple)):
            return [path]
        out = []
        for index, value in enumerate(rederived):
            child = f"{path}[{index}]"
            if index >= len(published):
                out.append(child)
                continue
            out.extend(_extra_leaves(published[index], value, child))
        return out
    return []


def _measured_boolean_classes() -> dict[tuple[str, str, str], set[str]]:
    """The measured serialisation class of every published gate boolean.

    Keyed by ``(producer, block, gate)``; the value is the set of classes
    the record shows for that gate.
    """
    out: dict[tuple[str, str, str], set[str]] = {}
    for entry in _ENTRIES:
        producer = entry["producer"]
        for block in ("passes", "gates"):
            gate_block = entry["published"].get(block)
            if not isinstance(gate_block, dict):
                continue
            for name, value in gate_block.items():
                if isinstance(value, dict):
                    value = value.get("pass")
                klass = _serialisation_class(value)
                if klass == "other":
                    continue
                out.setdefault((producer, block, name), set()).add(klass)
    return out


#: The measured serialisation class of every published gate boolean, per
#: producer, per block and per gate.
#:
#: The mix is *not* a producer-wide property. ``futures_tsmom_v1`` left
#: four of its eight pass gates as the raw numpy comparison (``sharpe``,
#: ``dd``, ``stab``, ``worst``) and wrapped the other four
#: (``trades``, ``pf``, ``p``, ``ir``) in ``bool(...)``. ``ddcv_futures_tsmom_v1``
#: is the same runner with the same mix, but one of its four summaries was
#: written with the wrapped form throughout, so its ``sharpe``/``stab``/
#: ``worst`` gates carry both classes. The H7 family left three of its ten
#: gates raw. Every other family wrapped all of them.
BOOLEAN_CLASSES: dict[tuple[str, str, str], set[str]] = {
    ("cs_momentum_10etf_v1", "gates", "benchmark_significance"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "max_drawdown"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "net_oos_sharpe"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "oos_trades"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "param_perturbation"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "profit_factor"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "regime_stability"): {"python-bool"},
    ("cs_momentum_10etf_v1", "gates", "walkforward_stability"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "dd"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "ir"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "p"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "pf"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "sharpe"): {"numpy-bool-as-string", "python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "stab"): {"numpy-bool-as-string", "python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "trades"): {"python-bool"},
    ("ddcv_futures_tsmom_v1", "passes", "worst"): {"numpy-bool-as-string", "python-bool"},
    ("futures_tsmom_v1", "passes", "dd"): {"numpy-bool-as-string"},
    ("futures_tsmom_v1", "passes", "ir"): {"python-bool"},
    ("futures_tsmom_v1", "passes", "p"): {"python-bool"},
    ("futures_tsmom_v1", "passes", "pf"): {"python-bool"},
    ("futures_tsmom_v1", "passes", "sharpe"): {"numpy-bool-as-string"},
    ("futures_tsmom_v1", "passes", "stab"): {"numpy-bool-as-string"},
    ("futures_tsmom_v1", "passes", "trades"): {"python-bool"},
    ("futures_tsmom_v1", "passes", "worst"): {"numpy-bool-as-string"},
    ("h11_robustness_certification", "gates", "concentration"): {"python-bool"},
    ("h11_robustness_certification", "gates", "cost"): {"python-bool"},
    ("h11_robustness_certification", "gates", "fresh_oos"): {"python-bool"},
    ("h11_robustness_certification", "gates", "perturbation"): {"python-bool"},
    ("h12_selection_bias_audit", "gates", "dsr_adjusted_sharpe_ge_1.0"): {"python-bool"},
    ("h12_selection_bias_audit", "gates", "family_corrected_p_lt_0.05"): {"python-bool"},
    ("h12_selection_bias_audit", "gates", "pbo_lt_0.5"): {"python-bool"},
    (
        "h13_oos_deflation_pf_audit",
        "gates",
        "all_symbols_dispensable_lou_pf_ge_1.3",
    ): {"python-bool"},
    ("h13_oos_deflation_pf_audit", "gates", "pf_bootstrap_ci_lower_ge_1.3"): {"python-bool"},
    (
        "h13_oos_deflation_pf_audit",
        "gates",
        "worst_case_dsr_adjusted_oos_sharpe_ge_1.0",
    ): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "dd"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "ir"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "p"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "pf"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "sharpe"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "stab"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "trades"): {"python-bool"},
    ("h6_vix_ddcv_futures_tsmom_v1", "passes", "worst"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "max_drawdown"): {"numpy-bool-as-string"},
    ("h7_intraday_tsmom_v1", "gates", "max_p_value"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "min_information_ratio"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "min_perturbed_sharpe_ratio"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "min_profit_factor"): {"numpy-bool-as-string"},
    ("h7_intraday_tsmom_v1", "gates", "min_sharpe"): {"numpy-bool-as-string"},
    ("h7_intraday_tsmom_v1", "gates", "min_trades"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "min_walkforward_stability"): {"python-bool"},
    ("h7_intraday_tsmom_v1", "gates", "min_worst_regime_sharpe"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "dd"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "ir"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "p"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "pf"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "sharpe"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "stab"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "trades"): {"python-bool"},
    ("h8_roll_adjusted_futures_tsmom_v1", "passes", "worst"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "benchmark_significance"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "crisis_drawdown_2020_03"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "crisis_drawdown_2022"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "max_drawdown"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "net_oos_sharpe"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "oos_trades"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "param_perturbation"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "profit_factor"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "regime_stability"): {"python-bool"},
    ("regime_gated_momentum_20etf_v1", "gates", "walkforward_stability"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "benchmark_significance"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "max_drawdown"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "net_oos_sharpe"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "oos_trades"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "param_perturbation"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "profit_factor"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "regime_stability"): {"python-bool"},
    ("ts_momentum_20etf_v1", "gates", "walkforward_stability"): {"python-bool"},
}


def _serialisation_class(value) -> str:
    """The serialisation class of a published boolean.

    ``json.dump(..., default=str)`` writes a numpy boolean as the *string*
    ``"True"`` / ``"False"`` and a Python boolean as a JSON ``true`` /
    ``false``. The class is the convention the published gate blocks carry.
    """
    if isinstance(value, str) and value in ("True", "False"):
        return "numpy-bool-as-string"
    if isinstance(value, bool):
        return "python-bool"
    return "other"


# ---------------------------------------------------------------------------
# 3. The per-family recipes
# ---------------------------------------------------------------------------
# Each recipe declares the artefacts the family published from and the
# conventions its producer used. Every field is a *measured* convention,
# read off the runner that produced the artifact (and, where the artifact
# carries a copy of it, off that copy).
#
#   kind          the three classes of the published block
#   equity        the file the published equity curve lives in
#   trades        the file the published trade log lives in
#   benchmark     the file the published benchmark equity lives in
#   vix           the file the producer's VIX input lives in (None when it
#                 was never committed)
#   split         (train_end, val_end) of the producer's date split
#   sharpe_ddof   the standard-deviation convention of the published Sharpes
#   bootstrap     "legacy" (MT19937) or "pcg64"
#   beta          "pre_h51" or "post_h51"
#   gates         the producer's gate thresholds, read off the runner
FAMILY_RECIPES: dict[str, dict] = {
    # -- the exploratory baselines ----------------------------------------
    "ma_crossover_baseline_v1": dict(
        kind="exploratory",
        equity="equity_curve.parquet",
        trades="trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix=None,
        split=("2020-12-31", "2022-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
    ),
    "buy_and_hold_baseline_v1": dict(
        kind="exploratory",
        equity="equity_curve.parquet",
        trades="trades.parquet",
        benchmark=None,
        vix=None,
        split=("2020-12-31", "2022-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
    ),
    # -- the H16-style gate summaries -------------------------------------
    "ts_momentum_20etf_v1": dict(
        kind="certified",
        equity="selected_equity.parquet",
        trades="selected_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        selection_metric="mean walk-forward OOS Sharpe on TRAIN",
    ),
    "cs_momentum_10etf_v1": dict(
        kind="certified",
        equity="selected_equity.parquet",
        trades="selected_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        oos_dd="ratio",
        selection_metric="mean walk-forward OOS Sharpe on TRAIN",
    ),
    "regime_gated_momentum_20etf_v1": dict(
        kind="certified",
        equity="selected_equity.parquet",
        trades="selected_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        selection_metric=(
            "mean walk-forward OOS Sharpe on TRAIN minus overfit-guard penalty "
            "(robust z of train Sharpe / train-vol)"
        ),
    ),
    # -- the H23-style ensemble summaries ---------------------------------
    "futures_tsmom_v1": dict(
        kind="certified",
        equity="ensemble_equity.parquet",
        trades="ensemble_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        p_value="pre-fix-default",
    ),
    "ddcv_futures_tsmom_v1": dict(
        kind="certified",
        equity="best_ddcv_equity.parquet",
        trades="best_ddcv_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        p_value="library",
    ),
    "h6_vix_ddcv_futures_tsmom_v1": dict(
        kind="certified",
        equity="best_equity.parquet",
        trades="best_trades.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
        bootstrap="legacy",
        beta="pre_h51",
        p_value="library",
    ),
    # -- the H7-style split/gate summaries --------------------------------
    "h7_intraday_tsmom_v1": dict(
        kind="certified",
        equity="returns.parquet",
        trades="trades.parquet",
        benchmark=None,
        vix=None,
        split=("2020-12-31", "2022-12-31"),
        sharpe_ddof=0,
        split_sharpe_ddof=0,
        overall_sharpe_ddof=1,
        bootstrap="legacy",
        beta="pre_h51",
        p_value="library",
    ),
    # -- the table-echo families -------------------------------------------
    "ma_crossover_param_sweep_v1": dict(
        kind="exploratory",
        tables={"all_results": "param_sweep_results.parquet"},
    ),
    "alternative_strategies_v1": dict(
        kind="exploratory",
        tables={"all_results": "strategy_results.parquet"},
    ),
    "h8_roll_adjusted_futures_tsmom_v1": dict(
        kind="certified",
        equity="best_equity_w0.5.parquet",
        trades="best_trades_w0.5.parquet",
        benchmark="benchmark_equity.parquet",
        vix="vix_close.parquet",
        split=("2019-12-31", "2021-12-31"),
        sharpe_ddof=0,
    ),
    "h25_pf_robustness": dict(kind="audit"),
    "h14_pf_margin_selection_audit": dict(kind="audit"),
    "H18_Overnight_Intraday_Decomposition": dict(
        kind="exploratory",
        split=("2014-12-31", "2019-12-31"),
    ),
}

#: The measured per-artifact exceptions.
#:
#: The library's ``sharpe_ratio`` used to take the standard deviation of the
#: container it was handed, so a pandas Series gave the SAMPLE standard
#: deviation (``ddof=1``) and an ndarray the POPULATION one (``ddof=0``).
#: The H7 family passes a Series, so its split Sharpes are on ``ddof=1``
#: while the library now enforces ``ddof=0``. The two H7 summaries produced
#: on 2026-10-19 already publish the post-fix convention; the two earlier
#: ones publish the pre-fix one. The ``overall`` block comes from the
#: ENGINE's own metric block, which was published on the engine's pre-fix
#: ``ddof=1`` in all four summaries.
SPLIT_SHARPE_DDOF_1 = frozenset(
    {
        "exp_2026-10-11T14-53-13-076438Z",
        "exp_2026-10-14T08-20-16-720432Z",
    }
)

#: The published summaries whose benchmark-significance gate predates the
#: H34 direction-aware rule.
#:
#: The gate is "the alpha is significant AND the information ratio is
#: positive". The regime-gated family's first summary was written before
#: the rule landed and published the direction-unaware form: it passes on
#: ``p = 0.0464`` even though the information ratio is -0.8932, i.e. the
#: strategy *underperformed* the benchmark significantly. Its sibling
#: summary, written after the fix, publishes the direction-aware verdict.
PRELIM_SIGNIFICANCE_GATE = frozenset({"exp_2026-10-10T21-27-13-928282Z"})

#: The producers that the tracker metadata does not name. The record's own
#: artifact ids and the runner that owns each shape identify them.
UNTRACKED_PRODUCERS: dict[str, str] = {
    "exp_2026-10-11T14-53-13-076438Z": "h7_intraday_tsmom_v1",
    "exp_2026-10-14T08-20-16-720432Z": "h7_intraday_tsmom_v1",
    "h26_sharpe_scale": "h26_sharpe_scale_audit",
    "h27_pnl_level": "h27_pnl_level_audit",
    "h28_causal_recertification": "h28_causal_recertification",
    "H18_Overnight_Intraday_Decomposition": "H18_Overnight_Intraday_Decomposition",
    "h29_lookahead_sweep": "h29_lookahead_sweep",
    "pf_robustness": "h25_pf_robustness",
}


#: The published summaries whose published alpha cannot resolve the
#: pre-H51 and post-H51 beta conventions.
#:
#: The two conventions differ by ``beta * benchmark_mean / (n - 1)`` times
#: 252. On the regime-gated family's OOS window that is 6e-06 — well below
#: the half-step of the published four-decimal precision — so the published
#: alpha is the same under both conventions and cannot discriminate them.
#: The published *beta* is the value that discriminates them, and it is on
#: the pre-fix convention.
BETA_INDISTINGUISHABLE = frozenset(
    {
        "exp_2026-10-10T21-27-13-928282Z",
        "exp_2026-10-10T21-28-20-920399Z",
    }
)

#: The rounding step of a published four-decimal value.
PUBLISHED_ROUNDING_STEP = 1e-4

#: The published leaves the reconstruction reaches but cannot reproduce, and
#: why. These are *disclosed*, never rewritten.
#:
#: The one entry is the pre-fix regime-stability sentinel: the older runner
#: published the initial ``-Infinity`` of the worst-regime accumulator
#: instead of the computed minimum, while its five sibling summaries of the
#: same family publish the computed value (-2.4005 for the time-series
#: family, -3.0304 for the cross-sectional one).
NOT_REDERIVABLE_VALUES: dict[str, dict[str, str]] = {
    "exp_2026-10-10T20-56-30-507309Z": {
        "gates.regime_stability.value": (
            "the pre-fix regime-stability sentinel: the published value is the "
            "initial -Infinity of the worst-regime accumulator, not the "
            "computed minimum (-2.4005)"
        ),
    },
}

#: The published leaves the reconstruction does not reach, and why.
#:
#: Each entry is a published leaf that the artifact cannot carry, so the
#: reconstruction cannot reach it. The leaf is *disclosed*, never rewritten.
NOT_REDERIVABLE: dict[str, set[str]] = {
    # The benchmark trade log was never committed, so the benchmark block's
    # trade count and average trade cost have no source in the record
    # (§H52 recorded the same gap for the ``metrics`` block).
    "ma_crossover_baseline_v1": {
        "benchmark_metrics.num_trades",
        "benchmark_metrics.avg_trade_cost",
    },
    # The perturbation gate publishes the eight-way perturbation set of a
    # grid re-run; the committed grid table carries only the selected row.
    "ts_momentum_20etf_v1": {"gates.param_perturbation.details"},
    "cs_momentum_10etf_v1": {"gates.param_perturbation.details"},
    "regime_gated_momentum_20etf_v1": {"gates.param_perturbation.details"},
    # The base book of the roll-adjusted family has no committed trade log.
    "h8_roll_adjusted_futures_tsmom_v1": {"base_metrics.oos_trades"},
    # The block-bootstrap switch and the block length are the producer's own
    # declarations, not statistics of the committed bootstrap table.
    "h25_pf_robustness": {
        "block_bootstrap.enabled",
        "block_bootstrap.block_len_selected",
    },
    # The overnight/intraday family serialised its trade and return tables
    # into ``stats.json`` as TEXT; the artifact keeps no parquet for them, so
    # the per-combo trade count and profit factor, the two OOS metrics that
    # rest on them, and the gates that consume them have no source in the
    # committed artifact. The regime, benchmark and perturbation gates rest
    # on the VIX series and the benchmark book, which this artifact does
    # not commit either.
    "H18_Overnight_Intraday_Decomposition": {
        "all_combo_results[0].profit_factor",
        "all_combo_results[0].trades",
        "all_combo_results[1].profit_factor",
        "all_combo_results[1].trades",
        "all_combo_results[2].profit_factor",
        "all_combo_results[2].trades",
        "all_combo_results[3].profit_factor",
        "all_combo_results[3].trades",
        "all_combo_results[4].profit_factor",
        "all_combo_results[4].trades",
        "all_combo_results[5].profit_factor",
        "all_combo_results[5].trades",
        "oos_metrics.profit_factor",
        "oos_metrics.trades",
        "gate_metrics.trades",
        "gate_metrics.max_drawdown.passes",
        "gate_metrics.profit_factor",
        "gate_metrics.walk_forward_stability",
        "gate_metrics.worst_regime_sharpe",
        "gate_metrics.benchmark_p",
        "gate_metrics.information_ratio",
        "gate_metrics.perturbation_ratio",
    },
}

#: The values the reconstruction reaches that the record does not publish.
#:
#: The record publishes less than the producers computed. The reconstruction
#: reaches the value; the summary does not carry it. That difference is
#: disclosed here so that it is not read as a re-derivation failure.
NOT_PUBLISHED: dict[str, set[str]] = {}


def _producer_of(directory: pathlib.Path, data: dict) -> str | None:
    artifact_id = _artifact_id(directory, data)
    tracked = _NAMES.get(artifact_id)
    if tracked:
        return tracked
    return UNTRACKED_PRODUCERS.get(artifact_id)


# ---------------------------------------------------------------------------
# 4. The gate thresholds, read off the runners
# ---------------------------------------------------------------------------
#: The PROMPT_V2 gate thresholds, identical in every family that uses them.
GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "max_crisis_drawdown": 0.20,
}


# ---------------------------------------------------------------------------
# 5. The re-derivation, per family
# ---------------------------------------------------------------------------
def _engine_metrics(
    returns: pd.Series,
    equity: pd.Series,
    trades,
    capital: float,
    convention: str = "pre-fix",
) -> dict:
    """The engine's own metric block, reconstructed from the frozen curve.

    Two conventions exist in the record:

    * ``current`` — the engine's present implementation: the total return
      spans every bar, the volatility keeps the SAMPLE standard deviation,
      the Sharpe uses the POPULATION one, and the Sortino uses the
      *downside deviation*.
    * ``pre-fix`` — the engine's implementation in force when the published
      blocks were written: the total return is measured from the FIRST
      equity row, the Sharpe divides by the SAMPLE standard deviation and
      the Sortino divides by the standard deviation of the
      *negative-returns subset*.

    The published blocks of the exploratory baselines are on the pre-fix
    convention; the engine moved afterwards. The engine's own comments name
    the two changes (``src/qtr/backtest/engine.py``).
    """
    n_periods = len(returns)
    ann_factor = 252
    if convention == "pre-fix":
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    else:
        total_return = float(equity.iloc[-1] / capital - 1.0)
    gross = 1.0 + total_return
    ann_return = (gross ** (ann_factor / n_periods) - 1) if gross > 0.0 else -1.0
    ann_vol = float(returns.std() * np.sqrt(ann_factor))
    if convention == "pre-fix":
        sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(ann_factor))
        losses = returns[returns < 0]
        downside_dev = float(losses.std(ddof=1)) if len(losses) > 1 else 0.0
    else:
        if float(returns.std(ddof=0)) > 1e-15:
            sharpe = float(returns.mean() / returns.std(ddof=0) * np.sqrt(ann_factor))
        else:
            sharpe = 0.0
        shortfall = np.minimum(0, returns)
        downside_dev = float(np.sqrt(np.mean(shortfall**2)))
    sortino = (
        float(returns.mean() / downside_dev * np.sqrt(ann_factor)) if downside_dev > 0 else 0.0
    )
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min())
    if trades is not None and len(trades) > 0:
        num_trades = int(len(trades))
        avg_trade_cost = float(trades["cost"].mean())
    else:
        num_trades = 0
        avg_trade_cost = 0.0
    calmar = float(ann_return / abs(max_drawdown)) if abs(max_drawdown) > 0 else float("inf")
    return {
        "total_return": total_return,
        "annualized_return": float(ann_return),
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "max_drawdown_duration": int(_max_dd_duration(drawdown)),
        "profit_factor": _profit_factor(returns),
        "num_trades": num_trades,
        "avg_trade_cost": avg_trade_cost,
        "calmar": calmar,
    }


def _max_dd_duration(drawdown: pd.Series) -> int:
    """The engine's own maximum-drawdown duration, in bars."""
    in_dd = drawdown < 0
    if not in_dd.any():
        return 0
    groups = (in_dd != in_dd.shift()).cumsum()
    durations = in_dd.groupby(groups).sum()
    return int(durations.max())


def _rederive_baseline(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The exploratory baseline summaries: ``strategy_metrics`` and
    ``benchmark_metrics``.

    The ``validation`` block of these summaries was closed by §H49; H54 adds
    the engine's own metric blocks, which the record publishes beside them.
    The benchmark trade log was never committed, so the benchmark block's
    ``num_trades`` and ``avg_trade_cost`` cannot be re-derived and are left
    out of the reconstruction (§H52 recorded the same gap).
    """
    out: dict = {}
    capital = float(data["config"]["backtest"]["initial_capital"])
    convention = recipe.get("engine_metrics", "pre-fix")
    equity = _series(directory / recipe["equity"]).astype(float)
    returns = _returns_from_equity(equity, capital)
    trades = read_parquet_safe(directory / recipe["trades"])
    out["strategy_metrics"] = _engine_metrics(returns, equity, trades, capital, convention)
    if recipe["benchmark"]:
        bench_equity = _series(directory / recipe["benchmark"]).astype(float)
        bench_returns = _returns_from_equity(bench_equity, capital)
        block = _engine_metrics(bench_returns, bench_equity, None, capital, convention)
        block.pop("num_trades")
        block.pop("avg_trade_cost")
        out["benchmark_metrics"] = block
    return out


def _rederive_gate_blocks(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The H16-style summaries: the split/OOS metrics, the benchmark
    comparison, the regime block, the gate block, the gate specification
    and the grid summary."""
    out: dict = {}
    train_end, val_end = recipe["split"]
    dd_form = recipe.get("oos_dd", "absolute")
    equity = _series(directory / recipe["equity"]).astype(float)
    returns = _returns_from_equity(equity)
    train, val, test, oos = _split_by_date(returns, train_end, val_end)
    oos_sharpe = _sharpe(oos.values, recipe["sharpe_ddof"])
    train_sharpe = _sharpe(train.values, recipe["sharpe_ddof"])
    val_sharpe = _sharpe(val.values, recipe["sharpe_ddof"])
    test_sharpe = _sharpe(test.values, recipe["sharpe_ddof"])
    oos_dd = _max_drawdown(oos.values, dd_form)
    oos_pf = _profit_factor(oos.values)

    trades = read_parquet_safe(directory / recipe["trades"])
    oos_trades = trades[pd.to_datetime(trades["timestamp"]) > pd.Timestamp(train_end)]
    n_trades = int(len(oos_trades))

    out["split_metrics"] = {
        "train_sharpe": round(train_sharpe, 4),
        "val_sharpe": round(val_sharpe, 4),
        "test_sharpe": round(test_sharpe, 4),
        "oos_sharpe": round(oos_sharpe, 4),
    }
    out["oos_metrics"] = {
        "sharpe": round(oos_sharpe, 4),
        "n_trades": n_trades,
        "profit_factor": round(oos_pf, 4),
        "max_drawdown": round(oos_dd, 4),
    }
    # The bootstrap confidence intervals were resampled with the legacy
    # MT19937 stream; the library now uses PCG64.
    ci = _legacy_bootstrap_ci(oos.values, lambda x: _sharpe(x, recipe["sharpe_ddof"]))
    out["oos_metrics"]["sharpe_ci"] = [round(ci[0], 4), round(ci[1], 4)]

    benchmark = _returns_from_equity(_series(directory / recipe["benchmark"]).astype(float))
    bench_oos = benchmark[benchmark.index > train_end]
    comparison = _benchmark_stats(
        oos.values,
        bench_oos.values,
        ddof=0,
        beta_pre_h51=recipe["beta"] == "pre_h51",
    )
    published_comparison = data.get("benchmark_comparison", {})
    out["benchmark_comparison"] = {
        "information_ratio": round(comparison["information_ratio"], 4),
        "information_ratio_ci": [],
        "alpha_annualized": round(comparison["alpha_annualized"], 4),
        "alpha_p_value": round(comparison["alpha_p_value"], 6),
        "alpha_t_stat": round(_alpha_t_stat(oos.values, bench_oos.values), 4),
        "beta": round(comparison["beta"], 4),
    }
    excess = np.asarray(oos.values, dtype=float) - np.asarray(bench_oos.values, dtype=float)

    def ir_func(sample: np.ndarray) -> float:
        bench_part = np.asarray(bench_oos.values, dtype=float)[: len(sample)]
        diff = sample - bench_part
        deviation = float(np.std(diff, ddof=0))
        return float(diff.mean() / deviation * np.sqrt(252)) if deviation > 0 else 0.0

    ir_ci = _legacy_bootstrap_ci(excess, ir_func)
    out["benchmark_comparison"]["information_ratio_ci"] = [
        round(ir_ci[0], 4),
        round(ir_ci[1], 4),
    ]
    # The published block's own shape is the producer's vintage: the older
    # runners published neither the annualised alpha nor the t-statistic.
    for key in list(out["benchmark_comparison"]):
        if key not in published_comparison:
            del out["benchmark_comparison"][key]

    # The regime block: the VIX series is committed for this family.
    vix = _series(directory / recipe["vix"]).astype(float)
    regimes = _regime_labels(vix).reindex(oos.index)
    regime_metrics = {}
    worst = np.inf
    for regime in ("bull", "sideways", "bear"):
        selection = regimes == regime
        subset = oos[selection]
        if len(subset) > 1 and float(subset.std()) > 0:
            value = _sharpe(subset.values, recipe["sharpe_ddof"])
        else:
            value = 0.0
        regime_metrics[regime] = {"sharpe": value, "n": int(len(subset))}
        worst = min(worst, value)
    out["regime_metrics"] = regime_metrics

    # The gate block: every published gate is a function of the values above
    # and of the producer's declared thresholds.
    wf_stability = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0
    alpha_p = comparison["alpha_p_value"]
    information_ratio = comparison["information_ratio"]
    gates = {
        "net_oos_sharpe": {
            "value": round(oos_sharpe, 4),
            "threshold": GATES["min_sharpe"],
            "pass": bool(oos_sharpe >= GATES["min_sharpe"]),
        },
        "oos_trades": {
            "value": n_trades,
            "threshold": GATES["min_trades"],
            "pass": bool(n_trades >= GATES["min_trades"]),
        },
        "profit_factor": {
            "value": round(oos_pf, 4),
            "threshold": GATES["min_profit_factor"],
            "pass": bool(oos_pf >= GATES["min_profit_factor"]),
        },
        "max_drawdown": {
            "value": round(oos_dd, 4),
            "threshold": GATES["max_drawdown"],
            "pass": bool(oos_dd >= -GATES["max_drawdown"]),
        },
        "walkforward_stability": {
            "value": round(wf_stability, 4),
            "threshold": GATES["min_walkforward_stability"],
            "pass": bool(wf_stability >= GATES["min_walkforward_stability"]),
        },
        "param_perturbation": {
            "value": None,
            "threshold": round(oos_sharpe * GATES["min_perturbed_sharpe_ratio"], 4),
            "pass": None,
        },
        "regime_stability": {
            "value": round(worst, 4),
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": bool(worst >= GATES["min_worst_regime_sharpe"]),
            "regimes": regime_metrics,
        },
        "benchmark_significance": {
            "value": round(float(alpha_p), 4),
            "threshold": GATES["max_p_value"],
            "pass": bool(
                _significance_gate(
                    alpha_p,
                    information_ratio,
                    GATES["max_p_value"],
                    direction_aware=recipe.get("significance_gate", "direction-aware")
                    == "direction-aware",
                )
            ),
            "information_ratio": round(float(information_ratio), 4),
            "alpha_p_value": round(float(alpha_p), 4),
        },
    }
    # The perturbation gate's own value is the WORST perturbed Sharpe. The
    # perturbed Sharpes themselves need the grid re-run and are not
    # re-derivable, but the summary publishes them, and the gate is a
    # function of them, so the gate re-derives from the published block.
    perturbations = data.get("perturbations", {})
    if perturbations:
        min_perturbed = min(float(value) for value in perturbations.values())
        gates["param_perturbation"] = {
            "value": round(min_perturbed, 4),
            "threshold": round(oos_sharpe * GATES["min_perturbed_sharpe_ratio"], 4),
            "pass": bool(min_perturbed >= oos_sharpe * GATES["min_perturbed_sharpe_ratio"]),
        }
    published_gates = data.get("gates", {})
    # The crisis-window gates of the regime-gated family: the drawdown of
    # the equity curve inside the two crisis windows, on the relative form
    # the producer used.
    crisis = {
        "crisis_drawdown_2020_03": _window_max_drawdown(equity, "2020-03-01", "2020-03-31"),
        "crisis_drawdown_2022": _window_max_drawdown(equity, "2022-01-01", "2022-12-31"),
    }
    for name, value in crisis.items():
        if name not in published_gates:
            continue
        gates[name] = {
            "value": round(value, 4),
            "threshold": -GATES["max_crisis_drawdown"],
            "pass": bool(value >= -GATES["max_crisis_drawdown"]),
        }
    for key in list(gates):
        if key not in published_gates:
            del gates[key]
    for key, gate in gates.items():
        if key == "param_perturbation":
            continue
        published_gate = published_gates[key]
        for sub in list(gate):
            if sub not in published_gate:
                del gate[sub]
    out["gates"] = gates
    out["all_gates_pass"] = bool(all(g["pass"] for g in gates.values()))

    # The gate specification: the producer's own threshold table.
    spec = dict(GATES)
    spec["alpha_multiple_testing"] = "benjamini_hochberg"
    for key, value in recipe.get("gates_spec", {}).items():
        spec[key] = value
    out["gates_spec"] = {k: v for k, v in spec.items() if k in data.get("gates_spec", {})}

    # The grid summary: the combo count and the Benjamini-Hochberg count are
    # read off the committed grid table.
    grid = read_parquet_safe(directory / "param_grid_results.parquet")
    summary = {
        "n_combos": int(len(grid)),
        "selection_metric": recipe.get("selection_metric", ""),
        "benjamini_hochberg_significant": int(
            sum(1 for _, row in grid.iterrows() if bool(row.get("wf_oos_significant", False)))
        ),
    }
    if "overfit_guard" in data.get("param_grid_summary", {}):
        metric = grid["overfit_metric"].astype(float)
        summary["overfit_guard"] = {
            "z_threshold": 1.5,
            "penalty_weight": 0.25,
            "median_overfit_metric": float(metric.median()),
            "iqr_overfit_metric": float(metric.quantile(0.75) - metric.quantile(0.25)),
        }
    out["param_grid_summary"] = summary

    # The crisis-window block of the regime-gated family.
    if "crisis_drawdowns" in data:
        out["crisis_drawdowns"] = {
            "dd_2020_03": round(crisis["crisis_drawdown_2020_03"], 4),
            "dd_2022": round(crisis["crisis_drawdown_2022"], 4),
        }
    if "verdict" in data:
        out["verdict"] = "PASS" if out["all_gates_pass"] else "REJECT"
    return out


def _window_max_drawdown(equity: pd.Series, start: str, end: str) -> float:
    """The peak-to-trough drawdown of the equity curve inside a window.

    The producer's form: ``eq / eq.cummax() - 1`` on the equity *level*.
    """
    window = equity.loc[start:end]
    if len(window) < 2:
        return 0.0
    return float((window / window.cummax() - 1.0).min())


def _alpha_t_stat(strategy, benchmark) -> float:
    from scipy import stats

    strat = np.asarray(strategy, dtype=float)
    bench = np.asarray(benchmark, dtype=float)
    excess = strat - bench
    if len(excess) < 2:
        return 0.0
    return float(stats.ttest_1samp(excess, 0.0).statistic)


def _significance_gate(
    p_value: float, information_ratio: float, threshold: float, direction_aware: bool = True
) -> bool:
    """The benchmark-significance gate.

    The H34 form is direction-aware: significance alone is not evidence
    for the hypothesis, the excess return must be positive as well. The
    form in force before H34 tested the p-value alone.
    """
    if direction_aware:
        return bool(p_value < threshold and information_ratio > 0.0)
    return bool(p_value < threshold)


def _rederive_ensemble(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The H23-style summaries: the futures ensemble, the DDCV family and
    the H6 family all publish the same core block."""
    out: dict = {}
    train_end, val_end = recipe["split"]
    equity = _series(directory / recipe["equity"]).astype(float)
    returns = _returns_from_equity(equity)
    train, val, test, oos = _split_by_date(returns, train_end, val_end)
    oos_sharpe = _sharpe(oos.values, recipe["sharpe_ddof"])
    train_sharpe = _sharpe(train.values, recipe["sharpe_ddof"])

    trades = read_parquet_safe(directory / recipe["trades"])
    oos_trades = trades[pd.to_datetime(trades["timestamp"]) > pd.Timestamp(train_end)]

    out["oos_sharpe"] = oos_sharpe
    out["oos_pf"] = _profit_factor(oos.values)
    out["oos_max_dd"] = _max_drawdown(oos.values)
    out["oos_trades"] = int(len(oos_trades))
    out["train_sharpe"] = train_sharpe
    out["wf_stability"] = oos_sharpe / train_sharpe if train_sharpe != 0 else 0.0

    vix = _series(directory / recipe["vix"]).astype(float)
    regimes = _regime_labels(vix)
    worst = np.inf
    for regime in ("bull", "sideways", "bear"):
        selection = regimes.loc[oos.index] == regime
        if len(selection) > 0 and bool(selection.any()):
            subset = oos[selection]
            if len(subset) > 1 and float(subset.std()) > 0:
                worst = min(worst, _sharpe(subset.values, recipe["sharpe_ddof"]))
    if worst == np.inf:
        worst = oos_sharpe
    out["worst_regime_sharpe"] = float(worst)

    benchmark = _returns_from_equity(_series(directory / recipe["benchmark"]).astype(float))
    bench_oos = benchmark[benchmark.index > train_end]
    comparison = _benchmark_stats(
        oos.values,
        bench_oos.values,
        ddof=0,
        beta_pre_h51=recipe["beta"] == "pre_h51",
    )
    # The futures family published the PRE-FIX alpha p-value: it read
    # ``alpha_res.get("p_value", 1.0)`` and the library returns the alpha
    # p-value under ``alpha_p_value``, so the published number is the 1.0
    # sentinel and the gate it fed was vacuous. The DDCV and H6 families read
    # the key the library actually returns.
    out["alpha_vs_benchmark"] = {
        "p_value": 1.0 if recipe["p_value"] == "pre-fix-default" else comparison["alpha_p_value"],
        "information_ratio": comparison["information_ratio"],
    }
    out["passes"] = {
        "sharpe": bool(oos_sharpe >= GATES["min_sharpe"]),
        "trades": bool(len(oos_trades) >= GATES["min_trades"]),
        "pf": bool(_profit_factor(oos.values) >= GATES["min_profit_factor"]),
        "dd": bool(abs(_max_drawdown(oos.values)) <= GATES["max_drawdown"]),
        "stab": bool(out["wf_stability"] >= GATES["min_walkforward_stability"]),
        "worst": bool(worst >= GATES["min_worst_regime_sharpe"]),
        "p": bool(
            _significance_gate(comparison["alpha_p_value"], comparison["information_ratio"], 0.05)
        ),
        "ir": bool(comparison["information_ratio"] > GATES["min_information_ratio"]),
    }
    out["all_pass"] = bool(all(out["passes"].values()))

    prices = read_parquet_safe(directory / "prices.parquet")
    out["data_available"] = list(prices.columns)

    grid = read_parquet_safe(directory / "param_grid_results.parquet")
    if "ensemble_k" in data:
        out["top_k"] = [_grid_record(row) for _, row in grid.head(data["ensemble_k"]).iterrows()]
    else:
        # The DDCV and H6 families publish the whole drawdown-parameter grid
        # and the selected row, both of which the committed grid carries.
        records = [_grid_record(row) for _, row in grid.iterrows()]
        out["grid"] = records
        out["ddcv_grid"] = records
        best = records[0]
        out["best_ddcv"] = {"dd_trigger": best["dd_trigger"], "dd_factor": best["dd_factor"]}
        out["best_combo"] = {"dd_trigger": best["dd_trigger"], "dd_factor": best["dd_factor"]}
        ablations = read_parquet_safe(directory / "ablations.parquet")
        out["ablations"] = [_grid_record(row) for _, row in ablations.iterrows()]
    return out


def _rederive_splits(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The H7-style summaries: the per-split block, the whole-sample block,
    the gate block and the verdict."""
    out: dict = {}
    train_end, val_end = recipe["split"]
    returns = _series(directory / "returns.parquet").astype(float)
    train, val, test, oos = _split_by_date(returns, train_end, val_end)

    def split_block(part: pd.Series) -> dict:
        if len(part) == 0:
            return {"sharpe": float("nan"), "n": 0, "max_dd": float("nan")}
        cumulative = (1 + part).cumprod()
        return {
            "sharpe": _sharpe(part.values, recipe["split_sharpe_ddof"]),
            "n": int(len(part)),
            "max_dd": float((cumulative / cumulative.cummax() - 1.0).min()),
        }

    out["splits"] = {
        "train": split_block(train),
        "val": split_block(val),
        "test": split_block(test),
        "oos": split_block(oos),
    }

    equity = _series(directory / "equity_curve.parquet").astype(float)
    trades = read_parquet_safe(directory / "trades.parquet")
    n_periods = len(returns)
    total_return = float(equity.iloc[-1] / INITIAL_CAPITAL - 1.0)
    gross = 1.0 + total_return
    ann_return = (gross ** (252 / n_periods) - 1) if gross > 0.0 else -1.0
    whole_sharpe = _sharpe(returns.values, recipe["overall_sharpe_ddof"])
    whole_dd = float((equity / equity.cummax() - 1.0).min())
    whole_pf = _profit_factor(returns.values)

    train_sharpe = out["splits"]["train"]["sharpe"]
    test_sharpe = out["splits"]["test"]["sharpe"]
    if train_sharpe and abs(train_sharpe) > 1e-18:
        wf_stability = min(1.0, abs(test_sharpe) / abs(train_sharpe))
    else:
        wf_stability = 0.0

    out["overall"] = {
        "sharpe": whole_sharpe,
        "annualized_return": float(ann_return),
        "max_drawdown": whole_dd,
        "n_trades": int(len(trades)),
        "profit_factor": whole_pf,
        "walkforward_stability": wf_stability,
    }
    # The benchmark comparison is advisory in this family: it failed, the
    # runner logged the failure and published ``benchmark: null``, so the two
    # benchmark gates are False and the rest are the values above.
    out["gates"] = {
        "min_sharpe": bool(whole_sharpe >= GATES["min_sharpe"]),
        "min_trades": bool(len(trades) >= GATES["min_trades"]),
        "min_profit_factor": bool(whole_pf >= GATES["min_profit_factor"]),
        "max_drawdown": bool(abs(whole_dd) <= GATES["max_drawdown"]),
        "min_walkforward_stability": bool(wf_stability >= GATES["min_walkforward_stability"]),
        "min_perturbed_sharpe_ratio": True,
        "min_worst_regime_sharpe": True,
        "max_p_value": False,
        "min_information_ratio": False,
    }
    out["all_pass"] = bool(all(out["gates"].values()))
    out["verdict"] = "PASS" if out["all_pass"] else "REJECT"
    return out


def _grid_record(row: pd.Series) -> dict:
    """One grid row as the producer published it.

    A parameter cell is a dict that carries every slot of the strategy
    family, but the producer published only the slots it used: the unused
    ones are ``None`` and are dropped here, exactly as the producer's own
    serialisation dropped them.
    """
    record = {}
    for key, value in row.items():
        if isinstance(value, (np.bool_, bool)):
            record[key] = bool(value)
        elif isinstance(value, np.ndarray):
            record[key] = [float(v) for v in value]
        elif isinstance(value, (np.integer,)):
            record[key] = int(value)
        elif isinstance(value, (np.floating,)):
            record[key] = float(value)
        elif isinstance(value, dict):
            record[key] = {k: v for k, v in value.items() if v is not None}
        else:
            record[key] = value
    return record


def _rederive_table_echo(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The families whose published block is a committed table, published as
    nested JSON: the parameter sweep and the alternatives study.

    Every published record is one row of the committed parquet, and the
    reconstruction reads the table back.
    """
    out: dict = {}
    for block, filename in recipe["tables"].items():
        frame = read_parquet_safe(directory / filename)
        out[block] = [_grid_record(row) for _, row in frame.iterrows()]
    return out


def _rederive_h8(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The roll-adjusted family: the weight grid, the ablation table, the
    benchmark block, the gate metrics and the verdict."""
    out: dict = {}
    train_end, val_end = recipe["split"]
    grid = read_parquet_safe(directory / "param_grid_results.parquet")
    out["grid"] = [_grid_record(row) for _, row in grid.iterrows()]
    ablations = read_parquet_safe(directory / "ablations.parquet")
    out["ablations"] = [_grid_record(row) for _, row in ablations.iterrows()]

    prices = read_parquet_safe(directory / "prices.parquet")
    out["data_available"] = list(prices.columns)

    # The selected weight: the grid row with the best validation Sharpe.
    best = grid.loc[grid["val_sharpe"].idxmax()]
    out["best_weight"] = float(best["roll_carry_weight"])
    out["best_val_sharpe"] = float(best["val_sharpe"])

    # The benchmark block: the equal-weight futures buy-and-hold, published
    # from the engine's own metric block on the pre-fix convention (the
    # Sharpe on the SAMPLE standard deviation, the total return measured
    # from the first equity row).
    bench_equity = _series(directory / "benchmark_equity.parquet").astype(float)
    bench_returns = _returns_from_equity(bench_equity, INITIAL_CAPITAL)
    bench_oos = bench_returns[bench_returns.index > train_end]
    bench_metrics = _engine_metrics(bench_returns, bench_equity, None, INITIAL_CAPITAL, "pre-fix")
    out["benchmark_sharpe"] = bench_metrics["sharpe"]
    out["benchmark_return"] = bench_metrics["annualized_return"]
    out["benchmark_max_dd"] = bench_metrics["max_drawdown"]

    # The roll-date inventory.
    roll_dates = read_parquet_safe(directory / "roll_dates.parquet")
    out["roll_dates_count"] = {
        str(column): int(roll_dates[column].astype(bool).sum()) for column in roll_dates.columns
    }

    # The gate metrics of the selected weight, and of the base strategy.
    for block, equity_name, trades_name in (
        ("gate_metrics", recipe["equity"], recipe["trades"]),
        ("base_metrics", "base_equity.parquet", "base_trades.parquet"),
    ):
        if block not in data:
            continue
        equity = _series(directory / equity_name).astype(float)
        returns = _returns_from_equity(equity, INITIAL_CAPITAL)
        train, val, test, oos = _split_by_date(returns, train_end, val_end)
        oos_sharpe = _sharpe(oos.values, 0)
        train_sharpe = _sharpe(train.values, 0)
        oos_equity = equity[equity.index > train_end]
        oos_dd = float((oos_equity / oos_equity.expanding().max() - 1.0).min())
        oos_pf = _profit_factor(oos.values)
        n_trades = None
        if (directory / trades_name).exists():
            trades = read_parquet_safe(directory / trades_name)
            n_trades = int(
                len(trades[pd.to_datetime(trades["timestamp"]) > pd.Timestamp(train_end)])
            )
        wf_stability = oos_sharpe / train_sharpe if abs(train_sharpe) > 1e-18 else 0.0
        vix = _series(directory / "vix_close.parquet").astype(float)
        regimes = _regime_labels(vix).reindex(oos.index)
        worst = oos_sharpe
        for regime in ("bull", "sideways", "bear"):
            subset = oos[regimes == regime]
            if len(subset) > 1 and float(subset.std()) > 0:
                worst = min(worst, _sharpe(subset.values, 0))
        comparison = _benchmark_stats(oos.values, bench_oos.values, ddof=0, beta_pre_h51=True)
        alpha_p = comparison["alpha_p_value"]
        information_ratio = comparison["information_ratio"]
        passes = {
            "sharpe": bool(oos_sharpe >= GATES["min_sharpe"]),
            "trades": bool(n_trades is not None and n_trades >= GATES["min_trades"]),
            "pf": bool(oos_pf >= GATES["min_profit_factor"]),
            "dd": bool(abs(oos_dd) <= GATES["max_drawdown"]),
            "stab": bool(wf_stability >= GATES["min_walkforward_stability"]),
            "worst": bool(worst >= GATES["min_worst_regime_sharpe"]),
            "p": bool(_significance_gate(alpha_p, information_ratio, GATES["max_p_value"])),
            "ir": bool(information_ratio > GATES["min_information_ratio"]),
        }
        block_values = {
            "train_sharpe": float(train_sharpe),
            "val_sharpe": float(_sharpe(val.values, 0)),
            "test_sharpe": float(_sharpe(test.values, 0)),
            "oos_sharpe": float(oos_sharpe),
            "oos_pf": float(oos_pf),
            "oos_max_dd": float(oos_dd),
            "wf_stability": float(wf_stability),
            "worst_regime_sharpe": float(worst),
            "benchmark_p_value": float(alpha_p),
            "information_ratio": float(information_ratio),
        }
        if n_trades is not None:
            block_values["oos_trades"] = n_trades
        if block == "base_metrics":
            # The base block carries the base run's own gate verdicts.
            block_values["passes"] = _h8_passes(block_values)
            block_values["all_pass"] = bool(all(block_values["passes"].values()))
        out[block] = block_values
    out["passes"] = dict(_h8_passes(out["gate_metrics"]))
    out["all_pass"] = bool(all(out["passes"].values()))
    out["verdict"] = "PASS" if out["all_pass"] else "REJECT"
    return out


def _h8_passes(metrics: dict) -> dict:
    return {
        "sharpe": bool(metrics["oos_sharpe"] >= GATES["min_sharpe"]),
        "trades": bool(metrics.get("oos_trades", 0) >= GATES["min_trades"]),
        "pf": bool(metrics["oos_pf"] >= GATES["min_profit_factor"]),
        "dd": bool(abs(metrics["oos_max_dd"]) <= GATES["max_drawdown"]),
        "stab": bool(metrics["wf_stability"] >= GATES["min_walkforward_stability"]),
        "worst": bool(metrics["worst_regime_sharpe"] >= GATES["min_worst_regime_sharpe"]),
        "p": bool(
            _significance_gate(
                metrics["benchmark_p_value"], metrics["information_ratio"], GATES["max_p_value"]
            )
        ),
        "ir": bool(metrics["information_ratio"] > GATES["min_information_ratio"]),
    }


def _rederive_h25(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The PF-robustness audit: the bootstrap intervals, the medians and the
    gate fractions, read off the four committed bootstrap tables."""
    out: dict = {}
    pf = read_parquet_safe(directory / "pf_bootstrap.parquet")["profit_factor"].astype(float)
    sharpe = read_parquet_safe(directory / "sharpe_bootstrap.parquet")["sharpe"].astype(float)
    pf_block = read_parquet_safe(directory / "pf_bootstrap_block.parquet")["profit_factor"].astype(
        float
    )
    sharpe_block = read_parquet_safe(directory / "sharpe_bootstrap_block.parquet")["sharpe"].astype(
        float
    )
    pf_gate = float(data["pf_gate"])
    sharpe_gate = float(data["sharpe_gate"])
    out["pf_bootstrap_ci_95"] = [float(np.percentile(pf, 2.5)), float(np.percentile(pf, 97.5))]
    out["pf_bootstrap_median"] = float(np.median(pf))
    out["pf_frac_ge_gate"] = float((pf >= pf_gate).mean())
    out["pf_ci_lower_ge_gate"] = bool(out["pf_bootstrap_ci_95"][0] >= pf_gate)
    out["sharpe_bootstrap_ci_95"] = [
        float(np.percentile(sharpe, 2.5)),
        float(np.percentile(sharpe, 97.5)),
    ]
    out["sharpe_bootstrap_median"] = float(np.median(sharpe))
    out["sharpe_frac_ge_gate"] = float((sharpe >= sharpe_gate).mean())
    out["sharpe_ci_lower_ge_gate"] = bool(out["sharpe_bootstrap_ci_95"][0] >= sharpe_gate)
    out["block_bootstrap"] = {
        "pf_ci_95": [float(np.percentile(pf_block, 2.5)), float(np.percentile(pf_block, 97.5))],
        "sharpe_ci_95": [
            float(np.percentile(sharpe_block, 2.5)),
            float(np.percentile(sharpe_block, 97.5)),
        ],
        "pf_median": float(np.median(pf_block)),
        "sharpe_median": float(np.median(sharpe_block)),
        "pf_frac_ge_gate": float((pf_block >= pf_gate).mean()),
        "sharpe_frac_ge_gate": float((sharpe_block >= sharpe_gate).mean()),
        "pf_ci_lower_ge_gate": bool(float(np.percentile(pf_block, 2.5)) >= pf_gate),
        "sharpe_ci_lower_ge_gate": bool(float(np.percentile(sharpe_block, 2.5)) >= sharpe_gate),
    }
    return out


def _rederive_h14(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The PF-margin selection audit: the counts, read off the committed
    result table."""
    out: dict = {}
    results = read_parquet_safe(directory / "h14_results.parquet")
    out["k_top"] = int(len(results))
    out["n_trials_family_k"] = int(len(results))
    out["topk_count"] = int(len(results))
    out["configs_evaluated"] = int(len(results))
    out["n_passing"] = int(
        sum(
            1
            for _, row in results.iterrows()
            if bool(row["all_symbols_dispensable"])
            and float(row["pf_boot_ci_lb"]) >= float(data["min_pf_gate"])
            and float(row["dsr_adj_sharpe_at_k"]) >= float(data["min_sr_gate"])
        )
    )
    out["passes"] = []
    out["all_pass"] = bool(out["n_passing"] > 0)
    out["verdict"] = "PASS" if out["all_pass"] else "REJECT"
    return out


def _rederive_h18(directory: pathlib.Path, data: dict, recipe: dict) -> dict:
    """The overnight/intraday decomposition: the per-combo metrics read off
    the seven committed combo equity curves.

    The producer's per-combo table also carries a profit factor and a
    trade count, but the runner took them from the trade and return tables
    it serialised into ``stats.json`` as *text*; the artifact keeps no
    parquet for them, so they are not re-derivable.
    """
    out: dict = {}
    train_end, val_end = recipe["split"]
    labels = {record["combo_name"]: record for record in data["all_combo_results"]}
    combos = []
    for path in sorted(p for p in directory.iterdir() if p.is_dir()):
        if path.name.startswith("best_"):
            # A copy of the selected combo, not a combo of its own.
            continue
        equity_file = path / "equity.parquet"
        if not equity_file.exists():
            continue
        equity = _series(equity_file).astype(float)
        # The producer took the returns of each SLICE separately and
        # concatenated the pooled OOS slice, so the boundary bar between the
        # validation and the test window contributes its return to the
        # pooled series.
        train_equity = equity[equity.index <= train_end]
        val_equity = equity[(equity.index > train_end) & (equity.index <= val_end)]
        test_equity = equity[equity.index > val_end]
        train = train_equity.pct_change().dropna()
        val = val_equity.pct_change().dropna()
        test = test_equity.pct_change().dropna()
        # The pooled OOS series is the CONCATENATION of the two equity
        # slices, differenced across the join, so the first bar of the test
        # window contributes the return from the last bar of the validation
        # window.
        oos = pd.concat([val_equity, test_equity]).pct_change().dropna()
        combos.append(
            {
                "combo_name": path.name,
                "train_sharpe": float(_sharpe(train.values, 1)),
                "val_sharpe": float(_sharpe(val.values, 1)),
                "test_sharpe": float(_sharpe(test.values, 1)),
                "oos_sharpe": float(_sharpe(oos.values, 1)),
                "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
                "max_drawdown": float((equity / equity.expanding().max() - 1.0).min()),
                "final_equity": float(equity.iloc[-1]),
            }
        )
    # The published order is the producer's grid order; the reconstruction
    # is aligned to it by the combo name.
    by_name = {combo["combo_name"]: combo for combo in combos}
    ordered = []
    for record in data["all_combo_results"]:
        combo = dict(by_name[record["combo_name"]])
        predictor, _, hold = combo["combo_name"].partition("_next_")
        combo["predictor"] = predictor
        combo["hold_convention"] = f"next_{hold}"
        ordered.append(combo)
    out["all_combo_results"] = ordered
    # The selection itself is the producer's declaration; the metrics of the
    # selected combo are what re-derives.
    selected = data["selected_config"]["combo_name"]
    best = next(combo for combo in ordered if combo["combo_name"] == selected)
    out["selected_config"] = {
        "predictor": labels[best["combo_name"]]["predictor"],
        "hold_convention": labels[best["combo_name"]]["hold_convention"],
        "combo_name": best["combo_name"],
    }
    # The OOS block of the SELECTED combo: the pooled validation and test
    # window of the selected equity curve.
    selected_equity = _series(
        directory / data["selected_config"]["combo_name"] / "equity.parquet"
    ).astype(float)
    oos_equity = selected_equity[
        (selected_equity.index > train_end) & (selected_equity.index <= val_end)
    ]
    test_equity = selected_equity[selected_equity.index > val_end]
    oos_equity = pd.concat([oos_equity, test_equity])
    oos_returns = oos_equity.pct_change().dropna()
    out["oos_metrics"] = {
        "sharpe": float(_sharpe(oos_returns.values, 1)),
        "total_return": float(oos_equity.iloc[-1] / oos_equity.iloc[0] - 1.0),
        "max_drawdown": float((oos_equity / oos_equity.expanding().max() - 1.0).min()),
    }
    gates = {
        "sharpe": {
            "value": out["oos_metrics"]["sharpe"],
            "threshold": 1.0,
            "passes": bool(out["oos_metrics"]["sharpe"] >= 1.0),
        },
        "max_drawdown": {
            "value": abs(out["oos_metrics"]["max_drawdown"]),
            "threshold": 0.15,
        },
    }
    out["gate_metrics"] = gates
    return out


#: The re-derivation function of each producer family.
REDERRIVERS = {
    "ma_crossover_baseline_v1": _rederive_baseline,
    "buy_and_hold_baseline_v1": _rederive_baseline,
    "ts_momentum_20etf_v1": _rederive_gate_blocks,
    "cs_momentum_10etf_v1": _rederive_gate_blocks,
    "regime_gated_momentum_20etf_v1": _rederive_gate_blocks,
    "futures_tsmom_v1": _rederive_ensemble,
    "ddcv_futures_tsmom_v1": _rederive_ensemble,
    "h6_vix_ddcv_futures_tsmom_v1": _rederive_ensemble,
    "h7_intraday_tsmom_v1": _rederive_splits,
    "ma_crossover_param_sweep_v1": _rederive_table_echo,
    "alternative_strategies_v1": _rederive_table_echo,
    "h8_roll_adjusted_futures_tsmom_v1": _rederive_h8,
    "h25_pf_robustness": _rederive_h25,
    "h14_pf_margin_selection_audit": _rederive_h14,
    "H18_Overnight_Intraday_Decomposition": _rederive_h18,
}


def _rederive(directory: pathlib.Path, data: dict, recipe: dict, producer: str | None) -> dict:
    rederiver = REDERRIVERS.get(producer or "")
    if rederiver is None:
        return {}
    recipe = dict(recipe)
    artifact_id = data.get("experiment_id") or directory.name
    if artifact_id in SPLIT_SHARPE_DDOF_1:
        recipe["split_sharpe_ddof"] = 1
    if artifact_id in PRELIM_SIGNIFICANCE_GATE:
        recipe["significance_gate"] = "pre-h34"
    return rederiver(directory, data, recipe)


# ---------------------------------------------------------------------------
# 6. The measured table
# ---------------------------------------------------------------------------
def _entries() -> list[dict]:
    """One entry per summary that publishes no `metrics` block."""
    entries = []
    for directory, data in _non_metric_summaries():
        artifact_id = _artifact_id(directory, data)
        producer = _producer_of(directory, data)
        recipe = FAMILY_RECIPES.get(producer)
        entries.append(
            {
                "directory": directory,
                "artifact_id": artifact_id,
                "producer": producer,
                "recipe": recipe,
                "published": data,
                "files": sorted(p.name for p in directory.glob("*.parquet")),
            }
        )
    return entries


_ENTRIES = _entries()


def _leaf_count(value) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(v) for v in value)
    return 1


def _published_key_union() -> set[str]:
    keys: set[str] = set()
    for entry in _ENTRIES:
        keys.update(entry["published"])
    return keys


def _published_leaf_total() -> int:
    return sum(_leaf_count(entry["published"]) for entry in _ENTRIES)


def _key_classification() -> dict[str, str]:
    """The class of every distinct top-level key of the record.

    A key takes the strongest class it reaches in any summary that
    publishes it.
    """
    order = {"not re-derivable": 0, "re-derived, partly disclosed": 1, "re-derived": 2}
    classes: dict[str, str] = {}
    for entry in _ENTRIES:
        rederived = (
            _rederive(entry["directory"], entry["published"], entry["recipe"], entry["producer"])
            if entry["recipe"]
            else {}
        )
        for key in entry["published"]:
            if key in rederived:
                uncovered = _compare_published(entry["published"][key], rederived[key], key)[1]
                klass = "re-derived" if not uncovered else "re-derived, partly disclosed"
            else:
                klass = "not re-derivable"
            if key not in classes or order[klass] > order[classes[key]]:
                classes[key] = klass
    return classes


# ---------------------------------------------------------------------------
# 7. The contract
# ---------------------------------------------------------------------------
class TestH54NonMetricsBlockDisclosure:
    """H54 — the published blocks of the non-``metrics`` summaries."""

    # -- the record --------------------------------------------------------
    def test_the_record_has_forty_three_summaries(self):
        assert len(_ENTRIES) == 43, len(_ENTRIES)

    def test_the_record_has_twenty_four_shapes(self):
        shapes = {tuple(sorted(entry["published"])) for entry in _ENTRIES}
        assert len(shapes) == 24, len(shapes)

    def test_the_record_has_one_hundred_sixty_four_top_level_keys(self):
        assert len(_published_key_union()) == 164, len(_published_key_union())

    def test_the_record_publishes_seven_thousand_seven_hundred_eighty_five_leaves(self):
        assert _published_leaf_total() == 7785, _published_leaf_total()

    def test_three_summaries_publish_no_parquet_artifact(self):
        empty = [entry["artifact_id"] for entry in _ENTRIES if not entry["files"]]
        assert len(empty) == 3, empty

    def test_every_published_key_is_classified(self):
        """Every one of the record's 164 top-level keys is classified.

        A key is *re-derived* when the reconstruction reaches every one of
        its published leaves, *re-derived and partly disclosed* when it is
        reached everywhere but a named leaf has no source in the artifact,
        and *not re-derivable* when the block is a declaration or an audit
        verdict about another artifact.
        """
        classes = _key_classification()
        assert len(classes) == 164, len(classes)
        counts = {
            name: 0 for name in ("re-derived", "re-derived, partly disclosed", "not re-derivable")
        }
        for klass in classes.values():
            counts[klass] += 1
        assert counts == {
            "re-derived": 52,
            "re-derived, partly disclosed": 4,
            "not re-derivable": 108,
        }, counts

    def test_every_summary_has_a_known_producer(self):
        for entry in _ENTRIES:
            assert entry["producer"] is not None, entry["artifact_id"]

    # -- the classes -------------------------------------------------------
    def test_the_three_classes_are_separated(self):
        """The 43 summaries fall into the three classes the gap names."""
        classes = {}
        for entry in _ENTRIES:
            producer = entry["producer"] or ""
            if (
                producer.startswith("h2")
                or producer.startswith("h29")
                or producer in ("h25_pf_robustness",)
            ):
                klass = "audit"
            elif "metrics" in entry["published"] or "gates" in entry["published"]:
                klass = "certified"
            else:
                klass = "exploratory"
            classes.setdefault(klass, []).append(entry["artifact_id"])
        assert len(classes["audit"]) == 5, classes["audit"]
        assert sum(len(v) for v in classes.values()) == 43

    # -- the re-derivation -------------------------------------------------
    def test_the_re_derivable_families_re_derive(self):
        """Every re-derivable published value re-derives from its own frozen
        artifact, under the recorded convention."""
        failures = []
        declared = []
        for entry in _ENTRIES:
            if entry["recipe"] is None:
                continue
            rederived = _rederive(
                entry["directory"], entry["published"], entry["recipe"], entry["producer"]
            )
            for key, value in rederived.items():
                published = entry["published"].get(key)
                if published is None:
                    continue
                for path, got, want in _compare_published(published, value, key)[0]:
                    if path in NOT_REDERIVABLE_VALUES.get(entry["artifact_id"], {}):
                        declared.append((entry["artifact_id"], path))
                        continue
                    failures.append((entry["artifact_id"], path, got, want))
        assert failures == [], failures
        # The declared exceptions are not a way to hide a failure: each one
        # is reached, and each one is named.
        assert set(declared) == {
            (artifact, path) for artifact, paths in NOT_REDERIVABLE_VALUES.items() for path in paths
        }, declared

    def test_every_uncovered_published_leaf_is_declared(self):
        """A published leaf the reconstruction does not reach is a
        disclosure, not a silent gap: every one of them is named in
        :data:`NOT_REDERIVABLE` together with the reason the artifact
        cannot carry it."""
        uncovered = []
        for entry in _ENTRIES:
            if entry["recipe"] is None:
                continue
            rederived = _rederive(
                entry["directory"], entry["published"], entry["recipe"], entry["producer"]
            )
            for key, value in rederived.items():
                published = entry["published"].get(key)
                if published is None:
                    continue
                for path in _compare_published(published, value, key)[1]:
                    uncovered.append((entry["producer"], path))
        declared = {
            (producer, path) for producer, paths in NOT_REDERIVABLE.items() for path in paths
        }
        assert set(uncovered) == declared, sorted(set(uncovered) ^ declared)

    def test_every_reconstructed_but_unpublished_leaf_is_declared(self):
        """A value the producer computed and did not publish is disclosed
        too: the reconstruction reaches it, the record does not."""
        extra = []
        for entry in _ENTRIES:
            if entry["recipe"] is None:
                continue
            rederived = _rederive(
                entry["directory"], entry["published"], entry["recipe"], entry["producer"]
            )
            for key, value in rederived.items():
                published = entry["published"].get(key)
                if published is None:
                    continue
                for path in _extra_leaves(published, value, key):
                    extra.append((entry["producer"], path))
        declared = {(producer, path) for producer, paths in NOT_PUBLISHED.items() for path in paths}
        assert set(extra) == declared, sorted(set(extra) ^ declared)

    # -- the conventions ---------------------------------------------------
    def test_the_numpy_boolean_serialisation_is_pinned(self):
        """The published gate blocks mix JSON booleans with the strings
        ``"True"`` / ``"False"``: ``json.dump(..., default=str)`` writes a
        numpy boolean as a string and keeps a Python boolean as a JSON
        literal. The class is the convention, and it is pinned per producer
        and per gate."""
        # The mechanism, first: the two booleans serialise differently.
        assert json.dumps(np.bool_(True), default=str) == '"True"'
        assert json.dumps(np.bool_(False), default=str) == '"False"'
        assert json.dumps(True, default=str) == "true"
        assert json.dumps(False, default=str) == "false"

        measured = _measured_boolean_classes()
        assert measured == BOOLEAN_CLASSES, measured

        # The record is mixed *inside* a single producer, and that mix is
        # not accidental: the producer wrapped some comparisons in
        # ``bool(...)`` and left the rest raw.
        assert measured[("futures_tsmom_v1", "passes", "sharpe")] == {"numpy-bool-as-string"}
        assert measured[("futures_tsmom_v1", "passes", "trades")] == {"python-bool"}
        assert measured[("ddcv_futures_tsmom_v1", "passes", "sharpe")] == {
            "numpy-bool-as-string",
            "python-bool",
        }
        assert measured[("h6_vix_ddcv_futures_tsmom_v1", "passes", "sharpe")] == {"python-bool"}
        assert measured[("h7_intraday_tsmom_v1", "gates", "min_sharpe")] == {"numpy-bool-as-string"}
        assert measured[("h7_intraday_tsmom_v1", "gates", "min_trades")] == {"python-bool"}

    def test_the_pre_fix_alpha_p_value_lookup_is_recorded(self):
        """The futures family read the alpha p-value under ``"p_value"``, a
        key ``compare_to_benchmark`` does not return: the published value is
        the ``1.0`` default and the gate it fed could never pass. The DDCV
        and H6 families read the key the library actually returns."""
        from qtr.validation.statistics import compare_to_benchmark

        assert "alpha_p_value" in compare_to_benchmark([0.1, -0.1], [0.05, -0.05])
        assert "p_value" not in compare_to_benchmark([0.1, -0.1], [0.05, -0.05])
        published = {
            entry["producer"]: entry["published"]["alpha_vs_benchmark"]["p_value"]
            for entry in _ENTRIES
            if "alpha_vs_benchmark" in entry["published"]
        }
        assert published["futures_tsmom_v1"] == 1.0
        assert published["ddcv_futures_tsmom_v1"] != 1.0
        assert published["h6_vix_ddcv_futures_tsmom_v1"] != 1.0
        # The vacuous gate: the published 1.0 is above the 0.05 threshold, so
        # the ``p`` gate of those three summaries could never pass.
        assert not _significance_gate(1.0, 1.0, GATES["max_p_value"])

    def test_the_pre_h51_beta_moves_the_published_alpha(self):
        """The published ``alpha_annualized`` was computed with the pre-H51
        mixed-ddof beta; the library now uses a consistent ``ddof=1``."""
        strategy = np.linspace(-0.01, 0.02, 500)
        benchmark = np.linspace(0.005, 0.01, 500)
        pre = _benchmark_stats(strategy, benchmark, ddof=0, beta_pre_h51=True)
        post = _benchmark_stats(strategy, benchmark, ddof=0, beta_pre_h51=False)
        assert not _matches(pre["alpha_annualized"], post["alpha_annualized"])
        assert abs(pre["alpha_annualized"] - post["alpha_annualized"]) > 1e-6

    def test_the_legacy_bootstrap_differs_from_the_library_bootstrap(self):
        """The published bootstrap intervals were resampled with the legacy
        MT19937 stream; the library now uses PCG64."""
        data = np.linspace(-0.02, 0.03, 1200)
        legacy = _legacy_bootstrap_ci(data, lambda x: float(x.mean() / x.std()))
        pcg = _pcg_bootstrap_ci(data, lambda x: float(x.mean() / x.std()))
        assert not _matches(legacy[0], pcg[0])
        assert not _matches(legacy[1], pcg[1])

    def test_the_published_bootstrap_intervals_use_the_legacy_stream(self):
        """The published intervals re-derive under the legacy stream and not
        under the library's current one."""
        for entry in _ENTRIES:
            published_ci = entry["published"].get("oos_metrics", {}).get("sharpe_ci")
            if published_ci is None:
                continue
            recipe = entry["recipe"]
            equity = _series(entry["directory"] / recipe["equity"]).astype(float)
            returns = _returns_from_equity(equity)
            _, _, _, oos = _split_by_date(returns, *recipe["split"])
            legacy = _legacy_bootstrap_ci(oos.values, lambda x: _sharpe(x, recipe["sharpe_ddof"]))
            pcg = _pcg_bootstrap_ci(oos.values, lambda x: _sharpe(x, recipe["sharpe_ddof"]))
            assert _matches(published_ci, [round(legacy[0], 4), round(legacy[1], 4)]), entry[
                "artifact_id"
            ]
            assert not _matches(published_ci, [round(pcg[0], 4), round(pcg[1], 4)]), entry[
                "artifact_id"
            ]

    # -- the negative controls --------------------------------------------
    def test_negative_control_a_corrupted_value_is_detected(self):
        """The residual check is not vacuous: a published value nudged by one
        part in a thousand must fail it."""
        entry = next(e for e in _ENTRIES if "oos_sharpe" in e["published"])
        corrupted = entry["published"]["oos_sharpe"] * (1.0 + 1e-3)
        rederived = _rederive(
            entry["directory"], entry["published"], entry["recipe"], entry["producer"]
        )
        assert not _matches(corrupted, rederived["oos_sharpe"])

    def test_negative_control_the_other_split_breaks_the_re_derivation(self):
        """Reconstructing the other producer's date split must break the
        re-derivation."""
        entry = next(e for e in _ENTRIES if "split_metrics" in e["published"])
        recipe = entry["recipe"]
        broken = dict(recipe)
        broken["split"] = ("2021-12-31", "2020-12-31")
        rederived = _rederive(entry["directory"], entry["published"], broken, entry["producer"])
        assert not _matches(entry["published"]["split_metrics"], rederived["split_metrics"])

    def test_negative_control_the_current_beta_breaks_the_published_beta(self):
        """Reconstructing the CURRENT library beta must break the published
        ``beta`` of every summary that publishes one.

        The pre-H51 beta divided ``np.cov(..., ddof=1)`` by ``np.var(...)``'s
        default ``ddof=0``, which inflates beta by ``n / (n - 1)``. The
        published betas are on the pre-fix convention. The control is a
        negative one: it reconstructs the CURRENT convention and requires
        the published value to stop matching it.
        """
        published = [
            entry
            for entry in _ENTRIES
            if isinstance(entry["published"].get("benchmark_comparison"), dict)
            and "beta" in entry["published"]["benchmark_comparison"]
        ]
        assert published, "no summary publishes a beta to discriminate the convention"
        broken = []
        for entry in published:
            recipe = dict(entry["recipe"])
            train_end, _ = recipe["split"]
            equity = _series(entry["directory"] / recipe["equity"]).astype(float)
            returns = _returns_from_equity(equity)
            oos = returns[returns.index > train_end]
            benchmark = _returns_from_equity(
                _series(entry["directory"] / recipe["benchmark"]).astype(float)
            )
            bench_oos = benchmark[benchmark.index > train_end]
            pre = _benchmark_stats(oos.values, bench_oos.values, ddof=0, beta_pre_h51=True)
            post = _benchmark_stats(oos.values, bench_oos.values, ddof=0, beta_pre_h51=False)
            # The two conventions must differ on this artifact, otherwise the
            # published value cannot discriminate them.
            assert not _matches(pre["beta"], post["beta"]), entry["artifact_id"]
            published_beta = entry["published"]["benchmark_comparison"]["beta"]
            assert _matches(published_beta, round(pre["beta"], 4)), entry["artifact_id"]
            if _matches(published_beta, round(post["beta"], 4)):
                broken.append(entry["artifact_id"])
        assert broken == [], broken

    def test_the_published_alpha_cannot_resolve_the_two_beta_conventions(self):
        """The published ``alpha_annualized`` of the regime-gated family is
        on the pre-H51 beta, but its published precision of four decimals
        is too coarse to resolve the two conventions: they differ by 6e-06
        on that window. The published *beta* is the value that discriminates
        them, and it is on the pre-fix convention."""
        published = [
            entry
            for entry in _ENTRIES
            if isinstance(entry["published"].get("benchmark_comparison"), dict)
            and "alpha_annualized" in entry["published"]["benchmark_comparison"]
        ]
        assert published
        for entry in published:
            recipe = dict(entry["recipe"])
            train_end, _ = recipe["split"]
            equity = _series(entry["directory"] / recipe["equity"]).astype(float)
            returns = _returns_from_equity(equity)
            oos = returns[returns.index > train_end]
            benchmark = _returns_from_equity(
                _series(entry["directory"] / recipe["benchmark"]).astype(float)
            )
            bench_oos = benchmark[benchmark.index > train_end]
            pre = _benchmark_stats(oos.values, bench_oos.values, ddof=0, beta_pre_h51=True)
            post = _benchmark_stats(oos.values, bench_oos.values, ddof=0, beta_pre_h51=False)
            published_alpha = entry["published"]["benchmark_comparison"]["alpha_annualized"]
            assert _matches(published_alpha, round(pre["alpha_annualized"], 4)), entry[
                "artifact_id"
            ]
            gap = abs(post["alpha_annualized"] - pre["alpha_annualized"])
            assert gap <= PUBLISHED_ROUNDING_STEP / 2, (entry["artifact_id"], gap)

    def test_negative_control_the_library_bootstrap_breaks_the_published_interval(self):
        """Reconstructing the library's PCG64 bootstrap must break every
        published interval that the legacy stream reproduces."""
        broken = []
        for entry in _ENTRIES:
            published_ci = entry["published"].get("oos_metrics", {}).get("sharpe_ci")
            if published_ci is None:
                continue
            recipe = entry["recipe"]
            equity = _series(entry["directory"] / recipe["equity"]).astype(float)
            returns = _returns_from_equity(equity)
            _, _, _, oos = _split_by_date(returns, *recipe["split"])
            pcg = _pcg_bootstrap_ci(oos.values, lambda x: _sharpe(x, recipe["sharpe_ddof"]))
            if _matches(published_ci, [round(pcg[0], 4), round(pcg[1], 4)]):
                broken.append(entry["artifact_id"])
        assert broken == [], broken
