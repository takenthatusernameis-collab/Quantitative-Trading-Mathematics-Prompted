from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261114_01", ROOT / "run_nf_20261114_01_commodity_termstructure_carry.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

DATES = pd.bdate_range("2024-01-02", periods=60)
PRODUCTS = ["CU", "AL", "RB"]


def _json_cross_section(rows: list[dict]) -> bytes:
    return json.dumps({"o_curinstrument": rows}).encode()


def _shfe_row(product: str, delivery: str, settle: str, oi: str) -> dict:
    return {
        "PRODUCTGROUPID": f"{product:<8}",
        "PRODUCTID": f"{product.lower()}_f",
        "DELIVERYMONTH": delivery,
        "SETTLEMENTPRICE": settle,
        "OPENINTEREST": oi,
    }


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261114_01_commodity_termstructure_carry"
    assert mod.NF_ID == "NF-20261114-01"
    assert mod.HYPOTHESIS == "H184"
    assert mod.START == "2016-01-04"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2023-06-30"
    assert mod.VAL_END == "2024-12-31"
    assert mod.GRID == {
        "entry_z": [0.5, 1.0, 1.5],
        "exit_z": [0.0, 0.5],
        "k": [1, 3, 5],
        "vol_target": [0.10, 0.15],
    }
    assert mod.GATES == {
        "min_sharpe": 1.0,
        "min_trades": 50,
        "min_profit_factor": 1.3,
        "max_drawdown": 0.15,
        "min_walkforward_stability": 0.7,
        "min_worst_regime_sharpe": 0.3,
        "max_p_value": 0.05,
        "min_information_ratio": 0.0,
        "min_perturbed_sharpe_ratio": 0.5,
    }
    assert mod.SIDE_BPS == 5.0
    assert mod.ROLL_CROSS_BPS == 1.0
    assert mod.OPEN_INTEREST_FLOOR == 100.0
    assert mod.FIRST_DATE[("INE", "SC")] == "2018-03-26"


def test_extreme_bounded_grid():
    combos = list(mod.iter_grid())
    assert len(combos) == 3 * 2 * 3 * 2
    for params in combos:
        assert params["exit_z"] <= params["entry_z"]
        assert params["k"] in {1, 3, 5}
        assert params["vol_target"] in {0.10, 0.15}


def test_normalize_delivery_resolves_decades():
    assert mod.normalize_delivery("2402", dt.date(2024, 1, 2)) == "202402"
    assert mod.normalize_delivery("2402", dt.date(2019, 12, 2)) == "202402"
    assert mod.normalize_delivery("202401", dt.date(2024, 1, 2)) == "202401"
    assert mod.normalize_delivery("2001", dt.date(2019, 12, 2)) == "202001"
    assert mod.normalize_delivery("TA401", dt.date(2024, 1, 2)) == ""
    assert mod.normalize_delivery("", dt.date(2024, 1, 2)) == ""


def test_parse_cross_section_keeps_four_digit_shfe_contracts():
    raw = _json_cross_section(
        [
            _shfe_row("CU", "2402", "68920", "49865"),
            _shfe_row("CU", "2403", "68990", "1234"),
            _shfe_row("X9", "2402", "100", "10"),
        ]
    )
    frame = mod.parse_cross_section("SHFE", raw, dt.date(2024, 1, 2))
    assert list(frame["product"]) == ["CU", "CU"]
    assert list(frame["delivery"]) == ["202402", "202403"]


def test_parse_cross_section_czce_six_digit():
    text = (
        "合约代码|昨结算|今开盘|最高价|最低价|今收盘|今结算|涨跌1|涨跌2|成交量|持仓量|增减量\n"
        "TA401 |4,000 |4,010 |4,020 |3,990 |4,015 |4,010 |1 |2 |10 |1,000 |0\n"
        "TA402 |3,900 |3,910 |3,920 |3,890 |3,915 |3,905 |1 |2 |5 |500 |0\n"
    ).encode()
    frame = mod.parse_cross_section("CZCE", text, dt.date(2024, 1, 2))
    assert list(frame["product"]) == ["TA", "TA"]
    assert list(frame["delivery"]) == ["202401", "202402"]


def test_front_second_excludes_delivery_month_and_thin_contracts():
    settle = pd.Series({"202401": 100.0, "202402": 90.0, "202403": 80.0})
    oi = pd.Series({"202401": 5000.0, "202402": 1000.0, "202403": 50.0})
    pick = mod.front_second(settle, oi)
    assert pick == ("202401", "202402", 100.0, 90.0)
    thin = pd.Series({"202401": 5000.0, "202402": 50.0})
    assert mod.front_second(settle, thin) is None
    assert mod.front_second(pd.Series({"202401": 100.0}), pd.Series({"202401": 5000.0})) is None


def test_term_panel_slope_formula():
    index = DATES[:3]
    settle = pd.DataFrame(
        {"202402": [100.0, 101.0, 102.0], "202404": [90.0, 91.0, 92.0]}, index=index
    )
    oi = pd.DataFrame(
        {"202402": [5000.0, 5000.0, 5000.0], "202404": [4000.0, 4000.0, 4000.0]}, index=index
    )
    term = mod.term_panel({"settle": settle, "oi": oi}, index)
    expected = math.log(100.0 / 90.0) * 12.0 / 2
    assert np.isclose(term["slope"].iloc[0], expected)
    assert term["front"].iloc[0] == "202402"
    assert term["second"].iloc[0] == "202404"
    assert bool(term["active"].all())


def test_term_panel_marks_missing_dates_inactive():
    index = DATES[:2]
    settle = pd.DataFrame({"202402": [100.0, np.nan], "202404": [90.0, np.nan]}, index=index)
    oi = pd.DataFrame({"202402": [5000.0, np.nan], "202404": [4000.0, np.nan]}, index=index)
    term = mod.term_panel({"settle": settle, "oi": oi}, index)
    assert bool(term["active"].iloc[0])
    assert not bool(term["active"].iloc[1])


def test_held_returns_use_same_contract_across_a_roll():
    index = DATES[:4]
    settle = pd.DataFrame(
        {"202401": [100.0, 110.0, 121.0, np.nan], "202402": [90.0, 95.0, 100.0, 105.0]},
        index=index,
    )
    oi = pd.DataFrame(1e6, index=index, columns=settle.columns)
    panel = {"settle": settle, "oi": oi}
    term = mod.term_panel(panel, index)
    # 202401 is excluded from the signal exactly in its delivery month only;
    # here it stays the front until day 2, then rolls to 202402.
    term["front"] = pd.Series(["202401", "202401", "202402", "202402"], index=index)
    out = mod.held_returns(panel, term, index)
    # Day 0 has no held contract; day 1 holds 202401 priced 100 -> 110.
    assert np.isnan(out["return"].iloc[0])
    assert np.isclose(out["return"].iloc[1], 0.10)
    # Day 2 is still the old front (rolled at the close of day 2): 110 -> 121.
    assert np.isclose(out["return"].iloc[2], 0.10)
    assert out["roll"].iloc[2] == 0.0
    # Day 3 holds the new front 202402: 100 -> 105.  A spliced front series
    # would have booked 105/121 - 1 = -0.132 (the roll gap as a fake loss).
    assert np.isclose(out["return"].iloc[3], 0.05)
    assert out["roll"].iloc[3] == 1.0


def test_held_returns_skip_when_held_contract_has_no_price():
    index = DATES[:3]
    settle = pd.DataFrame(
        {"202402": [90.0, np.nan, 92.0], "202403": [80.0, 81.0, 82.0]}, index=index
    )
    oi = pd.DataFrame(1e6, index=index, columns=settle.columns)
    panel = {"settle": settle, "oi": oi}
    term = mod.term_panel(panel, index)
    term["front"] = pd.Series(["202402", "202402", "202402"], index=index)
    out = mod.held_returns(panel, term, index)
    assert np.isnan(out["return"].iloc[1])  # held contract unquoted on day 1
    assert np.isnan(out["return"].iloc[2])  # prior day price missing


def test_cross_sectional_z_is_cross_sectional_and_needs_two_products():
    slope = pd.DataFrame({"CU": [1.0, 1.0], "AL": [2.0, 1.0], "RB": [3.0, 3.0]}, index=DATES[:2])
    z = mod.cross_sectional_z(slope)
    assert np.isclose(z["CU"].iloc[0], -1.224744871391589)
    assert np.isclose(z.iloc[0].mean(), 0.0)
    lone = pd.DataFrame({"CU": [1.0, 2.0], "AL": [np.nan, np.nan]}, index=DATES[:2])
    assert mod.cross_sectional_z(lone).isna().all().all()


def test_signal_weights_long_top_k_short_bottom_k_and_gross_one():
    slope = pd.DataFrame({"A": [1.0] * 30, "B": [2.0] * 30, "C": [3.0] * 30}, index=DATES[:30])
    z = mod.cross_sectional_z(slope)
    weights = mod.signal_weights(z, entry_z=0.5, exit_z=0.0, k=1)
    assert np.isclose(weights["C"].iloc[-1], 0.5)
    assert np.isclose(weights["A"].iloc[-1], -0.5)
    assert weights["B"].iloc[-1] == 0.0
    assert np.isclose(weights.iloc[-1].abs().sum(), 1.0)


def test_signal_weights_hysteresis_exits_only_below_exit_z():
    values = [3.0, 2.0, 1.0, 0.5, 0.0, -0.5]
    slope = pd.DataFrame(
        {"A": values, "B": [0.0] * len(values), "C": [-1.0] * len(values)},
        index=DATES[: len(values)],
    )
    z = mod.cross_sectional_z(slope)
    weights = mod.signal_weights(z, entry_z=1.0, exit_z=0.5, k=1)
    held = weights["A"].to_numpy()
    assert held[0] == 1.0  # single open leg -> gross-normalized to one
    assert held[3] == 0.5  # z still above exit_z -> hold
    assert held[5] == 0.0  # z fell to 0 -> exit


def test_signal_weights_no_lookahead():
    rng = np.random.default_rng(7)
    values = rng.normal(size=(40, 3))
    slope = pd.DataFrame(values, index=DATES[:40], columns=PRODUCTS)
    base = mod.signal_weights(mod.cross_sectional_z(slope), 1.0, 0.5, 1)
    future = slope.copy()
    future.iloc[-1] = 1e6
    changed = mod.signal_weights(mod.cross_sectional_z(future), 1.0, 0.5, 1)
    pd.testing.assert_frame_equal(base.iloc[:-1], changed.iloc[:-1])


def test_signal_weights_drops_inactive_positions():
    slope = pd.DataFrame(
        {"A": [3.0, 3.0, np.nan], "B": [-3.0, -3.0, -3.0], "C": [0.0, 0.0, 0.0]},
        index=DATES[:3],
    )
    weights = mod.signal_weights(mod.cross_sectional_z(slope), 1.0, 0.5, 1)
    assert weights["A"].iloc[1] != 0.0
    assert weights["A"].iloc[2] == 0.0


def test_vol_scale_delevers_only():
    index = pd.bdate_range("2024-01-02", periods=100)
    calm = pd.Series(np.repeat(0.001, 100), index=index)
    assert (mod.vol_scale(calm, 0.15) <= 1.0).all()
    wild = pd.Series(np.tile([0.05, -0.05], 50), index=index)
    scale = mod.vol_scale(wild, 0.15)
    assert (scale.tail(40) < 1.0).all()
    assert (scale > 0).all()
    flat = pd.Series(np.repeat(0.001, 100), index=index)
    assert (mod.vol_scale(flat, 0.15) == 1.0).all()  # zero vol never levers up


def test_backtest_shifts_one_bar_and_never_earns_same_day():
    index = DATES[:4]
    weights = pd.DataFrame({"A": [1.0, 1.0, 1.0, 1.0]}, index=index)
    returns = pd.DataFrame({"A": [0.0, 0.10, 0.0, 0.0]}, index=index)
    rolls = pd.DataFrame({"A": [0.0, 0.0, 0.0, 0.0]}, index=index)
    result = mod.backtest_metrics(weights, returns, rolls, side_bps=0.0, roll_bps=0.0)
    assert np.isclose(result["returns"].iloc[0], 0.0)  # nothing held yet
    assert np.isclose(result["returns"].iloc[1], 0.10)  # weight[0] * return[1]
    assert np.isclose(result["returns"].iloc[2], 0.0)


def test_backtest_charges_turnover_when_the_position_is_established():
    index = DATES[:4]
    weights = pd.DataFrame({"A": [1.0, 1.0, 0.0, 0.0]}, index=index)
    returns = pd.DataFrame({"A": [0.0, 0.0, 0.0, 0.0]}, index=index)
    rolls = pd.DataFrame({"A": [0.0, 0.0, 0.0, 0.0]}, index=index)
    result = mod.backtest_metrics(weights, returns, rolls, side_bps=5.0, roll_bps=1.0)
    # executed = shift(1) -> [0, 1, 1, 0]: the 1.0 leg is opened on day 1.
    assert result["returns"].iloc[1] == pytest.approx(-5.0 / 1e4)
    assert result["returns"].iloc[3] == pytest.approx(-5.0 / 1e4)
    assert result["trades"] == 2


def test_backtest_charges_roll_crossing_on_the_held_notional():
    index = DATES[:3]
    weights = pd.DataFrame({"A": [1.0, 1.0, 1.0]}, index=index)
    returns = pd.DataFrame({"A": [0.0, 0.0, 0.0]}, index=index)
    rolls = pd.DataFrame({"A": [0.0, 1.0, 0.0]}, index=index)
    result = mod.backtest_metrics(weights, returns, rolls, side_bps=0.0, roll_bps=1.0)
    # Day 1 holds weight[0]=1.0 and the contract rolls -> 1 bp.
    assert result["returns"].iloc[1] == pytest.approx(-1.0 / 1e4)


def test_metrics_helpers_fail_closed():
    assert mod.annualized_sharpe(pd.Series([0.01])) == 0.0
    assert mod.annualized_sharpe(pd.Series([0.0] * 30, dtype=float)) == 0.0
    assert mod.profit_factor(pd.Series([0.01, -0.01])) == pytest.approx(1.0)
    assert mod.profit_factor(pd.Series([0.01, 0.02])) == float("inf")
    assert mod.profit_factor(pd.Series([-0.01, -0.02])) == 0.0
    flat = pd.Series([1.0] * 30)
    assert mod.max_drawdown(flat) == 0.0
    assert mod.worst_rolling_sharpe(pd.Series(np.repeat(0.001, 30)), window=252) > 0


def test_passive_long_weights_equal_weight_over_active_products():
    returns = pd.DataFrame({"A": [0.01, np.nan], "B": [0.02, 0.03]}, index=DATES[:2])
    weights = mod.passive_long_weights(returns, DATES[:2])
    assert np.isclose(weights.iloc[0].sum(), 1.0)
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[1]["B"] == 1.0
    assert weights.iloc[1]["A"] == 0.0


def test_random_weights_match_active_leg_count_and_are_seeded():
    weights = pd.DataFrame({"A": [0.5, 0.0], "B": [-0.5, 0.5], "C": [0.0, -0.5]}, index=DATES[:2])
    returns = pd.DataFrame({"A": [0.0, 0.0], "B": [0.0, 0.0], "C": [0.0, 0.0]}, index=DATES[:2])
    first = mod.random_weights(weights, returns, seed=42)
    second = mod.random_weights(weights, returns, seed=42)
    pd.testing.assert_frame_equal(first, second)
    assert int((first.iloc[0] != 0).sum()) == 2
    assert int((first.iloc[1] != 0).sum()) == 2


def test_perturbation_returns_six_finite_sharpes():
    rng = np.random.default_rng(11)
    index = pd.bdate_range("2024-01-02", periods=200)
    slope = pd.DataFrame(rng.normal(size=(200, 3)) * 0.1, index=index, columns=PRODUCTS)
    returns = pd.DataFrame(rng.normal(size=(200, 3)) * 0.01, index=index, columns=PRODUCTS)
    rolls = pd.DataFrame(0.0, index=index, columns=PRODUCTS)
    selected = {"entry_z": 1.0, "exit_z": 0.5, "k": 1, "vol_target": 0.15}
    sharpes = mod.perturbation_sharpes(slope, selected, returns, rolls, PRODUCTS, index)
    assert len(sharpes) == 6
    assert all(np.isfinite(value) for value in sharpes)


def test_walk_forward_score_requires_enough_history():
    slope = pd.DataFrame({"A": [0.0], "B": [1.0]}, index=DATES[:1])
    returns = pd.DataFrame(0.0, index=DATES[:1], columns=["A", "B"])
    rolls = pd.DataFrame(0.0, index=DATES[:1], columns=["A", "B"])
    params = {"entry_z": 1.0, "exit_z": 0.5, "k": 1, "vol_target": 0.10}
    assert mod.walk_forward_score(slope, params, returns, rolls, ["A", "B"], DATES[:1]) == -999.0


def test_fetch_into_cache_resumes_and_marks_missing(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake(source, day, timeout=30.0, retries=0):
        calls["n"] += 1
        return b'{"o_curinstrument": []}'

    monkeypatch.setattr(mod, "fetch", fake)
    day = dt.date(2024, 1, 2)
    assert mod.fetch_into_cache("SHFE", day, tmp_path) == "OK"
    assert mod.fetch_into_cache("SHFE", day, tmp_path) == "HIT"
    assert calls["n"] == 1
    assert mod.cache_path("SHFE", day, tmp_path).exists()

    def missing(source, d, timeout=30.0, retries=0):
        return None

    monkeypatch.setattr(mod, "fetch", missing)
    assert mod.fetch_into_cache("INE", day, tmp_path) == "MISSING"
    assert mod.miss_path("INE", day, tmp_path).exists()
    assert mod.fetch_into_cache("INE", day, tmp_path) == "MISSING"
    assert calls["n"] == 1  # the miss marker prevented a second request


def test_fetch_into_cache_counts_transport_errors(tmp_path, monkeypatch):
    def broken(source, day, timeout=30.0, retries=0):
        raise mod.FetchError("boom")

    monkeypatch.setattr(mod, "fetch", broken)
    monkeypatch.setattr(mod.time, "sleep", lambda _seconds: None)
    assert mod.fetch_into_cache("SHFE", dt.date(2024, 1, 3), tmp_path) == "ERROR"


def test_ensure_cached_dedupes_venues(tmp_path, monkeypatch):
    seen = []

    def fake(source, day, cache_dir=None, retries=2, retry_delay=1.0):
        seen.append((source, str(day.date())))
        return "OK"

    monkeypatch.setattr(mod, "fetch_into_cache", fake)
    calendar = pd.bdate_range("2018-03-26", periods=3)
    provenance = mod.ensure_cached(
        [("SHFE", "RB"), ("SHFE", "CU"), ("INE", "SC")], calendar, cache_dir=tmp_path, workers=1
    )
    assert len(seen) == 6  # 3 SHFE dates + 3 INE dates, not 6 per extra SHFE product
    assert provenance["requests"] == 6
    assert provenance["status_counts"]["SHFE"]["OK"] == 3
    assert "{YYYYMMDD}" in provenance["url_patterns"]["SHFE"]


def test_load_product_data_handles_empty_cache(tmp_path):
    calendar = pd.bdate_range("2024-01-02", periods=3)
    panels = mod.load_product_data([("SHFE", "CU")], calendar, cache_dir=tmp_path)
    assert panels["SHFE:CU"]["settle"].shape == (3, 0)


def test_load_product_data_reads_cached_cross_sections(tmp_path):
    calendar = pd.bdate_range("2024-01-02", periods=2)
    raw = _json_cross_section(
        [
            _shfe_row("CU", "2402", "68920", "49865"),
            _shfe_row("CU", "2403", "68990", "1234"),
        ]
    )
    path = mod.cache_path("SHFE", calendar[0], tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    panels = mod.load_product_data([("SHFE", "CU")], calendar, cache_dir=tmp_path)
    settle = panels["SHFE:CU"]["settle"]
    assert list(settle.columns) == ["202402", "202403"]
    assert settle.loc[calendar[0], "202402"] == 68920.0
    assert np.isnan(settle.loc[calendar[1], "202402"])


def test_artifact_dir_honors_explicit_path(tmp_path):
    target = tmp_path / "art"
    resolved = mod.artifact_dir(str(target))
    assert resolved == target.resolve()
    assert resolved.exists()
