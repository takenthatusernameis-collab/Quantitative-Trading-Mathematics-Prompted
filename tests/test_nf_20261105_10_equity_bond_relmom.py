import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_10_equity_bond_relmom as nf10
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf10.GATES
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
        cfg = nf10.make_equity_config(allow_short=False)
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf10.MAX_POS
        cfg_s = nf10.make_equity_config(allow_short=True)
        assert cfg_s.allow_short is True

    def test_universe_and_splits(self):
        assert nf10.SPY == "SPY"
        assert nf10.TLT == "TLT"
        assert nf10.UNIVERSE == ["SPY", "TLT"]
        assert nf10.DATA_START == "2010-01-01"
        assert nf10.DATA_END == "2026-10-31"
        assert nf10.TRAIN_END == "2019-12-31"
        assert nf10.VAL_END == "2022-12-31"

    def test_grid(self):
        assert nf10.LOOKBACKS == [21, 63, 126, 252]
        assert nf10.VOL_TARGETS == [0.10, 0.15]
        assert nf10.ALLOW_SHORT == [False, True]
        grid = [
            (lb, vt, sh)
            for lb in nf10.LOOKBACKS
            for vt in nf10.VOL_TARGETS
            for sh in nf10.ALLOW_SHORT
        ]
        assert len(grid) == 16


class TestRelMomSignal:
    def _prices(self, n=400):
        idx = pd.bdate_range("2018-01-02", periods=n)
        rng = np.random.default_rng(123)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        tlt = 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, n)))
        return pd.DataFrame({"SPY": spy, "TLT": tlt}, index=idx)

    def test_output_shape_and_bounds_long_only(self):
        prices = self._prices()
        pos = nf10.build_relmom_targets(prices, lookback=21, vol_target=0.10, allow_short=False)
        assert list(pos.columns) == ["SPY"]
        assert len(pos) == len(prices)
        vals = pos["SPY"].dropna()
        assert (vals >= -1e-12).all()
        assert (vals <= nf10.MAX_POS + 1e-12).all()

    def test_output_bounds_short_allowed(self):
        prices = self._prices()
        pos = nf10.build_relmom_targets(prices, lookback=21, vol_target=0.10, allow_short=True)
        vals = pos["SPY"].dropna()
        assert (vals >= -nf10.MAX_POS - 1e-12).all()
        assert (vals <= nf10.MAX_POS + 1e-12).all()

    def test_warmup_is_flat(self):
        prices = self._prices()
        pos = nf10.build_relmom_targets(prices, lookback=63, vol_target=0.10, allow_short=False)
        # relmom needs lookback returns and vol needs 21; early bars should be 0/NaN-scaled to 0
        assert float(pos["SPY"].iloc[:10].abs().sum()) == 0.0

    def test_direction_follows_relmom_sign(self):
        # Construct deterministic: SPY trends up strongly, TLT flat -> relmom positive -> long.
        idx = pd.bdate_range("2018-01-02", periods=120)
        spy = np.linspace(100, 130, 120)
        tlt = np.full(120, 100.0)
        prices = pd.DataFrame({"SPY": spy, "TLT": tlt}, index=idx)
        pos = nf10.build_relmom_targets(prices, lookback=21, vol_target=0.10, allow_short=False)
        # After warmup, relmom should be positive -> position > 0
        tail = pos["SPY"].iloc[40:]
        assert (tail > 0).all()

    def test_short_allowed_goes_negative_when_spy_underperforms(self):
        idx = pd.bdate_range("2018-01-02", periods=120)
        spy = np.linspace(100, 80, 120)
        tlt = np.linspace(100, 110, 120)
        prices = pd.DataFrame({"SPY": spy, "TLT": tlt}, index=idx)
        pos = nf10.build_relmom_targets(prices, lookback=21, vol_target=0.10, allow_short=True)
        tail = pos["SPY"].iloc[40:]
        assert (tail < 0).all()

    def test_missing_symbol_returns_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame({"SPY": np.linspace(100, 110, 50)}, index=idx)
        pos = nf10.build_relmom_targets(prices, lookback=21, vol_target=0.10, allow_short=False)
        assert (pos["SPY"] == 0.0).all()
