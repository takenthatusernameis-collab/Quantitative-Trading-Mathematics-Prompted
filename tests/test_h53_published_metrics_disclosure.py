"""H53 — enumerate the summaries that publish a `metrics` block and pin their keys.

Read-only audit of the frozen artifact record: every summary.json that
publishes a non-empty `metrics` block is named, and the set of keys it
publishes is pinned. No artifact is rewritten; no value is re-derived here
beyond the structural enumeration.
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".experiments" / "artifacts"


def _metric_summaries():
    out = []
    for p in sorted(ARTIFACTS.glob("*/summary.json")):
        d = json.loads(p.read_text())
        m = d.get("metrics")
        if isinstance(m, dict) and m:
            out.append((p.parent.name, sorted(m.keys())))
    return out


def test_h53_metrics_summary_count_pinned():
    rows = _metric_summaries()
    assert len(rows) == 29, len(rows)


def test_h53_metrics_keys_union_pinned():
    rows = _metric_summaries()
    keys = set()
    for _, ks in rows:
        keys.update(ks)
    expected = {
        "train_sharpe", "val_sharpe", "test_sharpe", "oos_sharpe",
        "profit_factor", "max_drawdown", "trades", "wf_stability",
        "worst_regime_sharpe", "regime_sharpes", "benchmark_p_value",
        "information_ratio", "ablations", "benchmark_alpha_annual",
        "cross_validation", "perturbation", "perturbation_min_ratio",
    }
    assert keys == expected, sorted(keys)


def test_h53_negative_control_missing_metrics():
    # A summary without a metrics block must not be counted.
    rows = _metric_summaries()
    names = {n for n, _ in rows}
    assert "h27_pnl_level" not in names
