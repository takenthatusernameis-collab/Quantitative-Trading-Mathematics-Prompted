import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261106_02_move_rates_vol as nf
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf.GATES
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
        cfg = nf.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf.MAX_POS

    def test_universe_and_splits(self):
        assert nf.SPY == "SPY"
        assert nf.MOVE == "^MOVE"
        assert nf.UNIVERSE == ["SPY", "^MOVE"]
        assert nf.DATA_START == "2010-01-01"
        assert nf.DATA_END == "2026-10-31"
        assert nf.TRAIN_END == "2019-12-31"
        assert nf.VAL_END == "2022-12-31"

    def test_grid(self):
        grid = [
            (lb, ez, xz, vt)
            for lb in nf.LOOKBACKS
            for ez in nf.ENTRY_ZS
            for xz in nf.EXIT_ZS
            for vt in nf.VOL_TARGETS
        ]
        assert len(grid) == 36
        assert nf.LOOKBACKS == [63, 126, 252]
        assert nf.ENTRY_ZS == [1.0, 1.5, 2.0]
        assert nf.EXIT_ZS == [0.0, 0.5]
        assert nf.VOL_TARGETS == [0.10, 0.15]


class TestMoveSignal:
    def _prices(self, n=700):
        idx = pd.bdate_range("2015-01-02", periods=n)
        rng = np.random.default_rng(123)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        # MOVE-like positive level series
        move = 80 + np.cumsum(rng.normal(0.0, 1.5, n))
        move = np.maximum(move, 30.0)
        return pd.DataFrame({"SPY": spy, "^MOVE": move}, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=63, entry_z=1.0, exit_z=0.0, vol_target=0.10
        )
        assert list(pos.columns) == ["SPY"]
        assert len(pos) == len(prices)
        vals = pos["SPY"].dropna()
        assert (vals >= -1e-12).all()
        assert (vals <= nf.MAX_POS + 1e-12).all()

    def test_warmup_flat(self):
        prices = self._prices()
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=63, entry_z=1.0, exit_z=0.0, vol_target=0.10
        )
        assert float(pos["SPY"].iloc[:10].abs().sum()) == 0.0

    def test_elevated_move_reduces_exposure(self):
        idx = pd.bdate_range("2018-01-02", periods=600)
        rng = np.random.default_rng(3)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 600)))
        move = np.concatenate(
            [
                np.full(300, 60.0) + rng.normal(0, 1.0, 300),
                np.linspace(60, 150, 300) + rng.normal(0, 1.0, 300),
            ]
        )
        prices = pd.DataFrame({"SPY": spy, "^MOVE": move}, index=idx)
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=63, entry_z=0.5, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"].iloc[400:] == 0.0).any()

    def test_benign_move_goes_long(self):
        idx = pd.bdate_range("2018-01-02", periods=400)
        rng = np.random.default_rng(11)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 400)))
        move = 60.0 + rng.normal(0, 1.0, 400)
        prices = pd.DataFrame({"SPY": spy, "^MOVE": move}, index=idx)
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=63, entry_z=1.0, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"].iloc[120:] > 0).any()

    def test_missing_symbol_returns_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame({"SPY": np.linspace(100, 110, 50)}, index=idx)
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=21, entry_z=1.0, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"] == 0.0).all()

    def test_hysteresis_bounds(self):
        idx = pd.bdate_range("2018-01-02", periods=500)
        rng = np.random.default_rng(5)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 500)))
        move = 70 + 25 * np.sin(np.linspace(0, 20 * np.pi, 500))
        prices = pd.DataFrame({"SPY": spy, "^MOVE": move}, index=idx)
        pos = nf.build_move_rates_vol_targets(
            prices, lookback=63, entry_z=1.5, exit_z=0.0, vol_target=0.10
        )
        vals = pos["SPY"].dropna().values
        assert vals.min() >= -1e-12 and vals.max() <= nf.MAX_POS + 1e-12
