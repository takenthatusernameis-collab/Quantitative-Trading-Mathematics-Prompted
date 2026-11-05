import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_18_concentration_rv as nf18
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf18.GATES
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
        cfg = nf18.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf18.MAX_POS

    def test_universe_and_splits(self):
        assert nf18.SPY == "SPY"
        assert nf18.RSP == "RSP"
        assert nf18.UNIVERSE == ["SPY", "RSP"]
        assert nf18.DATA_START == "2010-01-01"
        assert nf18.DATA_END == "2026-10-31"
        assert nf18.TRAIN_END == "2019-12-31"
        assert nf18.VAL_END == "2022-12-31"

    def test_grid(self):
        grid = [
            (lb, ez, xz, vt)
            for lb in nf18.LOOKBACKS
            for ez in nf18.ENTRY_ZS
            for xz in nf18.EXIT_ZS
            for vt in nf18.VOL_TARGETS
        ]
        assert len(grid) == 36
        assert nf18.LOOKBACKS == [60, 126, 252]
        assert nf18.ENTRY_ZS == [1.5, 2.0, 2.5]
        assert nf18.EXIT_ZS == [0.0, 0.5]
        assert nf18.VOL_TARGETS == [0.10, 0.15]


class TestConcentrationSignal:
    def _prices(self, n=700):
        idx = pd.bdate_range("2015-01-02", periods=n)
        rng = np.random.default_rng(123)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        rsp = 95 * np.exp(np.cumsum(rng.normal(0.0002, 0.009, n)))
        return pd.DataFrame({"SPY": spy, "RSP": rsp}, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        pos = nf18.build_concentration_targets(
            prices, lookback=60, entry_z=2.0, exit_z=0.0, vol_target=0.10
        )
        assert list(pos.columns) == ["SPY"]
        assert len(pos) == len(prices)
        vals = pos["SPY"].dropna()
        assert (vals >= -1e-12).all()
        assert (vals <= nf18.MAX_POS + 1e-12).all()

    def test_warmup_flat(self):
        prices = self._prices()
        pos = nf18.build_concentration_targets(
            prices, lookback=60, entry_z=2.0, exit_z=0.0, vol_target=0.10
        )
        assert float(pos["SPY"].iloc[:10].abs().sum()) == 0.0

    def test_low_concentration_goes_long(self):
        # SPY cheap vs RSP (spread strongly negative vs its history) -> long
        # exposure at some point.
        idx = pd.bdate_range("2018-01-02", periods=500)
        t = np.arange(500, dtype=float)
        spy = 100 * np.exp(-0.002 * t)
        rsp = 95 * np.exp(0.001 * t)
        prices = pd.DataFrame({"SPY": spy, "RSP": rsp}, index=idx)
        pos = nf18.build_concentration_targets(
            prices, lookback=60, entry_z=2.0, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"].iloc[120:] > 0).any()

    def test_high_concentration_is_flat(self):
        # SPY rich vs RSP (spread strongly positive vs its history) -> flat
        # exposure at some point with a low entry threshold.
        idx = pd.bdate_range("2018-01-02", periods=500)
        t = np.arange(500, dtype=float)
        spy = 100 * np.exp(0.002 * t)
        rsp = 95 * np.exp(-0.001 * t)
        prices = pd.DataFrame({"SPY": spy, "RSP": rsp}, index=idx)
        pos = nf18.build_concentration_targets(
            prices, lookback=60, entry_z=0.5, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"].iloc[400:] == 0.0).any()

    def test_missing_symbol_returns_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame({"SPY": np.linspace(100, 110, 50)}, index=idx)
        pos = nf18.build_concentration_targets(
            prices, lookback=21, entry_z=2.0, exit_z=0.0, vol_target=0.10
        )
        assert (pos["SPY"] == 0.0).all()

    def test_hysteresis_bounds(self):
        idx = pd.bdate_range("2018-01-02", periods=500)
        rng = np.random.default_rng(5)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 500)))
        rsp = 95 * np.exp(np.cumsum(rng.normal(0.0001, 0.007, 500)))
        prices = pd.DataFrame({"SPY": spy, "RSP": rsp}, index=idx)
        pos = nf18.build_concentration_targets(
            prices, lookback=60, entry_z=2.5, exit_z=0.0, vol_target=0.10
        )
        vals = pos["SPY"].dropna().values
        assert vals.min() >= -1e-12 and vals.max() <= nf18.MAX_POS + 1e-12
