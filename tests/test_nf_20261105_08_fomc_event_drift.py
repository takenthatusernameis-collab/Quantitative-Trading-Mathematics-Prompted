import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "src"))

import run_nf_20261105_08_fomc_event_drift as nf08
from qtr.backtest.engine import AssetClass


def test_gates():
    g = nf08.GATES
    assert g["min_sharpe"] == 1.0


def test_config():
    cfg = nf08.make_equity_config()
    assert cfg.asset_class == AssetClass.EQUITY
    assert cfg.allow_short is False


def test_universe():
    assert nf08.UNIVERSE == ["SPY"]
    assert nf08.DATA_START == "2015-01-01"


def test_build_daily_targets_causal():
    import numpy as np
    import pandas as pd

    dates = pd.date_range("2015-01-26", periods=6, freq="B")
    prices = pd.DataFrame({"SPY": [100.0] * 6}, index=dates)
    t = nf08.build_daily_targets(prices, hold_days=1)
    assert "target" in t.columns
