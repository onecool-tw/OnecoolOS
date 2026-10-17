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


@pytest.mark.parametrize("url,content_type,body,reason", [
    ("https://www.anuefund.com/", "text/html", "系統升級中".encode(), "ANUE_NAV_MAINTENANCE"),
    ("https://www.anuefund.com/", "text/html", b"<html>Home</html>", "ANUE_NAV_ENDPOINT_REDIRECTED"),
    (AnueFundClient.endpoint, "text/html", b"<html>Unavailable</html>", "ANUE_NAV_NON_JSON_RESPONSE"),
    (AnueFundClient.endpoint, "application/json", b"\xef\xbb\xbf<html>Unavailable</html>", "ANUE_NAV_NON_JSON_RESPONSE"),
    (AnueFundClient.endpoint, "application/json", b"", "ANUE_NAV_EMPTY_RESPONSE"),
])
def test_http_success_is_not_nav_success(monkeypatch, url, content_type, body, reason):
    from onecool_os.market.fund_alpha import _download
    from onecool_os.market.etf_cta import ETFCTAError
    class Response:
        headers = {"Content-Type": content_type}
        def geturl(self): return url
        def read(self): return body
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr("onecool_os.market.fund_alpha.urlopen", lambda *a, **k: Response())
    with pytest.raises(ETFCTAError, match=reason):
        _download(AnueFundClient.endpoint + "?FundID=B16019")


def test_valid_nav_response_remains_unchanged(monkeypatch):
    from onecool_os.market.fund_alpha import _download
    body = json.dumps({"data": {"fundID": "B16019", "hearder": {"ccy": "美元"},
                              "navHIS": [{"navDate": "2026-10-15", "nav": 83.72}]}}).encode()
    class Response:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        def geturl(self): return AnueFundClient.endpoint
        def read(self): return body
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr("onecool_os.market.fund_alpha.urlopen", lambda *a, **k: Response())
    assert _download(AnueFundClient.endpoint) == body
    assert AnueFundClient().fetch_history("B16019")[0].nav == 83.72
