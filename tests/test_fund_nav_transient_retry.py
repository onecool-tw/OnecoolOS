import json
from urllib.error import HTTPError

import pytest

from onecool_os.market.fund_alpha import AnueFundClient


def test_transient_503_retries_same_fund_and_recovers(monkeypatch):
    waits, calls = [], []
    monkeypatch.setattr("onecool_os.market.fund_alpha.time.sleep", waits.append)
    def request(url):
        calls.append(url)
        if len(calls) < 3:
            raise HTTPError(url, 503, "Service Unavailable", {}, None)
        return json.dumps({"data": {"fundID": "B15080", "hearder": {"ccy": "美元"},
                                   "navHIS": [{"navDate": "2026-10-14", "nav": 60.95}]}}).encode()
    rows = AnueFundClient(request=request).fetch_history("B15080")
    assert len(calls) == 3 and len(set(calls)) == 1
    assert waits == [2, 4]
    assert rows[0].nav == 60.95


@pytest.mark.parametrize("status,expected_calls", [(503, 3), (404, 1)])
def test_failure_remains_visible_and_retry_is_bounded(monkeypatch, status, expected_calls):
    calls = []
    monkeypatch.setattr("onecool_os.market.fund_alpha.time.sleep", lambda _: None)
    def request(url):
        calls.append(url)
        raise HTTPError(url, status, "failure", {}, None)
    with pytest.raises(HTTPError):
        AnueFundClient(request=request).fetch_history("B15080")
    assert len(calls) == expected_calls


def test_invalid_payload_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr("onecool_os.market.fund_alpha.time.sleep", lambda _: pytest.fail("must not retry"))
    def request(url):
        calls.append(url)
        return b"not json"
    with pytest.raises(json.JSONDecodeError):
        AnueFundClient(request=request).fetch_history("B15080")
    assert len(calls) == 1
