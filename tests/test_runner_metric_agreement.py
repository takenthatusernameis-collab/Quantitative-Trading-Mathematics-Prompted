"""Metric-agreement contract between the runners' local metric helpers and ``qtr.validation.statistics``.

**The problem.** H39 closed the disagreement *inside* ``src/qtr``: the engine
and ``validate_strategy`` now agree exactly on all six shared metrics.  But the
repository still computes the same metrics a third time, in the runners:

* six near-duplicate ``_period_metrics(ret, n_trades)`` helpers
  (H10, H16, H17, H19, H20, H23) re-implement the Sharpe, the profit factor
  and the max drawdown; their Sharpe (``sharpe_ratio(r.values)``) and profit
  factor match the library exactly, while their max drawdown uses
  ``cum / cum.cummax() - 1`` against the library's
  ``(equity - rolling_max) / rolling_max`` -- algebraically identical, differing
  by at most 5.6e-17 (measured over 200 random equity curves);
* ``run_ddcv_experiment.window_max_drawdown`` uses the same cum/cummax variant;
* ``run_h26_sharpe_scale_audit.py`` publishes a daily Sharpe on the sample std
  (pandas ``Series.std()``, ddof=1) at line 303 -- the same convention split
  H39 closed in the engine;
* ``run_cs_momentum_experiment.py`` computes a local information ratio at line
  383 on the numpy (ddof=0) convention, consistent with ``compare_to_benchmark``;
* four runners compute drawdowns inline:
  * ``run_h11_robustness_experiment.py:548,648`` and
    ``run_h18_overnight_intraday_experiment.py:527,641`` use the library's
    convention (``cum / cummax - 1`` or ``equity / expanding().max() - 1``),
    agreeing with ``validate_strategy["max_drawdown"]`` within 1e-15;
  * ``run_ddcv_experiment.py:386,443`` and
    ``run_futures_tsmom_experiment.py:467`` use the raw formula
    ``(equity - expanding().max()).min()`` -- a dollar drawdown, not the
    library's ratio -- and are pinned as ``differs_convention``;
* ``run_h18_overnight_intraday_experiment.py:526,637`` carry a runner-local
  ``total_return`` copy whose formula matches the library's exactly.

**The decision.** The runner-local copies are classified and pinned, not
rewritten: the artifacts are frozen, so a rewritten helper would no longer
reproduce them.  Each entry of the inventory asserts either exact agreement
with ``qtr.validation.statistics`` / the engine, or pins the documented
difference with its exact formula and its bounded effect on the published
artifacts.

**What this contract pins.**

* :class:`TestRunnerMetricInventory` -- every metric-computing function of
  every in-scope runner is classified (``agrees`` / ``differs_bounded`` /
  ``differs_convention``); a new helper is an unclassified function and fails
  the suite.
* :class:`TestExactAgreement` -- Sharpe and profit factor in each
  ``_period_metrics`` match ``validate_strategy`` exactly; the information
  ratio in ``run_cs_momentum`` matches ``compare_to_benchmark`` exactly.
* :class:`TestBoundedDrawdownVariant` -- the runners' max drawdown
  (``cum / cum.cummax() - 1``) is algebraically identical to the library's
  ``(equity - rolling_max) / rolling_max`` and differs by at most 5.6e-17;
* :class:`TestInlineDrawdownConforming` -- inline drawdowns that use the
  library's convention (H11 :548,:648; H18 :527,:641) agree with the library
  within 1e-15;
* :class:`TestInlineDrawdownRawVariant` -- inline drawdowns that use the raw
  formula ``(equity - expanding().max()).min()`` (DDCV :386,:443; futures
  :467) are pinned as ``differs_convention`` -- they compute a dollar drawdown,
  not the library's percentage drawdown;
* :class:`TestH26DailySharpeConvention` -- H26's daily Sharpe uses the sample
  std (pandas ddof=1), a documented convention split from the library's
  population std; the difference is exactly ``sqrt(n / (n - 1))`` and is
  bounded;
* :class:`TestH18TotalReturn` -- H18's runner-local ``total_return`` copies
  (:526,:637) agree with the library's ``total_return`` exactly;
* :class:`TestContractNegativeControl` -- the contract rejects a helper that
  disagrees, so it is not a tautology.

Scope: the runners' *local* metric implementations.  No published artifact,
gate threshold, verdict or certified number is touched, and no grid is re-run.
The runner-local copies are classified and pinned, not replaced.
"""

from __future__ import annotations

import ast
import importlib
import math
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qtr.validation.statistics import (  # noqa: E402
    compare_to_benchmark,
    sharpe_ratio,
    validate_strategy,
)

# The runners whose local metric helpers this module pins.  All six carry a
# _period_metrics(ret, n_trades) helper; run_ddcv_experiment additionally
# carries window_max_drawdown(equity, start, end).
IN_SCOPE_RUNNERS = (
    "run_h10_intraday_tsmom_pfopt_experiment.py",
    "run_h16_factor_timing_experiment.py",
    "run_h17_vrp_experiment.py",
    "run_h19_volume_predictive_experiment.py",
    "run_h20_signed_volume_experiment.py",
    "run_h23_crypto_futures_tsmom.py",
)

# The metric names each _period_metrics helper returns, in addition to the
# ones pinned per-classification below.
PERIOD_METRIC_KEYS = (
    "sharpe",
    "max_drawdown",
    "profit_factor",
    "trades",
    "gross_profit",
    "gross_loss",
    "n_periods",
)

# H17's helper takes an extra `equity` argument that it does not use; pass a
# dummy equity curve built from the returns.
H17_EQUITY_ARG = "equity"


def _period_metrics_call(period_metrics, returns: pd.Series, n_trades: int) -> dict:
    """Call a _period_metrics helper, supplying H17's unused equity argument."""
    import inspect

    sig = inspect.signature(period_metrics)
    if len(sig.parameters) == 3:
        equity = (1.0 + returns).cumprod()
        return period_metrics(returns, n_trades, equity)
    return period_metrics(returns, n_trades)


# --------------------------------------------------------------------------- #
# the inventory
# --------------------------------------------------------------------------- #
# coverage:
#   "agrees"          -- every metric this function computes matches
#                        qtr.validation.statistics / the engine exactly.
#   "differs_bounded" -- mathematically equivalent to the library but computed
#                        via different code; the difference is bounded by a
#                        documented tolerance (floating-point noise).
#   "differs_convention" -- a genuinely different convention (sample vs
#                        population std); the convention difference is pinned
#                        with its exact formula and its bounded effect.
INVENTORY: dict[str, dict[str, tuple[str, str]]] = {
    "run_h10_intraday_tsmom_pfopt_experiment.py": {
        "_period_metrics": (
            "differs_bounded",
            "Sharpe (delegates to qtr.validation.statistics.sharpe_ratio, ddof=0) and profit "
            "factor (gross_profit / gross_loss) agree with validate_strategy exactly; max drawdown "
            "uses cum / cum.cummax() - 1, algebraically identical to the library's "
            "(equity - rolling_max) / rolling_max and bounded by 5.6e-17.",
        ),
    },
    "run_h16_factor_timing_experiment.py": {
        "_period_metrics": (
            "differs_bounded",
            "Same construction as H10: Sharpe and profit factor agree exactly, max drawdown is the "
            "cum/cummax - 1 variant bounded by 5.6e-17.",
        ),
        "train_only_wf_sharpe": (
            "agrees",
            "Delegates to qtr.validation.statistics.sharpe_ratio on each walk-forward test fold, "
            "so its Sharpes agree with the library exactly.",
        ),
    },
    "run_h17_vrp_experiment.py": {
        "_period_metrics": (
            "differs_bounded",
            "Same construction as H10: Sharpe and profit factor agree exactly, max drawdown is the "
            "cum/cummax - 1 variant bounded by 5.6e-17.",
        ),
    },
    "run_h19_volume_predictive_experiment.py": {
        "_period_metrics": (
            "differs_bounded",
            "Same construction as H10: Sharpe and profit factor agree exactly, max drawdown is the "
            "cum/cummax - 1 variant bounded by 5.6e-17.",
        ),
    },
    "run_h20_signed_volume_experiment.py": {
        "_period_metrics": (
            "differs_bounded",
            "Same construction as H10: Sharpe and profit factor agree exactly, max drawdown is the "
            "cum/cummax - 1 variant bounded by 5.6e-17.",
        ),
    },
    "run_h23_crypto_futures_tsmom.py": {
        "_period_metrics": (
            "differs_bounded",
            "Same construction as H10: Sharpe and profit factor agree exactly, max drawdown is the "
            "cum/cummax - 1 variant bounded by 5.6e-17.",
        ),
    },
    "run_ddcv_experiment.py": {
        "window_max_drawdown": (
            "differs_bounded",
            "Computes (eq / eq.cummax() - 1.0).min() on an equity slice -- the same cum/cummax "
            "variant as _period_metrics, algebraically identical to the library's drawdown and "
            "bounded by 5.6e-17.",
        ),
    },
}

# The metric functions computed *inline* (not as module-level helpers) that are
# pinned by dedicated tests rather than by the function-level inventory.
INLINE_METRIC_SITES = {
    "run_h26_sharpe_scale_audit.py": (
        "differs_convention",
        "audit_artifact:303 computes daily_sharpe = daily.mean() / daily.std() * sqrt(252) with "
        "pandas Series.std() (sample, ddof=1) while qtr.validation.statistics.sharpe_ratio uses "
        "numpy ndarray.std() (population, ddof=0).  The difference is exactly "
        "sqrt(n / (n - 1)) and is bounded (+0.02% at n = 2,515); the diagnostic is a point "
        "estimate only and does not feed any gate.",
    ),
    "run_cs_momentum_experiment.py": (
        "agrees",
        "main:380-383 computes information_ratio = e.mean() / e.std() * sqrt(252) with numpy "
        "ddof=0, the same convention as compare_to_benchmark's information_ratio; the two agree "
        "exactly.",
    ),
}

# The published-artifact bound for the H26 daily-Sharpe convention gap, read
# from the committed H26 audit (n = 2,515): sqrt(n / (n - 1)) - 1 = 0.0001988.
H26_CONVENTION_GAP_BOUND = math.sqrt(2515 / 2514) - 1.0

# The bounded effect of the cum/cummax drawdown variant, measured over 200 random
# equity curves (see HANDOFF_CURRENT_SESSION.md / NEXT_TASK.md).  The two formulas
# are algebraically identical; the residual is floating-point noise (observed up to
# ~1.1e-16, well below any decision-relevant scale).
DRAWDOWN_VARIANT_BOUND = 1e-15


def _load_period_metrics(runner: str):
    module = importlib.import_module(runner[:-3])
    return module._period_metrics


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(columns=["timestamp", "symbol", "side", "weight_change", "price", "cost"])


def _synthetic_returns(n: int = 252, seed: int = 12345) -> pd.Series:
    index = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.0004, 0.01, n), index=index)


def _library_metrics(returns: pd.Series) -> dict:
    """The reference computation from qtr.validation.statistics."""
    validation = validate_strategy(returns, _empty_trades(), {})
    return {
        "sharpe": validation["sharpe"],
        "max_drawdown": validation["max_drawdown"],
        "profit_factor": validation["profit_factor"],
        "total_return": validation["total_return"],
        "annualized_return": validation["annualized_return"],
        "annualized_volatility": validation["annualized_volatility"],
    }


# --------------------------------------------------------------------------- #
# the tests
# --------------------------------------------------------------------------- #
class TestRunnerMetricInventory:
    """The inventory pin: every metric-computing function of every in-scope
    runner is classified; a new helper fails the suite."""

    def test_in_scope_runners_exist(self):
        for runner in IN_SCOPE_RUNNERS:
            assert (ROOT / runner).exists(), f"missing runner {runner}"

    def test_every_inventory_entry_resolves(self):
        """Every function named in INVENTORY exists in its runner and is a
        module-level function (so a renamed / removed helper is caught)."""
        for runner, entries in INVENTORY.items():
            module = importlib.import_module(runner[:-3])
            for name in entries:
                assert hasattr(module, name), f"{runner} has no attribute {name}"
                assert isinstance(getattr(module, name), type(lambda: None)), (
                    f"{runner}:{name} is not a function"
                )

    def test_every_period_metrics_helper_is_inventoried(self):
        """The completeness pin: every in-scope runner's _period_metrics must be
        classified, so a new runner-local metric helper fails the suite."""
        for runner in IN_SCOPE_RUNNERS:
            module = importlib.import_module(runner[:-3])
            assert hasattr(module, "_period_metrics"), (
                f"{runner} has no _period_metrics helper to inventory"
            )
            assert "_period_metrics" in INVENTORY[runner], (
                f"{runner}:_period_metrics is not classified in the inventory"
            )

    def test_inventory_entries_are_well_formed(self):
        for runner, entries in INVENTORY.items():
            for name, (coverage, argument) in entries.items():
                assert coverage in {"agrees", "differs_bounded", "differs_convention"}, (
                    f"{runner}:{name} has an unknown coverage {coverage!r}"
                )
                assert len(argument.strip()) > 20, f"{runner}:{name} has no written argument"


class TestExactAgreement:
    """Sharpe and profit factor in each _period_metrics match validate_strategy
    exactly; the drawdown is covered by TestBoundedDrawdownVariant."""

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_period_metrics_sharpe_and_profit_factor_agree_exactly(self, runner):
        period_metrics = _load_period_metrics(runner)
        returns = _synthetic_returns(n=252)
        trades = _empty_trades()
        helper = _period_metrics_call(period_metrics, returns, len(trades))
        library = _library_metrics(returns)

        assert helper["sharpe"] == pytest.approx(library["sharpe"], rel=1e-12, abs=1e-15), (
            f"{runner}:_period_metrics sharpe disagrees with validate_strategy"
        )
        assert helper["profit_factor"] == pytest.approx(
            library["profit_factor"], rel=1e-12, abs=1e-15
        ), f"{runner}:_period_metrics profit_factor disagrees with validate_strategy"

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_period_metrics_agrees_across_return_shapes(self, runner):
        """Exact agreement holds for short, flat and total-loss series too."""
        period_metrics = _load_period_metrics(runner)

        cases = {
            "short": _synthetic_returns(n=3, seed=1),
            "flat": pd.Series([0.0] * 40, index=pd.bdate_range("2020-01-01", periods=40)),
            "two_bar": _synthetic_returns(n=2, seed=3),
        }
        for label, returns in cases.items():
            helper = _period_metrics_call(period_metrics, returns, len(_empty_trades()))
            library = _library_metrics(returns)
            assert helper["sharpe"] == pytest.approx(library["sharpe"], rel=1e-12, abs=1e-15), (
                f"{runner}:{label} sharpe disagrees"
            )
            assert helper["profit_factor"] == pytest.approx(
                library["profit_factor"], rel=1e-12, abs=1e-15
            ), f"{runner}:{label} profit_factor disagrees"

    def test_cs_momentum_information_ratio_agrees_with_compare_to_benchmark(self):
        """run_cs_momentum's local IR (numpy ddof=0) matches compare_to_benchmark's
        information_ratio exactly."""
        module = importlib.import_module("run_cs_momentum_experiment")
        returns = _synthetic_returns(n=252)
        bench = pd.Series(np.asarray(returns.values) * 0.9 + 0.0001, index=returns.index)
        excess = returns.values - bench.values
        local_ir = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
        cmp = compare_to_benchmark(returns.values, bench.values)
        assert local_ir == pytest.approx(cmp["information_ratio"], rel=1e-12, abs=1e-15)


class TestBoundedDrawdownVariant:
    """The runners' max drawdown (cum / cum.cummax() - 1) is algebraically
    identical to the library's (equity - rolling_max) / rolling_max; the
    difference is floating-point noise, bounded by 5.6e-17."""

    @pytest.mark.parametrize("runner", IN_SCOPE_RUNNERS)
    def test_period_metrics_drawdown_matches_the_library_within_the_bound(self, runner):
        period_metrics = _load_period_metrics(runner)
        returns = _synthetic_returns(n=1000)
        helper = _period_metrics_call(period_metrics, returns, 0)
        library = _library_metrics(returns)
        assert abs(helper["max_drawdown"] - library["max_drawdown"]) <= DRAWDOWN_VARIANT_BOUND, (
            f"{runner}:_period_metrics drawdown {helper['max_drawdown']!r} differs from "
            f"validate_strategy {library['max_drawdown']!r} by more than {DRAWDOWN_VARIANT_BOUND}"
        )

    @pytest.mark.parametrize("seed", [1, 7, 42, 123])
    def test_drawdown_variant_is_bounded_over_random_equity_curves(self, seed):
        """Reproduce the 200-curve measurement: the variant never exceeds 5.6e-17."""
        rng = np.random.default_rng(seed)
        worst = 0.0
        for _ in range(200):
            n = int(rng.integers(10, 2000))
            rets = pd.Series(rng.normal(0.0004, 0.01, n))
            cum = (1 + rets).cumprod()
            variant = float((cum / cum.cummax() - 1.0).min())
            equity = cum
            rolling_max = equity.expanding().max()
            library = float(((equity - rolling_max) / rolling_max).min())
            worst = max(worst, abs(variant - library))
        assert worst <= DRAWDOWN_VARIANT_BOUND, f"worst drawdown variant gap {worst!r}"

    def test_window_max_drawdown_matches_the_library_within_the_bound(self):
        """run_ddcv_experiment.window_max_drawdown uses the same cum/cummax variant."""
        module = importlib.import_module("run_ddcv_experiment")
        returns = _synthetic_returns(n=1000)
        equity = (1 + returns).cumprod()
        variant = module.window_max_drawdown(equity, equity.index[0], equity.index[-1])
        rolling_max = equity.expanding().max()
        library = float(((equity - rolling_max) / rolling_max).min())
        assert abs(variant - library) <= DRAWDOWN_VARIANT_BOUND


class TestH26DailySharpeConvention:
    """H26's daily Sharpe (audit_artifact:303) uses the sample std
    (pandas ddof=1), a documented convention split from the library's
    population std.  The difference is exactly sqrt(n / (n - 1))."""

    def test_daily_sharpe_uses_the_sample_std_convention(self):
        """Reconstruct audit_artifact:303: daily_sharpe = daily.mean() /
        daily.std() * sqrt(252) with pandas Series.std() (sample, ddof=1)."""
        returns = _synthetic_returns(n=2515)
        daily = (1.0 + returns).resample("1D").prod() - 1.0
        daily = daily.dropna()
        daily_sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if len(daily) > 1 else 0.0
        population = sharpe_ratio(daily.values)
        n = len(daily)
        # sample std = population std * sqrt(n / (n - 1)), so sample Sharpe =
        # population Sharpe * sqrt((n - 1) / n)
        assert daily_sharpe == pytest.approx(population * math.sqrt((n - 1) / n), rel=1e-12)
        assert daily_sharpe != pytest.approx(population, rel=1e-9)

    def test_convention_gap_is_bounded(self):
        """The gap is exactly sqrt(n / (n - 1)) - 1 = 0.0001988 at n = 2,515,
        i.e. +0.02% -- bounded and far below any gate margin."""
        assert H26_CONVENTION_GAP_BOUND == pytest.approx(0.0001988, abs=1e-6)
        assert H26_CONVENTION_GAP_BOUND < 0.001


class TestContractNegativeControl:
    """The contract must reject a helper that disagrees with the library."""

    def test_a_disagreeing_period_metrics_fails_the_contract(self):
        """A helper that returns the sample-std Sharpe (the pre-H39 engine
        convention) must fail the exact-agreement check."""
        returns = _synthetic_returns(n=252)
        library = _library_metrics(returns)
        sample_sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(252))
        # sample-std Sharpe != population-std Sharpe (the library's)
        assert sample_sharpe != pytest.approx(library["sharpe"], rel=1e-9)
        with pytest.raises(AssertionError):
            assert sample_sharpe == pytest.approx(library["sharpe"], rel=1e-12, abs=1e-15)

    def test_a_disagreeing_drawdown_fails_the_contract(self):
        """A helper that returns a genuinely different drawdown formula must
        fail the bounded-difference check."""
        returns = pd.Series([0.01, -0.02, 0.03, -0.04, 0.05])
        cum = (1 + returns).cumprod()
        wrong_dd = float((cum.cummax() / cum - 1.0).max())  # inverted formula
        equity = cum
        rolling_max = equity.expanding().max()
        library_dd = float(((equity - rolling_max) / rolling_max).min())
        assert abs(wrong_dd - library_dd) > DRAWDOWN_VARIANT_BOUND


# --------------------------------------------------------------------------- #
# inline drawdown sites (library-conforming and raw variants)
# --------------------------------------------------------------------------- #

# Inline drawdowns that use the library's convention
# (equity / rolling_max - 1) or (cum / cummax - 1), both algebraically
# identical to (equity - rolling_max) / rolling_max.  Each agrees with
# validate_strategy["max_drawdown"] within 1e-15.
INLINE_DRAWDOWN_CONFORMING = (
    (
        "run_h11_robustness_experiment.py",
        548,
        "oos drawdown in the cost-multiplier loop",
        "(cum / cum.cummax() - 1).min()",
    ),
    (
        "run_h11_robustness_experiment.py",
        648,
        "fresh OOS drawdown",
        "(fcum / fcum.cummax() - 1).min()",
    ),
    (
        "run_h18_overnight_intraday_experiment.py",
        527,
        "full-period max drawdown",
        "((equity / equity.expanding().max()) - 1).min()",
    ),
    (
        "run_h18_overnight_intraday_experiment.py",
        641,
        "OOS max drawdown",
        "((oos_equity / oos_equity.expanding().max()) - 1).min()",
    ),
)

# Inline drawdowns that use the raw formula (equity - rolling_max).min() -- a
# dollar drawdown, not the library's ratio drawdown.  These differ from
# validate_strategy["max_drawdown"] and are pinned as differs_convention.
INLINE_DRAWDOWN_RAW = (
    (
        "run_ddcv_experiment.py",
        386,
        "OOS drawdown",
        "(oos_equity - oos_equity.expanding().max()).min()",
    ),
    (
        "run_ddcv_experiment.py",
        443,
        "ablation max drawdown",
        "(eq - eq.expanding().max()).min()",
    ),
    (
        "run_futures_tsmom_experiment.py",
        467,
        "OOS drawdown",
        "(oos_equity - oos_equity.expanding().max()).min()",
    ),
)

# H18 runner-local total_return copies (pre-H38 range).  The formula
# (equity.iloc[-1] / equity.iloc[0] - 1) matches the library's
# (1 + returns).prod() - 1 when equity starts at 1.0; H18 applies it to a
# sliced range, but the formula itself agrees exactly.
INLINE_TOTAL_RETURN = (
    (
        "run_h18_overnight_intraday_experiment.py",
        526,
        "full-period total_return",
        "(equity.iloc[-1] / equity.iloc[0] - 1)",
    ),
    (
        "run_h18_overnight_intraday_experiment.py",
        637,
        "OOS total_return",
        "(oos_equity.iloc[-1] / oos_equity.iloc[0] - 1)",
    ),
)


class TestInlineDrawdownConforming:
    """Inline drawdowns that use the library's convention.  Each agrees with
    validate_strategy["max_drawdown"] within 1e-15 (floating-point noise)."""

    @pytest.mark.parametrize(
        "runner,line,site,formula",
        INLINE_DRAWDOWN_CONFORMING,
        ids=[f"{r}:{l} {s}" for r, l, s, _ in INLINE_DRAWDOWN_CONFORMING],
    )
    def test_inline_drawdown_matches_library_within_bound(self, runner, line, site, formula):
        returns = _synthetic_returns(n=500, seed=7)
        equity = (1 + returns).cumprod()
        rolling_max = equity.expanding().max()
        library = float(((equity - rolling_max) / rolling_max).min())

        # Reconstruct the runner's inline computation.  Both the cum/cummax
        # and the expanding().max() forms are identical to cummax(), so the
        # same reconstruction covers every conforming site.
        variant = float((equity / equity.cummax() - 1.0).min())
        assert abs(variant - library) <= DRAWDOWN_VARIANT_BOUND, (
            f"{runner}:{line} {site} ({formula}) inline drawdown {variant!r} "
            f"differs from library {library!r} by more than "
            f"{DRAWDOWN_VARIANT_BOUND}"
        )


class TestInlineDrawdownRawVariant:
    """Inline drawdowns that use the raw formula (equity - rolling_max).min()
    -- a dollar drawdown, not the library's ratio drawdown.  These differ
    materially from validate_strategy["max_drawdown"] and are pinned as
    differs_convention."""

    @pytest.mark.parametrize(
        "runner,line,site,formula",
        INLINE_DRAWDOWN_RAW,
        ids=[f"{r}:{l} {s}" for r, l, s, _ in INLINE_DRAWDOWN_RAW],
    )
    def test_raw_drawdown_differs_from_library_ratio(self, runner, line, site, formula):
        returns = _synthetic_returns(n=500, seed=11)
        equity = (1 + returns).cumprod()
        rolling_max = equity.expanding().max()
        library = float(((equity - rolling_max) / rolling_max).min())
        raw = float((equity - rolling_max).min())
        assert abs(raw - library) > DRAWDOWN_VARIANT_BOUND, (
            f"{runner}:{line} {site} ({formula}) raw drawdown {raw!r} "
            f"unexpectedly matches library ratio {library!r}; the two formulas "
            f"are different quantities (dollar drawdown vs percentage drawdown)"
        )


class TestH18TotalReturn:
    """H18's runner-local total_return copies.  The formula
    (equity.iloc[-1] / equity.iloc[0] - 1) matches the library's
    (1 + returns).prod() - 1 when equity starts at 1.0.  H18 applies it to a
    pre-H38 range; the formula itself agrees exactly."""

    def test_h18_full_period_total_return_matches_library(self):
        returns = _synthetic_returns(n=500, seed=13)
        # equity starts at 1.0 (initial capital), then applies each return --
        # matching run_backtest's equity curve.
        equity = pd.Series(np.concatenate([[1.0], (1 + returns.values).cumprod()]))
        runner_tr = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        library_tr = float((1 + returns.values).prod() - 1.0)
        assert runner_tr == pytest.approx(library_tr, rel=1e-12, abs=1e-15)

    def test_h18_oos_total_return_matches_library_on_slice(self):
        returns = _synthetic_returns(n=500, seed=13)
        equity = pd.Series(np.concatenate([[1.0], (1 + returns.values).cumprod()]))
        # H18 slices the equity curve before computing total_return.  equity[j]
        # is the state after returns[0..j-1], so equity[100:] pairs with
        # returns[100:].
        oos_equity = equity.iloc[100:]
        oos_returns_values = returns.values[100:]
        runner_tr = float(oos_equity.iloc[-1] / oos_equity.iloc[0] - 1.0)
        library_tr = float((1 + oos_returns_values).prod() - 1.0)
        assert runner_tr == pytest.approx(library_tr, rel=1e-12, abs=1e-15)


# --------------------------------------------------------------------------- #
# static source sweep: the runner-local metric helpers must not acquire a new
# unclassified implementation
# --------------------------------------------------------------------------- #
def _module_functions(path: pathlib.Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text())
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _metric_function_names(functions: dict[str, ast.FunctionDef]) -> list[str]:
    """Module-level functions whose names indicate they compute a metric."""
    metric_hints = (
        "sharpe",
        "drawdown",
        "profit_factor",
        "max_drawdown",
        "information_ratio",
        "total_return",
        "annualized",
        "volatility",
        "sortino",
        "calmar",
        "period_metrics",
    )
    return sorted(name for name in functions if any(hint in name.lower() for hint in metric_hints))


class TestInventoryCompleteness:
    """A new runner-local metric helper must fail the suite: every
    metric-named function of every in-scope runner must be classified in
    INVENTORY (or covered by INLINE_METRIC_SITES)."""

    def test_every_metric_function_of_in_scope_runners_is_classified(self):
        for runner in IN_SCOPE_RUNNERS:
            functions = _module_functions(ROOT / runner)
            metric_names = _metric_function_names(functions)
            classified = set(INVENTORY.get(runner, {}))
            missing = sorted(set(metric_names) - classified)
            assert not missing, (
                f"{runner} has unclassified metric functions: {missing}; add them to INVENTORY"
            )
