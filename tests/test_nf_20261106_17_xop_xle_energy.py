"""Tests for NF-20261106-17 / H109 (XOP/XLE energy-sector relative-strength supply-shock timing)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261106_17_xop_xle_energy as nf
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
        assert nf.XOP == "XOP"
        assert nf.XLE == "XLE"
        assert nf.UNIVERSE == ["XOP", "XLE", "SPY"]
        assert nf.DATA_START == "2010-01-01"
        assert nf.DATA_END == "2026-10-31"
        assert nf.TRAIN_END == "2019-12-31"
        assert nf.VAL_END == "2022-12-31"

    def test_grid(self):
        grid = [
            (lb, zw, es, vt)
            for lb in nf.LOOKBACKS
            for zw in nf.Z_WINDOWS
            for es in nf.ENTRY_SCALES
            for vt in nf.VOL_TARGETS
        ]
        assert len(grid) == 24
        assert nf.LOOKBACKS == [21, 63]
        assert nf.Z_WINDOWS == [126, 252]
        assert nf.ENTRY_SCALES == [1.0, 1.5, 2.0]
        assert nf.VOL_TARGETS == [0.10, 0.15]


class TestXopXleSignal:
    def _prices(self, n=700):
        idx = pd.bdate_range("2015-01-05", periods=n)
        rng = np.random.default_rng(123)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        xop = 110 * np.exp(np.cumsum(rng.normal(0.0001, 0.003, n)))
        xle = 80 * np.exp(np.cumsum(rng.normal(0.0001, 0.004, n)))
        return pd.DataFrame({"SPY": spy, "XOP": xop, "XLE": xle}, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        sig = nf.build_xop_xle_signal(
            prices, lookback=21, z_window=126, entry_scale=1.5, vol_target=0.10
        )
        assert list(sig.columns) == ["SPY"]
        assert len(sig) == len(prices)
        vals = sig["SPY"].values
        assert np.all(np.isfinite(vals))
        assert (vals >= -1e-12).all()
        assert (vals <= nf.MAX_POS + 1e-12).all()

    def test_warmup_zero(self):
        prices = self._prices()
        sig = nf.build_xop_xle_signal(
            prices, lookback=21, z_window=126, entry_scale=1.5, vol_target=0.10
        )
        assert float(sig["SPY"].iloc[:20].abs().sum()) == 0.0

    def test_weak_relative_strength_reduces_exposure(self):
        idx = pd.bdate_range("2015-01-05", periods=600)
        rng = np.random.default_rng(9)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 600)))
        # XOP weak vs XLE -> ratio declines -> signal reduced
        xop = 110 * np.exp(
            np.cumsum(np.linspace(-0.0008, -0.0001, 600) + rng.normal(0, 0.002, 600))
        )
        xle = 80 * np.exp(np.cumsum(np.linspace(0.0001, 0.0006, 600) + rng.normal(0, 0.003, 600)))
        prices = pd.DataFrame({"SPY": spy, "XOP": xop, "XLE": xle}, index=idx)
        sig = nf.build_xop_xle_signal(
            prices, lookback=21, z_window=126, entry_scale=1.0, vol_target=0.10
        )
        s = sig["SPY"].iloc[280:]
        assert s.mean() < nf.MAX_POS * 0.75

    def test_strong_relative_strength_increases_exposure(self):
        idx = pd.bdate_range("2015-01-05", periods=600)
        rng = np.random.default_rng(7)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.008, 600)))
        # XOP strong vs XLE -> ratio rises -> calm/full exposure
        xop = 110 * np.exp(np.cumsum(np.linspace(0.0001, 0.0006, 600) + rng.normal(0, 0.002, 600)))
        xle = 80 * np.exp(np.cumsum(np.linspace(-0.0002, -0.0008, 600) + rng.normal(0, 0.003, 600)))
        prices = pd.DataFrame({"SPY": spy, "XOP": xop, "XLE": xle}, index=idx)
        sig = nf.build_xop_xle_signal(
            prices, lookback=21, z_window=126, entry_scale=1.0, vol_target=0.10
        )
        assert (sig["SPY"].iloc[220:] > 0).any()

    def test_missing_symbol_raises(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame(
            {"SPY": np.linspace(100, 110, 50), "XOP": np.linspace(110, 111, 50)}, index=idx
        )
        try:
            nf.build_xop_xle_signal(
                prices, lookback=21, z_window=126, entry_scale=1.0, vol_target=0.10
            )
            raised = False
        except ValueError:
            raised = True
        assert raised

    def test_continuous_scaling(self):
        prices = self._prices(n=900)
        sig = nf.build_xop_xle_signal(
            prices, lookback=21, z_window=126, entry_scale=1.5, vol_target=0.10
        )
        vals = sig["SPY"].iloc[180:]
        assert ((vals > 0) & (vals < nf.MAX_POS - 1e-9)).sum() > 20
