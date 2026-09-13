from copy import deepcopy
from onecool_os.market.sec_fundamentals import extract_fundamentals


def fixture():
    def r(start,end,val,filed):
        return dict(start=start,end=end,val=val,filed=filed,form='10-Q',accn='fixture')
    q=[r('2026-04-01','2026-06-30',3,'2026-08-01'),r('2025-04-01','2025-06-30',2,'2026-08-01')]
    a=[r('2025-01-01','2025-12-31',10,'2026-02-01'),r('2024-01-01','2024-12-31',8,'2026-02-01')]
    rev=deepcopy(q)
    rev[0]['val'],rev[1]['val']=300,200
    return {'cik':1,'entityName':'Fixture','facts':{'us-gaap':{'EarningsPerShareDiluted':{'units':{'USD/shares':q+a}},'Revenues':{'units':{'USD':rev}}}}}


def test_extract_preserves_actual_periods_units_and_filing_evidence():
    evidence,status=extract_fundamentals(fixture(),'2026-09-11')
    assert status=='SEC_VERIFIED'
    assert evidence['pairs']['annual_eps']['prior']['val']==8
    assert evidence['pairs']['quarterly_eps']['current']['end']=='2026-06-30'


def test_nonpositive_base_is_explicitly_ineligible_not_provider_failure():
    facts=fixture()
    facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][1]['val']=-2
    evidence,status=extract_fundamentals(facts,'2026-09-11')
    assert status=='NONPOSITIVE_COMPARISON_BASE:quarterly_eps'
    assert evidence['pairs']['quarterly_eps']['prior']['val']==-2


def test_after_cutoff_and_same_day_filings_are_excluded():
    for filed in ('2026-09-11','2026-09-12'):
        facts=fixture()
        facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['filed']=filed
        _,status=extract_fundamentals(facts,'2026-09-11')
        assert status!='SEC_VERIFIED'


def test_ytd_and_mismatched_currency_are_not_substituted():
    facts=fixture()
    units=facts['facts']['us-gaap']['Revenues']['units']
    units['EUR']=units.pop('USD')
    assert extract_fundamentals(facts,'2026-09-11')[1]!='SEC_VERIFIED'
    facts=fixture()
    facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['start']='2026-01-01'
    assert extract_fundamentals(facts,'2026-09-11')[1]!='SEC_VERIFIED'


def test_verified_rule_exclusions_complete_assessment_without_inflating_validated_count():
    from onecool_os.market.sec_fundamentals import annotate_reviewed_exclusions
    scan={'validated_count':1,'universe_size':2,'exclusions':[{'symbol':'BA','technical_confidence':100,'reason':'fundamental validation unavailable'}]}
    row={'symbol':'BA','review_status':'VERIFIED','status':'NONPOSITIVE_COMPARISON_BASE','prior_eps':-1,'current_eps':1,'period_end':'2026-06-30','prior_period_end':'2025-06-30','published_as_of':'2026-07-28','valid_through':'2026-09-30','source_url':'https://www.sec.gov/fixture'}
    annotate_reviewed_exclusions(scan,{'results':[row]},'2026-09-11')
    assert scan['assessment_status']=='COMPLETE'
    assert scan['validated_count']==1
    assert scan['rule_excluded_count']==1
    scan={'validated_count':1,'universe_size':2,'exclusions':[{'symbol':'BA','technical_confidence':100,'reason':'fundamental validation unavailable'}]}
    annotate_reviewed_exclusions(scan,{'results':[row]},'2026-10-01')
    assert scan['assessment_status']=='PARTIAL'
