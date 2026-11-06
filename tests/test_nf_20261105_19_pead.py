import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_19_pead as nf19
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf19.GATES
        assert g["min_sharpe"] == 1.0
        assert g["min_trades"] == 200
        assert g["min_profit_factor"] == 1.3
        assert g["max_drawdown"] == 0.15

    def test_config(self):
        cfg = nf19.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is True

    def test_universe_and_splits(self):
        assert nf19.DATA_START == "2015-01-01"
        assert nf19.DATA_END == "2026-10-31"
        assert nf19.TRAIN_END == "2019-12-31"
        assert nf19.VAL_END == "2022-12-31"
        assert nf19.HOLD_DAYS == 20
        assert len(nf19.UNIVERSE) == 20

    def test_weight_is_price_invariant(self):
        w = nf19.MAX_POS / max(1, len(nf19.UNIVERSE))
        assert w == pytest.approx(0.5 / 20)


class TestBuildPeadTargets:
    def _prices(self, n=40):
        idx = pd.bdate_range("2020-01-02", periods=n)
        return pd.DataFrame({"AAPL": 100.0 + np.arange(n), "MSFT": 50.0 + np.arange(n)}, index=idx)

    def test_position_starts_after_announcement_and_holds(self):
        prices = self._prices()
        ann = prices.index[5]
        events = {
            "AAPL": pd.DataFrame({"sign": [1.0]}, index=pd.DatetimeIndex([ann])),
            "MSFT": pd.DataFrame({"sign": [-1.0]}, index=pd.DatetimeIndex([ann])),
        }
        pos = nf19.build_pead_targets(prices, events, hold_days=5)
        start = prices.index.get_loc(ann) + 1
        w = nf19.MAX_POS / 20
        aapl = pos["AAPL"].to_numpy()
        msft = pos["MSFT"].to_numpy()
        # flat on/ before announcement
        assert (aapl[:start] == 0.0).all()
        assert (msft[:start] == 0.0).all()
        # long AAPL / short MSFT for the hold window
        assert (aapl[start : start + 5] == w).all()
        assert (msft[start : start + 5] == -w).all()
        # flat after the window
        assert (aapl[start + 5 :] == 0.0).all()
        assert (msft[start + 5 :] == 0.0).all()

    def test_unknown_symbol_is_ignored(self):
        prices = self._prices()
        ann = prices.index[5]
        events = {"ZZZZ": pd.DataFrame({"sign": [1.0]}, index=pd.DatetimeIndex([ann]))}
        pos = nf19.build_pead_targets(prices, events, hold_days=5)
        assert (pos == 0.0).all().all()

    def test_no_events_returns_flat(self):
        prices = self._prices()
        pos = nf19.build_pead_targets(prices, {}, hold_days=5)
        assert (pos == 0.0).all().all()
