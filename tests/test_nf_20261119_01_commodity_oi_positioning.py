from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261119_01", ROOT / "run_nf_20261119_01_commodity_oi_positioning.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

DATES = pd.bdate_range("2024-01-02", periods=90)
PRODUCTS = ["SHFE:CU", "SHFE:AL", "SHFE:RB"]
CONTRACTS = ["202402", "202403", "202404"]


def _panel(settle_values, oi_values, contracts=CONTRACTS, index=DATES) -> dict:
    settle = pd.DataFrame(settle_values, index=index, columns=contracts, dtype=float)
    oi = pd.DataFrame(oi_values, index=index, columns=contracts, dtype=float)
    return {"settle": settle, "oi": oi}


def _flat_panel(level: float = 100.0, oi: float = 1000.0, n: int = len(DATES)) -> dict:
    settle = np.full((n, len(CONTRACTS)), level)
    open_interest = np.full((n, len(CONTRACTS)), oi)
    return _panel(settle, open_interest)


def _terms(panels: dict, keys=PRODUCTS) -> dict:
    return {product: mod.h184.term_panel(panels[product], DATES) for product in keys}


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261119_01_commodity_oi_positioning"
    assert mod.NF_ID == "NF-20261119-01"
    assert mod.HYPOTHESIS == "H185"
    assert mod.START == "2016-01-04"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2023-06-30"
    assert mod.VAL_END == "2024-12-31"
    assert mod.OI_FLOOR == 100.0
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.ROLL_CROSS_BPS == 1.0
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["oi_growth_21", "oi_growth_63", "front_share"]
    assert mod.OI_GROWTH_WINDOW == {"oi_growth_21": 21, "oi_growth_63": 63}


def test_bounded_grid_is_seventy_two_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 3 * 3 * 2 * 2 * 2 == 72
    assert {row["feature"] for row in combos} == {"oi_growth_21", "oi_growth_63", "front_share"}
    for row in combos:
        assert row["exit_z"] <= row["entry_z"]
        assert row["k"] in {1, 2}
        assert row["vol_target"] in {0.10, 0.15}


def test_reuses_h184_engine_instead_of_forking():
    assert mod.h184.EXPERIMENT == "nf_20261114_01_commodity_termstructure_carry"
    assert mod.h184.OI_FLOOR == mod.OI_FLOOR
    assert mod.h184.held_returns is mod.h184.held_returns


def test_total_open_interest_sums_only_tradable_contracts():
    settle = np.array([[100.0, 100.0, 100.0], [100.0, 0.0, 100.0], [100.0, 100.0, 100.0]])
    oi = np.array([[500.0, 400.0, 300.0], [500.0, 999.0, 300.0], [500.0, 99.0, 300.0]])
    panel = _panel(settle, oi, index=DATES[:3])
    totals = mod.total_open_interest(panel)
    assert totals.iloc[0] == 1200.0
    assert totals.iloc[1] == 800.0
    assert totals.iloc[2] == 800.0
    assert totals.isna().sum() == 0


def test_total_open_interest_is_nan_when_no_contract_is_tradable():
    settle = np.zeros((len(DATES), len(CONTRACTS)))
    oi = np.full((len(DATES), len(CONTRACTS)), 500.0)
    totals = mod.total_open_interest(_panel(settle, oi))
    assert totals.isna().all()


def test_front_share_uses_the_front_contract_and_stays_bounded():
    settle = np.full((len(DATES), len(CONTRACTS)), 100.0)
    oi = np.full((len(DATES), len(CONTRACTS)), 1000.0)
    oi[:, 0] = 2000.0
    panels = {product: _panel(settle.copy(), oi.copy()) for product in PRODUCTS}
    terms = _terms(panels)
    share = mod.front_share_series(panels["SHFE:CU"], terms["SHFE:CU"])
    assert share.dropna().between(0.0, 1.0).all()
    assert np.isclose(share.iloc[-1], 2000.0 / 4000.0)


def test_front_share_is_nan_when_the_front_contract_is_unknown():
    settle = np.full((len(DATES), len(CONTRACTS)), 100.0)
    oi = np.full((len(DATES), len(CONTRACTS)), 1000.0)
    panel = _panel(settle, oi)
    terms = pd.DataFrame(
        {"front": [None] * len(DATES)},
        index=DATES,
    )
    share = mod.front_share_series(panel, terms)
    assert share.isna().all()


def test_oi_growth_is_the_declared_log_ratio():
    settle = np.full((len(DATES), len(CONTRACTS)), 100.0)
    oi = np.full((len(DATES), len(CONTRACTS)), 1000.0)
    stepped = oi.copy()
    stepped[25:, :] = 2000.0
    panels = {product: _panel(settle.copy(), stepped.copy()) for product in PRODUCTS}
    features = mod.feature_panel(panels, _terms(panels), DATES, PRODUCTS)
    growth = features["oi_growth_21"]
    # Index 24 is the 21st row before index 45 (positional shift on the calendar).
    assert np.isclose(growth.iloc[45]["SHFE:CU"], np.log(2000.0 / 1000.0))
    assert growth.iloc[:21].isna().all().all()


def test_feature_panel_is_causal_no_future_information():
    settle = np.full((len(DATES), len(CONTRACTS)), 100.0)
    oi = np.linspace(1000.0, 3000.0, len(DATES))[:, None] * np.ones((1, len(CONTRACTS)))
    panels = {product: _panel(settle.copy(), oi.copy()) for product in PRODUCTS}
    terms = _terms(panels)
    baseline = mod.feature_panel(panels, terms, DATES, PRODUCTS)

    cut = 50
    mutated = {}
    for product in PRODUCTS:
        settle_two = settle.copy()
        oi_two = oi.copy()
        settle_two[cut + 1 :, :] = settle_two[cut + 1 :, :] * 3.0
        oi_two[cut + 1 :, :] = oi_two[cut + 1 :, :] * 7.0
        mutated[product] = _panel(settle_two, oi_two)
    mutated_terms = _terms(mutated)
    after = mod.feature_panel(mutated, mutated_terms, DATES, PRODUCTS)

    for name in mod.FEATURES:
        pd.testing.assert_frame_equal(baseline[name].iloc[: cut + 1], after[name].iloc[: cut + 1])


def test_train_collinearity_is_bounded_and_handles_constant_signal():
    signal = pd.DataFrame(
        {"SHFE:CU": [1.0] * len(DATES), "SHFE:AL": [2.0] * len(DATES)},
        index=DATES,
    )
    slope = pd.DataFrame(
        {"SHFE:CU": [0.01] * len(DATES), "SHFE:AL": [-0.01] * len(DATES)},
        index=DATES,
    )
    value = mod.train_collinearity(signal, slope, DATES[:60])
    assert -1.0 <= value <= 1.0


def test_artifact_dir_honors_explicit_path(tmp_path):
    path = mod.artifact_dir(str(tmp_path / "h185"))
    assert path.exists()
    assert path.resolve() == (tmp_path / "h185").resolve()
