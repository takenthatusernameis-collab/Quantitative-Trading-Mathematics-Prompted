import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261106_01_miner_gold_rv as nf99
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf99.GATES
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
        cfg = nf99.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is False
        assert cfg.max_leverage == 1.0
        assert cfg.max_position_size == nf99.MAX_POS

    def test_universe_and_splits(self):
        assert nf99.TRADE_SYM == "GDX"
        assert nf99.SIGNAL_SYM == "GLD"
        assert nf99.UNIVERSE == ["GDX", "GLD"]
        assert nf99.DATA_START == "2012-01-01"
        assert nf99.DATA_END == "2026-10-31"
        assert nf99.TRAIN_END == "2019-12-31"
        assert nf99.VAL_END == "2022-12-31"

    def test_grid(self):
        grid = [
            (lb, ez, xz, vt)
            for lb in nf99.LOOKBACKS
            for ez in nf99.ENTRY_ZS
            for xz in nf99.EXIT_ZS
            for vt in nf99.VOL_TARGETS
            if xz <= ez
        ]
        assert len(grid) == 36
        assert nf99.LOOKBACKS == [60, 126, 252]
        assert nf99.ENTRY_ZS == [1.0, 1.5, 2.0]
        assert nf99.EXIT_ZS == [0.0, 0.5]
        assert nf99.VOL_TARGETS == [0.08, 0.12]


class TestMinerGoldSignal:
    def _prices(self, n=700):
        idx = pd.bdate_range("2015-01-02", periods=n)
        rng = np.random.default_rng(123)
        gdx = 25 * np.exp(np.cumsum(rng.normal(0.0002, 0.018, n)))
        gld = 120 * np.exp(np.cumsum(rng.normal(0.0001, 0.009, n)))
        return pd.DataFrame({"GDX": gdx, "GLD": gld}, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        pos = nf99.build_miner_gold_targets(
            prices, lookback=60, entry_z=1.5, exit_z=0.0, vol_target=0.10
        )
        assert list(pos.columns) == ["GDX"]
        assert len(pos) == len(prices)
        vals = pos["GDX"].dropna()
        assert (vals >= -1e-12).all()
        assert (vals <= nf99.MAX_POS + 1e-12).all()

    def test_warmup_flat(self):
        prices = self._prices()
        pos = nf99.build_miner_gold_targets(
            prices, lookback=60, entry_z=1.5, exit_z=0.0, vol_target=0.10
        )
        assert float(pos["GDX"].iloc[:10].abs().sum()) == 0.0

    def test_miners_cheap_goes_long(self):
        # GDX depressed vs GLD (spread strongly negative vs its history) -> long
        # exposure at some point.
        idx = pd.bdate_range("2018-01-02", periods=500)
        t = np.arange(500, dtype=float)
        gdx = 30 * np.exp(-0.003 * t)
        gld = 120 * np.exp(0.001 * t)
        prices = pd.DataFrame({"GDX": gdx, "GLD": gld}, index=idx)
        pos = nf99.build_miner_gold_targets(
            prices, lookback=60, entry_z=1.5, exit_z=0.0, vol_target=0.10
        )
        assert (pos["GDX"].iloc[120:] > 0).any()

    def test_miners_rich_is_flat(self):
        # GDX rich vs GLD (spread strongly positive) -> flat at some point.
        idx = pd.bdate_range("2018-01-02", periods=500)
        t = np.arange(500, dtype=float)
        gdx = 30 * np.exp(0.003 * t)
        gld = 120 * np.exp(-0.001 * t)
        prices = pd.DataFrame({"GDX": gdx, "GLD": gld}, index=idx)
        pos = nf99.build_miner_gold_targets(
            prices, lookback=60, entry_z=0.5, exit_z=0.0, vol_target=0.10
        )
        assert (pos["GDX"].iloc[400:] == 0.0).any()

    def test_missing_symbol_returns_flat(self):
        idx = pd.bdate_range("2018-01-02", periods=50)
        prices = pd.DataFrame({"GDX": np.linspace(25, 30, 50)}, index=idx)
        pos = nf99.build_miner_gold_targets(
            prices, lookback=21, entry_z=1.5, exit_z=0.0, vol_target=0.10
        )
        assert (pos["GDX"] == 0.0).all()

    def test_hysteresis_bounds(self):
        idx = pd.bdate_range("2018-01-02", periods=500)
        rng = np.random.default_rng(5)
        gdx = 30 * np.exp(np.cumsum(rng.normal(0.0002, 0.015, 500)))
        gld = 120 * np.exp(np.cumsum(rng.normal(0.0001, 0.008, 500)))
        prices = pd.DataFrame({"GDX": gdx, "GLD": gld}, index=idx)
        pos = nf99.build_miner_gold_targets(
            prices, lookback=60, entry_z=2.0, exit_z=0.0, vol_target=0.10
        )
        vals = pos["GDX"].dropna().values
        assert vals.min() >= -1e-12 and vals.max() <= nf99.MAX_POS + 1e-12
