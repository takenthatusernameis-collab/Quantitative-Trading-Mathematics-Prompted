"""Regression tests for NF-20261110-08 / H182 insider net-buy signal timing.

The runner was executed without a focused test suite, and the first audit of it
found a point-in-time defect: filing acceptance timestamps were truncated to
their calendar date before being aligned to the price index.  A Form 4 accepted
after the cash close (or on a weekend) therefore moved the position on a close
that had already happened when the filing became public, and days before a
symbol's first filing were filled with a neutral ratio that the pre-registered
``entry_threshold`` grid (which contains exactly 0.5) reads as an entry.

These tests pin the corrected mapping offline.  No test here touches the
network: every case drives the pure signal functions with synthetic price and
transaction frames.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import run_nf_20261110_08_insider_signal as nf08

# Monday 2026-11-02 through Monday 2026-11-09.
SESSION_DAYS = pd.bdate_range("2026-11-02", periods=6)


def _prices(closes=None) -> pd.DataFrame:
    values = np.linspace(100.0, 105.0, len(SESSION_DAYS)) if closes is None else closes
    return pd.DataFrame({"AAPL": values}, index=SESSION_DAYS)


def _filing(code: str, accepted_at: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "transaction_code": [code],
            "available_at": [pd.Timestamp(accepted_at)],
        }
    )


def _ratio(code: str, accepted_at: str) -> pd.Series:
    return nf08._net_buy_ratio_by_signal_day(_prices(), _filing(code, accepted_at))


class TestEffectiveSignalDays:
    """Acceptance instant -> the trading day whose close it may first move."""

    def test_filing_before_the_close_acts_on_that_close(self):
        # 14:00 UTC is 09:00 ET on 2026-11-04, before the 16:00 ET close.
        effective = nf08._effective_signal_days(
            _prices(), pd.Series([pd.Timestamp("2026-11-04 14:00:00")])
        )
        assert effective.iloc[0] == pd.Timestamp("2026-11-04")

    def test_filing_after_the_close_acts_on_the_next_close(self):
        # 23:58:20 UTC is 18:58:20 ET on 2026-11-04: the close had already
        # happened, so the earliest actionable close is 2026-11-05.
        effective = nf08._effective_signal_days(
            _prices(), pd.Series([pd.Timestamp("2026-11-04 23:58:20")])
        )
        assert effective.iloc[0] == pd.Timestamp("2026-11-05")

    def test_weekend_filing_acts_on_the_next_session(self):
        effective = nf08._effective_signal_days(
            _prices(), pd.Series([pd.Timestamp("2026-11-07 15:00:00")])
        )
        assert effective.iloc[0] == pd.Timestamp("2026-11-09")

    def test_filing_after_the_last_close_is_unactionable(self):
        effective = nf08._effective_signal_days(
            _prices(), pd.Series([pd.Timestamp("2026-11-20 12:00:00")])
        )
        assert pd.isna(effective.iloc[0])

    def test_timezone_naive_input_is_read_as_utc(self):
        naive = nf08._effective_signal_days(
            _prices(), pd.Series([pd.Timestamp("2026-11-04 23:58:20")])
        )
        aware = nf08._effective_signal_days(
            _prices(),
            pd.Series([pd.Timestamp("2026-11-04 23:58:20", tz="UTC")]),
        )
        pd.testing.assert_series_equal(naive, aware)

    def test_empty_inputs_yield_an_empty_mapping(self):
        effective = nf08._effective_signal_days(_prices(), pd.Series([], dtype="datetime64[ns]"))
        assert len(effective) == 0

    def test_empty_price_panel_yields_all_nat(self):
        empty_prices = _prices().iloc[:0]
        effective = nf08._effective_signal_days(
            empty_prices, pd.Series([pd.Timestamp("2026-11-04 14:00:00")])
        )
        assert effective.isna().all()


class TestNetBuyRatioBySignalDay:
    def test_only_open_market_codes_count(self):
        frame = pd.DataFrame(
            {
                "transaction_code": ["P", "S", "A", "M", "G", "F", "C"],
                "available_at": [pd.Timestamp("2026-11-04 14:00:00")] * 7,
            }
        )
        ratios = nf08._net_buy_ratio_by_signal_day(_prices(), frame)
        assert ratios.loc[pd.Timestamp("2026-11-04")] == 0.5  # 1 buy, 1 sale

    def test_multiple_filings_on_one_signal_day_are_pooled(self):
        # A Friday-after-close purchase and a Saturday sale both land on Monday.
        frame = pd.DataFrame(
            {
                "transaction_code": ["P", "S", "S", "S"],
                "available_at": pd.to_datetime(
                    [
                        "2026-11-06 23:58:20",
                        "2026-11-07 15:00:00",
                        "2026-11-07 16:00:00",
                        "2026-11-07 17:00:00",
                    ]
                ),
            }
        )
        ratios = nf08._net_buy_ratio_by_signal_day(_prices(), frame)
        # Pooled counts, not averaged daily ratios: 1 buy of 4 rows.
        assert ratios.loc[pd.Timestamp("2026-11-09")] == 0.25

    def test_no_open_market_rows_yield_an_empty_series(self):
        frame = pd.DataFrame(
            {
                "transaction_code": ["A", "M"],
                "available_at": pd.to_datetime(["2026-11-04 14:00:00"] * 2),
            }
        )
        assert len(nf08._net_buy_ratio_by_signal_day(_prices(), frame)) == 0

    def test_all_filings_beyond_the_price_window_yield_an_empty_series(self):
        frame = _filing("P", "2026-12-01 14:00:00")
        assert len(nf08._net_buy_ratio_by_signal_day(_prices(), frame)) == 0


class TestNoLookAheadInDailySignals:
    def test_after_close_filing_does_not_move_the_acceptance_day(self):
        prices = _prices()
        corpus = {"AAPL": _filing("P", "2026-11-04 23:58:20")}
        signal = nf08._compute_daily_signals(prices, corpus, 0.6, 0.4)["AAPL"]
        # Flat on the acceptance day; the position starts the next session.
        assert signal.loc[pd.Timestamp("2026-11-04")] == 0.0
        assert signal.loc[pd.Timestamp("2026-11-05")] == 1.0

    def test_before_close_filing_acts_on_the_acceptance_day(self):
        prices = _prices()
        corpus = {"AAPL": _filing("P", "2026-11-04 14:00:00")}
        signal = nf08._compute_daily_signals(prices, corpus, 0.6, 0.4)["AAPL"]
        assert signal.loc[pd.Timestamp("2026-11-04")] == 1.0

    def test_warm_up_before_the_first_filing_is_flat(self):
        # The pre-registered grid contains entry_threshold == 0.5, so filling the
        # warm-up with 0.5 would enter the market with no filing at all.
        prices = _prices()
        corpus = {"AAPL": _filing("P", "2026-11-09 14:00:00")}
        signal = nf08._compute_daily_signals(prices, corpus, 0.5, 0.4)["AAPL"]
        assert (signal.iloc[:-1] == 0.0).all()
        assert signal.iloc[-1] == 1.0

    def test_symbol_without_a_corpus_stays_flat(self):
        prices = _prices()
        signal = nf08._compute_daily_signals(prices, {}, 0.5, 0.4)["AAPL"]
        assert (signal == 0.0).all()

    def test_future_filings_do_not_change_earlier_positions(self):
        prices = _prices()
        corpus = {"AAPL": _filing("P", "2026-11-04 14:00:00")}
        near = nf08._compute_daily_signals(prices, corpus, 0.6, 0.4)["AAPL"]
        # Append a filing far in the future and re-run.
        far = pd.concat([corpus["AAPL"], _filing("S", "2026-11-09 18:00:00")], ignore_index=True)
        far_signal = nf08._compute_daily_signals(prices, {"AAPL": far}, 0.6, 0.4)["AAPL"]
        pd.testing.assert_series_equal(near.iloc[:-1], far_signal.iloc[:-1])


class TestHysteresis:
    def test_position_enters_at_entry_and_exits_at_exit(self):
        signal = pd.Series([0.0, 0.7, 0.7, 0.5, 0.3, 0.3], index=SESSION_DAYS)
        positions = nf08._hysteresis(signal, 0.6, 0.4)
        assert positions.tolist() == [0.0, 1.0, 1.0, 1.0, 0.0, 0.0]

    def test_nan_is_treated_as_no_signal_and_holds_the_position(self):
        signal = pd.Series([np.nan, 0.7, np.nan, np.nan], index=SESSION_DAYS[:4])
        positions = nf08._hysteresis(signal, 0.6, 0.4)
        assert positions.tolist() == [0.0, 1.0, 1.0, 1.0]

    def test_exit_threshold_is_inclusive(self):
        signal = pd.Series([0.7, 0.4], index=SESSION_DAYS[:2])
        assert nf08._hysteresis(signal, 0.6, 0.4).tolist() == [1.0, 0.0]


class TestPreRegistrationIntact:
    def test_grid_is_thirty_six_combos(self):
        grid = nf08.GRID
        expected = (
            len(grid["entry_threshold"])
            * len(grid["exit_threshold"])
            * len(grid["vol_target"])
            * len(grid["max_pos"])
        )
        assert expected == 36

    def test_split_boundaries_are_the_pre_registered_ones(self):
        assert nf08.TRAIN_END == "2025-02-28"
        assert nf08.VAL_END == "2025-10-31"

    def test_universe_is_the_pre_registered_ten_names(self):
        assert nf08.UNIVERSE == [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "META",
            "JPM",
            "XOM",
            "JNJ",
            "WMT",
        ]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
