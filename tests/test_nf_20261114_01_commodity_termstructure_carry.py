from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

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
DAY = dt.date(2024, 1, 2)


def _slope_frame(values: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(values, index=DATES[: len(values)], columns=PRODUCTS)


def test_constants():
    assert mod.EXPERIMENT == "nf_20261114_01_commodity_termstructure_carry"
    assert mod.NF_ID == "NF-20261114-01"
    assert mod.HYPOTHESIS == "H184"
    assert mod.START == "2016-01-04"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2023-06-30"
    assert mod.VAL_END == "2024-12-31"
    assert set(mod.GRID) == {"entry_z", "exit_z", "k", "vol_target"}
    assert mod.GRID["entry_z"] == [0.5, 1.0, 1.5]
    assert mod.GRID["exit_z"] == [0.0, 0.5]
    assert mod.GRID["k"] == [1, 3, 5]
    assert mod.GRID["vol_target"] == [0.10, 0.15]
    assert set(mod.GATES) == {
        "min_sharpe",
        "min_trades",
        "min_profit_factor",
        "max_drawdown",
        "min_walkforward_stability",
        "min_worst_regime_sharpe",
        "max_p_value",
        "min_information_ratio",
        "min_perturbed_sharpe_ratio",
    }
    assert mod.SIDE_BPS == 5.0
    assert mod.ROLL_CROSS_BPS == 1.0
    assert mod.OPEN_INTEREST_FLOOR == 100.0


def test_iter_grid_size_and_constraints():
    combos = list(mod._iter_grid())
    assert len(combos) == 3 * 2 * 3 * 2
    for params in combos:
        assert params["exit_z"] <= params["entry_z"]
        assert params["k"] in {1, 3, 5}
        assert params["vol_target"] in {0.10, 0.15}


def test_download_universe_all_missing(monkeypatch):
    def missing(source, day, timeout=30.0):
        return [], "MISSING"

    monkeypatch.setattr(mod, "_one_date", missing)
    frame, provenance = mod._download_universe()
    assert list(frame.columns) == [
        "date",
        "product",
        "delivery",
        "settlement",
        "open_interest",
    ]
    assert len(frame) == 0
    assert set(provenance) == {"SHFE", "INE", "CZCE", "CFFEX"}
    for source in provenance:
        assert provenance[source]["status_counts"]["MISSING"] > 0
        assert "{YYYYMMDD}" in provenance[source]["url_pattern"]


def test_fetch_cached_resumes_without_redownload(tmp_path, monkeypatch):
    mod.CACHE_DIR = tmp_path / "commodity_settlements"
    day = DAY
    calls = {"n": 0}

    def fake(source, d, timeout=30.0):
        calls["n"] += 1
        return b'{"o_curinstrument": []}'

    monkeypatch.setattr(mod, "probe_fetch", fake)
    payload, status = mod._fetch_cached("SHFE", day)
    assert status == "OK"
    assert payload == b'{"o_curinstrument": []}'
    assert calls["n"] == 1
    assert (tmp_path / "commodity_settlements" / "SHFE" / "20240102.dat").exists()
    payload, status = mod._fetch_cached("SHFE", day)
    assert status == "OK"
    assert calls["n"] == 1  # cache hit: no re-download

    def missing(source, d, timeout=30.0):
        return None

    monkeypatch.setattr(mod, "probe_fetch", missing)
    payload, status = mod._fetch_cached("INE", day)
    assert status == "MISSING"
    assert payload is None


def test_parse_cross_section_excludes_non_universe_and_delivery_window():
    raw = json.dumps(
        {
            "o_curinstrument": [
                {
                    "PRODUCTGROUPID": "CU      ",
                    "PRODUCTID": "cu_f    ",
                    "DELIVERYMONTH": "2402",
                    "SETTLEMENTPRICE": "68920",
                    "OPENINTEREST": "49865",
                },
                {
                    "PRODUCTGROUPID": "X9      ",
                    "PRODUCTID": "x9_f    ",
                    "DELIVERYMONTH": "2402",
                    "SETTLEMENTPRICE": "100",
                    "OPENINTEREST": "10",
                },
            ]
        }
    ).encode()
    frame = mod._parse_cross_section("SHFE", raw, DAY)
    assert list(frame["product"]) == ["CU"]
    assert list(frame["delivery"]) == ["2402"]


def test_parse_czce_excludes_current_delivery_month():
    text = (
        "合约代码|昨结算|今开盘|最高价|最低价|今收盘|今结算|涨跌1|涨跌2|成交量|持仓量|增减量\n"
        "TA401 |4,000 |4,010 |4,020 |3,990 |4,015 |4,010 |1 |2 |10 |1,000 |0\n"
        "TA402 |3,900 |3,910 |3,920 |3,890 |3,915 |3,905 |1 |2 |5 |500 |0\n"
    ).encode()
    frame = mod._parse_cross_section("CZCE", text, dt.date(2024, 1, 2))
    assert list(frame["product"]) == ["TA"]
    assert list(frame["delivery"]) == ["202402"]


def test_term_structure_oi_floor_and_two_nearest():
    frame = pd.DataFrame(
        {
            "date": [DAY] * 5,
            "product": ["CU", "CU", "CU", "AL", "AL"],
            "delivery": ["2401", "2402", "2403", "2401", "2402"],
            "settlement": [100.0, 90.0, 80.0, 20000.0, 19900.0],
            "open_interest": [5000.0, 1000.0, 50.0, 3000.0, 50.0],
        }
    )
    term = mod._term_structure(frame)
    assert len(term) == 1
    row = term.iloc[0]
    assert row["product"] == "CU"
    assert row["front"] == "2401"
    assert row["second"] == "2402"
    assert abs(row["slope"] - math.log(100.0 / 90.0) * 12.0) < 1e-12


def test_signal_frame_full_date_range():
    term = pd.DataFrame(
        {
            "date": [DAY, DAY],
            "product": ["CU", "CU"],
            "front": ["2401", "2402"],
            "front_settle": [100.0, 90.0],
            "slope": [0.1, 0.05],
        }
    )
    slope, settle, delivery = mod._signal_frame(term, DATES, ["CU"])
    assert list(slope.index) == list(DATES)
    assert list(slope.columns) == ["CU"]
    assert slope.iloc[0]["CU"] == 0.1
    assert settle.iloc[0]["CU"] == 100.0
    assert delivery.iloc[0]["CU"] == "2401"


def test_cross_sectional_signal_ranking():
    slope = _slope_frame(
        [[i + 1, i + 2, i * 2 + 3] for i in range(len(DATES))]
    )  # RB highest, CU lowest
    signal, spread, spread_z = mod._cross_sectional_signal(slope, k=1, entry_z=-1e9, exit_z=-1e9)
    # entry low enough to enter immediately after spread_z warm-up; exit never triggers
    active = spread_z.notna()
    assert (signal.loc[active, "RB"] == 1.0).all()
    assert (signal.loc[active, "CU"] == -1.0).all()
    assert (signal.loc[active, "AL"] == 0.0).all()
    assert spread.notna().all()
    assert spread_z.loc[active].notna().all()


def test_cross_sectional_signal_gated_off():
    slope = _slope_frame([[1.0, 2.0, 3.0]] * len(DATES))
    signal, _, _ = mod._cross_sectional_signal(slope, k=1, entry_z=1e9, exit_z=0.0)
    assert (signal == 0.0).all().all()


def test_cross_sectional_signal_insufficient_products_flat():
    slope = pd.DataFrame({"CU": [1.0, 2.0]}, index=DATES[:2]).reindex(index=DATES, columns=PRODUCTS)
    signal, spread, _ = mod._cross_sectional_signal(slope, k=1, entry_z=-1e9, exit_z=-1e9)
    assert (signal == 0.0).all().all()
    assert spread.isna().all()


def test_no_lookahead_signal_only_depends_on_past():
    slope = _slope_frame([[i, i + 1, i + 2] for i in range(len(DATES))])
    signal, _, _ = mod._cross_sectional_signal(slope, k=1, entry_z=-1e9, exit_z=-1e9)
    baseline = signal.copy()
    future = slope.copy()
    future.iloc[-1] = 1e6  # change the last date only
    signal2, _, _ = mod._cross_sectional_signal(future, k=1, entry_z=-1e9, exit_z=-1e9)
    pd.testing.assert_frame_equal(signal.iloc[:-1], signal2.iloc[:-1])


def test_execute_shifts_signal_by_one_bar():
    dates = DATES[:4]
    signal = pd.DataFrame({"A": [1.0, -1.0, 0.5, 0.0]}, index=dates)
    scale = pd.Series([1.0, 2.0, 1.0, 1.0], index=dates)
    returns = pd.DataFrame({"A": [0.01, 0.02, -0.01, 0.03]}, index=dates)
    changed = pd.DataFrame(False, index=dates, columns=["A"])
    _, _, _, executed = mod._execute(signal, scale, returns, changed)
    assert executed.iloc[0]["A"] == 0.0  # nothing to shift into the first bar
    assert executed.iloc[1]["A"] == 1.0  # signal[0] * scale[0]
    assert executed.iloc[2]["A"] == -1.0  # signal[1] * scale[1] = -2.0, leverage-capped to -1.0


def test_execute_applies_turnover_and_roll_costs():
    dates = DATES[:3]
    signal = pd.DataFrame({"A": [1.0, 1.0, 0.0]}, index=dates)
    scale = pd.Series([1.0, 1.0, 1.0], index=dates)
    returns = pd.DataFrame(0.0, index=dates, columns=["A"])
    changed = pd.DataFrame({"A": [False, True, False]}, index=dates)  # front changes at t=1
    strat, _, cost, executed = mod._execute(signal, scale, returns, changed)
    # executed = shift(1)(signal): [0, 1, 1]
    assert executed.iloc[0]["A"] == 0.0
    assert executed.iloc[1]["A"] == 1.0  # position formed at t=0 holds into t=1
    assert executed.iloc[2]["A"] == 1.0  # held again into t=2
    # t=0: flat -> no cost; t=1: establish 1.0 -> 5 bps turnover; no prior position -> no roll
    assert cost.iloc[0] == 0.0
    assert cost.iloc[1] == 5.0 / 1e4
    # t=2: keep position (no turnover); front change at t=1 already crossed -> no new roll
    assert cost.iloc[2] == 0.0
    assert strat.iloc[0] == 0.0
    assert strat.iloc[1] == -5.0 / 1e4
    assert strat.iloc[2] == 0.0


def test_vol_scale_flatlining():
    signal = pd.DataFrame({"A": [1.0, -1.0, 0.5]}, index=DATES[:3])
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02]}, index=DATES[:3])
    scale = mod._vol_scale(signal, returns, 0.15)
    assert len(scale) == 3


def test_front_returns_and_flags():
    settle = pd.DataFrame({"A": [100.0, 100.0, 102.0]}, index=DATES[:3])
    delivery = pd.DataFrame({"A": ["2401", "2401", "2402"]}, index=DATES[:3])
    returns, changed = mod._front_returns(settle, delivery)
    assert np.isclose(returns.iloc[1]["A"], 0.0)
    assert np.isclose(returns.iloc[2]["A"], 0.02)
    assert not bool(changed.iloc[0]["A"])
    assert not bool(changed.iloc[1]["A"])
    assert bool(changed.iloc[2]["A"])


def test_backtest_ledgers():
    dates = DATES
    signal = pd.DataFrame(0.0, index=dates, columns=["A"])
    signal.iloc[10:30] = 1.0
    scale = pd.Series(1.0, index=dates)
    returns = pd.DataFrame(np.repeat(0.001, len(dates)), index=dates, columns=["A"])
    changed = pd.DataFrame(False, index=dates, columns=["A"])
    bt = mod._backtest(signal, scale, returns, changed, dates)
    assert set(bt) >= {
        "sharpe",
        "profit_factor",
        "max_drawdown",
        "trades",
        "periods",
        "total_return",
        "worst_regime_rolling252_sharpe",
        "equity",
        "returns",
        "executed",
        "cost_bps_sum",
    }
    assert len(bt["equity"]) == len(dates)
    assert len(bt["returns"]) == len(dates)
    assert bt["executed"].shape == (len(dates), 1)


def test_wf_score_returns_float():
    dates = DATES
    signal = pd.DataFrame(0.0, index=dates, columns=["A"])
    scale = pd.Series(1.0, index=dates)
    returns = pd.DataFrame(np.repeat(0.001, len(dates)), index=dates, columns=["A"])
    changed = pd.DataFrame(False, index=dates, columns=["A"])
    score = mod._wf_score(signal, scale, returns, changed, dates, n_folds=4)
    assert isinstance(score, float)
    assert np.isfinite(score)


def test_benchmark_weights_fully_invested():
    settle = pd.DataFrame({"A": [100.0, np.nan], "B": [200.0, 201.0]}, index=DATES[:2])
    weights = mod._benchmark_weights(settle)
    assert np.isclose(weights.iloc[0].sum(), 1.0)
    assert np.isclose(weights.iloc[1]["B"], 1.0)
    assert weights.iloc[0]["A"] == 0.5


def test_information_ratio_and_pvalue_shapes():
    a = pd.Series(np.repeat(0.001, len(DATES)), index=DATES) + np.linspace(
        -0.0005, 0.0005, len(DATES)
    )
    b = pd.Series(np.repeat(0.0005, len(DATES)), index=DATES)
    ir = mod._information_ratio(a, b)
    p = mod._benchmark_pvalue(a, b, n_boot=200)
    assert np.isfinite(ir) and ir > 0
    assert 0.0 <= p <= 1.0


def test_perturbation_returns_finite_values():
    slope = _slope_frame([[i, i + 1, i + 2] for i in range(len(DATES))])
    returns = pd.DataFrame({p: np.repeat(0.001, len(DATES)) for p in PRODUCTS}, index=DATES)
    changed = pd.DataFrame(False, index=DATES, columns=PRODUCTS)
    selected = {"entry_z": 1.0, "exit_z": 0.5, "k": 1, "vol_target": 0.15}
    sharpes = mod._perturbation_oos_sharpes(slope, returns, changed, DATES, selected)
    assert len(sharpes) == 6  # 3 params x 2 perturbed values
    assert all(np.isfinite(v) for v in sharpes)


def test_gates_keys_drive_summary_keys():
    assert set(mod.GATES) == {
        "min_sharpe",
        "min_trades",
        "min_profit_factor",
        "max_drawdown",
        "min_walkforward_stability",
        "min_worst_regime_sharpe",
        "max_p_value",
        "min_information_ratio",
        "min_perturbed_sharpe_ratio",
    }
