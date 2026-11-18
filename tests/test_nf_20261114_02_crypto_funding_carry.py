from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261114_02", ROOT / "run_nf_20261114_02_crypto_funding_carry.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

DAY_MS = 86_400_000


def _zip_csv(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def _funding_zip(header: bool, start_ms: int = 1577836800000, days: int = 2) -> bytes:
    rows = ["calc_time,funding_interval_hours,last_funding_rate"] if header else []
    for day in range(days):
        for hour in (0, 8, 16):
            rows.append(f"{start_ms + day * DAY_MS + hour * 3_600_000},8,0.0001")
    return _zip_csv("f.csv", "\n".join(rows) + "\n")


def _kline_zip(header: bool, start_ms: int = 1577836800000, days: int = 3) -> bytes:
    rows = (
        [
            "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
            "taker_buy_volume,taker_buy_quote_volume,ignore"
        ]
        if header
        else []
    )
    for day in range(days):
        open_ms = start_ms + day * DAY_MS
        close = 100.0 + day
        rows.append(f"{open_ms},1,2,0.5,{close},10,{open_ms + DAY_MS - 1},1,1,1,1,0")
    return _zip_csv("k.csv", "\n".join(rows) + "\n")


def _panel(n: int = 700, seed: int = 3, funding: float = 0.0001, basis_vol: float = 0.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    perp_ret = rng.normal(0.0005, 0.02, n)
    spot_ret = perp_ret + rng.normal(0.0, basis_vol, n)
    spot = 100.0 * np.exp(np.cumsum(spot_ret))
    perp = 100.0 * np.exp(np.cumsum(perp_ret))
    funding_day = funding + rng.normal(0.0, abs(funding) * 0.3, n)
    return pd.DataFrame({"spot": spot, "perp": perp, "funding": funding_day}, index=dates)


def test_month_range_inclusive_and_empty():
    assert mod.month_range("2020-01", "2020-03") == ["2020-01", "2020-02", "2020-03"]
    assert mod.month_range("2020-03", "2020-02") == []


def test_archive_urls_and_unknown_kind():
    assert mod.archive_url("funding", "BTCUSDT", "2020-01").endswith(
        "BTCUSDT-fundingRate-2020-01.zip"
    )
    assert "/futures/um/monthly/klines/" in mod.archive_url("perp", "BTCUSDT", "2020-01")
    assert "/spot/monthly/klines/" in mod.archive_url("spot", "BTCUSDT", "2020-01")
    with pytest.raises(ValueError):
        mod.archive_url("options", "BTCUSDT", "2020-01")


@pytest.mark.parametrize("header", [True, False])
def test_parse_funding_zip_handles_both_formats(header: bool):
    daily = mod.parse_funding_zip(_funding_zip(header=header, days=2))
    assert len(daily) == 2
    assert daily.iloc[0] == pytest.approx(0.0003)


@pytest.mark.parametrize("header", [True, False])
def test_parse_kline_zip_handles_both_formats(header: bool):
    close = mod.parse_kline_zip(_kline_zip(header=header, days=3))
    assert len(close) == 3
    assert list(close.to_numpy()) == [100.0, 101.0, 102.0]


def test_build_panel_aligns_and_zero_fills_missing_funding():
    spot = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]))
    perp = spot.copy()
    funding = pd.Series([0.001], index=pd.to_datetime(["2020-01-02"]))
    panel = mod._build_panel(spot, perp, funding, "2020-01-01", "2020-01-03")
    assert len(panel) == 3
    assert panel["funding"].iloc[0] == 0.0
    assert panel["funding"].iloc[1] == 0.001


def test_signal_is_past_only():
    panel = _panel(n=60, funding=0.0002)
    base = mod._signal(panel, 7)
    changed = panel.copy()
    changed.iloc[50:, changed.columns.get_loc("funding")] += 1.0
    altered = mod._signal(changed, 7)
    pd.testing.assert_series_equal(base.iloc[:50], altered.iloc[:50])


def test_weights_hysteresis_enters_and_exits():
    index = pd.RangeIndex(6)
    signal = pd.Series([np.nan, 0.0002, 0.00015, 0.00005, 0.0002, 0.00005], index=index)
    weights = mod._weights_from_signal(signal, entry=0.0001, exit_level=0.0001, weight=0.5)
    assert list(weights) == [0.0, 0.5, 0.5, 0.0, 0.5, 0.0]


def test_weights_respect_exit_level():
    signal = pd.Series([0.0002, 0.00012, 0.00005, 0.00012], dtype=float)
    weights = mod._weights_from_signal(signal, entry=0.0001, exit_level=0.00008, weight=0.2)
    assert list(weights) == [0.2, 0.2, 0.0, 0.2]


def test_run_bt_identity_equals_funding_minus_costs():
    panel = _panel(n=50, funding=0.0001)
    panel["spot"] = panel["perp"]
    panel["funding"] = 0.0001
    weights = pd.DataFrame({"BTCUSDT": np.full(len(panel), 1.0 / mod.N_ASSETS)}, index=panel.index)
    strat, equity, trades = mod._run_bt({"BTCUSDT": panel}, weights, cost_bps=14.0)
    expected = 0.0001 / mod.N_ASSETS
    assert strat.iloc[1:].mean() == pytest.approx(expected, rel=1e-6)
    assert equity.iloc[-1] > 1.0
    assert trades == 1


def test_run_bt_cost_applied_on_turnover():
    panel = _panel(n=40, funding=0.0)
    panel["spot"] = panel["perp"]
    weights = pd.DataFrame({"BTCUSDT": [0.5] * 20 + [1.0] * 20}, index=panel.index)
    strat, _, trades = mod._run_bt({"BTCUSDT": panel}, weights, cost_bps=14.0)
    assert strat.iloc[0] == pytest.approx(-0.5 * 14.0 / 1e4)
    assert strat.iloc[20] == pytest.approx(-0.5 * 14.0 / 1e4)
    assert trades == 2


def test_metrics_keys_and_grid_bounds():
    panel = _panel(n=400, funding=0.0001)
    weights = mod._compute_weights({"BTCUSDT": panel}, 7, 0.0, 0.0)
    strat, equity, trades = mod._run_bt({"BTCUSDT": panel}, weights)
    metrics = mod._metrics(strat, equity, trades)
    for key in (
        "sharpe",
        "profit_factor",
        "max_drawdown",
        "trades",
        "periods",
        "total_return",
        "worst_regime_rolling252_sharpe",
    ):
        assert key in metrics
    grid = list(mod._iter_grid())
    assert len(grid) == 20
    assert all(row["exit_bps"] <= row["entry_bps"] for row in grid)


def test_wf_score_finite_and_always_on_bounded():
    panels = {"BTCUSDT": _panel(n=600, funding=0.0001), "ETHUSDT": _panel(n=600, seed=9)}
    score = mod._wf_score(panels, {"funding_window": 7, "entry_bps": 0.0, "exit_bps": 0.0}, panels["BTCUSDT"].index)
    assert np.isfinite(score)
    always_on = mod._always_on_weights(panels, panels["BTCUSDT"].index)
    assert always_on.sum(axis=1).max() <= 1.0 + 1e-12


def test_random_weights_match_active_count():
    panels = {"BTCUSDT": _panel(n=300, funding=0.0001)}
    weights = mod._compute_weights(panels, 7, 0.0, 0.0)
    random_weights = mod._random_weights(weights, panels)
    assert int((random_weights["BTCUSDT"] > 0).sum()) == int((weights["BTCUSDT"] > 0).sum())
    assert random_weights.sum(axis=1).max() <= 1.0 + 1e-12


def test_benchmark_statistics_direction():
    index = pd.date_range("2024-01-01", periods=300, freq="B")
    good = pd.Series(0.001, index=index)
    flat = pd.Series(0.0, index=index)
    assert mod._information_ratio(good, flat) > 0
    assert mod._benchmark_pvalue(good, flat) <= 0.05
    assert mod._information_ratio(flat, good) < 0


def test_perturbation_returns_finite_list():
    panels = {"BTCUSDT": _panel(n=500, funding=0.0001)}
    sharpes = mod._perturbation_oos_sharpes(
        panels, {"funding_window": 7, "entry_bps": 0.0, "exit_bps": 0.0}, panels["BTCUSDT"].index
    )
    assert sharpes
    assert all(np.isfinite(value) for value in sharpes)


def test_main_writes_summary_with_injected_data(tmp_path, monkeypatch):
    panels = {
        "BTCUSDT": _panel(n=1600, funding=0.0002),
        "ETHUSDT": _panel(n=1600, seed=11, funding=0.00015),
    }
    provenance = [{"symbol": symbol, "rows": len(panel)} for symbol, panel in panels.items()]
    monkeypatch.setattr(mod, "_download_all", lambda symbols=None: (panels, provenance))
    summary = mod.main(out=str(tmp_path))
    assert summary["experiment"] == mod.EXPERIMENT
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_total"] == 8
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "grid.csv").exists()


def test_fetch_cache_key_distinguishes_spot_and_perp(tmp_path, monkeypatch):
    class FakeResponse:
        def __init__(self, payload: bytes) -> None:
            self.payload = payload

        def read(self) -> bytes:
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout=0):
        return FakeResponse(request.full_url.encode())

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    perp = mod._fetch(mod.archive_url("perp", "BTCUSDT", "2024-06"), cache_dir=tmp_path)
    spot = mod._fetch(mod.archive_url("spot", "BTCUSDT", "2024-06"), cache_dir=tmp_path)
    assert perp != spot
    assert len(list(tmp_path.iterdir())) == 2


def test_epoch_timestamps_detects_microsecond_archives():
    micro = _zip_csv(
        "k.csv",
        "1735689600000000,1,2,0.5,100,10,1735775999999999\n"
        "1735776000000000,1,2,0.5,101,10,1735862399999999\n",
    )
    close = mod.parse_kline_zip(micro)
    assert close.index[0] == pd.Timestamp("2025-01-01")
    assert close.index[-1] == pd.Timestamp("2025-01-02")
    milli = mod.parse_kline_zip(_kline_zip(header=False, days=2))
    assert milli.index[0] == pd.Timestamp("2020-01-01")


def test_spot_archive_until_2026_present_after_unit_fix(tmp_path):
    frames = {
        "spot": _zip_csv(
            "k.csv",
            "1735689600000000,1,2,0.5,100,10,1735775999999999\n"
            "1735776000000000,1,2,0.5,101,10,1735862399999999\n",
        ),
        "perp": _zip_csv(
            "k.csv",
            "1735689600000,1,2,0.5,100,10,1735775999999\n"
            "1735776000000,1,2,0.5,101,10,1735862399999\n",
        ),
        "funding": _zip_csv(
            "f.csv",
            "1735689600000,8,0.0001\n1735776000000,8,0.0001\n",
        ),
    }

    def fake_fetch(url: str):
        kind = "funding" if "fundingRate" in url else ("spot" if "/spot/" in url else "perp")
        return frames[kind]

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(mod, "_fetch", lambda url, cache_dir=None: fake_fetch(url))
        raw = mod._download_symbol("BTCUSDT", ["2025-01"], cache_dir=tmp_path)
    finally:
        monkeypatch.undo()
    panel = mod._build_panel(raw["spot"], raw["perp"], raw["funding"], "2025-01-01", "2025-12-31")
    assert len(panel) == 2
