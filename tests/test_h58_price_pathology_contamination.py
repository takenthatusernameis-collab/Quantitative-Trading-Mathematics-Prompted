"""H58: a negative print in the committed price panels reaches the published
gate booleans.

The record's price panels are the only copy of the market data the published
numbers were computed from, and until now nothing screened them.  The screen
that H58 adds found one:

    **CL=F closes at -37.63 on 2020-04-20** in twenty-one committed
    ``prices.parquet`` panels (and the H8 ``opens.parquet`` carries
    CL=F = -14.0 on 2020-04-21): twenty-two committed files in twenty-one
    artifact directories.

That is the WTI front-month contract that expired into negative territory on
2020-04-20.  Yahoo's continuous series splices it in front of the next
contract, so the panel contains a price that crosses zero, and the engine's
``prices.pct_change()`` turns it into two garbage bars:

    2020-04-20:  (-37.63 - 18.27) / 18.27   = -305.966%
    2020-04-21:  ( 10.01 + 37.63) / -37.63  = -126.601%

(the second bar is garbage because the *base* is negative, which inverts the
sign of the price move as well).

The chain from that one cell to the published record is measured here, end to
end, from the committed artifacts alone:

1. the committed price panels carry exactly the disclosed non-positive
   closes -- no more, no fewer;
2. the committed *benchmark* equity curves carry the corresponding bar:
   fifteen published benchmarks lose 61.657% on 2020-04-20, which equals
   the mean of the five panel returns of that bar to **0.0** (the benchmark
   is the engine's own product of the contaminated panel);
3. in two families the committed *strategy* equity carries the bar too: a
   -130.10% single-bar loss, and the published equity curve goes **negative**
   (-463,814.84), which is why the published ``oos_max_dd`` is -150.96%;
4. the published statistics of eleven affected summaries re-derive from the
   committed equity curves to 1e-15, so the contaminated bars are demonstrably
   the ones the published numbers were computed from;
5. under the counterfactual -- *the two zero-crossing sessions contribute no
   return* -- **nine published ``ir`` gate booleans flip from True to
   False**.  Those gates are the only gates that pass in their families, and
   they pass only because the contaminated benchmark bar hands the strategy a
   +61.66% excess return.

Point 5 is the finding that matters: the contamination did not merely
distort numbers that were already failing, it **manufactured nine passing
gates** in the direction this repository cares about most -- a failure that
looks like a pass.

The blast radius is bounded and is measured here as well: every affected
summary is a REJECT, and the certified families (H10, H21, H22, H25) are
structurally immune because their panels cover 2024-10-13..2026-10-09 and
never contain 2020-04-20.  No certified number, no published verdict and no
gate that already failed is touched by this audit.

The root cause is fixed at the data boundary: ``qtr.data.fetcher`` now
refuses a panel that carries a non-positive close instead of handing it to the
engine, and ``qtr.data.non_positive_prices`` is the screen that does it.

Scope: read-only against the committed artifacts, plus the one library change
described above.  No published artifact, gate threshold, verdict or certified
number is modified, and no grid is re-run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qtr.data import non_positive_prices  # noqa: E402
from qtr.data.fetcher import DataCache, DataFetcher  # noqa: E402
from qtr.validation.statistics import compare_to_benchmark  # noqa: E402

ARTIFACTS = ROOT / ".experiments" / "artifacts"

HYPOTHESIS = "H58"

# --------------------------------------------------------------------------- #
# frozen constants (the measurement, not a parameter of the probe)           #
# --------------------------------------------------------------------------- #
CAPITAL = 1_000_000.0  # the runners' INITIAL_CAPITAL
TRAIN_END = pd.Timestamp("2019-12-31")  # the H4/H5/H6/H8 runners' TRAIN_END
MIN_INFORMATION_RATIO = 0.0  # the families' ``min_information_ratio`` gate

# The two sessions on which the WTI front-month contract's price crossed zero.
# The first carries the negative close; the second carries the negative
# *base*.  Both are artifacts of the splice, and both are removed by the
# counterfactual.
ZERO_CROSSING_SESSIONS = (pd.Timestamp("2020-04-20"), pd.Timestamp("2020-04-21"))

# The panel prints the screen found.  The value is the float32-rounded close.
NEGATIVE_CLOSE_SYMBOL = "CL=F"
NEGATIVE_CLOSE_DATE = pd.Timestamp("2020-04-20")
NEGATIVE_CLOSE_VALUE = -37.630001068115234

# The twenty committed ``prices.parquet`` panels that carry the print, and
# the H8 ``opens.parquet`` that carries the -14.0 open on the next session.
PANEL_FILES_WITH_NEGATIVE_CLOSE = 22

# The affected summaries: (artifact directory, strategy equity file,
# published information ratio, counterfactual information ratio).
#
# The published IR re-derives from the committed equity curves to 1e-15; the
# counterfactual IR is what the same computation returns when the two
# zero-crossing sessions contribute no return to either series.
#
# Nine of the eleven publish an ``ir`` gate of True and all nine flip to
# False; the remaining two publish a negative IR, which the contamination
# made *more* negative (they fail either way).
AFFECTED_FAMILIES = [
    (
        "exp_2026-10-10T21-58-28-353634Z",
        "ensemble_equity.parquet",
        -0.6399266589647274,
        -0.2660349072071191,
    ),
    (
        "exp_2026-10-10T21-59-16-546117Z",
        "ensemble_equity.parquet",
        -0.6399266589647274,
        -0.2660349072071191,
    ),
    (
        "exp_2026-10-10T22-59-01-182037Z",
        "ensemble_equity.parquet",
        0.33150832181222434,
        -0.41197920944771954,
    ),
    (
        "exp_2026-10-11T00-26-35-750834Z",
        "best_ddcv_equity.parquet",
        0.3943394550648367,
        -0.28500991820648836,
    ),
    (
        "exp_2026-10-11T00-34-05-381535Z",
        "best_ddcv_equity.parquet",
        0.3943394550648367,
        -0.28500991820648836,
    ),
    (
        "exp_2026-10-11T02-44-40-301520Z",
        "best_equity.parquet",
        0.35981069144282585,
        -0.3628828643247474,
    ),
    (
        "exp_2026-10-11T02-46-37-311994Z",
        "best_equity.parquet",
        0.35981069144282585,
        -0.3628828643247474,
    ),
    (
        "exp_2026-10-11T07-18-39-160945Z",
        "best_equity.parquet",
        0.35981069144282585,
        -0.3628828643247474,
    ),
    (
        "exp_2026-10-11T08-02-22-999214Z",
        "best_equity.parquet",
        0.35981069144282585,
        -0.3628828643247474,
    ),
    (
        "exp_2026-10-14T08-27-02-650342Z",
        "ensemble_equity.parquet",
        0.33150832181222434,
        -0.41197920944771954,
    ),
    (
        "exp_2026-10-11T15-21-31-333870Z",
        "best_equity_w0.5.parquet",
        0.5248619387848141,
        -0.017530752291060953,
    ),
]

# The families whose published ``ir`` gate passes and is decided by the
# contamination.
FLIPPED_GATE_FAMILIES = [row for row in AFFECTED_FAMILIES if row[2] > 0.0]

# The published benchmark bar of 2020-04-20: the mean of the five panel
# returns of that bar (the benchmark is the equal-weight buy-and-hold of the
# futures universe).
BENCHMARK_BAR_RETURN = -0.6165725404331034

# The published strategy bar of 2020-04-20 in the two contaminated families,
# and the published minimum of that equity curve (which is negative).
STRATEGY_BAR_RETURN = -1.3010291798708913
STRATEGY_EQUITY_MINIMUM = -463814.8436171526


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _summary(artifact: str) -> dict:
    with open(ARTIFACTS / artifact / "summary.json") as handle:
        return json.load(handle)


def _equity(artifact: str, name: str) -> pd.Series:
    return pd.read_parquet(ARTIFACTS / artifact / name).iloc[:, 0]


def _returns(equity: pd.Series) -> pd.Series:
    """The engine's net returns, recovered from a committed equity curve.

    The engine compounds ``(1 + net_returns)`` into the equity curve, so the
    bar-over-bar ratio of the curve *is* the net return; the first bar is the
    return against the initial capital.
    """
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / CAPITAL - 1.0
    return returns


def _oos(returns: pd.Series) -> pd.Series:
    return returns[returns.index > TRAIN_END]


def _information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    """The runners' IR: ``compare_to_benchmark`` over the OOS window.

    The H8 runner aligns the strategy to the benchmark's OOS length; the
    others pass the two OOS series as they are.  Aligning the tail is a
    no-op for the others (both series carry the same bars), so one
    implementation serves all eleven.
    """
    strategy_oos = _oos(strategy)
    benchmark_oos = _oos(benchmark)
    result = compare_to_benchmark(strategy_oos.values[-len(benchmark_oos) :], benchmark_oos.values)
    return float(result["information_ratio"])


def _counterfactual_returns(returns: pd.Series) -> pd.Series:
    """The counterfactual: the two zero-crossing sessions contribute no return.

    Setting the two bars to zero removes them from the return series; every
    later bar is a ratio of consecutive levels and is therefore unchanged.
    The published path is scaled by ``1 / (1 + r_contaminated)`` from the
    crossing onwards, and the counterfactual path is the same path with that
    factor removed.
    """
    cleaned = returns.copy()
    for session in ZERO_CROSSING_SESSIONS:
        if session in cleaned.index:
            cleaned.loc[session] = 0.0
    return cleaned


def _price_panels() -> list[Path]:
    return sorted(ARTIFACTS.glob("*/prices.parquet"))


# --------------------------------------------------------------------------- #
# the screen                                                                  #
# --------------------------------------------------------------------------- #
class TestTheScreen:
    """``qtr.data.non_positive_prices`` -- the screen the audit found."""

    def test_it_finds_a_negative_close_in_a_wide_panel(self):
        panel = pd.DataFrame(
            {"ES=F": [1.0, 2.0], "CL=F": [3.0, -37.63]},
            index=pd.to_datetime(["2020-04-17", "2020-04-20"]),
        )
        bad = non_positive_prices(panel)
        assert list(bad.columns) == ["symbol", "timestamp", "price"]
        assert len(bad) == 1
        assert bad.iloc[0]["symbol"] == "CL=F"
        assert bad.iloc[0]["timestamp"] == pd.Timestamp("2020-04-20")
        assert bad.iloc[0]["price"] == pytest.approx(-37.63)

    def test_it_finds_a_zero_close_in_a_long_panel(self):
        panel = pd.DataFrame(
            {"close": [1.0, 0.0]},
            index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
        )
        bad = non_positive_prices(panel)
        assert len(bad) == 1
        assert bad.iloc[0]["price"] == 0.0

    def test_a_clean_panel_is_clean(self):
        panel = pd.DataFrame(
            {"ES=F": [1.0, 2.0], "CL=F": [3.0, 4.0]},
            index=pd.to_datetime(["2020-04-17", "2020-04-20"]),
        )
        assert len(non_positive_prices(panel)) == 0

    def test_an_empty_panel_is_clean(self):
        assert len(non_positive_prices(pd.DataFrame())) == 0
        assert len(non_positive_prices(None)) == 0

    def test_the_screen_is_not_vacuous(self):
        """A negative control: the probe fires on a panel it must reject.

        Without this, "the screen found nothing" and "the screen is broken"
        would be indistinguishable.
        """
        poisoned = pd.DataFrame(
            {"CL=F": [18.27, -37.63, 10.01]},
            index=pd.to_datetime(["2020-04-17", "2020-04-20", "2020-04-21"]),
        )
        assert len(non_positive_prices(poisoned)) == 1
        assert len(non_positive_prices(poisoned.iloc[:1])) == 0


class TestTheFetcherRefuses:
    """The root-cause fix: the data boundary refuses the panel."""

    def _fetcher(self, tmp_path: Path) -> DataFetcher:
        return DataFetcher(cache=DataCache(cache_dir=tmp_path))

    def _frame(self, closes: list[float]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "volume": [100] * len(closes),
            },
            index=pd.to_datetime(["2020-04-17", "2020-04-20", "2020-04-21"][: len(closes)]),
        )

    def test_a_clean_panel_is_returned(self, tmp_path, monkeypatch):
        import sys
        import types

        frame = self._frame([18.27, 19.0, 10.01])

        class FakeTicker:
            def history(self, **kwargs):
                return frame

        fake_yf = types.ModuleType("yfinance")
        fake_yf.Ticker = lambda symbol: FakeTicker()
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

        result = self._fetcher(tmp_path).fetch_futures(
            ["CL=F"], "2020-04-01", "2020-05-01", use_cache=False
        )
        assert "close" in result["CL=F"].columns

    def test_a_negative_close_is_refused(self, tmp_path, monkeypatch):
        import sys
        import types

        frame = self._frame([18.27, -37.63, 10.01])

        class FakeTicker:
            def history(self, **kwargs):
                return frame

        fake_yf = types.ModuleType("yfinance")
        fake_yf.Ticker = lambda symbol: FakeTicker()
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

        with pytest.raises(ValueError, match="non-positive price"):
            self._fetcher(tmp_path).fetch_futures(
                ["CL=F"], "2020-04-01", "2020-05-01", use_cache=False
            )

    def test_the_cached_panel_is_refused_too(self, tmp_path, monkeypatch):
        """The cache is a second entry point into the same pipeline."""
        import sys
        import types

        frame = self._frame([18.27, -37.63, 10.01])

        class FakeTicker:
            def history(self, **kwargs):
                return frame

        fake_yf = types.ModuleType("yfinance")
        fake_yf.Ticker = lambda symbol: FakeTicker()
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

        cache = DataCache(cache_dir=tmp_path)
        cache.set("yahoo_futures", "CL=F", "2020-04-01", "2020-05-01", "1d", frame)
        with pytest.raises(ValueError, match="non-positive price"):
            DataFetcher(cache=cache).fetch_futures(
                ["CL=F"], "2020-04-01", "2020-05-01", use_cache=True
            )

    def test_the_message_names_the_symbol_date_and_value(self, tmp_path):
        frame = self._frame([18.27, -37.63, 10.01])
        with pytest.raises(ValueError) as excinfo:
            DataFetcher._reject_non_positive_prices("CL=F", frame)
        message = str(excinfo.value)
        assert "CL=F" in message
        assert "2020-04-20" in message
        assert "-37.63" in message


# --------------------------------------------------------------------------- #
# the record                                                                  #
# --------------------------------------------------------------------------- #
class TestTheCommittedPanels:
    """What the screen found in the committed record."""

    def test_the_non_positive_closes_are_exactly_the_disclosed_ones(self):
        found: dict[str, list[tuple[str, str, float]]] = {}
        for panel_path in sorted(ARTIFACTS.glob("*/*.parquet")):
            name = panel_path.name.lower()
            if "price" not in name and "open" not in name:
                continue
            frame = pd.read_parquet(panel_path)
            bad = non_positive_prices(frame)
            if len(bad):
                key = f"{panel_path.parent.name}/{panel_path.name}"
                found[key] = [
                    (row["symbol"], str(row["timestamp"]), float(row["price"]))
                    for _, row in bad.iterrows()
                ]
        assert len(found) == PANEL_FILES_WITH_NEGATIVE_CLOSE
        for key, rows in found.items():
            for symbol, timestamp, price in rows:
                assert symbol == NEGATIVE_CLOSE_SYMBOL
                assert timestamp in (
                    "2020-04-20 00:00:00",
                    "2020-04-21 00:00:00",
                )
                assert price <= 0.0
        assert found["exp_2026-10-10T22-59-01-182037Z/prices.parquet"] == [
            (NEGATIVE_CLOSE_SYMBOL, "2020-04-20 00:00:00", NEGATIVE_CLOSE_VALUE)
        ]

    def test_the_print_creates_the_two_garbage_bars(self):
        """The engine's own arithmetic on the committed panel."""
        panel = pd.read_parquet(ARTIFACTS / "exp_2026-10-10T22-59-01-182037Z" / "prices.parquet")
        returns = panel["CL=F"].pct_change()
        assert returns.loc[NEGATIVE_CLOSE_DATE] == pytest.approx(-3.059661, abs=1e-6)
        # the next bar's *base* is negative, which inverts the sign of the move
        assert returns.loc[pd.Timestamp("2020-04-21")] == pytest.approx(-1.266011, abs=1e-6)

    def test_no_other_committed_panel_has_a_non_positive_close(self):
        """The panels that carry no futures universe are clean."""
        for panel_path in _price_panels():
            frame = pd.read_parquet(panel_path)
            if "CL=F" not in frame.columns:
                assert len(non_positive_prices(frame)) == 0

    def test_the_other_price_pathology_is_disclosed_and_not_caught(self):
        """SVXY's unadjusted 1-for-5 reverse split, 2018-02-06.

        The screen added by this audit catches a *non-positive* price.  It
        cannot catch a split, because a split leaves every price positive and
        is only visible as a price-level discontinuity -- which is a market
        move and a corporate action at the same time.  The H17 panel carries
        the discontinuity (the close falls from 143.64 to 24.48 in one
        session, an 82.96% drop) and the published H17 benchmark equity
        carries the matching bar.

        This is disclosed here rather than fixed: the record is on a
        price-return basis (H57), and choosing between the price basis and
        the split-adjusted basis is a research decision, not a bug fix.
        """
        artifact = "exp_2026-10-13T21-51-45-034237Z"
        panel = pd.read_parquet(ARTIFACTS / artifact / "prices.parquet")
        returns = panel["SVXY"].pct_change()
        split = pd.Timestamp("2018-02-06")
        assert returns.loc[split] == pytest.approx(-0.8295739372998041, abs=1e-12)
        assert panel["SVXY"].loc[split] > 0.0  # the screen does not see it
        assert len(non_positive_prices(panel)) == 0
        benchmark = _equity(artifact, "benchmark_equity.parquet")
        assert benchmark.pct_change().loc[split] == pytest.approx(-0.8295739372998041, abs=1e-12)
        assert _summary(artifact)["all_pass"] is False


class TestTheContaminatedEquity:
    """The contaminated bars, in the committed equity curves."""

    def test_the_benchmark_bar_equals_the_mean_of_the_panel_returns(self):
        """The benchmark is the engine's product of the contaminated panel.

        The equality is exact (0.0), not approximate: the published benchmark
        equity is the committed panel run through the engine.
        """
        artifact = "exp_2026-10-10T22-59-01-182037Z"
        panel = pd.read_parquet(ARTIFACTS / artifact / "prices.parquet")
        benchmark = _equity(artifact, "benchmark_equity.parquet")
        panel_return = panel.pct_change().loc[NEGATIVE_CLOSE_DATE].mean()
        assert panel_return == pytest.approx(BENCHMARK_BAR_RETURN, abs=1e-15)
        assert benchmark.pct_change().loc[NEGATIVE_CLOSE_DATE] == pytest.approx(
            panel_return, abs=1e-15
        )

    def test_the_contaminated_benchmark_artifacts_are_exactly_the_disclosed_ones(self):
        contaminated: dict[str, float] = {}
        for path in sorted(ARTIFACTS.glob("*/*equity*.parquet")):
            frame = pd.read_parquet(path)
            series = frame.iloc[:, 0]
            if not isinstance(series.index, pd.DatetimeIndex) or len(series) < 3:
                continue
            if NEGATIVE_CLOSE_DATE not in series.index:
                continue
            returns = series.pct_change()
            if returns.loc[NEGATIVE_CLOSE_DATE] < -0.5:
                contaminated[f"{path.parent.name}/{path.name}"] = float(
                    returns.loc[NEGATIVE_CLOSE_DATE]
                )
        # fifteen published buy-and-hold benchmarks and two published strategy
        # equity curves carry the bar; nothing else in the record does.
        assert len(contaminated) == 17, contaminated
        benchmarks = {
            k: v for k, v in contaminated.items() if k.endswith("benchmark_equity.parquet")
        }
        strategies = {
            k: v for k, v in contaminated.items() if k.endswith("ensemble_equity.parquet")
        }
        assert len(benchmarks) == 15, benchmarks
        assert len(strategies) == 2, strategies
        for value in benchmarks.values():
            assert value == pytest.approx(BENCHMARK_BAR_RETURN, abs=1e-12)
        for value in strategies.values():
            assert value == pytest.approx(STRATEGY_BAR_RETURN, abs=1e-12)

    def test_two_strategy_equity_curves_carry_the_bar_and_go_negative(self):
        for artifact in ("exp_2026-10-10T21-58-28-353634Z", "exp_2026-10-10T21-59-16-546117Z"):
            equity = _equity(artifact, "ensemble_equity.parquet")
            returns = equity.pct_change()
            assert returns.loc[NEGATIVE_CLOSE_DATE] == pytest.approx(STRATEGY_BAR_RETURN, abs=1e-9)
            assert equity.min() == pytest.approx(STRATEGY_EQUITY_MINIMUM, abs=1e-2)
            assert equity.min() < 0.0

    def test_the_published_max_drawdown_is_the_contaminated_one(self):
        """A drawdown of more than 100% is a data artifact, not a loss."""
        for artifact in ("exp_2026-10-10T21-58-28-353634Z", "exp_2026-10-10T21-59-16-546117Z"):
            summary = _summary(artifact)
            assert summary["oos_max_dd"] < -1.0


class TestThePublishedNumbers:
    """The published statistics re-derive from the committed equity curves."""

    def test_the_published_information_ratio_re_derives(self):
        for artifact, strategy_file, published, _counterfactual in AFFECTED_FAMILIES:
            strategy = _returns(_equity(artifact, strategy_file))
            benchmark = _returns(_equity(artifact, "benchmark_equity.parquet"))
            assert _information_ratio(strategy, benchmark) == pytest.approx(published, abs=1e-12), (
                artifact
            )

    def test_the_published_ensemble_metrics_re_derive(self):
        """Sharpe, profit factor and max drawdown, from the equity curve."""
        from qtr.validation.statistics import sharpe_ratio

        for artifact in ("exp_2026-10-10T22-59-01-182037Z", "exp_2026-10-14T08-27-02-650342Z"):
            summary = _summary(artifact)
            equity = _equity(artifact, "ensemble_equity.parquet")
            returns = _returns(equity)
            oos = _oos(returns)
            assert sharpe_ratio(oos.values) == pytest.approx(summary["oos_sharpe"], abs=1e-12)
            gross_profit = oos[oos > 0].sum()
            gross_loss = abs(oos[oos < 0].sum())
            assert gross_profit / gross_loss == pytest.approx(summary["oos_pf"], abs=1e-12)
            curve = (1 + oos).cumprod()
            drawdown = (curve - curve.expanding().max()).min()
            assert drawdown == pytest.approx(summary["oos_max_dd"], abs=1e-12)

    def test_the_h8_benchmark_metrics_re_derive(self):
        """The published ``benchmark_sharpe`` and ``benchmark_max_dd``.

        ``benchmark_sharpe`` is the full-sample Sharpe of the committed
        benchmark on the record's sample-std convention (ddof=1), and
        ``benchmark_max_dd`` is the engine-style drawdown of the OOS window.
        """
        import numpy as np

        artifact = "exp_2026-10-11T15-21-31-333870Z"
        summary = _summary(artifact)
        equity = _equity(artifact, "benchmark_equity.parquet")
        returns = equity.pct_change()
        returns.iloc[0] = equity.iloc[0] / CAPITAL - 1.0
        sharpe = returns.mean() / returns.std(ddof=1) * np.sqrt(252)
        assert sharpe == pytest.approx(summary["benchmark_sharpe"], abs=1e-12)

        oos_equity = equity[equity.index > TRAIN_END]
        drawdown = (
            (oos_equity - oos_equity.expanding().max()) / oos_equity.expanding().max()
        ).min()
        assert drawdown == pytest.approx(summary["benchmark_max_dd"], abs=1e-12)

    def test_the_re_derivation_is_not_vacuous(self):
        """A nudged published number breaks the check."""
        artifact, strategy_file, published, _counterfactual = AFFECTED_FAMILIES[2]
        strategy = _returns(_equity(artifact, strategy_file))
        benchmark = _returns(_equity(artifact, "benchmark_equity.parquet"))
        nudged = published + 1e-6
        assert _information_ratio(strategy, benchmark) != pytest.approx(nudged, abs=1e-12)


class TestTheCounterfactual:
    """The counterfactual: the two zero-crossing sessions contribute no return."""

    def test_nine_published_gate_booleans_flip(self):
        assert len(FLIPPED_GATE_FAMILIES) == 9
        for artifact, _strategy_file, published, counterfactual in FLIPPED_GATE_FAMILIES:
            assert published > MIN_INFORMATION_RATIO
            assert counterfactual < MIN_INFORMATION_RATIO
            assert _summary(artifact)["passes"]["ir"] is True

    def test_the_counterfactual_moves_every_published_information_ratio(self):
        for artifact, strategy_file, published, counterfactual in AFFECTED_FAMILIES:
            strategy = _returns(_equity(artifact, strategy_file))
            benchmark = _returns(_equity(artifact, "benchmark_equity.parquet"))
            measured = _information_ratio(
                _counterfactual_returns(strategy),
                _counterfactual_returns(benchmark),
            )
            assert measured == pytest.approx(counterfactual, abs=1e-12), artifact
            assert measured != pytest.approx(published, abs=1e-12), artifact

    def test_the_counterfactual_is_not_vacuous(self):
        """The counterfactual must actually change the statistic."""
        artifact, strategy_file, published, _counterfactual = AFFECTED_FAMILIES[2]
        strategy = _returns(_equity(artifact, strategy_file))
        benchmark = _returns(_equity(artifact, "benchmark_equity.parquet"))
        cleaned = _counterfactual_returns(benchmark)
        assert benchmark.loc[list(ZERO_CROSSING_SESSIONS)].abs().sum() > 0.0
        assert cleaned.loc[list(ZERO_CROSSING_SESSIONS)].eq(0.0).all()


class TestTheBlastRadius:
    """What the contamination does *not* touch."""

    def test_every_affected_summary_is_a_reject(self):
        affected_dirs = {
            path.parent.name
            for path in ARTIFACTS.glob("*/prices.parquet")
            if len(non_positive_prices(pd.read_parquet(path))) > 0
        }
        assert len(affected_dirs) == 21
        checked = 0
        for artifact in affected_dirs:
            summary_path = ARTIFACTS / artifact / "summary.json"
            if not summary_path.exists():
                continue
            with open(summary_path) as handle:
                summary = json.load(handle)
            assert summary.get("all_pass") is False, artifact
            checked += 1
        assert checked >= 11

    def test_the_certified_families_are_structurally_immune(self):
        """H10, H21, H22 and H25 never see the crossing."""
        certified = {
            "H10": "exp_2026-10-11T17-41-18-169363Z",
            "H21": "exp_2026-10-13T23-27-52-101656Z",
            "H22": "exp_2026-10-14T18-52-08-943792Z",
            "H25": "exp_2026-10-14T20-08-34-613690Z",
        }
        for family, artifact in certified.items():
            panel = pd.read_parquet(ARTIFACTS / artifact / "prices.parquet")
            assert len(non_positive_prices(panel)) == 0, family
            assert NEGATIVE_CLOSE_DATE not in panel.index, family
            assert panel.to_numpy().min() > 0.0, family

    def test_the_verdict_is_the_expected_one(self):
        assert HYPOTHESIS == "H58"
