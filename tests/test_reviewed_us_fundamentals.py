import copy
import json
from pathlib import Path

import pytest

from onecool_os.market.reviewed_us_fundamentals import load_reviewed_fundamentals
from onecool_os.market.us_breakout_scan import score_security
from tests.test_us_breakout_scan import _history


def evidence():
    return json.loads(Path("data/market/us_stock_intelligence/reviewed_fundamentals.json").read_text())


def test_rh_official_inputs_reproduce_growth_without_stored_score():
    f = load_reviewed_fundamentals(evidence(), "2026-09-08")["RH"]
    assert f.quarterly_eps_growth == pytest.approx(-2.825)
    assert f.quarterly_revenue_growth == pytest.approx(800328 / 813952 - 1)
    assert f.annual_eps_growth == pytest.approx(6.31 / 3.62 - 1)
    assert len(f.source_urls) == 2


@pytest.mark.parametrize("cutoff", ["2026-06-10", "2026-09-10"])
def test_fallback_never_uses_unpublished_or_expired_evidence(cutoff):
    assert load_reviewed_fundamentals(evidence(), cutoff) == {}


@pytest.mark.parametrize("defect", ["missing", "zero", "non_gaap", "period", "source"])
def test_invalid_evidence_is_not_filled(defect):
    p = copy.deepcopy(evidence())
    r = p["results"][0]
    if defect == "missing":
        r["annual_eps"]["current"] = None
    elif defect == "zero":
        r["quarterly_eps"]["prior"] = 0
    elif defect == "non_gaap":
        r["accounting_basis"] = "ADJUSTED"
    elif defect == "period":
        r["quarterly_eps"]["prior_period_end"] = "2026-02-01"
    else:
        r["sources"] = []
    assert load_reviewed_fundamentals(p, "2026-09-08") == {}


def test_liquidity_failure_contains_measured_value_and_limit():
    h = _history(end_volume=100)
    from dataclasses import replace
    h = [replace(b, volume=100) for b in h]
    r = score_security("UPBD", h, None, _history(), str(h[-1].trading_date))
    assert r["liquidity_average_50d_usd"] < r["liquidity_minimum_50d_usd"]
    assert r["minervini_score"] is None
