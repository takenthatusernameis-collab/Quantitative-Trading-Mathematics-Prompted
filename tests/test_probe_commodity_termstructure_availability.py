from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "probe_termstructure", ROOT / "scripts" / "probe_commodity_termstructure_availability.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _shfe_json(rows: list[dict[str, object]]) -> bytes:
    return json.dumps({"o_curinstrument": rows}).encode()


def _shfe_row(product: str, delivery: str, settle: float, oi: float) -> dict[str, object]:
    return {
        "PRODUCTGROUPID": f"{product}      ",
        "PRODUCTID": f"{product}_f    ",
        "DELIVERYMONTH": delivery,
        "SETTLEMENTPRICE": settle,
        "OPENINTEREST": oi,
    }


def test_source_urls_are_stable_and_date_stamped():
    day = dt.date(2024, 1, 2)
    assert mod.source_url("SHFE", day).endswith("/kx20240102.dat")
    assert mod.source_url("INE", day).endswith("/kx20240102.dat")
    assert "ine.cn" in mod.source_url("INE", day)
    assert mod.source_url("CZCE", day) == (
        "http://www.czce.com.cn/cn/DFSStaticFiles/Future/2024/20240102/FutureDataDaily.txt"
    )
    assert mod.source_url("CFFEX", day).endswith("/202401/02/20240102_1.csv")


def test_unknown_source_raises():
    try:
        mod.source_url("DCE", dt.date(2024, 1, 2))
    except ValueError as error:
        assert "DCE" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_clean_number_handles_thousands_and_blanks():
    assert mod._clean_number("1,234.5") == 1234.5
    assert mod._clean_number("  ") is None
    assert mod._clean_number("-") is None
    assert mod._clean_number("n/a") is None
    assert mod._clean_number(float("nan")) is None


def test_parse_exchange_json_with_and_without_product_group():
    raw = _shfe_json(
        [
            _shfe_row("CU", "2401", 68920, 49865),
            _shfe_row("CU", "2402", 68900, 1000),
            {
                "PRODUCTID": "al_f    ",
                "DELIVERYMONTH": "2401",
                "SETTLEMENTPRICE": 19000,
                "OPENINTEREST": 500,
            },
        ]
    )
    frame = mod.parse_exchange_json(raw)
    assert set(frame["product"]) == {"CU", "AL"}
    assert len(frame) == 3


def test_parse_exchange_json_drops_zero_settlement_and_bad_delivery():
    raw = _shfe_json(
        [
            _shfe_row("CU", "2401", 0, 100),
            _shfe_row("CU", "2402", 100, 0),
            _shfe_row("CU", "TOTAL", 100, 100),
        ]
    )
    frame = mod.parse_exchange_json(raw)
    assert list(frame["delivery"]) == ["2402"]


def test_normalize_ymm_resolves_decade():
    assert mod._normalize_ymm("401", dt.date(2024, 1, 2)) == "202401"
    assert mod._normalize_ymm("912", dt.date(2019, 12, 2)) == "201912"
    assert mod._normalize_ymm("001", dt.date(2019, 12, 2)) == "202001"
    assert mod._normalize_ymm("12", dt.date(2024, 1, 2)) == ""


def test_parse_pipe_text_skips_headers_and_subtotals():
    text = (
        "\t\t郑商所期货每日行情表(2024-01-02)\n"
        "合约代码|昨结算|今开盘|最高价|最低价|今收盘|今结算|涨跌1|涨跌2|成交量(手)|持仓量|增减量|成交额\n"
        "TA401 |4,000 |4,010 |4,020 |3,990 |4,015 |4,010 |1 |2 |10 |1,000 |0 |400\n"
        "TA402 |3,900 |3,910 |3,920 |3,890 |3,915 |3,905 |1 |2 |5 |500 |0 |200\n"
        "小计 | | | | | | | | |15 |1,500 |0 |600\n"
    ).encode()
    frame = mod.parse_pipe_text(bytes(text), reference=dt.date(2024, 1, 2))
    assert list(frame["product"]) == ["TA", "TA"]
    assert list(frame["delivery"]) == ["202401", "202402"]
    assert frame["settlement"].iloc[0] == 4010.0
    assert frame["open_interest"].iloc[1] == 500.0


def test_parse_pipe_text_decodes_legacy_gbk_payload():
    text = "合约代码|昨结算|今开盘|最高价|最低价|今收盘|今结算|涨跌1|涨跌2|成交量|持仓量|增减量\n"
    text += "SR601 |5,000 |5,010 |5,020 |4,990 |5,015 |5,010 |1 |2 |10 |1,000 |0\n"
    raw = ("\t\t郑商所每日行情\n" + text).encode("gbk")
    frame = mod.parse_pipe_text(raw, reference=dt.date(2016, 1, 4))
    assert list(frame["delivery"]) == ["201601"]
    assert frame["settlement"].iloc[0] == 5010.0


def test_parse_cffex_csv_keeps_futures_and_drops_options():
    csv = (
        "合约代码,今开盘,最高价,最低价,成交量,成交金额,持仓量,持仓变化,今收盘,今结算,前结算\n"
        "IF2401                 ,3400,3410,3390,1000,100,12000,10,3405,3402,3399\n"
        "IF2402                 ,3380,3390,3370,200,20,3000,5,3385,3382,3380\n"
        "IF2401-C-3400          ,10,20,5,50,1,500,0,15,14,13\n"
        "HO2401-C-2000          ,228,248,228,10,2,33,1,240,239,242\n"
    ).encode("gbk")
    frame = mod.parse_cffex_csv(csv)
    assert list(frame["product"]) == ["IF", "IF"]
    assert frame["settlement"].iloc[1] == 3382.0


def test_parse_cffex_csv_rejects_html_error_page():
    frame = mod.parse_cffex_csv(b"<!DOCTYPE html><html><body>404</body></html>")
    assert frame.empty


def test_term_structure_empty_frame():
    summary = mod.term_structure(pd.DataFrame())
    assert summary["contracts"] == 0
    assert summary["curves"] == 0
    assert summary["spread_bps"] is None


def test_term_structure_uses_two_nearest_most_liquid_product():
    raw = _shfe_json(
        [
            _shfe_row("CU", "2401", 69000, 5000),
            _shfe_row("CU", "2402", 68000, 100),
            _shfe_row("CU", "2403", 67000, 50),
            _shfe_row("AL", "2401", 19000, 100),
            _shfe_row("AL", "2402", 19100, 90),
        ]
    )
    summary = mod.term_structure(mod.parse_exchange_json(raw))
    assert summary["contracts"] == 5
    assert summary["products"] == 2
    assert summary["curves"] == 2
    assert summary["sample_product"] == "CU"
    assert summary["front_delivery"] == "2401"
    assert summary["second_delivery"] == "2402"
    assert summary["spread_bps"] == (69000 - 68000) / 68000 * 1e4


def test_term_structure_ignores_single_contract_products():
    raw = _shfe_json([_shfe_row("CU", "2401", 69000, 5000)])
    summary = mod.term_structure(mod.parse_exchange_json(raw))
    assert summary["curves"] == 0
    assert summary["spread_bps"] is None


def test_probe_missing_returns_missing_status():
    row = mod.probe("SHFE", dt.date(2020, 1, 1), fetch_fn=lambda source, day: None)
    assert row["status"] == "MISSING"
    assert row["contracts"] == 0
    assert row["category"] == "industrial metals term structure"


def test_probe_unparsable_payload_is_reported_not_raised():
    row = mod.probe("SHFE", dt.date(2024, 1, 2), fetch_fn=lambda source, day: b"not json")
    assert row["status"] == "UNPARSABLE"


def test_probe_ok_reports_curve_evidence():
    raw = _shfe_json(
        [
            _shfe_row("CU", "2401", 69000, 5000),
            _shfe_row("CU", "2402", 68000, 100),
        ]
    )
    row = mod.probe("SHFE", dt.date(2024, 1, 2), fetch_fn=lambda source, day: raw)
    assert row["status"] == "OK"
    assert row["sample_product"] == "CU"
    assert row["curves"] == 1


def test_main_exit_codes_and_output(capsys):
    assert mod.main([], fetch_fn=lambda source, day: None) == 1
    assert "NO USABLE SOURCE" in capsys.readouterr().err

    metadata_raw = _shfe_json(
        [
            _shfe_row("CU", "2401", 69000, 5000),
            _shfe_row("CU", "2402", 68000, 100),
        ]
    )
    pipe_raw = (
        "合约代码|昨结算|今开盘|最高价|最低价|今收盘|今结算|涨跌1|涨跌2|成交量|持仓量|增减量\n"
        "SR601 |5,000 |5,010 |5,020 |4,990 |5,015 |5,010 |1 |2 |10 |1,000 |0\n"
        "SR603 |4,900 |4,910 |4,920 |4,890 |4,915 |4,905 |1 |2 |5 |500 |0\n"
    ).encode()
    cffex_raw = (
        "合约代码,今开盘,最高价,最低价,成交量,成交金额,持仓量,持仓变化,今收盘,今结算,前结算\n"
        "IF2401                 ,3400,3410,3390,1000,100,12000,10,3405,3402,3399\n"
        "IF2402                 ,3380,3390,3370,200,20,3000,5,3385,3382,3380\n"
    ).encode("gbk")

    def fake(source, day):
        if source in {"SHFE", "INE"}:
            return metadata_raw
        return pipe_raw if source == "CZCE" else cffex_raw

    assert mod.main([], fetch_fn=fake) == 0
    out = capsys.readouterr().out
    assert "Usable sources: CFFEX, CZCE, INE, SHFE (4/4)." in out
    assert "per-contract commodity term structure" in out


def test_probe_reports_transport_failure_as_unreachable():
    def boom(source, day):
        raise mod.FetchError("connection reset by peer")

    row = mod.probe("SHFE", dt.date(2024, 1, 2), fetch_fn=boom)
    assert row["status"] == "UNREACHABLE"
    assert row["contracts"] == 0


def test_fetch_maps_transport_errors_to_fetch_error(monkeypatch):
    import urllib.error

    def boom(*args, **kwargs):
        raise urllib.error.URLError("connection reset by peer")

    monkeypatch.setattr(mod.urllib.request, "urlopen", boom)
    try:
        mod.fetch("SHFE", dt.date(2024, 1, 2))
    except mod.FetchError as error:
        assert "connection reset by peer" in str(error)
    else:
        raise AssertionError("expected FetchError")


def test_fetch_returns_none_on_404(monkeypatch):
    import urllib.error

    def not_found(*args, **kwargs):
        error = urllib.error.HTTPError("http://x", 404, "not found", {}, None)
        error.close()
        raise error

    monkeypatch.setattr(mod.urllib.request, "urlopen", not_found)
    assert mod.fetch("SHFE", dt.date(2010, 1, 1)) is None
