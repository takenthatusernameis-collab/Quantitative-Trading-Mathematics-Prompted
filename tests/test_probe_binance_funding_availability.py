from __future__ import annotations

import datetime as dt
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "probe_binance", ROOT / "scripts" / "probe_binance_funding_availability.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _zip_csv(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def test_month_range_and_latest_complete_month():
    assert mod.month_range("2020-01", "2020-04") == ["2020-01", "2020-02", "2020-03", "2020-04"]
    assert mod.month_range("2020-02", "2020-01") == []
    assert mod.latest_complete_month(dt.date(2026, 11, 18)) == "2026-10"
    assert mod.latest_complete_month(dt.date(2026, 1, 1)) == "2025-12"


def test_archive_urls_for_every_kind():
    assert "fundingRate" in mod.archive_url("funding", "BTCUSDT", "2020-01")
    assert "/futures/um/monthly/klines/" in mod.archive_url("perp", "BTCUSDT", "2020-01")
    assert "/spot/monthly/klines/" in mod.archive_url("spot", "BTCUSDT", "2020-01")


def test_parse_funding_and_kline_archives():
    funding = mod.parse_funding_archive(
        _zip_csv(
            "f.csv",
            "calc_time,funding_interval_hours,last_funding_rate\n"
            "1577836800000,8,-0.0001\n1577865600000,8,0.0002\n",
        )
    )
    assert len(funding) == 2
    assert funding["last_funding_rate"].iloc[0] == -0.0001
    klines = mod.parse_kline_archive(
        _zip_csv(
            "k.csv",
            "open_time,open,high,low,close,volume,close_time\n"
            "1577836800000,1,2,0.5,100,10,1577923199999\n",
        )
    )
    assert klines["close"].iloc[0] == 100.0


def test_first_available_month_skips_missing_archives():
    seen = []

    def fetch(url: str):
        seen.append(url)
        return b"data" if "2020-07" in url else None

    assert mod.first_available_month("BNBUSDT", fetch=fetch) == "2020-07"
    assert len(seen) == 2


def test_probe_symbol_reports_usable_and_missing():
    def full_fetch(url: str):
        if "fundingRate" in url:
            return _zip_csv(
                "f.csv",
                "calc_time,funding_interval_hours,last_funding_rate\n"
                "1577836800000,8,0.0001\n1577865600000,8,0.0001\n",
            )
        return _zip_csv(
            "k.csv",
            "open_time,open,high,low,close,volume,close_time\n"
            "1577836800000,1,2,0.5,100,10,1577923199999\n",
        )

    row = mod.probe_symbol("BTCUSDT", "2026-10", fetch=full_fetch)
    assert row["status"] == "OK"
    assert row["first_month"] == "2020-01"
    assert row["perp_ok"] and row["spot_ok"]
    assert row["funding_obs"] == 2

    missing = mod.probe_symbol("NOPEUSDT", "2026-10", fetch=lambda url: None)
    assert missing["status"] == "NO_FUNDING"
    assert not missing["perp_ok"]


def test_main_exit_codes(capsys):
    def usable(url: str):
        if "fundingRate" in url:
            return _zip_csv(
                "f.csv",
                "calc_time,funding_interval_hours,last_funding_rate\n1577836800000,8,0.0001\n",
            )
        return _zip_csv(
            "k.csv",
            "open_time,open,high,low,close,volume,close_time\n"
            "1577836800000,1,2,0.5,100,10,1577923199999\n",
        )

    assert mod.main(["BTCUSDT"], fetch=usable) == 0
    assert mod.main(["BTCUSDT"], fetch=lambda url: None) == 1
    out = capsys.readouterr().out
    assert "Usable symbols" in out
