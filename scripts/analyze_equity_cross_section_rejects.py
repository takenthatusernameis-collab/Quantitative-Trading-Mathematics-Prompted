#!/usr/bin/env python3
"""Quantify why the equity cross-section anomalies (H187-H197) are rejected.

The research register attributes the 11-cycle REJECT streak (H187-H197) to the
passive equal-weight long book dominating.  That claim is qualitative.  This
script turns it into hard numbers by reading the *committed* ``summary.json``
artifacts under ``.experiments/nf_runs/`` and decomposing every equity
cross-section run into:

* the strategy's out-of-sample Sharpe versus the passive-book Sharpe,
* the strategy's beta to the passive book (is it long-biased, market-neutral,
  or short-biased?),
* the annualised alpha and information ratio versus the passive book.

The decomposition answers the one question that decides the next research move:
is the reject streak a *benchmark construction artifact* (every strategy is
long-biased, so a net-long book wins by construction), or is it *genuine
mechanism weakness* (the strategies span the beta spectrum yet carry no alpha)?

The script is strictly read-only.  It opens committed artifacts, never writes
them, and changes no gate, verdict, threshold, or frozen number.  It is offline
and dependency-free (standard library only) so it runs in any checkout.

Usage
-----
    python scripts/analyze_equity_cross_section_rejects.py
    python scripts/analyze_equity_cross_section_rejects.py --repo-root /path/to/repo
    python scripts/analyze_equity_cross_section_rejects.py --json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = Path(".experiments") / "nf_runs"

# Beta bands used to label a run's net exposure to the passive equal-weight book.
# A long-short anomaly with beta ~ 0 is (near) market-neutral; beta ~ 1 is a
# long-biased book that merely carries less beta than the fully-invested passive
# portfolio.  The bands are descriptive, not a gate.
LONG_BIAS_MIN_BETA = 0.5
SHORT_BIAS_MAX_BETA = -0.5


def is_equity_cross_section(data: Any) -> bool:
    """Whether an artifact's ``data`` block identifies an equity cross-section.

    Equity cross-section runs (H187-H197) record a symbol list under
    ``universe_symbols``.  The commodity (CFTC) and crypto (Binance) runs record
    a generic ``universe`` instead and are therefore excluded.
    """
    return isinstance(data, dict) and "universe_symbols" in data


def exposure_class(beta: float | None) -> str:
    """Label a run's net exposure to the passive book from its beta."""
    if beta is None:
        return "unknown"
    if beta >= LONG_BIAS_MIN_BETA:
        return "long_biased"
    if beta <= SHORT_BIAS_MAX_BETA:
        return "short_biased"
    return "market_neutral"


def _finite(value: Any) -> float | None:
    """Return ``value`` as a finite float, else ``None``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if result == result and result not in (float("inf"), float("-inf")) else None


def _block_sharpe(block: Any) -> float | None:
    """Return the ``sharpe`` from a ``val``/``test``/``oos_val_test`` block, else None."""
    if isinstance(block, dict):
        return _finite(block.get("sharpe"))
    return None


def load_record(path: Path | str) -> dict[str, Any] | None:
    """Parse one ``summary.json`` into a normalised record, or ``None``.

    Returns ``None`` for unreadable files and for artifacts that are not equity
    cross-sections (so the caller can sweep the whole ``nf_runs`` directory).
    """
    path = Path(path)
    try:
        summary = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(summary, dict):
        return None
    data = summary.get("data")
    if not is_equity_cross_section(data):
        return None

    strategy = summary.get("oos_val_test") or {}
    benchmark = summary.get("benchmark_passive_equal_weight_long_oos") or {}
    comparison = summary.get("benchmark_comparison") or {}
    if not isinstance(strategy, dict) or not isinstance(benchmark, dict):
        return None

    beta = _finite(comparison.get("beta")) if isinstance(comparison, dict) else None
    gates_total = summary.get("gates_total")
    return {
        "run": summary.get("experiment") or summary.get("nf_id") or path.parent.name,
        "strategy_sharpe": _finite(strategy.get("sharpe")),
        "benchmark_sharpe": _finite(benchmark.get("sharpe")),
        "train_sharpe": _finite(summary.get("wf_train_sharpe")),
        "val_sharpe": _block_sharpe(summary.get("val")),
        "test_sharpe": _block_sharpe(summary.get("test")),
        "full_sample_sharpe": _block_sharpe(summary.get("full_sample")),
        "beta": beta,
        "information_ratio": (
            _finite(comparison.get("information_ratio")) if isinstance(comparison, dict) else None
        ),
        "alpha_annualized": (
            _finite(comparison.get("alpha_annualized")) if isinstance(comparison, dict) else None
        ),
        "verdict": summary.get("verdict"),
        "gates_passed": summary.get("gates_passed"),
        "gates_total": gates_total if isinstance(gates_total, int) else None,
    }


def collect_records(repo_root: Path | str) -> list[dict[str, Any]]:
    """Load every equity cross-section record under ``.experiments/nf_runs``."""
    root = Path(repo_root)
    runs_dir = root / RUNS_DIR
    if not runs_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for summary_path in sorted(runs_dir.glob("nf_*/summary.json")):
        record = load_record(summary_path)
        if record is not None:
            record["run"] = record["run"] or summary_path.parent.name
            record["beta_class"] = exposure_class(record["beta"])
            records.append(record)
    return records


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-run records into a root-cause summary.

    The summary is deliberately descriptive: it reports what the committed
    artifacts show and does *not* recompute any verdict or gate.
    """
    if not records:
        return {
            "n_runs": 0,
            "conclusion": "no equity cross-section artifacts found",
        }

    strategy = [r["strategy_sharpe"] for r in records if r["strategy_sharpe"] is not None]
    benchmark = [r["benchmark_sharpe"] for r in records if r["benchmark_sharpe"] is not None]
    train = [r["train_sharpe"] for r in records if r["train_sharpe"] is not None]
    val = [r["val_sharpe"] for r in records if r["val_sharpe"] is not None]
    test = [r["test_sharpe"] for r in records if r["test_sharpe"] is not None]
    full_sample = [r["full_sample_sharpe"] for r in records if r["full_sample_sharpe"] is not None]
    betas = [r["beta"] for r in records if r["beta"] is not None]
    iris = [r["information_ratio"] for r in records if r["information_ratio"] is not None]
    alphas = [r["alpha_annualized"] for r in records if r["alpha_annualized"] is not None]

    paired = [
        (r["strategy_sharpe"], r["benchmark_sharpe"])
        for r in records
        if r["strategy_sharpe"] is not None and r["benchmark_sharpe"] is not None
    ]
    n_beats = sum(1 for s, b in paired if s > b)
    n_negative_ir = sum(1 for x in iris if x < 0)
    n_negative_alpha = sum(1 for x in alphas if x < 0)
    n_positive_alpha = sum(1 for x in alphas if x > 0)

    beta_classes = [r["beta_class"] for r in records]
    n_long = beta_classes.count("long_biased")
    n_neutral = beta_classes.count("market_neutral")
    n_short = beta_classes.count("short_biased")

    strategy_median = _median(strategy)
    benchmark_median = _median(benchmark)
    train_median = _median(train)
    val_median = _median(val)
    test_median = _median(test)
    full_sample_median = _median(full_sample)
    alpha_median = _median(alphas)

    # In-sample (train) to out-of-sample (val/test/oos) decay per run, measured
    # only where both train and OOS are present.  A run "decays" when OOS < train.
    decay_pairs = [
        (r["train_sharpe"], r["strategy_sharpe"])
        for r in records
        if r["train_sharpe"] is not None and r["strategy_sharpe"] is not None
    ]
    n_train_to_oos_decay = sum(1 for train_s, oos_s in decay_pairs if oos_s < train_s)
    train_to_oos_decay = _median([oos_s - train_s for train_s, oos_s in decay_pairs])

    benchmark_dominates = bool(
        strategy_median is not None
        and benchmark_median is not None
        and strategy_median < benchmark_median
        and n_beats * 2 <= len(paired)
    )
    # A "uniform long-bias artifact" would require *every* run to be long-biased;
    # a single market-neutral or short-biased run falsifies it.
    uniform_long_bias_artifact = bool(betas) and all(
        r["beta_class"] == "long_biased" for r in records
    )
    genuine_negative_alpha = bool(alphas) and n_positive_alpha == 0

    return {
        "n_runs": len(records),
        "strategy_sharpe_median": strategy_median,
        "benchmark_sharpe_median": benchmark_median,
        "train_sharpe_median": train_median,
        "val_sharpe_median": val_median,
        "test_sharpe_median": test_median,
        "full_sample_sharpe_median": full_sample_median,
        "n_strategy_beats_benchmark": n_beats,
        "n_paired": len(paired),
        "n_negative_ir": n_negative_ir,
        "n_measured_ir": len(iris),
        "beta_min": min(betas) if betas else None,
        "beta_max": max(betas) if betas else None,
        "beta_median": _median(betas),
        "n_long_biased": n_long,
        "n_market_neutral": n_neutral,
        "n_short_biased": n_short,
        "alpha_median": alpha_median,
        "n_negative_alpha": n_negative_alpha,
        "n_positive_alpha": n_positive_alpha,
        "n_train_to_oos_decay": n_train_to_oos_decay,
        "n_train_measured": len(decay_pairs),
        "train_to_oos_decay_median": train_to_oos_decay,
        "benchmark_dominates": benchmark_dominates,
        "uniform_long_bias_artifact": uniform_long_bias_artifact,
        "genuine_negative_alpha": genuine_negative_alpha,
        "conclusion": _conclusion(
            benchmark_dominates=benchmark_dominates,
            uniform_long_bias_artifact=uniform_long_bias_artifact,
            genuine_negative_alpha=genuine_negative_alpha,
            n_neutral=n_neutral,
            n_short=n_short,
            n_long=n_long,
        ),
    }


def _conclusion(
    *,
    benchmark_dominates: bool,
    uniform_long_bias_artifact: bool,
    genuine_negative_alpha: bool,
    n_neutral: int,
    n_short: int,
    n_long: int,
) -> str:
    """Human-readable root-cause statement from the aggregate flags."""
    if uniform_long_bias_artifact:
        return (
            "benchmark construction artifact: every run is long-biased, so the "
            "net-long passive book wins by construction rather than by alpha"
        )
    parts = []
    if benchmark_dominates:
        parts.append(
            "the passive equal-weight book has a higher median OOS Sharpe than the anomalies"
        )
    if n_neutral or n_short:
        parts.append(
            f"exposure spans the beta spectrum ({n_long} long-biased / "
            f"{n_neutral} market-neutral / {n_short} short-biased), so the reject "
            "is not a uniform long-bias artifact"
        )
    if genuine_negative_alpha:
        parts.append("no run shows positive annualised alpha (genuine mechanism weakness)")
    if not parts:
        return "inconclusive: artifacts lack the fields needed for a decomposition"
    return "; ".join(parts)


def format_table(records: list[dict[str, Any]]) -> str:
    """Render the per-run decomposition as a fixed-width text table."""

    def cell(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:7.3f}"
        if value is None:
            return f"{'n/a':>7s}"
        return f"{str(value):>7s}"

    header = (
        f"{'run':52s} {'train':>7s} {'val':>7s} {'test':>7s} {'oosSh':>7s} {'beta':>7s} "
        f"{'IR':>7s} {'alpha':>7s} {'class':>14s} {'verd':>7s}"
    )
    lines = [header, "-" * len(header)]
    for r in records:
        run = str(r["run"])[:52]
        lines.append(
            f"{run:52s} {cell(r['train_sharpe'])} {cell(r['val_sharpe'])} "
            f"{cell(r['test_sharpe'])} {cell(r['strategy_sharpe'])} {cell(r['beta'])} "
            f"{cell(r['information_ratio'])} {cell(r['alpha_annualized'])} "
            f"{r['beta_class']:>14s} {str(r['verdict']):>7s}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help=f"repository root holding .experiments/nf_runs (default: {ROOT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the summary as JSON instead of a text table",
    )
    args = parser.parse_args(argv)

    records = collect_records(args.repo_root)
    summary = summarize(records)
    if not records:
        print(summary["conclusion"])
        return 1

    if args.json:
        print(json.dumps({"summary": summary, "runs": records}, indent=2, sort_keys=True))
        return 0

    print(format_table(records))
    print()
    print(f"runs: {summary['n_runs']}")
    print(
        "median OOS Sharpe: strategy "
        f"{summary['strategy_sharpe_median']:.3f} vs passive book "
        f"{summary['benchmark_sharpe_median']:.3f}"
    )
    train = summary["train_sharpe_median"]
    val = summary["val_sharpe_median"]
    test = summary["test_sharpe_median"]
    oos = summary["strategy_sharpe_median"]

    def fmt(x: float | None) -> str:
        return f"{x:.3f}" if x is not None else "n/a"

    print(
        "median Sharpe path: train "
        f"{fmt(train)} -> val {fmt(val)} -> test {fmt(test)} -> OOS {fmt(oos)}"
    )
    decay = summary["train_to_oos_decay_median"]
    print(
        f"train->OOS decay: {summary['n_train_to_oos_decay']}/{summary['n_train_measured']} "
        f"runs decay (OOS < train); median delta {fmt(decay)}"
    )
    print(
        f"beta range: [{summary['beta_min']:.3f}, {summary['beta_max']:.3f}] "
        f"({summary['n_long_biased']} long / {summary['n_market_neutral']} neutral / "
        f"{summary['n_short_biased']} short)"
    )
    print(
        f"negative IR: {summary['n_negative_ir']}/{summary['n_measured_ir']}; "
        f"alpha: {summary['n_negative_alpha']} negative / "
        f"{summary['n_positive_alpha']} positive"
    )
    print(f"conclusion: {summary['conclusion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
