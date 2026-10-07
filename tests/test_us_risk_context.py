from datetime import date
from onecool_os.market.etf_cta import DailyBar
from onecool_os.market.us_risk_context import collect_us_risk_context, RISK_SYMBOLS


def bar(day='2026-10-06'):
    return DailyBar(date.fromisoformat(day), 5, 6, 4, 5.3, 0, adjusted_close=5.3, source='yahoo_finance_raw')


def test_context_same_cutoff_without_cta_or_score():
    class Fetch:
        def fetch_raw_daily(self, symbol, period):
            assert symbol in {'^TNX', '^SOX'}
            return [bar('2026-10-05'), bar(), bar('2026-10-07')]
    got=collect_us_risk_context('2026-10-06', {s:[bar()] for s in ['VIX','DXY','US30Y']}, Fetch())
    assert got['data_status']=='READY'
    assert len(got['results'])==5
    assert all(r['as_of']=='2026-10-06' and r['value']==5.3 for r in got['results'])
    assert not any('cta' in r or 'score' in r for r in got['results'])


def test_stale_duplicate_and_fetch_failure_are_isolated():
    class Fetch:
        def fetch_raw_daily(self,*args,**kwargs): raise TimeoutError('provider request timed out')
    got=collect_us_risk_context('2026-10-06', {'VIX':[bar('2026-10-05')],'DXY':[bar(),bar()],'US30Y':[bar()]}, Fetch())
    assert got['data_status']=='PARTIAL'
    rows={r['symbol']:r for r in got['results']}
    assert rows['US30Y']['data_status']=='READY'
    for s in ['VIX','DXY','US10Y','SOX']:
        assert rows[s]['data_status']=='UNKNOWN' and rows[s]['value'] is None
    assert rows['US10Y']['error_type']=='TimeoutError'
