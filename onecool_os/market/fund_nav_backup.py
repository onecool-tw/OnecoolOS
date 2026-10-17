"""Independent NAV acquisition with strict identity and append-only validation."""
from __future__ import annotations

from datetime import date, timedelta, datetime, UTC
from hashlib import sha256
from math import isfinite
import re
import unicodedata
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from onecool_os.market.etf_cta import ETFCTAError
from onecool_os.market.fund_alpha import FundNav

# Explicit share-class mappings; never discover a replacement by fuzzy name.
MONEYDJ_FUNDS = {
    'A10124': ('ACFP111', 'yp010000', '富邦AI智能新趨勢多重資產型基金-A類型(美元)'),
    'A16075': ('ACCA74', 'yp010000', '群益印度中小基金(美元)'),
    'B23554': ('PYZQ4', 'yp010001', '施羅德環球基金系列-環球黃金(美元)A-累積'),
    'B15080': ('FLZ81', 'yp010001', '富蘭克林坦伯頓全球投資系列生技領航基金美元A(acc)'),
    'B09007': ('SHZ19', 'yp010001', '貝萊德世界礦業基金A2美元'),
    'B16019': ('ISZ04', 'yp010001', '景順環球消費趨勢基金A股美元'),
    'B23070': ('PYZE3', 'yp010001', '施羅德環球基金系列-環球能源(美元)A1-累積'),
}


def _normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))


def parse_moneydj_nav(document: bytes, fund_code: str, *, today=None):
    """Read raw USD NAV, anchored to the page's explicit full valuation date."""
    _, _, identity = MONEYDJ_FUNDS[fund_code]
    soup = BeautifulSoup(document.decode('big5', errors='strict'), 'html.parser')
    title = soup.title.get_text() if soup.title else ''
    if _normalized(identity) not in _normalized(title):
        raise ETFCTAError('BACKUP_IDENTITY_MISMATCH: share class or currency differs')
    full, short = [], []
    for row in soup.find_all('tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        values = [c.get_text('', strip=True) for c in cells]
        if len(values) < 2:
            continue
        if re.fullmatch(r'\d{4}/\d{2}/\d{2}', values[0]):
            full.append((date.fromisoformat(values[0].replace('/', '-')), float(values[1].replace(',', ''))))
        elif re.fullmatch(r'\d{2}/\d{2}', values[0]):
            short.append((values[0], float(values[1].replace(',', ''))))
    if len(full) != 1:
        raise ETFCTAError('BACKUP_DATE_ANCHOR_MISSING_OR_DUPLICATED')
    anchor, latest_nav = full[0]
    if anchor > (today or date.today()):
        raise ETFCTAError('BACKUP_FUTURE_DATE')
    rows = {}
    for month_day, nav in short:
        month, day = map(int, month_day.split('/'))
        # Only the recent table is used; December rows on a January page
        # belong to the previous year, never to an invented future date.
        year = anchor.year - ((month, day) > (anchor.month, anchor.day))
        day = date(year, month, day)
        if not (anchor - timedelta(days=90) <= day <= anchor):
            raise ETFCTAError('BACKUP_DATE_OUTSIDE_RECENT_WINDOW')
        if not isfinite(nav) or nav <= 0 or day in rows:
            raise ETFCTAError('BACKUP_INVALID_OR_DUPLICATE_NAV')
        rows[day] = FundNav(nav_date=day, nav=nav, currency='USD', source='moneydj_public_verified')
    if len(rows) < 8 or anchor not in rows or abs(rows[anchor].nav - latest_nav) > 0.000050001:
        raise ETFCTAError('BACKUP_HEADER_HISTORY_MISMATCH_OR_INSUFFICIENT_ROWS')
    return sorted(rows.values(), key=lambda row: row.nav_date)


def validate_backup(existing, incoming):
    """Require eight matching overlaps; reject conflicts and never revise history."""
    if not existing or not incoming:
        raise ETFCTAError('BACKUP_BASELINE_REQUIRED')
    old = {x.nav_date: x for x in existing}
    if len(old) != len(existing) or len({x.nav_date for x in incoming}) != len(incoming):
        raise ETFCTAError('BACKUP_DUPLICATE_DATE')
    if any(x.currency != 'USD' or not isfinite(x.nav) or x.nav <= 0 for x in [*existing, *incoming]):
        raise ETFCTAError('BACKUP_INVALID_CURRENCY_OR_NAV')
    latest = max(old)
    if max(x.nav_date for x in incoming) < latest:
        raise ETFCTAError('BACKUP_STALE_BEHIND_EXISTING')
    overlap = [x for x in incoming if x.nav_date in old]
    if len(overlap) < 8 or latest not in {x.nav_date for x in overlap}:
        raise ETFCTAError('BACKUP_INSUFFICIENT_OVERLAP')
    if any(abs(x.nav - old[x.nav_date].nav) > 0.000050001 for x in overlap):
        raise ETFCTAError('BACKUP_CONFLICT: overlapping NAV differs beyond four-decimal rounding')
    return [x for x in incoming if x.nav_date > latest], len(overlap)


class MoneyDJFundClient:
    def __init__(self, request=None):
        self.request = request or self._download
        self.evidence = {}

    @staticmethod
    def _download(url):
        with urlopen(Request(url, headers={'User-Agent': 'OnecoolOS/1.0'}), timeout=20) as response:
            if response.geturl() != url:
                raise ETFCTAError('BACKUP_UNEXPECTED_REDIRECT')
            return response.read()

    def fetch_verified(self, fund_code, existing):
        code, page, _ = MONEYDJ_FUNDS[fund_code]
        url = f'https://www.moneydj.com/funddj/ya/{page}.djhtm?a={code}'
        body = self.request(url)
        rows = parse_moneydj_nav(body, fund_code)
        new_rows, overlap = validate_backup(existing, rows)
        self.evidence[fund_code] = {
            'provider': 'moneydj_public_verified', 'source_url': url,
            'document_sha256': sha256(body).hexdigest(),
            'fetched_at': datetime.now(UTC).isoformat(),
            'effective_source_date': rows[-1].nav_date.isoformat(),
            'overlap_observations': overlap, 'appended_observations': len(new_rows),
            'validation': 'MATCHED_OVERLAP_APPEND_ONLY',
        }
        return new_rows
