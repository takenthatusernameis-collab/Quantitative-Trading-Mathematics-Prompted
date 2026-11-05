import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_14_credit_regime as nf14
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf14.GATES
        assert g["min_sharpe"] == 1.0
        assert g["min_trades"] == 200
        assert g["min_profit_factor"] == 1.3
        assert g["max_drawdown"] == 0.15
        assert g["min_walkforward_stability"] == 0.7
        assert g["min_worst_regime_sharpe"] == 0.3
        assert g["max_p_value"] == 0.05
        assert g["min_information_ratio"] == 0.0
        assert g["min_perturbed_sharpe_ratio"] == 0.5

    def test_config(self):
        cfg = nf14.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf14.MAX_POS

    def test_universe_and_splits(self):
        assert nf14.SPY == "SPY"
        assert nf14.HYG == "HYG"
        assert nf14.IEF == "IEF"
        assert nf14.UNIVERSE == ["SPY", "HYG", "IEF"]
        assert nf14.DATA_START == "2010-01-01"
        assert nf14.DATA_END == "2026-10-31"
        assert nf14.TRAIN_END == "2019-12-31"
        assert nf14.VAL_END == "2022-12-31"

    def test_grid(self):
        grid = [
            (lb, vt, sm)
            for lb in nf14.LOOKBACKS
            for vt in nf14.VOL_TARGETS
            for sm in nf14.SIGNAL_MODES
        ]
        assert len(grid) == 12
        assert nf14.LOOKBACKS == [21, 63, 126]
        assert nf14.SIGNAL_MODES == ["sign", "zscore"]


class TestCreditSignal:
    def _prices(self, n=500):
        idx = pd.bdate_range("2015-01-02", periods=n)
        rng = np.random.default_rng(123)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        hyg = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.004, n)))
        ief = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.003, n)))
        return pd.DataFrame({"SPY": spy, "HYG": hyg, "IEF": ief}, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        for mode in nf14.SIGNAL_MODES:
            pos = nf14.build_credit_targets(prices, lookback=21, vol_target=0.10, signal_mode=mode)
            assert list(pos.columns) == ["SPY"]
            assert len(pos) == len(prices)
            vals = pos["SPY"].dropna()
            assert (vals >= -1e-12).all()
            assert (vals <= nf14.MAX_POS + 1e-12).all()

    def test_warmup_flat(self):
        prices = self._prices()
        pos = nf14.build_credit_targets(prices, lookback=63, vol_target=0.10, signal_mode="sign")
        assert float(pos["SPY"].iloc[:10].abs().sum()) == 0.0

    def test_benign_credit_goes_long(self):
        idx = pd.bdate_range("2018-01-02", periods=160)
        spy = np.linspace(100, 120, 160)
        hyg = np.linspace(100, 115, 160)  # credit strong
        ief = np.full(160, 100.0)
        prices = pd.DataFrame({"SPY": spy, "HYG": hyg, "IEF": ief}, index=idx)
        pos = nf14.build_credit_targets(prices, lookback=21, vol_target=0.10, signal_mode="sign")
        assert (pos["SPY"].iloc[40:] > 0).all()

    def test_stressed_credit_goes_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=160)
        spy = np.linspace(100, 120, 160)
        hyg = np.linspace(100, 85, 160)  # credit weak
        ief = np.full(160, 100.0)
        prices = pd.DataFrame({"SPY": spy, "HYG": hyg, "IEF": ief}, index=idx)
        pos = nf14.build_credit_targets(prices, lookback=21, vol_target=0.10, signal_mode="sign")
        assert (pos["SPY"].iloc[40:] == 0.0).all()

    def test_missing_symbol_returns_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame(
            {"SPY": np.linspace(100, 110, 50), "HYG": np.linspace(100, 105, 50)}, index=idx
        )
        pos = nf14.build_credit_targets(prices, lookback=21, vol_target=0.10, signal_mode="sign")
        assert (pos["SPY"] == 0.0).all()

    def test_unknown_mode_raises(self):
        prices = self._prices(120)
        try:
            nf14.build_credit_targets(prices, lookback=21, vol_target=0.10, signal_mode="bad")
        except ValueError:
            return
        raise AssertionError("expected ValueError")
