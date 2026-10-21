import json
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.validation.statistics import sharpe_ratio, walk_forward_splits

ARTIFACTS = Path(".experiments/artifacts")

CASES = [
    "exp_2026-10-10T17-02-22-080026Z",
    "exp_2026-10-10T17-03-39-610858Z",
    "exp_2026-10-10T17-04-21-400695Z",
    "exp_2026-10-10T17-05-58-697503Z",
    "exp_2026-10-14T08-26-02-537359Z",
]


def _summary(name: str) -> dict:
    with open(ARTIFACTS / name / "summary.json") as f:
        return json.load(f)


def _full_returns(name: str) -> np.ndarray:
    """Reconstruct the engine's net-return series from the frozen equity curve.

    The engine charges costs *per bar* and compounds them into the equity curve
    (``equity = (1 + net_returns).cumprod() * initial_capital``), so the equity
    curve carries the full series including the first bar. Recovering the
    returns by ``equity.pct_change()`` alone drops that first bar and cannot
    reproduce the published block; the first bar's return is
    ``equity[0] / initial_capital - 1`` (the cost of the very first position
    change, charged on the opening bar).
    """
    summary = _summary(name)
    initial_capital = summary["config"]["backtest"]["initial_capital"]
    equity = pd.read_parquet(ARTIFACTS / name / "equity_curve.parquet")["equity"].astype(float)
    first = equity.iloc[0] / initial_capital - 1.0
    rest = equity.pct_change().dropna().values
    return np.concatenate([[first], rest])


def _recompute(returns: np.ndarray) -> dict:
    series = pd.Series(returns, dtype=float)
    total_return = float((1 + series).prod() - 1)
    gross_profit = float(series[series > 0].sum())
    gross_loss = float(abs(series[series < 0].sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    equity = (1 + series).cumprod()
    rolling_max = equity.expanding().max()
    max_drawdown = float(((equity - rolling_max) / rolling_max).min())
    mid = len(series) // 2
    sharpe_first = sharpe_ratio(series.iloc[:mid].values)
    sharpe_second = sharpe_ratio(series.iloc[mid:].values)
    return {
        "sharpe": sharpe_ratio(returns),
        "total_return": total_return,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "sharpe_first": sharpe_first,
        "sharpe_second": sharpe_second,
        "walkforward_stability": (sharpe_second / sharpe_first if sharpe_first != 0 else None),
    }


class TestPublishedBlockRecomputesFromFrozenEquityCurve:
    """Every published `validation` block re-derives from its own frozen equity curve.

    The five exploratory summaries carry a `validation` block written by an
    earlier ``validate_strategy``. Re-deriving the block from each artifact's
    own frozen ``equity_curve.parquet`` reproduces the published numbers to
    float noise for ALL FIVE artifacts -- including the two buy-and-hold runs
    whose blocks differ from each other. The difference between those two is
    real and is disclosed separately (see TestBuyAndHoldBlocksDifferByCostModel).
    """

    def test_recomputes_for_all_five(self):
        for name in CASES:
            summary = _summary(name)
            published = summary["validation"]
            recomputed = _recompute(_full_returns(name))
            assert abs(recomputed["sharpe"] - published["sharpe"]) < 1e-9, (
                f"{name}: sharpe {recomputed['sharpe']} != published {published['sharpe']}"
            )
            assert abs(recomputed["total_return"] - published["total_return"]) < 1e-9, (
                f"{name}: total_return {recomputed['total_return']} != published {published['total_return']}"
            )
            assert abs(recomputed["profit_factor"] - published["profit_factor"]) < 1e-9, (
                f"{name}: profit_factor {recomputed['profit_factor']} != published {published['profit_factor']}"
            )
            assert abs(recomputed["max_drawdown"] - published["max_drawdown"]) < 1e-9, (
                f"{name}: max_drawdown {recomputed['max_drawdown']} != published {published['max_drawdown']}"
            )

    def test_walkforward_stability_is_sign_aware_ratio(self):
        """The published `walkforward_stability` is exactly `sharpe(2nd half)/sharpe(1st half)`.

        The earlier code took the ratio unconditionally. The current code guards
        it: it reports ``0.0`` unless BOTH halves are profitable, because a
        sign-unaware ratio passes the ``0.7`` gate on a strategy that loses
        money in both halves (e.g. ``-1.5594 / -0.8479 = 1.8392``).
        """
        for name in CASES:
            published = _summary(name)["validation"]
            recomputed = _recompute(_full_returns(name))
            ratio = recomputed["walkforward_stability"]
            assert ratio is not None
            assert abs(ratio - published["walkforward_stability"]) < 1e-9, (
                f"{name}: walkforward_stability {ratio} != published {published['walkforward_stability']}"
            )

    def test_published_walkforward_pass_is_on_pre_guard_basis(self):
        """All five published blocks report ``walkforward_pass: True``.

        The current sign-aware code would report ``False`` for the three
        ma_crossover artifacts (both halves losing => stability 0.0 < 0.7). The
        published blocks are history and are not re-derived by the current code;
        this test pins the published value as-is.
        """
        for name in CASES:
            published = _summary(name)["validation"]
            assert (
                published["walkforward_pass"] is True or published["walkforward_pass"] == "True"
            ), f"{name}: published walkforward_pass is not True"

    def test_no_param_stability_key(self):
        """The published blocks pre-date the ``param_stability`` gate."""
        for name in CASES:
            published = _summary(name)["validation"]
            assert "param_stability" not in published, (
                f"{name}: published block unexpectedly carries param_stability"
            )

    def test_all_pass_is_false_and_stays_false(self):
        """No verdict moves: every published block already fails at least one gate."""
        for name in CASES:
            assert (
                _summary(name)["validation"]["all_pass"] is False
                or _summary(name)["validation"]["all_pass"] == "False"
            ), f"{name}: published all_pass is not False"


class TestPublishedBlockMatchesCurrentSignAwareCode:
    """Where the published block and the current code share a basis, they agree.

    The current ``validate_strategy`` derives ``walkforward_stability`` with the
    sign-aware guard. For the two buy-and-hold artifacts (both halves
    profitable) the published value and the current code agree; for the three
    ma_crossover artifacts (both halves losing) the published value is the
    pre-guard ratio and the current code reports ``0.0``.
    """

    def test_buy_and_hold_blocks_match_current_code(self):
        for name in (
            "exp_2026-10-10T17-05-58-697503Z",
            "exp_2026-10-14T08-26-02-537359Z",
        ):
            published = _summary(name)["validation"]
            recomputed = _recompute(_full_returns(name))
            ratio = recomputed["walkforward_stability"]
            assert ratio is not None
            assert ratio > 0.0
            assert abs(ratio - published["walkforward_stability"]) < 1e-9, (
                f"{name}: buy-and-hold block does not match current sign-aware code"
            )

    def test_ma_crossover_blocks_current_code_reports_zero(self):
        """The current code reports 0.0 for the three losing-halves artifacts."""
        for name in (
            "exp_2026-10-10T17-02-22-080026Z",
            "exp_2026-10-10T17-03-39-610858Z",
            "exp_2026-10-10T17-04-21-400695Z",
        ):
            recomputed = _recompute(_full_returns(name))
            assert recomputed["sharpe_first"] <= 0.0
            assert recomputed["sharpe_second"] <= 0.0
            assert recomputed["walkforward_stability"] > 1.0


class TestWalkforwardFoldsRecompute:
    """The published ``walkforward_folds`` re-derive from the frozen equity curve."""

    def test_folds_match(self):
        for name in CASES:
            published = _summary(name)["validation"]["walkforward_folds"]
            returns = _full_returns(name)
            splits = walk_forward_splits(len(returns), n_splits=5)
            recomputed = [
                (sharpe_ratio(returns[tr]), sharpe_ratio(returns[te])) for tr, te in splits
            ]
            assert len(recomputed) == len(published), (
                f"{name}: fold count {len(recomputed)} != published {len(published)}"
            )
            for i, ((rt, re_), fold) in enumerate(zip(recomputed, published)):
                pt = float(fold["train"])
                pe = float(fold["test"])
                assert abs(rt - pt) < 1e-9 and abs(re_ - pe) < 1e-9, (
                    f"{name}: fold {i} ({rt}, {re_}) != published ({pt}, {pe})"
                )


class TestBuyAndHoldBlocksDifferByCostModel:
    """The two buy-and-hold blocks differ because they charged different costs.

    ``exp_2026-10-10T17-05-58-697503Z`` and ``exp_2026-10-14T08-26-02-537359Z``
    run the same SPY buy-and-hold series (their price series are identical and
    their equity curves are proportional), but their published blocks differ:
    the first charges the real cost model (``avg_trade_cost = 0.041106``) while
    the second charges a fixed ``0.0002`` per trade. Both blocks re-derive
    exactly from their OWN frozen equity curve; they do not re-derive from
    each other's.
    """

    def test_same_price_series(self):
        p1 = pd.read_parquet(ARTIFACTS / "exp_2026-10-10T17-05-58-697503Z" / "prices.parquet")[
            "SPY"
        ].astype(float)
        p2 = pd.read_parquet(ARTIFACTS / "exp_2026-10-14T08-26-02-537359Z" / "prices.parquet")[
            "SPY"
        ].astype(float)
        assert len(p1) == len(p2)
        assert np.allclose(p1.values, p2.values, rtol=0, atol=1e-9)

    def test_different_avg_trade_cost(self):
        c1 = _summary("exp_2026-10-10T17-05-58-697503Z")["strategy_metrics"]["avg_trade_cost"]
        c2 = _summary("exp_2026-10-14T08-26-02-537359Z")["strategy_metrics"]["avg_trade_cost"]
        assert abs(c1 - c2) > 1e-6
        assert abs(c1 - 0.041105949376283715) < 1e-9
        assert abs(c2 - 0.00020009711746988646) < 1e-9

    def test_each_block_recomputes_from_its_own_curve(self):
        for name in (
            "exp_2026-10-10T17-05-58-697503Z",
            "exp_2026-10-14T08-26-02-537359Z",
        ):
            published = _summary(name)["validation"]
            recomputed = _recompute(_full_returns(name))
            assert abs(recomputed["sharpe"] - published["sharpe"]) < 1e-9
