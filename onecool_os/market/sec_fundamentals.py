"""Conservative point-in-time fallback from SEC company facts.

Never substitutes adjusted earnings, YTD EPS, or a different currency.
Same-day filings are excluded because Company Facts only supplies filing dates.
"""
from datetime import date
from math import isfinite

TAGS = {
    'us-gaap': {
        'eps': ('EarningsPerShareDiluted',),
        'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'),
    },
    'ifrs-full': {
        'eps': ('DilutedEarningsLossPerShare',),
        'revenue': ('Revenue',),
    },
}


def _series(facts, namespace, tags, cutoff, duration):
    candidates = []
    for tag in tags:
        for unit, rows in facts.get('facts', {}).get(namespace, {}).get(tag, {}).get('units', {}).items():
            # Preserve one tag/unit per comparison; do not merge taxonomies.
            valid = {}
            for row in rows:
                try:
                    start, end, filed = [date.fromisoformat(row[k]) for k in ('start', 'end', 'filed')]
                    if not (duration[0] <= (end-start).days <= duration[1] and end <= cutoff and filed < cutoff):
                        continue
                    if row.get('form') not in {'10-Q', '10-K', '20-F', '40-F', '6-K', '10-Q/A', '10-K/A', '20-F/A'} or not isfinite(float(row['val'])):
                        continue
                    key = (row['start'], row['end'])
                    if key not in valid or row['filed'] > valid[key]['filed']:
                        valid[key] = row
                except (KeyError, TypeError, ValueError, OverflowError):
                    continue
            if valid:
                candidates.append((tag, unit, sorted(valid.values(), key=lambda r: (r['end'], r['filed']), reverse=True)))
    return candidates


def _pair(rows):
    current = rows[0]
    end = date.fromisoformat(current['end'])
    length = (end-date.fromisoformat(current['start'])).days
    prior = [r for r in rows[1:] if 350 <= (end-date.fromisoformat(r['end'])).days <= 380
             and abs((date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days-length) <= 10]
    return (current, prior[0]) if prior else None


def extract_fundamentals(facts, expected_as_of):
    """Return raw evidence and an explicit reason; a nonpositive base is invalid."""
    cutoff = date.fromisoformat(expected_as_of)
    for namespace, tags in TAGS.items():
        eps_series = _series(facts, namespace, tags['eps'], cutoff, (70, 105))
        if not eps_series:
            continue
        latest_end = max(rows[0]['end'] for _, _, rows in eps_series)
        for eps_tag, eps_unit, eps_rows in eps_series:
            if eps_rows[0]['end'] != latest_end:
                continue
            quarter = _pair(eps_rows)
            if not quarter:
                return None, 'SEC_QUARTERLY_EPS_COMPARISON_MISSING'
            if not eps_unit.endswith('/shares'):
                continue
            currency = eps_unit.split('/')[0]
            revenue_options = _series(facts, namespace, tags['revenue'], cutoff, (70, 105))
            revenue = next(((_pair(rows), tag) for tag, unit, rows in revenue_options
                            if unit == currency and rows[0]['end'] == latest_end and _pair(rows)), None)
            annual_options = _series(facts, namespace, tags['eps'], cutoff, (330, 380))
            annual = next((_pair(rows) for tag, unit, rows in annual_options if tag == eps_tag and unit == eps_unit and _pair(rows)), None)
            if revenue is None or annual is None:
                return None, 'SEC_COMPARABLE_REVENUE_OR_ANNUAL_EPS_MISSING'
            pairs = {'quarterly_eps': quarter, 'quarterly_revenue': revenue[0], 'annual_eps': annual}
            if quarter[1]['end'] != revenue[0][1]['end'] or quarter[0]['start'] != revenue[0][0]['start'] or quarter[1]['start'] != revenue[0][1]['start']:
                return None, 'SEC_PERIOD_MISMATCH'
            evidence = {'accounting_basis': namespace, 'currency': currency, 'cik': facts.get('cik'),
                        'entity_name': facts.get('entityName'), 'eps_tag': eps_tag, 'revenue_tag': revenue[1],
                        'pairs': {k: {'current': a, 'prior': b} for k, (a, b) in pairs.items()}}
            if (cutoff-date.fromisoformat(latest_end)).days > 180:
                return evidence, 'SEC_STALE_QUARTER'
            if (cutoff-date.fromisoformat(annual[0]['end'])).days > 550:
                return evidence, 'SEC_STALE_ANNUAL'
            invalid = [k for k, (_, b) in pairs.items() if float(b['val']) <= 0]
            if invalid:
                return evidence, 'NONPOSITIVE_COMPARISON_BASE:' + ','.join(invalid)
            return evidence, 'SEC_VERIFIED'
    return None, 'SEC_QUARTERLY_DILUTED_EPS_MISSING'


def fill_missing_fundamentals(client, histories, fundamentals, expected_as_of, cache, diagnostics, registry_mapping=None):
    """Fetch SEC sequentially, retaining raw filing evidence and distinct exclusions."""
    from dataclasses import asdict
    from onecool_os.market.us_breakout_scan import FundamentalMetrics, technical_confidence
    expected = date.fromisoformat(expected_as_of)
    missing = [s for s, bars in histories.items() if s not in fundamentals and technical_confidence(bars, expected)[0] >= 90]
    if not missing:
        return {}
    try:
        registry = client._fetch('https://www.sec.gov/files/company_tickers.json')
        mapping = {r['ticker']: str(r['cik_str']).zfill(10) for r in registry.values()}
    except Exception:
        mapping = registry_mapping or {}
        if not mapping:
            return {s: {'status': 'SEC_REGISTRY_UNAVAILABLE'} for s in missing}
    details = {}
    for symbol in missing:
        cik = mapping.get(symbol)
        if not cik:
            details[symbol] = {'status': 'SEC_TICKER_UNMAPPED'}
            continue
        try:
            facts = client.fetch_companyfacts(cik)
            if int(facts['cik']) != int(cik):
                raise ValueError('CIK mismatch')
            evidence, reason = extract_fundamentals(facts, expected_as_of)
            details[symbol] = {'status': reason, 'source_url': f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', 'evidence': evidence}
            if reason != 'SEC_VERIFIED':
                diagnostics[symbol] = reason
                continue
            pairs = evidence['pairs']
            fundamental = FundamentalMetrics(
                as_of=pairs['quarterly_eps']['current']['end'],
                quarterly_eps_growth=pairs['quarterly_eps']['current']['val']/pairs['quarterly_eps']['prior']['val']-1,
                quarterly_revenue_growth=pairs['quarterly_revenue']['current']['val']/pairs['quarterly_revenue']['prior']['val']-1,
                annual_eps_growth=pairs['annual_eps']['current']['val']/pairs['annual_eps']['prior']['val']-1,
                institutional_holders_available=False,
                source_urls=(details[symbol]['source_url'],),
                published_as_of=max(r['filed'] for p in pairs.values() for r in p.values()),
            )
            fundamentals[symbol] = fundamental
            cache.setdefault(symbol, {}).update(metrics=asdict(fundamental), fetched_as_of=expected_as_of, provider='SEC', sec_evidence=evidence)
            diagnostics[symbol] = 'SEC_VERIFIED'
        except Exception as exc:
            details[symbol] = {'status': 'SEC_FETCH_FAILED', 'error_type': type(exc).__name__}
    return details


def annotate_reviewed_exclusions(scan, reviewed, expected_as_of):
    """Explain reviewed rule exclusions without relabeling them as scored stocks."""
    expected = date.fromisoformat(expected_as_of)
    rules = {}
    for row in reviewed.get('results', []):
        try:
            period = date.fromisoformat(row['period_end'])
            if (row['review_status'] == 'VERIFIED' and row['status'] == 'NONPOSITIVE_COMPARISON_BASE'
                and float(row['prior_eps']) <= 0 and isfinite(float(row['current_eps']))
                and row['source_url'].startswith('https://')
                and date.fromisoformat(row['published_as_of']) < expected <= date.fromisoformat(row['valid_through'])
                and 0 <= (expected-period).days <= 180
                and 350 <= (period-date.fromisoformat(row['prior_period_end'])).days <= 380):
                rules[row['symbol']] = row
        except (KeyError, ValueError, TypeError):
            continue
    for exclusion in scan.get('exclusions', []):
        symbol = exclusion['symbol']
        if symbol in rules and exclusion.get('technical_confidence', 0) >= 90 and exclusion.get('reason') == 'fundamental validation unavailable':
            exclusion['assessment_status'] = 'RULE_EXCLUDED'
            exclusion['reason'] = 'Reviewed nonpositive prior EPS; growth comparison is not meaningful under the existing rule'
            exclusion['reviewed_evidence'] = rules[symbol]
    ruled = sum(r.get('assessment_status') == 'RULE_EXCLUDED' for r in scan.get('exclusions', []))
    scan['rule_excluded_count'] = ruled
    scan['assessment_count'] = scan.get('validated_count', 0) + ruled
    scan['assessment_status'] = 'COMPLETE' if scan['assessment_count'] == scan.get('universe_size', 0) else 'PARTIAL'
