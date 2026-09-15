import pytest
from onecool_os.market.taiwan_financial_quality import assess_financial_quality


def row(op, nonop, pretax):
    return {'營業利益（損失）': op, '營業外收入及支出': nonop,
            '稅前淨利（淨損）': pretax,
            '_financial_source': 'https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci'}


@pytest.mark.parametrize('values,status', [
    ((-10, 20, 10), 'REVIEW'), ((10, 20, 30), 'REVIEW'),
    ((20, 10, 30), 'INSUFFICIENT_DATA'), ((20, -30, -10), 'REVIEW'),
    ((20, 10, 300), 'INSUFFICIENT_DATA'),
    ((20, 'NaN', 30), 'INSUFFICIENT_DATA'),
    ((20, '', 30), 'INSUFFICIENT_DATA'),
])
def test_evidence_limits(values, status):
    result = assess_financial_quality(row(*values), '半導體業', '2026Q2')
    assert result['status'] == status
    assert len(result['missing_checks']) >= 3
    assert result['ranking_effect'] == 'NONE'
    assert result['as_of'] == '2026Q2'


def test_financial_sector_is_not_checked_as_manufacturing():
    result = assess_financial_quality(row(-10, 20, 10), '金融保險業', '2026Q2')
    assert result['status'] == 'INSUFFICIENT_DATA'
    assert not result['flags']


def test_special_statement_schema_is_not_checked_as_manufacturing():
    source = row(-10, 20, 10)
    source['_financial_source'] = source['_financial_source'].replace('_ci', '_fh')
    assert assess_financial_quality(source, '其他', '2026Q2')['status'] == 'INSUFFICIENT_DATA'
