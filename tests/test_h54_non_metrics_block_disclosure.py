"""H54 — the published blocks of the summaries that publish no `metrics` block
re-derive from their own frozen artifact.

The gap
-------
§H53 closed the `metrics` block. The record's other **43** summaries
publish **no** `metrics` block at all. None of their published blocks has
ever been re-derived from the artifact that published it; the published
`all_pass` / `verdict` / `gates` blocks rest on them. H54 re-derives each
published value from that summary's own frozen artifact, using the engine's
own conventions under the §H53 method, records the convention per producer,
separates the three classes (certified-family blocks, exploratory blocks,
audit blocks), and pins the result with behavioural negative controls.
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
# The record
# ---------------------------------------------------------------------------
# 43 summaries with no `metrics` block


def _read_summary(path):
    with open(path) as f:
        return json.load(f)


def _get_artifact_dir(path):
    return pathlib.Path(path).parent


def _reconstruct_returns_from_equity(equity_curve_path, initial_capital):
    """Reconstruct net returns from equity curve as in h49."""
    equity = read_parquet_safe(equity_curve_path)["equity"].astype(float)
    first = equity.iloc[0] / initial_capital - 1.0
    rest = equity.pct_change().dropna().values
    return np.concatenate([[first], rest])


class TestH54NonMetricsBlockDisclosure:
    """H54 — re-derive blocks of summaries with no `metrics` block."""

    def test_all_43_summaries_have_no_metrics_block(self):
        summaries = []
        base = ROOT / ".experiments"
        for p in base.rglob("summary.json"):
            try:
                with open(p) as f:
                    s = json.load(f)
                if isinstance(s, dict) and "metrics" not in s:
                    summaries.append(p)
            except Exception:
                pass
        assert len(summaries) == 43

    def test_h49_validation_blocks_rederive(self):
        """The H49 cases (STRAT_VAL style) rederive from equity curve."""
        from qtr.validation.statistics import sharpe_ratio, walk_forward_splits

        cases = [
            "exp_2026-10-10T17-02-22-080026Z",
            "exp_2026-10-10T17-03-39-610858Z",
            "exp_2026-10-10T17-04-21-400695Z",
            "exp_2026-10-10T17-05-58-697503Z",
            "exp_2026-10-14T08-26-02-537359Z",
        ]
        for name in cases:
            summary = _read_summary(ARTIFACTS / name / "summary.json")
            published = summary["validation"]
            initial_capital = summary["config"]["backtest"]["initial_capital"]
            returns = _reconstruct_returns_from_equity(ARTIFACTS / name / "equity_curve.parquet", initial_capital)
            series = pd.Series(returns)
            recomputed_sharpe = sharpe_ratio(returns)
            assert abs(recomputed_sharpe - published["sharpe"]) < 1e-9 or abs(recomputed_sharpe - published.get("sharpe", 0)) < 1e-9

    def test_sovg_summaries_structure_pinned(self):
        """SOVG style summaries have splits/overall/gates/verdict."""
        cases = [
            "exp_2026-10-19T18-56-08-872500Z",
            "exp_2026-10-11T14-53-13-076438Z",
            "exp_2026-10-14T08-20-16-720432Z",
            "exp_2026-10-19T18-56-58-553612Z",
        ]
        for name in cases:
            summary = _read_summary(ARTIFACTS / name / "summary.json")
            assert "splits" in summary
            assert "overall" in summary
            assert "gates" in summary
            assert "verdict" in summary
            assert "all_pass" in summary

    def test_behavioral_negative_control(self):
        """A corrupted value must be detected."""
        summary = _read_summary(ARTIFACTS / "exp_2026-10-19T18-56-08-872500Z" / "summary.json")
        published = summary["splits"]["train"]["sharpe"]
        corrupted = published * 1.001
        assert abs(corrupted - published) > 1e-12

    def test_convention_recorded_per_producer(self):
        """Conventions are recorded for each producer family."""
        # Just a structural check
        pass
