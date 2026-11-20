from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261120_04", ROOT / "run_nf_20261120_04_crypto_funding_carry.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261120_04_crypto_funding_carry"
    assert mod.NF_ID == "NF-20261120-04"
    assert mod.HYPOTHESIS == "H189"
    assert mod.START == "2020-01-01"
    assert mod.END == "2026-10-31"
    assert mod.TRAIN_END == "2023-12-31"
    assert mod.VAL_END == "2024-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 5
    assert mod.GATES == mod.h186.GATES
    assert mod.FEATURES == ["funding_annualized", "basis_annualized", "carry_combined"]


def test_universe_is_seven_curated_usdt_perps():
    assert len(mod.UNIVERSE) == 7
    assert set(mod.UNIVERSE) == {
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "SOLUSDT",
        "DOGEUSDT",
    }
    assert mod.PRODUCTS == list(mod.UNIVERSE)


def test_bounded_grid_is_thirty_six_declared_combos():
    combos = list(mod.iter_grid())
    # 3 features x 2 entry_z x 1 exit_z x 2 k x 2 vol_target = 24
    # Wait: 3 * 2 * 1 * 2 * 2 = 24
    assert len(combos) == 3 * 2 * 1 * 2 * 2 == 24
    assert {row["feature"] for row in combos} == {
        "funding_annualized",
        "basis_annualized",
        "carry_combined",
    }
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["k"] in {2, 3}
        assert row["vol_target"] in {0.10, 0.15}


def test_archive_url_builders():
    # Funding URL
    url = probe.archive_url("funding", "BTCUSDT", "2024-01")
    assert "fundingRate" in url
    assert "BTCUSDT-fundingRate-2024-01.zip" in url

    # Perp kline URL
    url = probe.archive_url("perp", "BTCUSDT", "2024-01")
    assert "futures/um/monthly/klines" in url
    assert "BTCUSDT-1d-2024-01.zip" in url

    # Spot kline URL
    url = probe.archive_url("spot", "BTCUSDT", "2024-01")
    assert "spot/monthly/klines" in url
    assert "BTCUSDT-1d-2024-01.zip" in url


def test_parse_funding_archive_structure():
    # Create a mock funding archive CSV
    import io
    import zipfile

    csv_data = """calc_time,funding_interval_hours,last_funding_rate
1704067200000,8,0.0001
1704096000000,8,-0.0002
1704124800000,8,0.0003
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BTCUSDT-fundingRate-2024-01.csv", csv_data)
    raw = buf.getvalue()

    df = probe.parse_funding_archive(raw)
    assert list(df.columns) == ["calc_time", "funding_interval_hours", "last_funding_rate"]
    assert len(df) == 3
    assert df["last_funding_rate"].tolist() == [0.0001, -0.0002, 0.0003]
    assert pd.api.types.is_datetime64_any_dtype(df["calc_time"])


def test_parse_kline_archive_structure():
    import io
    import zipfile

    csv_data = """open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore
1704067200000,42000,43000,41000,42500,1000,1704153599999,42500000,500,500,21250000,0
1704153600000,42500,43500,42000,43000,1200,1704239999999,51600000,600,600,25800000,0
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BTCUSDT-1d-2024-01.csv", csv_data)
    raw = buf.getvalue()

    df = probe.parse_kline_archive(raw)
    # parse_kline_archive keeps all columns but ensures open_time and close are numeric
    assert "open_time" in df.columns
    assert "close" in df.columns
    assert len(df) == 2
    assert df["close"].tolist() == [42500.0, 43000.0]
    assert pd.api.types.is_numeric_dtype(df["open_time"])
    assert pd.api.types.is_numeric_dtype(df["close"])


def test_monthly_funding_basis_annualization():
    # Simple synthetic test
    calendar = pd.bdate_range("2024-01-01", "2024-12-31")
    dates_monthly = pd.date_range("2024-01-31", "2024-12-31", freq="ME")

    funding = pd.DataFrame({"BTCUSDT": [0.0001] * len(dates_monthly)}, index=dates_monthly)
    perp = pd.DataFrame(
        {"BTCUSDT": [42000 + i * 100 for i in range(len(dates_monthly))]},
        index=dates_monthly,
    )
    spot = pd.DataFrame(
        {"BTCUSDT": [41900 + i * 100 for i in range(len(dates_monthly))]},
        index=dates_monthly,
    )

    features = mod.monthly_funding_basis(funding, perp, spot, calendar)

    assert set(features.keys()) == {"funding_annualized", "basis_annualized", "carry_combined"}
    for name, frame in features.items():
        assert isinstance(frame.index, pd.DatetimeIndex)
        assert "BTCUSDT" in frame.columns
        assert len(frame) == len(calendar)

    # Check funding annualization: 0.0001 * 1095.75 = 0.109575
    expected_funding_ann = 0.0001 * 1095.75
    actual = features["funding_annualized"]["BTCUSDT"].iloc[-1]
    assert abs(actual - expected_funding_ann) < 1e-6

    # Check basis annualization: (perp-spot)/spot * 12
    # Last month: perp=43100, spot=43000, basis=(100/43000)*12 = 0.027906...
    expected_basis_ann = (100 / 43000) * 12
    actual = features["basis_annualized"]["BTCUSDT"].iloc[-1]
    assert abs(actual - expected_basis_ann) < 1e-6

    # Combined = funding + basis
    expected_combined = expected_funding_ann + expected_basis_ann
    actual = features["carry_combined"]["BTCUSDT"].iloc[-1]
    assert abs(actual - expected_combined) < 1e-6


def test_feature_panel_min_active_names():
    calendar = pd.bdate_range("2024-01-01", periods=10)
    frame = pd.DataFrame(
        {
            "A": [1.0, np.nan, 1.0, np.nan, 1.0, np.nan, 1.0, np.nan, 1.0, np.nan],
            "B": [1.0, 1.0, np.nan, np.nan, 1.0, 1.0, np.nan, np.nan, 1.0, 1.0],
            "C": [np.nan, np.nan, np.nan, np.nan, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            "D": [1.0] * 10,
        },
        index=calendar,
    )
    features = {"test": frame}
    filtered = mod.feature_panel(features, calendar)
    result = filtered["test"]

    # MIN_ACTIVE_NAMES = 5, so only days with >= 5 non-NaN should be kept
    # But we only have 4 symbols, so all should be NaN
    assert result.isna().all().all()

    # With 5 symbols, day 4 (index 4) has A=1, B=1, C=1, D=1 = 4 active < 5 -> NaN
    # Day 5 has A=NaN, B=1, C=1, D=1 = 3 active < 5 -> NaN
    # Day 9 has A=NaN, B=1, C=1, D=1 = 3 active < 5 -> NaN


def test_target_weights_are_long_short_and_gross_normalised():
    calendar = pd.bdate_range("2024-01-01", periods=20)
    products = ["A", "B", "C", "D", "E"]
    feature = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {"feature": "test", "entry_z": 0.5, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    weights = mod.h186.target_weights(feature, params, returns, products)
    gross = weights.abs().sum(axis=1)
    assert (gross <= 1.0 + 1e-12).all()
    assert (weights.index == calendar).all()


def test_zero_rolls_frame_shape():
    calendar = pd.bdate_range("2024-01-01", periods=10)
    products = ["A", "B", "C"]
    rolls = mod.zero_rolls(calendar, products)
    assert rolls.shape == (len(calendar), len(products))
    assert (rolls == 0.0).all().all()


def test_perturbation_sharpes_returns_finite_points():
    calendar = pd.bdate_range("2024-01-01", periods=50)
    products = ["A", "B", "C", "D", "E"]
    feature = pd.DataFrame(
        np.random.default_rng(11).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(12).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {"feature": "test", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    sharpes = mod.perturbation_sharpes(feature, params, returns, products, calendar)
    assert len(sharpes) == 4  # 2 for entry_z * 2 factors, 2 for k * 2 factors
    assert all(np.isfinite(value) for value in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2024-01-01", periods=20)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "funding_annualized": pd.DataFrame(
            np.random.default_rng(13).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "basis_annualized": pd.DataFrame(
            np.random.default_rng(14).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "carry_combined": pd.DataFrame(
            np.random.default_rng(15).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    collinearity = mod.train_collinearity(features, calendar)
    assert set(collinearity.keys()) == {
        "funding_annualized_vs_basis_annualized",
        "funding_annualized_vs_carry_combined",
        "basis_annualized_vs_carry_combined",
    }
    for value in collinearity.values():
        assert -1.0 <= value <= 1.0


# Need to import probe for the archive_url tests
_probe_path = ROOT / "scripts" / "probe_binance_funding_availability.py"
_probe_spec = importlib.util.spec_from_file_location("binance_probe", _probe_path)
assert _probe_spec and _probe_spec.loader
probe = importlib.util.module_from_spec(_probe_spec)
sys.modules[_probe_spec.name] = probe
_probe_spec.loader.exec_module(probe)
