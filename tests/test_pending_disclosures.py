from copy import deepcopy
from datetime import date
from types import SimpleNamespace

from onecool_os.market.us_valuation_inputs import check_pending_disclosures, collect_valuation_inputs


def setup_rows(times=None):
    recent = {
        'accessionNumber': ['0000000001-26-000001', '0000000001-26-000002', '0000000001-26-000003'],
        'filingDate': ['2026-10-20'] * 3,
        'form': ['10-Q', '8-K', '4'],
        'primaryDocument': ['earnings.htm', 'event.htm', 'insider.xml'],
        'acceptanceDateTime': times or ['2026-10-20T19:59:00Z', '2026-10-20T20:01:00Z', '2026-10-20T15:00:00Z'],
    }
    payload = {'cik': 1, 'filings': {'recent': recent}}
    calls = []
    def fetch(url):
        calls.append(url)
        return payload
    official = {'symbol': 'TEST', 'company_name': 'Test Inc.', 'published_at': '2026-08-01',
        'reviewed_as_of': '2026-10-19', 'valid_through': '2026-10-23',
        'sources': ['https://www.sec.gov/Archives/old.htm'], 'reported_facts': {'eps': 5},
        'model_gaps': ['POST_TRANSACTION_BRIDGE_UNAVAILABLE'],
        'source_review': {'status': 'EXTERNAL_DISCLOSURE_PENDING', 'checked_at': '2026-10-20T08:00:00Z'}}
    return SimpleNamespace(_fetch=fetch), official, payload, calls


def test_before_close_only_and_identity_and_form_filters():
    client, official, _, calls = setup_rows()
    result = check_pending_disclosures(client, '1', official, date(2026, 10, 20))
    assert result['status'] == 'NEW_DISCLOSURE_REQUIRES_REVIEW'
    assert len(result['filings']) == 1
    assert result['filings'][0]['form'] == '10-Q'
    assert '/1/000000000126000001/earnings.htm' in result['filings'][0]['url']
    assert len(calls) == 1


def test_same_day_without_timestamp_cannot_enter_and_future_cannot_enter():
    client, official, payload, _ = setup_rows(['', '', ''])
    payload['filings']['recent']['filingDate'][1] = '2026-10-21'
    result = check_pending_disclosures(client, 1, official, date(2026, 10, 20))
    assert result['status'] == 'NO_NEW_ELIGIBLE_FILINGS'


def test_malformed_or_wrong_cik_is_failure_not_no_news():
    for kind in ['identity', 'schema']:
        client, official, payload, _ = setup_rows()
        if kind == 'identity':
            payload['cik'] = 2
        else:
            payload['filings']['recent']['form'].pop()
        result = check_pending_disclosures(client, 1, official, date(2026, 10, 20))
        assert result['status'] == 'FETCH_OR_VALIDATION_FAILED'


def test_timeout_isolated_from_other_candidates_and_no_score_mutation():
    client, official, _, _ = setup_rows()
    def fail(url):
        raise TimeoutError('bounded SEC failure')
    client._fetch = fail
    scan = {'expected_as_of': '2026-10-20', 'data_status': 'READY', 'price_basis': 'adjusted_close',
        'top5': [{'symbol': 'TEST', 'price_as_of': '2026-10-20', 'validation_status': 'PASSED',
                  'technical_confidence': 100, 'canslim_score': 75, 'minervini_score': 90}]}
    original = deepcopy(scan)
    bars = {'TEST': [SimpleNamespace(trading_date=date(2026, 10, 20), adjusted_close=100, close=100, source='yahoo')]}
    result = collect_valuation_inputs(scan, bars, None, client, {'TEST': '1'}, {'results': {'TEST': official}})
    record = result['results'][0]
    assert record['valuation_input_collection']['official_disclosure_watch']['status'] == 'FETCH_OR_VALIDATION_FAILED'
    assert record['gates']['valuation']['status'] == 'UNKNOWN'
    assert scan == original


def test_discovery_does_not_invent_earnings_or_promote_valuation():
    client, official, _, _ = setup_rows()
    scan = {'expected_as_of': '2026-10-20', 'data_status': 'READY', 'price_basis': 'adjusted_close',
        'top5': [{'symbol': 'TEST', 'price_as_of': '2026-10-20', 'validation_status': 'PASSED', 'technical_confidence': 100}]}
    bars = {'TEST': [SimpleNamespace(trading_date=date(2026, 10, 20), adjusted_close=100, close=100, source='yahoo')]}
    result = collect_valuation_inputs(scan, bars, None, client, {'TEST': '1'}, {'results': {'TEST': official}})
    record = result['results'][0]
    assert record['gates']['valuation']['status'] == 'UNKNOWN'
    assert record['gates']['valuation']['data_gap'] == 'NEW_OFFICIAL_DISCLOSURE_REQUIRES_NORMALIZATION_REVIEW'
    assert record['valuation_input_collection']['inputs'] == {'adjusted_close': 100}
