"""Guard the coverage gate: it must be declared, reproducible and complete.

The published record quotes ``python -m pytest --cov=qtr --cov-report=term-missing``
as showing ``src/qtr`` at 100% coverage. Until now that number was never
*measured* in the sessions that quoted it -- ``pytest-cov`` was not installed
-- so the claim was re-asserted from an argument about "no new branch is
introduced" rather than from the tool.

Two things are pinned here.

1. The gate itself is **declared** in ``pyproject.toml`` and therefore
   reproducible from a bare clone: branch coverage is required (not just
   statement coverage), the measured scope is the package, and the gate
   fails below 100%. The ``coverage`` configuration is additionally read
   back through the coverage API, so a text edit that the tool would
   ignore cannot pass for a committed configuration.

2. The gate is **complete**: every partial branch the first real
   measurement found is closed by a named test that exercises the
   corresponding defensive guard. Each guard below was previously
   unreachable-in-practice or never executed, which is exactly where a
   silent defect hides -- an untested guard is a guard nobody has ever
   seen work.

The measurement itself is a separate, explicit step (it runs the whole
suite and therefore cannot live inside the suite):

    python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing

"""

from __future__ import annotations

import pathlib
import sys
import types

import numpy as np
import pandas as pd
import pytest

from qtr.data.fetcher import DataCache, DataFetcher
from qtr.strategies import baselines
from qtr.tracking.experiment import Experiment, ExperimentTracker
from qtr.validation import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _section(text: str, header: str) -> str:
    """Return the body of a TOML section (everything up to the next header)."""
    start = text.index(f"[{header}]") + len(f"[{header}]")
    rest = text[start:]
    end = len(rest)
    for index, line in enumerate(rest.splitlines()):
        if line.startswith("["):
            end = index
            break
    return "\n".join(rest.splitlines()[:end])


# --------------------------------------------------------------------------- #
# 1. The gate is declared and reproducible
# --------------------------------------------------------------------------- #
def test_coverage_tool_is_declared_as_a_test_dependency():
    """pytest-cov must be an installable extra, or the gate cannot be run."""
    deps = _section(PYPROJECT.read_text(), "project.optional-dependencies")
    assert "pytest-cov" in deps, "pytest-cov must be declared under [project.optional-dependencies]"


def test_coverage_configuration_is_committed():
    """The [tool.coverage]* configuration must be committed so the quoted
    coverage command is reproducible from the repository."""
    pyproject = PYPROJECT.read_text()
    for header in ("tool.coverage.run", "tool.coverage.report"):
        assert f"[{header}]" in pyproject, f"missing committed [{header}] section"


def test_branch_coverage_is_required():
    """Statement coverage alone cannot see a guard that is never taken.

    The record's "100% coverage" was a statement-coverage figure; the
    eleven defects it hid are all branch-level, so branch coverage is part
    of the gate from now on.
    """
    section = _section(PYPROJECT.read_text(), "tool.coverage.run")
    assert "branch = true" in section, "coverage must be measured with branch=True"


def test_measured_scope_is_the_package():
    """The gate covers src/qtr, which is the scope the record quotes."""
    section = _section(PYPROJECT.read_text(), "tool.coverage.run")
    assert 'source = ["src/qtr"]' in section


def test_coverage_gate_fails_below_full_coverage():
    """A coverage gate that cannot fail is not a gate."""
    section = _section(PYPROJECT.read_text(), "tool.coverage.report")
    assert "fail_under = 100" in section


def test_coverage_tool_reads_the_committed_configuration():
    """The committed configuration must be the one the coverage tool uses.

    Reading the values back through the coverage API (rather than by
    matching text) means a section that the tool ignores -- a mis-spelled
    key, a section placed where coverage does not look -- cannot pass for
    a committed gate.
    """
    coverage = pytest.importorskip("coverage")
    cov = coverage.Coverage(config_file=str(PYPROJECT))
    assert cov.config.branch is True
    assert cov.config.fail_under == 100
    assert list(cov.config.source) == ["src/qtr"]


# --------------------------------------------------------------------------- #
# 2. qtr.data.fetcher -- partial branches
# --------------------------------------------------------------------------- #
def _fake_yfinance(monkeypatch, df: pd.DataFrame) -> None:
    """Install a yfinance stub whose Ticker always returns ``df``."""

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)


def test_fetch_futures_caches_every_symbol_it_downloads(monkeypatch, tmp_path):
    """A futures download must cache *each* symbol of the request.

    The cache write sits at the end of the per-symbol body, so the branch
    that returns to the loop head is only taken when a second symbol
    follows the first. A single-symbol request never exercises it, which
    is how a cache write that only happens for the last symbol of a
    universe would go unnoticed.
    """
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    _fake_yfinance(monkeypatch, df)

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    res = fetcher.fetch_futures(["ES=F", "CL=F"], "2020-01-01", "2020-01-02", use_cache=True)
    assert set(res) == {"ES=F", "CL=F"}
    assert not res["ES=F"].empty
    assert not res["CL=F"].empty

    # Both symbols were written to the cache, so a second request is served
    # from disk and downloads nothing.
    calls = []

    class CountingTicker:
        def history(self, **kw):
            calls.append(kw)
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: CountingTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    res2 = fetcher.fetch_futures(["ES=F", "CL=F"], "2020-01-01", "2020-01-02", use_cache=True)
    assert calls == []
    for symbol in ("ES=F", "CL=F"):
        pd.testing.assert_frame_equal(res2[symbol], res[symbol], check_names=False)


def test_fetch_futures_with_the_cache_disabled_leaves_the_cache_untouched(monkeypatch, tmp_path):
    """``use_cache=False`` must bypass the cache in both directions.

    A successful download must not populate the cache (otherwise the
    "disabled" flag only hides reads, and the next run would silently
    serve a stale frame from disk), and the next request must download
    again rather than reuse what was written.
    """
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    calls = []

    class CountingTicker:
        def history(self, **kw):
            calls.append(kw)
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: CountingTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    res = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-01-02", use_cache=False)
    assert not res["ES=F"].empty
    assert len(calls) == 1
    assert list(tmp_path.glob("*.parquet")) == []

    # A second request downloads again: nothing was written to the cache.
    res2 = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-01-02", use_cache=False)
    assert len(calls) == 2
    assert list(tmp_path.glob("*.parquet")) == []


def test_fetch_ccxt_paginates_until_the_window_is_exhausted(monkeypatch, tmp_path):
    """The pagination loop must end on the requested window, not on a page.

    ``fetch_ccxt`` has three ways out of its fetch loop: an empty page, a
    short page, and the ``while`` condition becoming false. The last one
    is the normal end of a well-formed download (the exchange answered with
    a full page and the remaining window is already covered), and it is
    the one this test drives: a full 1000-row page whose last bar is past
    the requested end.

    The assertions pin both halves of that behaviour -- the full page is
    *not* re-requested (the window was exhausted, so exactly one call is
    made) and every bar inside the requested window is returned.
    """
    start = "2020-01-01"
    end = "2020-01-02"
    since = int(pd.Timestamp(start).timestamp() * 1000)
    end_ms = int(pd.Timestamp(end).timestamp() * 1000)

    # 1000 bars, spaced widely enough that the page covers more than a
    # day, so the last bar is past `end` for any calendar-day length.
    step_ms = 200_000
    timestamps = [since + i * step_ms for i in range(1000)]
    assert len(timestamps) == 1000
    assert timestamps[-1] + 1 >= end_ms, "the page must reach past the end of the window"

    calls = []

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            calls.append(since)
            return [[ts, 1.0, 2.0, 0.5, 1.5, 100.0] for ts in timestamps]

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], start, end, use_cache=False)

    assert calls == [since], "a full page must not be re-requested once the window is exhausted"
    df = res["BTC/USDT"]
    expected = sum(1 for ts in timestamps if pd.Timestamp(ts, unit="ms") <= pd.Timestamp(end))
    assert expected > 0
    assert len(df) == expected
    assert df.index.is_monotonic_increasing


# --------------------------------------------------------------------------- #
# 3. qtr.strategies.baselines -- partial branches
# --------------------------------------------------------------------------- #
def test_momentum_without_negative_symbols_leaves_the_short_leg_empty():
    """With no negative momentum there is no short leg to build.

    The cross-sectional momentum builder only assigns the short leg when
    at least one symbol has negative momentum. A universe that is entirely
    non-negative (a flat or rising market) must leave the short leg
    unassigned -- and must still advance to the next bar.
    """
    idx = pd.date_range("2020-01-01", periods=60, freq="D")
    data = np.zeros((60, 3))
    for i in range(60):
        data[i, 0] = 0.01 * i  # up
        data[i, 1] = 0.005 * i  # up
        data[i, 2] = 100.0  # flat (positive price => zero, not NaN, momentum)
    prices = pd.DataFrame(data, index=idx, columns=["S0", "S1", "S2"])

    sig = baselines.momentum_signals(prices, lookback=30, skip=5, long_only=False)
    assert sig.shape == prices.shape

    momentum = prices.pct_change(30).shift(5)
    # The flat symbol has zero momentum: it is neither a long nor a short.
    assert (momentum["S2"].dropna() == 0.0).all()
    assert (sig["S2"] == 0.0).all()
    # The two rising symbols split the long leg equally.
    valid = momentum.dropna().index
    assert (sig.loc[valid, "S0"] == 0.5).all()
    assert (sig.loc[valid, "S1"] == 0.5).all()


def test_vol_scale_leaves_a_position_unscaled_when_the_volatility_is_not_positive():
    """A non-positive realized volatility carries no risk information.

    ``_vol_scale`` is the volatility-targeting multiplier. With a
    non-positive volatility the position must be left unscaled rather than
    amplified (or made to divide by zero). The guard used to live inline
    in ``time_series_momentum_signals``, where the realized-volatility
    series is sanitized to be strictly positive by construction -- so the
    guard could never fire and was never executed by any test.
    """
    assert baselines._vol_scale(0.0, 0.15) == 1.0
    assert baselines._vol_scale(-0.2, 0.15) == 1.0
    # A positive volatility scales towards the target and is capped at 2x.
    assert baselines._vol_scale(0.30, 0.15) == pytest.approx(0.5)
    assert baselines._vol_scale(0.075, 0.15) == pytest.approx(2.0)
    assert baselines._vol_scale(0.01, 0.15) == 2.0


# --------------------------------------------------------------------------- #
# 4. qtr.tracking.experiment -- partial branches
# --------------------------------------------------------------------------- #
def test_start_experiment_uses_the_caller_supplied_seeds(tmp_path):
    """An explicit seed set must be recorded verbatim, not replaced by the
    default. The default only applies when the caller supplies none."""
    tracker = ExperimentTracker(log_dir=tmp_path / "logs")
    tracker.start_experiment("exp", random_seeds={"numpy": 7, "python": 11})
    assert tracker.current_experiment is not None
    assert tracker.current_experiment.random_seeds == {"numpy": 7, "python": 11}
    tracker.finish_experiment()


def test_log_artifact_without_metadata_writes_no_sidecar(tmp_path):
    """Logging an artifact without metadata must not leave a sidecar file.

    The sidecar is what carries the artifact's metadata, so writing an
    empty one would publish a misleading record; and a stray file per
    artifact would accumulate in the log directory.
    """
    tracker = ExperimentTracker(log_dir=tmp_path / "logs")
    tracker.start_experiment("exp")
    artifact = tmp_path / "f.txt"
    artifact.write_text("hi")

    file_hash = tracker.log_artifact("a", artifact)
    assert len(file_hash) == 16
    assert list((tmp_path / "logs").glob("*.meta.json")) == []
    tracker.finish_experiment()


def test_experiment_constructor_preserves_existing_metadata(tmp_path):
    """Re-opening an experiment must not truncate its metadata.

    The constructor writes an empty metadata file only when none exists;
    an existing file is left alone, so a second process attaching to the
    same experiment cannot wipe the first one's results.
    """
    first = Experiment("exp", base_dir=tmp_path)
    first.log_metadata(key="value")

    second = Experiment("exp", base_dir=tmp_path)
    assert second.load_metadata() == {"key": "value"}


# --------------------------------------------------------------------------- #
# 5. qtr.validation.statistics -- partial branches
# --------------------------------------------------------------------------- #
def test_walk_forward_drops_a_fold_with_an_empty_test_side():
    """A gap wider than the window leaves no test bars, so no fold is emitted.

    Emitting a fold with an empty test side would make a downstream
    stability score look like a measurement when it is an artefact.
    """
    assert st.walk_forward_splits(100, n_splits=5, gap=1000) == []


def test_walk_forward_drops_a_fold_with_an_empty_train_side():
    """A training ratio that rounds the train side down to zero yields no
    fold rather than a fold with no training data."""
    assert st.walk_forward_splits(10, n_splits=5, train_ratio=0.1) == []


def test_purged_kfold_drops_a_fold_with_no_training_data():
    """A purge wider than the series leaves nothing to train on.

    The purge is the mechanism that keeps training data away from the test
    fold; when it is wide enough to cover the whole series there is no
    admissible training set and the fold must be dropped.
    """
    assert st.purged_kfold_splits(4, n_splits=2, purge=10) == []


def test_combinatorial_purged_cv_drops_a_fold_with_no_training_data():
    """Same rule for the combinatorial scheme: no admissible training set
    means no split, not an empty one."""
    assert st.combinatorial_purged_cv(4, n_splits=2, n_test_splits=1, purge=10) == []
