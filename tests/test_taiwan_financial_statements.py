from datetime import datetime, timezone
import pytest
from onecool_os.market.taiwan_financial_statements import assess_filing, parse_filing
from scripts.update_taiwan_financial_quality import enrich

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


def filing():
    contexts = {'end': ('', '2026-06-30'), 'opening': ('', '2025-12-31'),
                'prior': ('', '2025-06-30'), 'ytd': ('2026-01-01', '2026-06-30'),
                'prior_ytd': ('2025-01-01', '2025-06-30')}
    raw = '<html><ix:nonnumeric name="tifrs-notes:CompanyID">1234</ix:nonnumeric>'
    raw += '<xbrli:unit id="TWD"><xbrli:measure>iso4217:TWD</xbrli:measure></xbrli:unit>'
    for key, (start, end) in contexts.items():
        dates = f'<xbrli:startdate>{start}</xbrli:startdate><xbrli:enddate>{end}</xbrli:enddate>' if start else f'<xbrli:instant>{end}</xbrli:instant>'
        raw += f'<xbrli:context id="{key}"><xbrli:entity><xbrli:identifier>1234</xbrli:identifier></xbrli:entity><xbrli:period>{dates}</xbrli:period></xbrli:context>'
    fields = [
        ('ProfitLoss', 'ytd', 10), ('Revenue', 'ytd', 100), ('Revenue', 'prior_ytd', 90),
        ('ProfitLossFromOperatingActivities', 'ytd', 12), ('ProfitLossBeforeTax', 'ytd', 13),
        ('CashFlowsFromUsedInOperatingActivities', 'ytd', 11),
        ('Assets', 'end', 100), ('Assets', 'opening', 90), ('Equity', 'end', 60),
        ('Equity', 'opening', 50), ('Liabilities', 'end', 40),
        ('Inventories', 'end', 10), ('Inventories', 'prior', 9),
    ]
    fields += [('tifrs-bsci-ci:AccountsReceivableNet', 'end', 10),
               ('tifrs-bsci-ci:AccountsReceivableNet', 'prior', 9),
               ('tifrs-bsci-ci:NonoperatingIncomeAndExpenses', 'ytd', 1)]
    for name, ctx, value in fields:
        name = name if ':' in name else 'ifrs-full:' + name
        raw += f'<ix:nonfraction name="{name}" contextref="{ctx}" unitref="TWD" format="ixt:numdotdecimal" scale="3">{value}</ix:nonfraction>'
    return (raw + '</html>').encode()


def test_complete_period_and_scale():
    q = assess_filing(filing(), '1234', '2026Q2', NOW.isoformat())
    assert q['status'] == 'NORMAL'
    assert q['metrics']['operating_cashflow_twd'] == 11000
    assert q['metrics']['consolidated_roe_ytd_pct'] == pytest.approx(10 / 55 * 100)
    assert q['metrics']['consolidated_roe_ytd_pct'] == pytest.approx(
        q['metrics']['consolidated_roa_ytd_pct'] * q['metrics']['average_equity_multiplier'])


def test_negative_cash_flow():
    raw = filing().replace(b'format="ixt:numdotdecimal" scale="3">11<', b'format="ixt:numdotdecimal" scale="3" sign="-">11<')
    assert 'NEGATIVE_OPERATING_CASHFLOW' in assess_filing(raw, '1234', '2026Q2', NOW.isoformat())['flags']


def test_missing_cash_cannot_be_normal():
    raw = filing().replace(b'ifrs-full:CashFlowsFromUsedInOperatingActivities', b'ifrs-full:WrongConcept')
    assert assess_filing(raw, '1234', '2026Q2', NOW.isoformat())['status'] == 'INSUFFICIENT_DATA'


def test_wrong_entity_and_period():
    with pytest.raises(ValueError):
        assess_filing(filing(), '6669', '2026Q2', NOW.isoformat())
    assert assess_filing(filing(), '1234', '2026Q1', NOW.isoformat())['status'] == 'INSUFFICIENT_DATA'


def test_conflict_stays_invalid_after_third_duplicate():
    extra = b'<ix:nonfraction name="ifrs-full:Assets" contextref="end" unitref="TWD" format="ixt:numdotdecimal" scale="3">999</ix:nonfraction>'
    raw = filing() + extra + extra
    assert parse_filing(raw, '1234')[('ifrs-full:Assets', '', '2026-06-30')]['value'] is None


def test_enrichment_preserves_selection_and_caches():
    screen = {'top5': [{'symbol': '1234', 'industry': '電子', 'fundamentals_as_of': '2026Q2', 'score': 90}], 'rankings': [], 'cta': 'SELL'}
    cache = {}
    result = enrich(screen, cache, fetcher=lambda _: filing(), now=NOW)
    assert result['top5'][0]['score'] == 90 and result['cta'] == 'SELL'
    assert 'financial_quality' not in screen['top5'][0]
    def unavailable(_):
        raise AssertionError('Cache should avoid network')
    assert enrich(screen, cache, fetcher=unavailable, now=NOW) == result


def test_failure_and_sector_do_not_become_normal():
    screen = {'top5': [{'symbol': '1234', 'industry': '電子', 'fundamentals_as_of': '2026Q2'}]}
    def unavailable(_):
        raise OSError('Offline')
    result = enrich(screen, {}, fetcher=unavailable, now=NOW)
    assert result['top5'][0]['financial_quality']['status'] == 'INSUFFICIENT_DATA'
    screen['top5'][0]['industry'] = '金融保險'
    result = enrich(screen, {}, fetcher=lambda _: filing(), now=NOW)
    assert result['top5'][0]['financial_quality']['status'] == 'INSUFFICIENT_DATA'
