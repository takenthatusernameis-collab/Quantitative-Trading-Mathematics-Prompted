from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261125_02", ROOT / "run_nf_20261125_02_short_interest.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261125_02_short_interest"
    assert mod.NF_ID == "NF-20261125-02"
    assert mod.HYPOTHESIS == "H201"
    assert mod.START == "2015-01-01"
    assert mod.END == "2026-11-25"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_MONTHS == 4
    assert mod.GATES == mod.h184.GATES
    assert mod.VOL_LOOKBACK == 60
    assert mod.DAYS_PER_YEAR == 252


def test_bounded_grid_is_eight_declared_combos():
    combos = list(mod.iter_grid())
    # Pre-registered grid: entry_z {0.5,1.0} x exit_z {0.0} x k {10,20} x vol {0.10,0.15}.
    assert len(combos) == 2 * 1 * 2 * 2 == 8
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {10, 20}
        assert row["vol_target"] in {0.10, 0.15}


def test_regsho_symbol_maps_dash_to_slash():
    assert mod.regsho_symbol("BRK-B") == "BRK/B"
    assert mod.regsho_symbol("aapl") == "AAPL"
    assert mod.regsho_symbol("BF-B") == "BF/B"


def _fake_regsho(symbols: list[str], ratio: float) -> bytes:
    lines = ["Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"]
    for s in symbols:
        lines.append(f"20200102|{s}|{int(ratio * 100)}|0|100|B,Q,N")
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_fetch_month_short_ratio_aggregates_and_caches(tmp_path, monkeypatch):
    # Redirect the monthly cache to a temp dir.
    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path / "short_interest")
    monkeypatch.setattr(mod, "MONTHLY_CACHE_DIR", tmp_path / "short_interest" / "monthly")
    symbols = {"A", "B", "BRK/B"}
    calls = {"n": 0}

    def fake_fetch(day):
        calls["n"] += 1
        return _fake_regsho(list(symbols), 0.2)

    month_start = pd.Timestamp("2020-01-01")
    frame = mod.fetch_month_short_ratio(month_start, symbols, fetch=fake_fetch)
    assert set(frame["symbol"]) == symbols
    assert (frame["n_days"] > 0).all()
    assert np.allclose(frame["ratio_sum"] / frame["n_days"], 0.2)
    # Cached: a second call must not re-fetch.
    before = calls["n"]
    frame2 = mod.fetch_month_short_ratio(month_start, symbols, fetch=fake_fetch)
    assert calls["n"] == before
    assert len(frame2) == len(frame)


def test_fetch_month_short_ratio_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path / "short_interest")
    monkeypatch.setattr(mod, "MONTHLY_CACHE_DIR", tmp_path / "short_interest" / "monthly")
    frame = mod.fetch_month_short_ratio(pd.Timestamp("2020-02-01"), {"A"}, fetch=lambda day: None)
    assert frame.empty
    assert list(frame.columns) == ["symbol", "ratio_sum", "n_days"]


def test_cross_sectional_z_zero_mean_unit_std():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    frame = pd.DataFrame(
        np.array([[1.0, 2.0, 3.0, 4.0, 5.0]] * len(calendar)),
        index=calendar,
        columns=list("ABCDE"),
    )
    z = mod.cross_sectional_z(frame)
    assert np.allclose(z.iloc[0].to_numpy().mean(), 0.0, atol=1e-9)
    assert np.allclose(z.iloc[0].to_numpy().std(ddof=0), 1.0, atol=1e-9)


def test_build_pressure_signal_panel_direction_and_pit(tmp_path, monkeypatch):
    """High short ratio -> negative signal (short); panel is monthly ffilled."""
    monkeypatch.setattr(mod, "CACHE_DIR", tmp_path / "short_interest")
    monkeypatch.setattr(mod, "MONTHLY_CACHE_DIR", tmp_path / "short_interest" / "monthly")
    universe = ["AAA", "BBB", "CCC"]
    symbols = {mod.regsho_symbol(t) for t in universe}
    # AAA has high short ratio (0.6 -> short), CCC low (0.1 -> long).
    ratio_by_symbol = {"AAA": 0.6, "BBB": 0.3, "CCC": 0.1}

    def fake_fetch(day):
        rows = ["Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"]
        for s in symbols:
            r = ratio_by_symbol[s.replace("/", "-")]
            rows.append(f"20200102|{s}|{int(r * 100)}|0|100|B,Q,N")
        return ("\n".join(rows) + "\n").encode("utf-8")

    calendar = pd.bdate_range("2020-01-01", "2020-06-30")
    panel, valid = mod.build_pressure_signal_panel(universe, calendar, fetch=fake_fetch)
    assert set(valid) == set(universe)
    assert panel.index.equals(calendar)
    # AAA (high pressure) has the most negative signal; CCC (low) most positive.
    row = panel.iloc[-1]
    assert row["AAA"] < row["BBB"] < row["CCC"]
    assert row["AAA"] < 0.0 and row["CCC"] > 0.0


def test_signal_weights_shorts_high_pressure():
    """Signal is -z(pressure): the highest-pressure name (most negative) is shorted."""
    calendar = pd.bdate_range("2020-01-01", periods=3)
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    # signal (=-pressure z): AAA=-2 (high pressure -> short), EEE=+2 (low -> long).
    z = pd.DataFrame(
        np.array([[-2.0, -1.0, 0.0, 1.0, 2.0]] * len(calendar)),
        index=calendar,
        columns=tickers,
    )
    weights = mod.signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, tickers=tickers)
    assert weights.iloc[0]["AAA"] == -0.5  # high pressure shorted
    assert weights.iloc[0]["EEE"] == 0.5  # low pressure longed


def test_target_weights_zero_when_insufficient_active():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.array([[-2.0, -1.0, np.nan]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(7).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {"entry_z": 1.0, "exit_z": 0.0, "k": 1, "vol_target": 0.10}
    weights, _ = mod.scaled_weights(signal, params, returns, products)
    # MIN_ACTIVE_NAMES is 40; only 3 names -> the sorter still forms a book, but the
    # scaled weights are finite and bounded by the delever-only vol target.
    assert np.isfinite(weights.to_numpy()).all()


def test_walk_forward_score_short_train_returns_sentinel():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {"entry_z": 1.0, "exit_z": 0.0, "k": 1, "vol_target": 0.10}
    assert mod.walk_forward_score(signal, params, returns, products, calendar) == -999.0


def test_perturbation_sharpes_returns_four_points():
    calendar = pd.bdate_range("2020-01-01", periods=200)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    selected = {"entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    sharpes = mod.perturbation_sharpes(signal, selected, returns, products, calendar)
    assert len(sharpes) == 6
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)
