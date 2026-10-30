import io
from types import SimpleNamespace
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor

import pytest
from onecool_os.market import us_valuation_inputs as sec


def test_shared_rate_budget_serializes_concurrent_starts(monkeypatch):
    now = [0.0]
    def sleep(delay):
        now[0] += delay
    monkeypatch.setattr(sec, 'clock', SimpleNamespace(monotonic=lambda: now[0], sleep=sleep))
    monkeypatch.setattr(sec, '_SEC_NEXT_REQUEST', 0.0)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: sec._wait_for_sec_slot(), range(8)))
    assert now[0] == 3.5


def test_rate_limit_retry_obeys_retry_after_and_declares_contact(monkeypatch):
    attempts, delays = [], []
    monkeypatch.setattr(sec, '_wait_for_sec_slot', lambda: None)
    monkeypatch.setattr(sec, 'clock', SimpleNamespace(sleep=delays.append))
    def fetch(request, timeout):
        assert request.get_header('From') == 'luke@example.com'
        attempts.append(request.full_url)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 429, 'retry later', {'Retry-After': '7'}, None)
        return io.BytesIO(b'{"ok": true}')
    monkeypatch.setattr(sec, 'urlopen', fetch)
    assert sec.fetch_sec_json('https://data.sec.gov/test', 'Luke luke@example.com') == {'ok': True}
    assert len(attempts) == 2 and delays == [7.0]


@pytest.mark.parametrize('code', [403, 404])
def test_access_denial_is_not_retried(monkeypatch, code):
    calls = []
    monkeypatch.setattr(sec, '_wait_for_sec_slot', lambda: None)
    def fetch(request, timeout):
        calls.append(1)
        raise HTTPError(request.full_url, code, 'denied', {}, None)
    monkeypatch.setattr(sec, 'urlopen', fetch)
    with pytest.raises(HTTPError):
        sec.fetch_sec_json('https://data.sec.gov/test', '')
    assert len(calls) == 1


def test_malformed_json_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(sec, '_wait_for_sec_slot', lambda: None)
    def fetch(request, timeout):
        calls.append(1)
        return io.BytesIO(b'not json')
    monkeypatch.setattr(sec, 'urlopen', fetch)
    with pytest.raises(ValueError):
        sec.fetch_sec_json('https://data.sec.gov/test', '')
    assert len(calls) == 1


def test_fundamental_batch_preserves_denial_code_without_retry(monkeypatch):
    from onecool_os.market.sec_fundamentals import fill_missing_fundamentals
    from onecool_os.market import us_breakout_scan
    monkeypatch.setattr(us_breakout_scan, 'technical_confidence', lambda *_: (100, []))
    calls = []
    def fetch(cik):
        calls.append(cik)
        raise HTTPError('https://data.sec.gov/test', 403, 'denied', {}, None)
    client = SimpleNamespace(fetch_companyfacts=fetch, request_spacing_seconds=0)
    fundamentals = {}
    result = fill_missing_fundamentals(client, {'V': [object()]}, fundamentals,
        '2026-10-29', {}, {}, registry_mapping={'V': '1403161'})
    assert calls == ['0001403161']
    assert result['V']['http_status'] == 403
    assert fundamentals == {}


def test_batch_does_not_multiply_transport_retry_budget(monkeypatch):
    from onecool_os.market.sec_fundamentals import fill_missing_fundamentals
    from onecool_os.market import us_breakout_scan
    monkeypatch.setattr(us_breakout_scan, 'technical_confidence', lambda *_: (100, []))
    monkeypatch.setattr(sec, '_wait_for_sec_slot', lambda: None)
    monkeypatch.setattr(sec, 'clock', SimpleNamespace(sleep=lambda _: None))
    calls = []
    def fetch(request, timeout):
        calls.append(1)
        raise HTTPError(request.full_url, 503, 'unavailable', {}, None)
    monkeypatch.setattr(sec, 'urlopen', fetch)
    client = SimpleNamespace(fetch_companyfacts=lambda cik: sec.fetch_sec_json(
        'https://data.sec.gov/test', ''), request_spacing_seconds=0)
    result = fill_missing_fundamentals(client, {'V': [object()]}, {},
        '2026-10-29', {}, {}, registry_mapping={'V': '1403161'})
    assert len(calls) == 2
    assert result['V']['http_status'] == 503
