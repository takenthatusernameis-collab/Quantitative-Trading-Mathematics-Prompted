from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261119_02", ROOT / "run_nf_20261119_02_commodity_hedging_pressure.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

REPORT_DATES = pd.date_range("2024-01-02", periods=8, freq="W-TUE")
DAILY = pd.bdate_range("2024-01-02", periods=40)
PRODUCTS = ["GLD", "SLV", "USO", "UNG", "CORN"]


def _rows() -> pd.DataFrame:
    records = []
    for code in [code for _, code in mod.UNIVERSE]:
        for i, day in enumerate(REPORT_DATES):
            records.append(
                {
                    "code": code,
                    "report_date": day,
                    "comm_long": 100.0 + i,
                    "comm_short": 200.0 + i,
                    "open_interest": 1000.0,
                }
            )
    return pd.DataFrame(records)


def _hp_weekly() -> pd.DataFrame:
    rows = _rows()
    return mod.weekly_hedging_pressure(rows, mod.UNIVERSE)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261119_02_commodity_hedging_pressure"
    assert mod.NF_ID == "NF-20261119-02"
    assert mod.HYPOTHESIS == "H186"
    assert mod.START == "2012-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.PUBLISH_LAG_DAYS == 3
    assert mod.MIN_ACTIVE_NAMES == 5
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["hp", "hp_change_4w"]


def test_universe_maps_each_etf_to_one_cftc_code():
    assert len(mod.UNIVERSE) == 9
    etfs = [etf for etf, _ in mod.UNIVERSE]
    codes = [code for _, code in mod.UNIVERSE]
    assert len(set(etfs)) == len(etfs)
    assert len(set(codes)) == len(codes)
    assert mod.PRODUCTS == etfs


def test_bounded_grid_is_sixteen_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 2 * 1 * 2 * 2 == 16
    assert {row["feature"] for row in combos} == {"hp", "hp_change_4w"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["k"] in {2, 3}
        assert row["vol_target"] in {0.10, 0.15}


def test_cftc_query_url_quotes_codes_and_filters_dates():
    url = mod.cftc_query_url(["088691", "084691"], start="2020-01-01", end="2020-12-31")
    assert url.startswith(mod.SOCRATA_URL)
    assert "088691" in url and "084691" in url
    assert "2020-01-01T00%3A00%3A00.000" in url
    assert "2020-12-31T23%3A59%3A59.999" in url
    assert "open_interest_all" in url


def test_parse_cftc_rows_coerces_and_sorts():
    rows = [
        {
            "cftc_contract_market_code": "088691",
            "report_date_as_yyyy_mm_dd": "2024-01-09T00:00:00.000",
            "open_interest_all": "1000",
            "comm_positions_long_all": "100",
            "comm_positions_short_all": "300",
        },
        {
            "cftc_contract_market_code": "088691",
            "report_date_as_yyyy_mm_dd": "2024-01-02T00:00:00.000",
            "open_interest_all": "900",
            "comm_positions_long_all": "50",
            "comm_positions_short_all": "250",
        },
    ]
    parsed = mod.parse_cftc_rows(rows)
    assert list(parsed["report_date"]) == sorted(parsed["report_date"])
    assert parsed["open_interest"].tolist() == [900.0, 1000.0]
    empty = mod.parse_cftc_rows([])
    assert empty.empty and "code" in empty.columns


def test_hedging_pressure_row_math_and_index():
    frame = pd.DataFrame(
        {
            "report_date": REPORT_DATES[:3],
            "comm_long": [100.0, 150.0, 200.0],
            "comm_short": [300.0, 250.0, 0.0],
            "open_interest": [1000.0, 500.0, 0.0],
        }
    )
    hp = mod.hedging_pressure_row(frame)
    assert hp.loc[REPORT_DATES[0]] == 0.2
    assert hp.loc[REPORT_DATES[1]] == 0.2
    assert np.isnan(hp.loc[REPORT_DATES[2]])
    assert isinstance(hp.index, pd.DatetimeIndex)


def test_weekly_hedging_pressure_requires_minimum_active_names():
    hp = _hp_weekly()
    assert list(hp.columns) == mod.PRODUCTS
    assert hp.notna().all().all()
    partial = _rows()
    dropped = {code for _, code in mod.UNIVERSE[:5]}
    partial = partial[~partial["code"].isin(dropped)]
    thinned = mod.weekly_hedging_pressure(partial, mod.UNIVERSE)
    assert thinned.isna().all().all()


def test_publication_dates_lag_three_calendar_days():
    published = mod.publication_dates(REPORT_DATES)
    assert (published - pd.DatetimeIndex(REPORT_DATES)).days.tolist() == [3] * len(REPORT_DATES)


def test_align_to_daily_has_no_lookahead():
    hp = _hp_weekly()
    published = mod.publication_dates(hp.index)
    aligned = mod.align_to_daily(hp, hp.index, DAILY)
    for day in DAILY:
        visible = published[published <= day]
        if len(visible) == 0:
            assert aligned.loc[day].isna().all()
        else:
            expected = hp.iloc[len(visible) - 1]
            pd.testing.assert_series_equal(
                aligned.loc[day], expected, check_names=False, check_freq=False
            )


def test_feature_panel_change_uses_four_report_lag():
    hp = _hp_weekly()
    features = mod.feature_panel(hp)
    assert set(features) == {"hp", "hp_change_4w"}
    change = features["hp_change_4w"]
    assert change.iloc[: mod.CHANGE_WINDOW_REPORTS].isna().all().all()
    delta = hp.iloc[4] - hp.iloc[0]
    pd.testing.assert_series_equal(
        change.iloc[4], delta, check_names=False, check_freq=False, check_exact=False
    )


def test_target_weights_are_long_short_and_gross_normalised():
    hp = _hp_weekly()
    aligned = mod.align_to_daily(hp, hp.index, DAILY)
    returns = pd.DataFrame(
        np.random.default_rng(7).normal(0, 0.01, size=(len(DAILY), len(mod.PRODUCTS))),
        index=DAILY,
        columns=mod.PRODUCTS,
    )
    params = {"feature": "hp", "entry_z": 0.5, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    weights = mod.target_weights(aligned, params, returns, mod.PRODUCTS)
    gross = weights.abs().sum(axis=1)
    assert (gross <= 1.0 + 1e-12).all()
    assert (weights.index == DAILY).all()


def test_zero_rolls_frame_shape():
    rolls = mod.zero_rolls(DAILY, PRODUCTS)
    assert rolls.shape == (len(DAILY), len(PRODUCTS))
    assert (rolls == 0.0).all().all()


def test_train_collinearity_is_bounded():
    hp = _hp_weekly()
    features = mod.feature_panel(hp)
    value = mod.train_collinearity(features, hp.index)
    assert -1.0 <= value <= 1.0


def test_perturbation_sharpes_returns_finite_points():
    hp = _hp_weekly()
    aligned = mod.align_to_daily(hp, hp.index, DAILY)
    returns = pd.DataFrame(
        np.random.default_rng(11).normal(0, 0.01, size=(len(DAILY), len(mod.PRODUCTS))),
        index=DAILY,
        columns=mod.PRODUCTS,
    )
    params = {"feature": "hp", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    sharpes = mod.perturbation_sharpes(aligned, params, returns, mod.PRODUCTS, DAILY)
    assert len(sharpes) == 4
    assert all(np.isfinite(value) for value in sharpes)
