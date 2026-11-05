import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261105_13_idiosyncratic_vol as nf13
from qtr.backtest.engine import AssetClass


class TestPreRegistration:
    def test_gates(self):
        g = nf13.GATES
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
        cfg = nf13.make_equity_config()
        assert cfg.asset_class == AssetClass.EQUITY
        assert cfg.allow_short is True
        assert cfg.max_leverage == nf13.MAX_LEVERAGE
        assert cfg.max_position_size == nf13.MAX_POS

    def test_universe_and_splits(self):
        assert nf13.SPY == "SPY"
        assert nf13.TRADEABLE == [
            "QQQ",
            "IWM",
            "EFA",
            "EEM",
            "VWO",
            "TLT",
            "AGG",
            "HYG",
            "GLD",
            "USO",
            "VNQ",
            "XLB",
        ]
        assert "SPY" not in nf13.TRADEABLE
        assert nf13.DATA_START == "2010-01-01"
        assert nf13.DATA_END == "2026-10-31"
        assert nf13.TRAIN_END == "2019-12-31"
        assert nf13.VAL_END == "2022-12-31"

    def test_grid(self):
        assert nf13.IVOL_LOOKBACKS == [63, 126, 252]
        assert nf13.QUINTILE_SHARES == [0.2, 0.33]
        assert nf13.VOL_TARGETS == [0.10, 0.15]
        grid = [
            (lb, qs, vt)
            for lb in nf13.IVOL_LOOKBACKS
            for qs in nf13.QUINTILE_SHARES
            for vt in nf13.VOL_TARGETS
        ]
        assert len(grid) == 12


class TestIvolSignal:
    def _prices(self, n=300):
        idx = pd.bdate_range("2018-01-02", periods=n)
        rng = np.random.default_rng(7)
        data = {}
        for s in nf13.TRADEABLE + [nf13.SPY]:
            data[s] = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        return pd.DataFrame(data, index=idx)

    def test_output_shape_and_bounds(self):
        prices = self._prices()
        pos = nf13.build_ivol_targets(prices, ivol_lookback=63, quintile_share=0.2, vol_target=0.10)
        assert list(pos.columns) == nf13.TRADEABLE
        assert len(pos) == len(prices)
        vals = pos.values[np.isfinite(pos.values)]
        assert (vals >= -nf13.MAX_POS - 1e-12).all()
        assert (vals <= nf13.MAX_POS + 1e-12).all()

    def test_warmup_is_flat(self):
        prices = self._prices(n=100)
        pos = nf13.build_ivol_targets(prices, ivol_lookback=63, quintile_share=0.2, vol_target=0.10)
        # IVOL needs 63 days of returns; early bars flat.
        assert float(pos.iloc[:10].abs().sum().sum()) == 0.0

    def test_only_traded_symbols_receive_weights(self):
        prices = self._prices()
        pos = nf13.build_ivol_targets(prices, ivol_lookback=63, quintile_share=0.2, vol_target=0.10)
        active = (pos.abs() > 1e-12).any(axis=0)
        assert set(active.index[active.values]) <= set(nf13.TRADEABLE)
        assert nf13.SPY not in active.index[active.values]

    def test_long_leg_has_positive_weights_short_leg_negative(self):
        # Deterministic spread: some symbols track SPY closely (low IVOL), others
        # are pure noise (high IVOL). quintile_share=0.2 on 12 symbols -> k=2
        # long and k=2 short per month-end rebalance.
        idx = pd.bdate_range("2018-01-02", periods=260)
        rng = np.random.default_rng(3)
        spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 260)))
        data = {nf13.SPY: spy}
        for s in nf13.TRADEABLE[:6]:
            data[s] = spy * 1.0001  # near-zero residual IVOL vs SPY
        for s in nf13.TRADEABLE[6:]:
            data[s] = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.05, 260)))  # high IVOL
        prices = pd.DataFrame(data, index=idx)
        pos = nf13.build_ivol_targets(prices, ivol_lookback=63, quintile_share=0.2, vol_target=0.10)
        tail = pos.iloc[100:]
        low = tail[nf13.TRADEABLE[:6]]
        high = tail[nf13.TRADEABLE[6:]]
        # Longs (positive) must come from the low-IVOL group; shorts (negative)
        # from the high-IVOL group. k=2 of each on any active rebalance day.
        assert float(high[high > 1e-12].sum().sum()) == 0.0
        assert float(low[low < -1e-12].sum().sum()) == 0.0
        active = tail[tail.abs().sum(axis=1) > 1e-12]
        if len(active) > 0:
            assert ((active > 1e-12).sum(axis=1) == 2).all()
            assert ((active < -1e-12).sum(axis=1) == 2).all()

    def test_monthly_rebalance_holds_constant(self):
        idx = pd.bdate_range("2018-01-02", periods=260)
        rng = np.random.default_rng(11)
        data = {
            s: 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 260)))
            for s in nf13.TRADEABLE + [nf13.SPY]
        }
        prices = pd.DataFrame(data, index=idx)
        pos = nf13.build_ivol_targets(prices, ivol_lookback=63, quintile_share=0.2, vol_target=0.10)
        # Between month ends the weights should be constant.
        month_ends = nf13._month_end_dates(prices.index)
        for i in range(len(month_ends) - 1):
            start = month_ends[i]
            end = month_ends[i + 1]
            seg = pos.loc[start:end].iloc[:-1]  # exclude next month-end rebalance
            first = seg.iloc[0]
            assert (seg == first.values).all(axis=None), "weights changed mid-month"
