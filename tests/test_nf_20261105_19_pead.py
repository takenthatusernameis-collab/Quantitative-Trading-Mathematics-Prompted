import sys
from pathlib import Path

import numpy as np
import pandas as pd

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

    def test_build_pead_targets(self):
        idx = pd.bdate_range("2020-01-02", periods=40)
        prices = pd.DataFrame({"AAPL": 100.0 + np.arange(40)}, index=idx)
        surprises = pd.DataFrame({"ticker": ["AAPL"], "date": [idx[5]], "surprise": [1.0]})
        pos = nf19.build_pead_targets(prices, surprises, hold_days=5)
        assert pos.shape == prices.shape
        assert (pos.iloc[6:11, 0] != 0).all()
