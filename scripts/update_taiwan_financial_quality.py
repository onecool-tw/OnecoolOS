"""Enrich formal Top 5 with official three-statement notes, without reranking."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from onecool_os.market.taiwan_financial_statements import VERSION, assess_filing, filing_url


def fetch_filing(url):
    with urlopen(Request(url, headers={'User-Agent': 'OnecoolOS/1.0'}), timeout=30) as response:
        return response.read(8_000_000)


def enrich(screen, cache, *, fetcher=fetch_filing, now=None):
    now = now or datetime.now(timezone.utc)
    results = {}

    def run(item):
        symbol, period = item['symbol'], item['fundamentals_as_of']
        fallback = deepcopy(item.get('financial_quality', {}))
        fallback.update(status='INSUFFICIENT_DATA', label='資料不足', as_of=period,
                        scope='THREE_STATEMENTS_UNVERIFIED', ranking_effect='NONE',
                        missing_checks=['official_xbrl_unavailable'], flags=[], metrics={},
                        evidence={}, observed_at=now.isoformat())
        if any(word in item.get('industry', '') for word in ('金融', '保險', '銀行', '證券')):
            fallback['reason'] = '金融業需專屬財報檢核'
            return symbol, fallback
        key = symbol + ':' + period
        old = cache.get(key, {})
        try:
            age = (now - datetime.fromisoformat(old['observed_at'])).total_seconds()
            if (old.get('version') == VERSION and old.get('as_of') == period
                    and old.get('status') in ('NORMAL', 'REVIEW') and 0 <= age < 86400):
                return symbol, deepcopy(old)
        except (KeyError, TypeError, ValueError):
            pass
        try:
            result = assess_filing(fetcher(filing_url(symbol, period)), symbol, period, now.isoformat())
            return symbol, result
        except Exception as exc:
            fallback['reason'] = '官方三表未能驗證：' + type(exc).__name__
            return symbol, fallback

    with ThreadPoolExecutor(max_workers=2) as pool:
        for symbol, result in pool.map(run, screen.get('top5', [])):
            results[symbol] = result
            cache[symbol + ':' + result['as_of']] = result
    updated = deepcopy(screen)
    for collection in ('top5', 'rankings', 'watchlist'):
        for item in updated.get(collection, []):
            if item['symbol'] in results:
                item['financial_quality'] = deepcopy(results[item['symbol']])
    return updated


def update(data_dir, *, fetcher=fetch_filing, now=None):
    screen_path = data_dir / 'screen_latest.json'
    screen = json.loads(screen_path.read_text())
    cache_path = data_dir / 'financial_quality_cache.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    result = enrich(screen, cache, fetcher=fetcher, now=now)
    # Only advisory metadata changes. Date, ranking and other source fields persist.
    destinations = [(screen_path, result), (cache_path, cache)]
    snapshot = data_dir / 'snapshots' / (screen['expected_as_of'] + '.json')
    if snapshot.exists():
        destinations.append((snapshot, result))
    for path, payload in destinations:
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        temporary.replace(path)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('data/market/taiwan_stock_intelligence'))
    args = parser.parse_args()
    result = update(args.data_dir)
    print(json.dumps([{ 'symbol': item['symbol'], 'quality': item['financial_quality']['label']}
                      for item in result['top5']], ensure_ascii=False))
