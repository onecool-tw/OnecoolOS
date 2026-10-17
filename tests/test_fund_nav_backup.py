from datetime import date, timedelta
from pathlib import Path
import shutil
from dataclasses import replace

import pytest
from onecool_os.market.etf_cta import ETFCTAError
from onecool_os.market.fund_alpha import FundNav, read_nav_history
from onecool_os.market.fund_nav_backup import (
    MONEYDJ_FUNDS, MoneyDJFundClient, parse_moneydj_nav, validate_backup,
)
from scripts.update_fund_nav_cta import update

ROOT = Path(__file__).resolve().parents[1]


def document(code, rows):
    name = MONEYDJ_FUNDS[code][2]
    last = rows[-1]
    header = f'<tr><td>{last.nav_date:%Y/%m/%d}</td><td>{last.nav:.4f}</td></tr>'
    history = ''.join(f'<tr><td>{r.nav_date:%m/%d}</td><td>{r.nav:.4f}</td><td>0%</td></tr>' for r in reversed(rows))
    return f'<html><head><title>{name}-淨值表</title></head><body><table>{header}</table><table>{history}</table></body></html>'.encode('big5')


def history(code):
    return read_nav_history(ROOT / f'data/market/fund_nav/history/{code}.csv')


@pytest.mark.parametrize('code', MONEYDJ_FUNDS)
def test_seven_explicit_share_class_mappings_and_append_only(code):
    old = history(code)
    new = FundNav(old[-1].nav_date + timedelta(days=1), old[-1].nav, 'USD')
    rows = parse_moneydj_nav(document(code, old[-29:] + [new]), code)
    appended, overlaps = validate_backup(old, rows)
    assert overlaps == 29
    assert len(appended) == 1 and appended[0].nav_date == new.nav_date
    assert appended[0].source == 'moneydj_public_verified'


def test_backup_conflict_insufficient_overlap_duplicate_currency_and_stale():
    old = history('B16019')
    incoming = old[-30:]
    bad_cases = [
        [replace(incoming[0], nav=incoming[0].nav + .01)] + incoming[1:],
        incoming[-7:], incoming + [incoming[-1]],
        [replace(x, currency='TWD') for x in incoming], incoming[:-1],
    ]
    for rows in bad_cases:
        with pytest.raises(ETFCTAError):
            validate_backup(old, rows)
    unchanged, count = validate_backup(old, incoming)
    assert unchanged == [] and count == 30


def test_parser_rejects_wrong_class_missing_anchor_future_and_invalid_nav():
    rows = history('A10124')[-10:]
    body = document('A10124', rows)
    for bad in [body.replace('A類型'.encode('big5'), 'N類型'.encode('big5')),
                body.replace(rows[-1].nav_date.strftime('%Y/').encode(), b''),
                body.replace(f'{rows[-1].nav:.4f}'.encode(), b'nan')]:
        with pytest.raises((ETFCTAError, ValueError)):
            parse_moneydj_nav(bad, 'A10124')
    with pytest.raises(ETFCTAError, match='IDENTITY'):
        parse_moneydj_nav(document('A16075', history('A16075')[-10:]), 'A10124')
    with pytest.raises(ETFCTAError, match='FUTURE'):
        parse_moneydj_nav(body, 'A10124', today=rows[-1].nav_date - timedelta(days=1))


def test_explicit_year_anchor_handles_new_year_without_future_rows():
    rows = [FundNav(date(2025,12,26)+timedelta(days=i), 100., 'USD') for i in range(10)]
    parsed = parse_moneydj_nav(document('B16019', rows), 'B16019', today=date(2026,1,5))
    assert [x.nav_date for x in parsed] == [x.nav_date for x in rows]


def test_all_primary_failed_can_publish_verified_backup(tmp_path):
    dest = tmp_path / 'data/market/fund_nav/history'
    dest.mkdir(parents=True)
    documents = {}
    for code in MONEYDJ_FUNDS:
        shutil.copy(ROOT / f'data/market/fund_nav/history/{code}.csv', dest)
        old = history(code)
        extra = replace(old[-1], nav_date=old[-1].nav_date+timedelta(days=1))
        documents[MONEYDJ_FUNDS[code][0]] = document(code, old[-29:]+[extra])
    class Failed:
        def fetch_history(self, code):
            raise ETFCTAError('ANUE_NAV_MAINTENANCE')
    backup = MoneyDJFundClient(request=lambda url: documents[url.split('=')[-1]])
    p = update(tmp_path, client=Failed(), backup_client=backup)
    assert p['nav_refresh']['status'] == 'COMPLETE'
    assert p['nav_refresh']['successful_provider_reads'] == 7
    for x in p['results']:
        audit = x['nav_refresh']['backup']
        assert audit['overlap_observations'] == 29
        assert audit['appended_observations'] == 1
        assert x['nav_refresh']['primary_error'].endswith('ANUE_NAV_MAINTENANCE')
        persisted = read_nav_history(dest / (x['fund_code']+'.csv'))
        assert persisted[:-1] == history(x['fund_code'])
        assert persisted[-1].source == 'moneydj_public_verified'


def test_healthy_primary_does_not_call_backup(tmp_path):
    class Primary:
        def fetch_history(self, code): return history(code)
    class Backup:
        def fetch_verified(self, *args): pytest.fail('healthy primary must not use backup')
    p = update(tmp_path, client=Primary(), backup_client=Backup())
    assert all('backup' not in x['nav_refresh'] for x in p['results'])


def test_conflicting_backup_cannot_change_verified_files(tmp_path):
    dest = tmp_path / 'data/market/fund_nav/history'
    dest.mkdir(parents=True)
    before = {}
    for code in MONEYDJ_FUNDS:
        target = dest / (code+'.csv')
        shutil.copy(ROOT / f'data/market/fund_nav/history/{code}.csv', target)
        before[code] = target.read_bytes()
    class Primary:
        def fetch_history(self, code): raise ETFCTAError('maintenance')
    class Backup:
        def fetch_verified(self, code, existing): raise ETFCTAError('BACKUP_CONFLICT')
    with pytest.raises(ETFCTAError, match='All seven'):
        update(tmp_path, client=Primary(), backup_client=Backup())
    assert all((dest/(code+'.csv')).read_bytes() == body for code,body in before.items())
    assert not (dest.parent/'fund_cta_latest.json').exists()
