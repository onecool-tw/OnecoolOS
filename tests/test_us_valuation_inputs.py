from datetime import date
from types import SimpleNamespace
from onecool_os.market.us_valuation_inputs import collect_valuation_inputs

def fixture():
    scan = {"expected_as_of": "2026-09-17", "data_status": "READY", "price_basis": "adjusted_close",
            "top5": [{"symbol": "TEST", "validation_status": "PASSED", "technical_confidence": 100, "price_as_of": "2026-09-17"}]}
    bars = {"TEST": [SimpleNamespace(trading_date=date(2026,9,17), adjusted_close=100, close=100, source="yahoo_finance")]}
    rows = [{"start":"2025-01-01", "end":"2025-12-31", "filed":"2026-02-10", "form":"10-K", "val":5},
            {"start":"2025-01-01", "end":"2025-12-31", "filed":"2026-09-17", "form":"10-K/A", "val":20}]
    facts = {"cik": 1, "facts":{"us-gaap":{"EarningsPerShareDiluted":{"units":{"USD/shares":rows}}}}}
    return scan, bars, SimpleNamespace(fetch_companyfacts=lambda cik: facts)

def test_actual_bar_and_point_in_time_filing_preserved_without_promoting_gate():
    scan, bars, client = fixture()
    evidence = {"results":[{"symbol":"TEST", "gates":{"valuation":{"status":"UNKNOWN"}}}]}
    got = collect_valuation_inputs(scan,bars,evidence,client,{"TEST":"1"})
    row = got["results"][0]
    assert row["valuation_input_collection"]["inputs"] == {"adjusted_close":100,"annual_gaap_diluted_eps":5}
    assert row["gates"] == evidence["results"][0]["gates"]
    assert "valuation_input_collection" not in evidence["results"][0]

def test_missing_or_duplicate_close_never_substituted():
    scan, bars, client = fixture()
    for histories in ({}, {"TEST":bars["TEST"]*2}):
        pack = collect_valuation_inputs(scan,histories,None,client,{"TEST":"1"})["results"][0]["valuation_input_collection"]
        assert "adjusted_close" not in pack["inputs"]
        assert "SAME_CUTOFF_ADJUSTED_CLOSE_UNAVAILABLE" in pack["gaps"]

def test_provider_failure_is_explicit_and_does_not_throw():
    scan, bars, client = fixture()
    def fail(cik): raise TimeoutError()
    client.fetch_companyfacts=fail
    pack = collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"})["results"][0]["valuation_input_collection"]
    assert pack["fundamental_fetch_status"] == "FETCH_FAILED"
    assert pack["fetch_error_type"] == "TimeoutError"

def test_stale_scan_rejected():
    scan,bars,client=fixture()
    scan["data_status"]="UNKNOWN"
    try: collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"})
    except ValueError: return
    raise AssertionError("stale scan accepted")

def reviewed_fixture():
    return {"results": {"TEST": {
        "symbol": "TEST", "company_name": "Test Inc.",
        "published_at": "2026-09-01", "valid_through": "2026-09-30",
        "sources": ["https://issuer.example/earnings"],
        "reported_facts": {"forward_eps": 5},
        "model_gaps": ["SOURCE_BACKED_FAIR_VALUE_RANGE_REQUIRED"],
    }}}

def test_official_fallback_avoids_sec_and_names_actual_model_gap():
    scan, bars, client = fixture()
    def fail(cik): raise AssertionError("SEC must not be called")
    client.fetch_companyfacts = fail
    got = collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"},reviewed_fixture())
    row=got["results"][0]
    assert row["valuation_input_collection"]["fundamental_fetch_status"] == "REVIEWED_OFFICIAL_REFERENCE"
    assert row["valuation_input_collection"]["gaps"] == ["SOURCE_BACKED_FAIR_VALUE_RANGE_REQUIRED"]
    assert row["gates"]["valuation"]["status"] == "UNKNOWN"

def complete_model():
    reviewed=reviewed_fixture()
    row=reviewed["results"]["TEST"]
    row["model_gaps"]=[]
    row["valuation_model"]={"method":"normalized_pe", "denominator":5,
        "currency":"USD", "share_basis":"listed_security", "fair_range":[15,25],
        "rationale":"Test scenario", "normalization_bridge":"No adjustments",
        "denominator_source":"https://issuer.example/earnings",
        "fair_range_rationale":"Explicit test policy assumptions",
        "fair_range_sources":["https://example.com/test-policy"], "policy_version":"test-v1"}
    return reviewed

def test_complete_model_refreshes_price_and_uses_existing_gate_validator():
    scan,bars,client=fixture()
    for price,expected in ((100,"PASS"),(150,"FAIL")):
        bars["TEST"][0].adjusted_close=price
        got=collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"},complete_model())
        gate=got["results"][0]["gates"]["valuation"]
        assert gate["status"] == expected
        assert gate["inputs"]["multiple"] == price/5
        assert gate["price_as_of"] == gate["valid_through"] == scan["expected_as_of"]
        assert scan["top5"][0]["technical_confidence"] == 100

def test_expired_future_and_wrong_identity_references_rejected():
    scan,bars,client=fixture()
    for field,value in (("valid_through","2026-09-16"),("published_at","2026-09-17"),("symbol","WRONG")):
        reviewed=reviewed_fixture()
        reviewed["results"]["TEST"][field]=value
        got=collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"},reviewed)
        row=got["results"][0]
        assert row["valuation_input_collection"]["official_reference_status"] == "REJECTED"
        assert row["gates"]["valuation"]["status"] == "UNKNOWN"

def test_stale_pass_cannot_survive_missing_close_or_invalid_candidate():
    scan,bars,client=fixture()
    evidence={"results":[{"symbol":"TEST","gates":{"valuation":{"status":"PASS","as_of":"2026-09-16"}}}]}
    got=collect_valuation_inputs(scan,{},evidence,client,{"TEST":"1"},complete_model())
    assert got["results"][0]["gates"]["valuation"]["status"] == "UNKNOWN"
    scan["top5"][0]["technical_confidence"]=89
    got=collect_valuation_inputs(scan,bars,evidence,client,{"TEST":"1"},complete_model())
    assert got["results"][0]["gates"]["valuation"]["status"] == "UNKNOWN"

def test_incomplete_or_wrong_currency_model_never_promoted():
    scan,bars,client=fixture()
    for field,value in (("currency","TWD"),("denominator",0),("fair_range",[25,15]),("normalization_bridge","")):
        reviewed=complete_model()
        reviewed["results"]["TEST"]["valuation_model"][field]=value
        got=collect_valuation_inputs(scan,bars,None,client,{"TEST":"1"},reviewed)
        assert got["results"][0]["gates"]["valuation"]["status"] == "UNKNOWN"
