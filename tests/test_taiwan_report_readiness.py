from copy import deepcopy
from onecool_os.market.taiwan_stock_intelligence import report_readiness


def inputs():
    return ({'expected_as_of': '2026-09-10', 'data_status': 'READY',
             'top5': [{'symbol': '3006', 'price_as_of': '2026-09-10'}]},
            {'results': [{'symbol': '3006', 'as_of': '2026-09-10',
                          'cta': 'BUY', 'update_status': 'CURRENT'}]},
            {'results': [{'symbol': x, 'as_of': '2026-09-10', 'cta': 'BUY'}
                         for x in ['0050', '2330']]})


def test_same_day_ready_without_requiring_asia_or_monthly_data_today():
    s, c, d = inputs()
    before = deepcopy((s, c, d))
    assert report_readiness(s, c, d, '2026-09-10')['status'] == 'READY'
    assert (s, c, d) == before


def test_yesterday_screen_and_today_cta_is_not_complete():
    s, c, d = inputs()
    s['expected_as_of'] = s['top5'][0]['price_as_of'] = '2026-09-09'
    assert report_readiness(s, c, d, '2026-09-10')['status'] == 'UPDATE_INCOMPLETE'


def test_today_screen_cannot_hide_missing_duplicate_or_stale_cta():
    for mode in ['missing', 'duplicate', 'stale']:
        s, c, d = inputs()
        if mode == 'missing':
            c['results'] = []
        elif mode == 'duplicate':
            c['results'] *= 2
        else:
            c['results'][0]['update_status'] = 'STALE_LAST_KNOWN'
        assert report_readiness(s, c, d, '2026-09-10')['status'] == 'UPDATE_INCOMPLETE'


def test_missing_dashboard_cannot_be_complete():
    s, c, _ = inputs()
    assert report_readiness(s, c, {}, '2026-09-10')['status'] == 'UPDATE_INCOMPLETE'
