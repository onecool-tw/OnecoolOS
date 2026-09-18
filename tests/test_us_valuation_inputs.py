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
