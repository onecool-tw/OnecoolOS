"""Official consolidated iXBRL evidence for advisory Taiwan quality checks."""
from __future__ import annotations

import calendar
import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from bs4 import BeautifulSoup

VERSION = 'onecool_tw_financial_quality_v2'


def filing_url(symbol, period):
    year, quarter = period.split('Q')
    if not (str(symbol).isdigit() and len(str(symbol)) == 4 and quarter in '1234' and len(quarter) == 1):
        raise ValueError('Invalid company or financial period')
    return ('https://mopsov.twse.com.tw/server-java/t164sb01?step=1'
            f'&CO_ID={symbol}&SYEAR={int(year)}&SSEASON={quarter}&REPORT_ID=C')


def parse_filing(raw: bytes, symbol: str) -> dict:
    soup = BeautifulSoup(raw, 'html.parser')
    identities = {t.get_text(strip=True) for t in soup.find_all('ix:nonnumeric')
                  if t.get('name') == 'tifrs-notes:CompanyID'}
    if identities != {symbol}:
        raise ValueError('Filing company identity mismatch')
    units = {t.get('id'): t.get_text(strip=True) for t in soup.find_all('xbrli:unit')}
    contexts = {}
    for t in soup.find_all('xbrli:context'):
        identifier = t.find('xbrli:identifier')
        if identifier is None or identifier.get_text(strip=True) != symbol:
            continue
        if t.find(['xbrldi:explicitmember', 'xbrldi:typedmember', 'xbrli:segment', 'xbrli:scenario']):
            continue
        instant = t.find('xbrli:instant')
        start, end = t.find('xbrli:startdate'), t.find('xbrli:enddate')
        if instant:
            contexts[t['id']] = ('', instant.get_text(strip=True))
        elif start and end:
            contexts[t['id']] = (start.get_text(strip=True), end.get_text(strip=True))
    facts = {}
    for t in soup.find_all('ix:nonfraction'):
        context = contexts.get(t.get('contextref'))
        if context is None or units.get(t.get('unitref')) != 'iso4217:TWD':
            continue
        if t.get('xsi:nil') in ('true', '1'):
            continue
        if t.get('format', '').split(':')[-1] not in ('numdotdecimal', 'num-dot-decimal', 'zerodash'):
            continue
        try:
            value = Decimal(t.get_text(strip=True).replace(',', '').replace('\xa0', ''))
            value *= Decimal(10) ** int(t.get('scale', '0'))
            if t.get('sign') == '-':
                value = -value
            if not value.is_finite():
                continue
        except (InvalidOperation, ValueError):
            continue
        key = (t.get('name'), *context)
        evidence = {'concept': key[0], 'start': key[1], 'end': key[2],
                    'value': float(value), 'unit': 'TWD', 'context_id': t.get('contextref')}
        if key in facts and (facts[key]['value'] is None or facts[key]['value'] != evidence['value']):
            # Ambiguous duplicate facts must never be chosen arbitrarily.
            facts[key]['value'] = None
        else:
            facts[key] = evidence
    return facts


def assess_filing(raw, symbol, period, observed_at):
    year, quarter = map(int, period.split('Q'))
    month = quarter * 3
    end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    prior_end = date(year - 1, month, calendar.monthrange(year - 1, month)[1]).isoformat()
    start, prior_start = f'{year}-01-01', f'{year-1}-01-01'
    beginning = f'{year-1}-12-31'
    if end > observed_at[:10]:
        raise ValueError('Future financial period')
    facts = parse_filing(raw, symbol)
    evidence, missing = {}, []

    def take(label, concept, start_date='', end_date=end):
        fact = facts.get((concept, start_date, end_date))
        if fact is None or fact['value'] is None:
            missing.append(label)
            return None
        evidence[label] = fact
        return fact['value']

    values = {}
    for label, concept in {
        'profit': 'ifrs-full:ProfitLoss', 'revenue': 'ifrs-full:Revenue',
        'operating_profit': 'ifrs-full:ProfitLossFromOperatingActivities',
        'nonoperating_profit': 'tifrs-bsci-ci:NonoperatingIncomeAndExpenses',
        'pretax_profit': 'ifrs-full:ProfitLossBeforeTax',
        'cashflow': 'ifrs-full:CashFlowsFromUsedInOperatingActivities',
    }.items():
        values[label] = take(label, concept, start)
    values['prior_revenue'] = take('prior_revenue', 'ifrs-full:Revenue', prior_start, prior_end)
    for label, concept in {
        'assets': 'ifrs-full:Assets', 'equity': 'ifrs-full:Equity',
        'liabilities': 'ifrs-full:Liabilities', 'inventory': 'ifrs-full:Inventories',
        'receivables': 'tifrs-bsci-ci:AccountsReceivableNet',
    }.items():
        values[label] = take(label, concept)
        if label in ('assets', 'equity'):
            values['opening_' + label] = take('opening_' + label, concept, '', beginning)
        if label in ('inventory', 'receivables'):
            values['prior_' + label] = take('prior_' + label, concept, '', prior_end)
    result = {'version': VERSION, 'status': 'INSUFFICIENT_DATA', 'label': '資料不足',
              'as_of': period, 'observed_at': observed_at, 'source_url': filing_url(symbol, period),
              'source_sha256': hashlib.sha256(raw).hexdigest(), 'scope': 'CONSOLIDATED_THREE_STATEMENTS',
              'period_basis': 'YEAR_TO_DATE', 'ranking_effect': 'NONE',
              'point_in_time_backtest_eligible': False, 'evidence': evidence,
              'missing_checks': missing, 'flags': [], 'metrics': {},
              'policy': 'Research warnings only; normal means no configured warning, not an audit opinion.'}
    if missing:
        result['reason'] = '官方財報缺少或無法唯一核對：' + '、'.join(missing)
        return result
    v = values
    tolerance = max(1000, abs(v['assets']) * 0.00001)
    if abs(v['assets'] - v['equity'] - v['liabilities']) > tolerance:
        result['reason'] = '資產與負債加權益無法勾稽'; result['missing_checks'] = ['balance_reconciliation']; return result
    if abs(v['operating_profit'] + v['nonoperating_profit'] - v['pretax_profit']) > max(1000, abs(v['pretax_profit']) * 0.00001):
        result['reason'] = '損益無法勾稽'; result['missing_checks'] = ['income_reconciliation']; return result
    denominators = ('assets', 'equity', 'opening_assets', 'opening_equity', 'prior_revenue', 'prior_inventory', 'prior_receivables')
    if any(v[k] <= 0 for k in denominators):
        result['reason'] = '比較基期或權益非正，不能可靠計算比率'; result['missing_checks'] = ['nonpositive_denominator']; return result
    avg_assets = (v['assets'] + v['opening_assets']) / 2
    avg_equity = (v['equity'] + v['opening_equity']) / 2
    growth = lambda current, previous: (current / previous - 1) * 100
    m = result['metrics'] = {
        'operating_cashflow_twd': v['cashflow'],
        'cashflow_to_profit': v['cashflow'] / v['profit'] if v['profit'] > 0 else None,
        'consolidated_roe_ytd_pct': v['profit'] / avg_equity * 100,
        'consolidated_roa_ytd_pct': v['profit'] / avg_assets * 100,
        'average_equity_multiplier': avg_assets / avg_equity,
        'liabilities_to_assets_pct': v['liabilities'] / v['assets'] * 100,
        'revenue_yoy_pct': growth(v['revenue'], v['prior_revenue']),
        'inventory_yoy_pct': growth(v['inventory'], v['prior_inventory']),
        'trade_receivables_ex_related_yoy_pct': growth(v['receivables'], v['prior_receivables']),
    }
    warnings = []
    def warn(code, reason):
        result['flags'].append(code); warnings.append(reason)
    if v['cashflow'] < 0:
        warn('NEGATIVE_OPERATING_CASHFLOW', '營業現金流為負，需核對資金占用')
    elif v['profit'] > 0 and m['cashflow_to_profit'] < 0.5:
        warn('LOW_CASH_CONVERSION', '營業現金流低於同期淨利一半')
    if m['average_equity_multiplier'] >= 3:
        warn('HIGH_EQUITY_MULTIPLIER', '平均資產／權益達3倍，ROE有明顯槓桿效果')
    for field, code, name in [('inventory_yoy_pct', 'INVENTORY_GROWTH', '存貨'),
                             ('trade_receivables_ex_related_yoy_pct', 'RECEIVABLES_GROWTH', '應收帳款')]:
        if m[field] > max(20, m['revenue_yoy_pct'] + 20):
            warn(code, name + '年增逾20%，且高於營收年增20個百分點')
    if v['operating_profit'] <= 0 or v['pretax_profit'] <= 0:
        warn('PROFITABILITY_REVIEW', '本業或稅前未獲利')
    elif v['nonoperating_profit'] > v['operating_profit']:
        warn('NON_OPERATING_DOMINANT', '業外淨收益高於本業，需核對持續性')
    result.update(status='REVIEW' if warnings else 'NORMAL', label='需留意' if warnings else '正常',
                  reason='；'.join(warnings) if warnings else '已核對三表及同期比較，未觸發本版研究警示',
                  thresholds={'cashflow_to_profit_min': 0.5, 'equity_multiplier_max': 3,
                              'working_capital_growth_min_pct': 20, 'growth_gap_pp': 20})
    return result
