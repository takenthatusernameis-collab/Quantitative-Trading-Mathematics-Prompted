"""Tests for the SEC EDGAR Form 4 insider-transaction layer (no network).

Every test drives the module through a stubbed transport: ``fetch_json`` /
``fetch_text`` / ``urllib.request.urlopen`` are monkeypatched, so the suite
never contacts EDGAR. The fixture XML mirrors the real document structure
(``ownershipDocument`` -> ``issuer`` / ``reportingOwner`` /
``nonDerivativeTable`` / ``derivativeTable``), which was verified against a
live Apple Form 4 on 2026-11-14.
"""

import io
import json

import pandas as pd
import pytest

from qtr.data import insider

NON_DERIVATIVE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <schemaVersion>X0508</schemaVersion>
  <documentType>4</documentType>
  <periodOfReport>2026-11-10</periodOfReport>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerName>Apple Inc.</issuerName>
    <issuerTradingSymbol>AAPL</issuerTradingSymbol>
  </issuer>
  <notSubjectToSection16>false</notSubjectToSection16>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001234567</rptOwnerCik>
      <rptOwnerName>EXAMPLE, OFFICER</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>false</isDirector>
      <isOfficer>true</isOfficer>
      <isTenPercentOwner>false</isTenPercentOwner>
      <isOther>false</isOther>
      <officerTitle>SVP, GC</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <aff10b5One>true</aff10b5One>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-11-10</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>S</transactionCode>
        <equitySwapInvolved>false</equitySwapInvolved>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>2,399</value></transactionShares>
        <transactionPricePerShare><value>351.36</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <postTransactionAmounts>
        <sharesOwnedFollowingTransaction><value>10,000</value></sharesOwnedFollowingTransaction>
      </postTransactionAmounts>
      <ownershipNature>
        <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
        <natureOfOwnership><value></value></natureOfOwnership>
      </ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <footnotes></footnotes>
</ownershipDocument>
"""

DERIVATIVE_AND_PURCHASE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
  <issuer>
    <issuerName>Test Issuer</issuerName>
    <issuerTradingSymbol>TST</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>DIRECTOR ONE</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>true</isDirector>
      <isOfficer>false</isOfficer>
      <isTenPercentOwner>false</isTenPercentOwner>
      <isOther>false</isOther>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-11-02</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>500</value></transactionShares>
        <transactionPricePerShare><value>100.5</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <ownershipNature>
        <directOrIndirectOwnership><value>I</value></directOrIndirectOwnership>
        <natureOfOwnership><value>By trust</value></natureOfOwnership>
      </ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <derivativeTable>
    <derivativeTransaction>
      <securityTitle><value>Employee Stock Option</value></securityTitle>
      <conversionOrExerciseDate><value>2026-11-02</value></conversionOrExerciseDate>
      <transactionDate><value>2026-11-02</value></transactionDate>
      <transactionCoding>
        <transactionFormType>4</transactionFormType>
        <transactionCode>M</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <conversionOrExercisePrice><value>50.0</value></conversionOrExercisePrice>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <exerciseDate><value>2026-11-02</value></exerciseDate>
      <expirationDate><value>2030-01-01</value></expirationDate>
      <underlyingSecurity>
        <underlyingSecurityTitle><value>Common Stock</value></underlyingSecurityTitle>
        <underlyingSecurityShares><value>500</value></underlyingSecurityShares>
        <underlyingSecurityPrice><value>100.5</value></underlyingSecurityPrice>
      </underlyingSecurity>
      <ownershipNature>
        <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
      </ownershipNature>
    </derivativeTransaction>
  </derivativeTable>
</ownershipDocument>
"""

NO_TRANSACTION_XML = """<ownershipDocument>
  <issuer><issuerName>No Transactions Inc.</issuerName></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Nobody</rptOwnerName></reportingOwnerId>
  </reportingOwner>
</ownershipDocument>
"""

NO_OWNER_XML = """<ownershipDocument>
  <issuer><issuerName>Ownerless Inc.</issuerName></issuer>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-01-02</value></transactionDate>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

NAMESPACED_XML = """<ownershipDocument xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <issuer><issuerName>Namespaced Inc.</issuerName></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>NS OWNER</rptOwnerName></reportingOwnerId>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-03-04</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts><transactionShares><value>10</value></transactionShares></transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

SUBMISSIONS = {
    "cik": "0000320193",
    "filings": {
        "recent": {
            "accessionNumber": [
                "0001140361-26-043484",
                "0001140361-26-042149",
                "0000000000-00-000000",
            ],
            "filingDate": ["2026-11-12", "2026-11-05", "2026-10-01"],
            "reportDate": ["2026-11-10", "", "2026-09-01"],
            "acceptanceDateTime": [
                "2026-11-12T23:58:20.000Z",
                "2026-11-05T23:30:13.000Z",
                "2026-10-01T12:00:00.000Z",
            ],
            "form": ["4", "4", "8-K"],
            "primaryDocument": ["form4.xml", "form4.xml", "filing.txt"],
        },
        "files": [{"name": "CIK0000320193-submissions-001.json"}],
    },
}

FILING_INDEX = {
    "directory": {
        "item": [
            {"name": "0001140361-26-043484-index.html"},
            {"name": "form4.xml"},
        ]
    }
}

FILING_INDEX_NO_XML = {"directory": {"item": [{"name": "filing.txt"}, {"name": "index.html"}]}}


def _submissions(monkeypatch, payload):
    monkeypatch.setattr(insider, "fetch_json", lambda *a, **k: payload)


def test_user_agent_prefers_explicit_then_env_then_default(monkeypatch):
    assert insider.user_agent("custom/1.0 (a@b.c)") == "custom/1.0 (a@b.c)"
    monkeypatch.setenv("QTR_SEC_USER_AGENT", "env/1.0 (a@b.c)")
    assert insider.user_agent() == "env/1.0 (a@b.c)"
    monkeypatch.delenv("QTR_SEC_USER_AGENT")
    assert insider.user_agent() == insider.DEFAULT_USER_AGENT


def test_normalize_cik_pads_and_strips_dashes():
    assert insider.normalize_cik(320193) == "0000320193"
    assert insider.normalize_cik("0000320193") == "0000320193"
    with pytest.raises(ValueError):
        insider.normalize_cik("no-digits")


def test_urls_use_padded_cik_and_dash_free_accession():
    assert insider.submissions_url(320193).endswith("/submissions/CIK0000320193.json")
    assert insider.filing_index_url(320193, "0001140361-26-043484").endswith(
        "/Archives/edgar/data/320193/000114036126043484/index.json"
    )
    assert insider.filing_document_url(320193, "0001140361-26-043484", "form4.xml").endswith(
        "/000114036126043484/form4.xml"
    )


def test_http_get_sends_user_agent_and_decodes(monkeypatch):
    captured = {}

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["timeout"] = timeout
        return _Response(b"payload")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert insider.fetch_text("https://example.test/a", user_agent="ua/1.0") == "payload"
    assert captured["headers"].get("User-agent") == "ua/1.0"
    assert captured["timeout"] == 30.0


def test_http_get_propagates_network_errors(monkeypatch):
    def boom(request, timeout):
        raise OSError("offline")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(OSError):
        insider.fetch_json("https://example.test/a")


def test_fetch_json_decodes(monkeypatch):
    monkeypatch.setattr(insider, "_http_get", lambda *a, **k: json.dumps({"a": 1}).encode())
    assert insider.fetch_json("https://example.test/a") == {"a": 1}


def test_recent_filings_pads_short_arrays():
    payload = {"filings": {"recent": {"accessionNumber": ["1", "2"], "form": ["4"]}}}
    frame = insider._recent_filings(payload)
    assert list(frame.columns) == list(insider.FILING_COLUMNS)
    assert frame["form"].tolist() == ["4", ""]
    assert frame["cik"].tolist() == ["", ""]


def test_recent_filings_absent_block():
    assert len(insider._recent_filings({"filings": {}})) == 0
    assert len(insider._recent_filings({})) == 0
    assert len(insider._recent_filings({"filings": {"recent": []}})) == 0


def test_fetch_filings_filters_forms_and_window(monkeypatch):
    _submissions(monkeypatch, SUBMISSIONS)
    frame = insider.fetch_filings(320193, forms=("4",), start="2026-11-01", end="2026-11-30")
    assert frame["accession_number"].tolist() == [
        "0001140361-26-043484",
        "0001140361-26-042149",
    ]
    assert frame["cik"].tolist() == ["0000320193", "0000320193"]
    assert str(frame["acceptance_datetime"].iloc[0]) == "2026-11-12 23:58:20+00:00"


def test_fetch_filings_start_only_and_end_only(monkeypatch):
    _submissions(monkeypatch, SUBMISSIONS)
    frame = insider.fetch_filings(320193, forms=("4",), start="2026-11-06")
    assert frame["accession_number"].tolist() == ["0001140361-26-043484"]
    ended = insider.fetch_filings(320193, forms=("4",), end="2026-11-06")
    assert ended["accession_number"].tolist() == ["0001140361-26-042149"]


def test_fetch_filings_returns_empty_with_columns_when_nothing_matches(monkeypatch):
    _submissions(monkeypatch, SUBMISSIONS)
    frame = insider.fetch_filings(320193, forms=("3",))
    assert len(frame) == 0
    assert list(frame.columns) == list(insider.FILING_COLUMNS)


def test_fetch_filings_returns_empty_when_cik_has_no_recent_block(monkeypatch):
    _submissions(monkeypatch, {"filings": {}})
    assert len(insider.fetch_filings(320193)) == 0


def test_filing_documents_maps_names_to_urls(monkeypatch):
    _submissions(monkeypatch, FILING_INDEX)
    documents = insider.filing_documents(320193, "0001140361-26-043484")
    assert set(documents) == {"0001140361-26-043484-index.html", "form4.xml"}
    assert documents["form4.xml"].endswith("/form4.xml")


def test_filing_documents_skips_nameless_or_non_mapping_items(monkeypatch):
    payload = {"directory": {"item": [{"name": ""}, "not-a-mapping", {"name": "form4.xml"}]}}
    _submissions(monkeypatch, payload)
    assert insider.filing_documents(320193, "0001140361-26-043484") == {
        "form4.xml": "https://www.sec.gov/Archives/edgar/data/320193/000114036126043484/form4.xml"
    }


def test_filing_documents_tolerates_a_missing_directory(monkeypatch):
    _submissions(monkeypatch, {})
    assert insider.filing_documents(320193, "0001140361-26-043484") == {}


def test_number_rejects_non_numeric_text():
    assert pd.isna(insider._number("not-a-number"))
    assert insider._number("1,234") == 1234.0
    assert pd.isna(insider._number(""))
    documents = {"a.xml": "u1", "form4.xml": "u2"}
    assert insider._form4_document(documents) == "u2"


def test_form4_document_accepts_lone_generated_name():
    assert insider._form4_document({"wk-form4_1.xml": "u"}) == "u"


def test_form4_document_refuses_ambiguous_or_absent():
    assert insider._form4_document({"a.xml": "u", "b.xml": "v"}) is None
    assert insider._form4_document({"index.html": "u"}) is None
    assert insider._form4_document({}) is None


def test_parse_form4_non_derivative_row():
    frame = insider.parse_form4(NON_DERIVATIVE_XML)
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["issuer_name"] == "Apple Inc."
    assert row["issuer_trading_symbol"] == "AAPL"
    assert row["reporting_owner"] == "EXAMPLE, OFFICER"
    assert row["officer_title"] == "SVP, GC"
    assert bool(row["is_officer"]) and not bool(row["is_director"])
    assert row["security_kind"] == "non_derivative"
    assert row["security_title"] == "Common Stock"
    assert str(row["transaction_date"].date()) == "2026-11-10"
    assert row["transaction_code"] == "S"
    assert row["shares"] == 2399.0
    assert row["price_per_share"] == 351.36
    assert row["acquired_disposed"] == "D"
    assert row["direct_or_indirect"] == "D"
    assert row["nature_of_ownership"] == ""


def test_parse_form4_covers_both_tables_and_indirect_ownership():
    frame = insider.parse_form4(DERIVATIVE_AND_PURCHASE_XML)
    assert len(frame) == 2
    assert set(frame["security_kind"]) == {"non_derivative", "derivative"}
    assert bool(frame["is_director"].iloc[0])
    purchase = frame[frame["security_kind"] == "non_derivative"].iloc[0]
    assert purchase["direct_or_indirect"] == "I"
    assert purchase["nature_of_ownership"] == "By trust"
    option = frame[frame["security_kind"] == "derivative"].iloc[0]
    assert option["security_title"] == "Employee Stock Option"
    assert option["transaction_code"] == "M"
    assert option["shares"] == 500.0
    assert option["price_per_share"] == 50.0


def test_parse_form4_returns_empty_schema_when_no_transaction():
    frame = insider.parse_form4(NO_TRANSACTION_XML)
    assert len(frame) == 0
    assert "transaction_code" in frame.columns


def test_parse_form4_synthesizes_an_owner_row_when_absent():
    frame = insider.parse_form4(NO_OWNER_XML)
    assert len(frame) == 1
    assert frame["reporting_owner"].tolist() == [""]
    assert frame["is_director"].tolist() == [False]


def test_parse_form4_handles_a_namespaced_document():
    frame = insider.parse_form4(NAMESPACED_XML)
    assert len(frame) == 1
    assert frame["issuer_name"].tolist() == ["Namespaced Inc."]
    assert frame["reporting_owner"].tolist() == ["NS OWNER"]


def test_parse_form4_blank_numeric_fields_become_nan():
    frame = insider.parse_form4(NO_OWNER_XML)
    assert pd.isna(frame["shares"].iloc[0])
    assert pd.isna(frame["price_per_share"].iloc[0])


def test_parse_form4_rejects_malformed_and_wrong_root():
    with pytest.raises(ValueError, match="not well-formed"):
        insider.parse_form4("<ownershipDocument>")
    with pytest.raises(ValueError, match="not an ownershipDocument"):
        insider.parse_form4("<somethingElse/>")


def test_parse_form4_non_numeric_fields_become_nan():
    frame = insider.parse_form4(NAMESPACED_XML.replace("<value>10</value>", "<value>abc</value>"))
    assert pd.isna(frame["shares"].iloc[0])


def test_parse_form4_handles_a_missing_issuer_element():
    frame = insider.parse_form4(
        "<ownershipDocument><nonDerivativeTable>"
        "<nonDerivativeTransaction><transactionDate><value>2026-01-02</value></transactionDate>"
        "</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"
    )
    assert frame["issuer_name"].tolist() == [""]


def test_acceptance_datetime_handles_all_shapes():
    assert pd.isna(insider._acceptance_datetime(None))
    assert pd.isna(insider._acceptance_datetime(""))
    assert pd.isna(insider._acceptance_datetime("not-a-date"))
    stamp = insider._acceptance_datetime("2026-11-12T23:58:20.000Z")
    assert str(stamp) == "2026-11-12 23:58:20"


def _transactions_fixture():
    return pd.DataFrame(
        {
            "cik": ["0000320193"] * 3,
            "accession_number": ["a", "b", "b"],
            "form": ["4", "4", "4"],
            "issuer_name": ["Apple Inc."] * 3,
            "issuer_trading_symbol": ["AAPL"] * 3,
            "reporting_owner": ["X", "Y", "Y"],
            "officer_title": ["", "", ""],
            "is_director": [False, False, False],
            "is_officer": [True, True, True],
            "is_ten_percent_owner": [False, False, False],
            "is_other": [False, False, False],
            "security_kind": ["non_derivative"] * 3,
            "security_title": ["Common Stock"] * 3,
            "transaction_date": pd.to_datetime(["2026-11-10", "2026-11-02", "2026-11-02"]),
            "transaction_code": ["S", "P", "A"],
            "transaction_form_type": ["4", "4", "4"],
            "shares": [2399.0, 500.0, 1000.0],
            "price_per_share": [351.36, 100.5, 0.0],
            "acquired_disposed": ["D", "A", "A"],
            "direct_or_indirect": ["D", "D", "D"],
            "nature_of_ownership": ["", "", ""],
            "accepted_at": pd.to_datetime(
                [
                    "2026-11-12 23:58:20",
                    "2026-11-05 23:30:13",
                    "2026-11-05 23:30:13",
                ]
            ),
            "available_at": pd.to_datetime(
                [
                    "2026-11-12 23:58:20",
                    "2026-11-05 23:30:13",
                    "2026-11-05 23:30:13",
                ]
            ),
        }
    )


def test_fetch_insider_transactions_end_to_end(monkeypatch):
    filings = pd.DataFrame(
        {
            "cik": ["0000320193"],
            "accession_number": ["0001140361-26-043484"],
            "form": ["4"],
            "filing_date": ["2026-11-12"],
            "acceptance_datetime": pd.to_datetime(["2026-11-12T23:58:20Z"]),
            "report_date": ["2026-11-10"],
            "primary_document": ["form4.xml"],
        }
    )
    monkeypatch.setattr(insider, "fetch_filings", lambda *a, **k: filings)
    monkeypatch.setattr(
        insider, "filing_documents", lambda *a, **k: {"form4.xml": "https://example.test/form4.xml"}
    )
    monkeypatch.setattr(insider, "fetch_text", lambda *a, **k: NON_DERIVATIVE_XML)

    frame = insider.fetch_insider_transactions(320193)
    assert list(frame.columns) == list(insider.TRANSACTION_COLUMNS)
    assert len(frame) == 1
    assert frame["accession_number"].tolist() == ["0001140361-26-043484"]
    assert frame["reporting_owner"].tolist() == ["EXAMPLE, OFFICER"]
    assert str(frame["available_at"].iloc[0]) == "2026-11-12 23:58:20"


def test_fetch_insider_transactions_no_filings_returns_empty(monkeypatch):
    monkeypatch.setattr(insider, "fetch_filings", lambda *a, **k: pd.DataFrame())
    frame = insider.fetch_insider_transactions(320193)
    assert len(frame) == 0
    assert list(frame.columns) == list(insider.TRANSACTION_COLUMNS)


def test_fetch_insider_transactions_skips_filings_without_xml_or_with_bad_xml(monkeypatch):
    filings = pd.DataFrame(
        {
            "cik": ["0000320193"] * 4,
            "accession_number": ["no-xml", "malformed", "no-transaction", "ok"],
            "form": ["4"] * 4,
            "filing_date": ["2026-11-12"] * 4,
            "acceptance_datetime": pd.to_datetime(["2026-11-12T23:58:20Z"] * 4),
            "report_date": ["2026-11-10"] * 4,
            "primary_document": ["form4.xml"] * 4,
        }
    )
    monkeypatch.setattr(insider, "fetch_filings", lambda *a, **k: filings)
    documents = {
        "no-xml": FILING_INDEX_NO_XML,
        "malformed": {"form4.xml": "u"},
        "no-transaction": {"form4.xml": "u"},
        "ok": {"form4.xml": "u"},
    }
    monkeypatch.setattr(
        insider, "filing_documents", lambda cik, accession, **k: documents[accession]
    )
    # Every filing resolves to the same document URL, so the text is driven by
    # filing order rather than by URL.
    calls = iter(["<ownershipDocument>", NO_TRANSACTION_XML, NON_DERIVATIVE_XML])
    monkeypatch.setattr(insider, "fetch_text", lambda *a, **k: next(calls))

    frame = insider.fetch_insider_transactions(320193)
    assert frame["accession_number"].tolist() == ["ok"]


def test_fetch_insider_transactions_skips_a_filing_whose_index_fails(monkeypatch):
    filings = pd.DataFrame(
        {
            "cik": ["0000320193"],
            "accession_number": ["broken"],
            "form": ["4"],
            "filing_date": ["2026-11-12"],
            "acceptance_datetime": pd.to_datetime(["2026-11-12T23:58:20Z"]),
            "report_date": ["2026-11-10"],
            "primary_document": ["form4.xml"],
        }
    )

    def boom(*a, **k):
        raise OSError("index down")

    monkeypatch.setattr(insider, "fetch_filings", lambda *a, **k: filings)
    monkeypatch.setattr(insider, "filing_documents", boom)
    frame = insider.fetch_insider_transactions(320193)
    assert len(frame) == 0


def test_fetch_insider_transactions_honours_delay(monkeypatch):
    slept = []
    monkeypatch.setattr(insider.time, "sleep", lambda seconds: slept.append(seconds))
    filings = pd.DataFrame(
        {
            "cik": ["0000320193"],
            "accession_number": ["no-xml"],
            "form": ["4"],
            "filing_date": ["2026-11-12"],
            "acceptance_datetime": pd.to_datetime(["2026-11-12T23:58:20Z"]),
            "report_date": ["2026-11-10"],
            "primary_document": ["form4.xml"],
        }
    )
    monkeypatch.setattr(insider, "fetch_filings", lambda *a, **k: filings)
    monkeypatch.setattr(insider, "filing_documents", lambda *a, **k: FILING_INDEX_NO_XML)
    insider.fetch_insider_transactions(320193, delay=0.25)
    assert slept == [0.25]


def test_insider_net_buy_ratio_counts_only_open_market_trades():
    frame = insider.insider_net_buy_ratio(_transactions_fixture())
    assert frame["available_at"].tolist() == [
        pd.Timestamp("2026-11-05"),
        pd.Timestamp("2026-11-12"),
    ]
    purchase_day = frame.iloc[0]
    assert purchase_day["buys"] == 1
    assert purchase_day["sells"] == 0
    assert purchase_day["net_buy_ratio"] == 1.0
    sale_day = frame.iloc[1]
    assert sale_day["buys"] == 0
    assert sale_day["sells"] == 1
    assert sale_day["net_buy_ratio"] == 0.0


def test_insider_net_buy_ratio_empty_inputs():
    empty_columns = ["available_at", "buys", "sells", "net_buy_ratio"]
    assert insider.insider_net_buy_ratio(pd.DataFrame()).columns.tolist() == empty_columns
    no_open_market = pd.DataFrame(
        {"transaction_code": ["A", "M"], "available_at": pd.to_datetime(["2026-01-02"] * 2)}
    )
    assert insider.insider_net_buy_ratio(no_open_market).columns.tolist() == empty_columns
