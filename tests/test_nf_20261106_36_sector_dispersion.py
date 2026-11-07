import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261106_36_sector_dispersion as nf36
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf36.GATES
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
        cfg = nf36.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf36.MAX_POS

    def test_universe_and_splits(self):
        assert nf36.SPY == "SPY"
        assert nf36.UNIVERSE == nf36.SECTORS + ["SPY"]
        assert nf36.DATA_START == "2010-01-01"
        assert nf36.DATA_END == "2026-10-31"
        assert nf36.TRAIN_END == "2019-12-31"
        assert nf36.VAL_END == "2022-12-31"

    def test_grid(self):
        assert nf36.LOOKBACKS == [21, 63]
        assert nf36.VOL_TARGETS == [0.10, 0.15]


class TestDispersionSignal:
    def _prices(self, n=400):
        idx = pd.bdate_range("2018-01-02", periods=n)
        rng = np.random.default_rng(123)
        data = {"SPY": 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))}
        for s in nf36.SECTORS:
            data[s] = 100 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n)))
        return pd.DataFrame(data, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        pos = nf36.build_dispersion_targets(
            prices, lookback=21, z_window=126, entry_scale=1.0, vol_target=0.10
        )
        assert list(pos.columns) == ["SPY"]
        assert len(pos) == len(prices)
        vals = pos["SPY"].dropna()
        assert (vals >= -1e-12).all()
        assert (vals <= nf36.MAX_POS + 1e-12).all()
