"""Export a read-only, allowlisted projection of formal Taiwan SSOT files.

No market feeds, CTA engines, pressure evaluators or ranking algorithms run here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

OUTPUT = 'data/public/taiwan_stock_family_latest.json'
SOURCES = {
    'dashboard': 'data/market/dashboard/dashboard_latest.json',
    'screen': 'data/market/taiwan_stock_intelligence/screen_latest.json',
    'cta': 'data/market/taiwan_stock_intelligence/cta/cta_latest.json',
    'context': 'data/market/taiwan_stock_intelligence/daily_context_latest.json',
}
CTA_FIELDS = ('symbol', 'as_of', 'cta', 'trend', 'state', 'update_status',
              'price_basis', 'weekly_data_as_of', 'source_data_as_of', 'error')
STOCK_FIELDS = ('symbol', 'company_name', 'industry', 'score', 'pe', 'pb',
                'price_as_of', 'fundamentals_as_of', 'monthly_revenue_as_of',
                'price_basis', 'selection_status', 'action_eligibility')


def unique(items):
    result = {}
    for item in items:
        symbol = item['symbol']
        if symbol in result:
            raise ValueError('Duplicate symbol: ' + symbol)
        result[symbol] = item
    return result


def project(item, fields):
    return {key: item[key] for key in fields if key in item}


def build_snapshot(root: Path):
    docs, provenance = {}, {}
    for name, path in SOURCES.items():
        raw = (root / path).read_bytes()
        docs[name] = json.loads(raw)
        provenance[name] = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}
    screen, context = docs['screen'], docs['context']
    stocks = unique(docs['cta']['results'])
    indices = unique(docs['dashboard']['results'])
    rows = screen['top5']
    unique(rows)
    if len(rows) > 5 or [r['symbol'] for r in rows] != [r['symbol'] for r in context['top5']]:
        raise ValueError('Screen/context Top 5 mismatch')
    if screen['expected_as_of'] != context['screen_as_of']:
        raise ValueError('Screen/context cutoff mismatch')
    top5 = []
    for row, merged in zip(rows, context['top5']):
        for key, value in project(row, STOCK_FIELDS).items():
            if merged.get(key) != value:
                raise ValueError('Screen/context field mismatch: ' + key)
        cached = stocks.get(row['symbol'])
        individual = merged['individual_cta']
        if cached is not None:
            for key in ('cta', 'as_of', 'update_status'):
                if individual.get(key) != cached.get(key):
                    raise ValueError('CTA/context mismatch: ' + row['symbol'])
        elif individual.get('update_status') != 'UNKNOWN':
            raise ValueError('Unbacked individual CTA')
        top5.append({**project(merged, STOCK_FIELDS),
                     'individual_cta': project(cached or individual, CTA_FIELDS)})
    pressure = context['market_pressure']
    for key in ('as_of', 'status', 'light', 'action'):
        if key not in pressure:
            raise ValueError('Missing pressure field: ' + key)
    return {
        'schema_version': '1.0',
        'module': 'Onecool Taiwan Family Read-only Snapshot',
        'consumer_policy': {
            'read_only': True, 'recalculate_cta': False,
            'recalculate_market_pressure': False, 'rerank_top5': False,
            'preserve_source_dates_and_status': True,
            'stale_or_missing_data': 'NO_NEW_EXPOSURE',
        },
        'sources': provenance,
        'source_generated_at': {k: v.get('generated_at') for k, v in docs.items()},
        'screen_as_of': context['screen_as_of'],
        'display_status': context['display_status'],
        'report_readiness': context.get('report_readiness', {'status': 'Unknown'}),
        'candidate_action_gate': context['candidate_action_gate'],
        'market_pressure': pressure,
        'market_cta': {symbol: project(indices[symbol], CTA_FIELDS)
                       for symbol in ('0050', '2330', '1306', '069500')},
        'top5': top5,
    }


def export_snapshot(root: Path, check=False):
    payload = build_snapshot(root)
    destination = root / OUTPUT
    if check:
        if json.loads(destination.read_text(encoding='utf-8')) != payload:
            raise ValueError('Snapshot does not match current formal sources')
        return payload
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                     delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    export_snapshot(root, check=True)
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = export_snapshot(args.root, args.check)
    print(json.dumps({'validated': True, 'screen_as_of': result['screen_as_of'],
                      'top5_count': len(result['top5'])}))
