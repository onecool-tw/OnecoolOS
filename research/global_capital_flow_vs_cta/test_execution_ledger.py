"""Synthetic next-open execution regression tests; no historical-PIT claim."""
import unittest
from datetime import date, datetime, timedelta, timezone
from .execution_ledger import Observation, evaluate

def fake(n=260, flow=True, cta="BUY"):
    start=date(2025,1,1)
    return [Observation(start+timedelta(days=i),1.01**i,
                        datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=i,hours=21),
                        cta,flow) for i in range(n)]

class TestExecutionLedger(unittest.TestCase):
    def test_next_open(self):
        r=evaluate(fake())
        self.assertEqual(r["ledger"][0]["executed"],"2025-01-02")
        self.assertEqual(r["trades"]["cta"],1)
        self.assertEqual(r["strategies"]["cta"],r["strategies"]["buy_hold"])
    def test_flow_false_cash(self):
        r=evaluate(fake(flow=False))
        self.assertEqual(r["strategies"]["flow"]["total_pct"],0)
        self.assertEqual(r["strategies"]["flow_cta"]["total_pct"],0)
    def test_watch_does_not_enter(self):
        self.assertEqual(evaluate(fake(cta="WATCH"))["strategies"]["cta"]["total_pct"],0)
    def test_late_decision(self):
        rows=fake()
        rows[0]=Observation(rows[0].date,1.,datetime(2025,1,2,23,tzinfo=timezone.utc),"BUY",True)
        with self.assertRaises(ValueError): evaluate(rows)
    def test_missing_flow(self):
        rows=fake()
        x=rows[100]
        rows[100]=Observation(x.date,x.adjusted_open,x.decision_at_utc,x.cta,None)
        with self.assertRaises(ValueError): evaluate(rows)
    def test_short(self):
        with self.assertRaises(ValueError): evaluate(fake(100))
    def test_flow_reentry_after_watch(self):
        rows=fake()
        for i in range(10,20):
            r=rows[i]
            rows[i]=Observation(r.date,r.adjusted_open,r.decision_at_utc,"WATCH",False)
        for i in range(20,30):
            r=rows[i]
            rows[i]=Observation(r.date,r.adjusted_open,r.decision_at_utc,"WATCH",True)
        result=evaluate(rows)
        self.assertFalse(result["ledger"][15]["positions"]["flow_cta"])
        self.assertTrue(result["ledger"][25]["positions"]["flow_cta"])
        self.assertEqual(result["trades"]["flow_cta"],3)
    def test_sell_resets_cta_stance(self):
        rows=fake()
        r=rows[10]
        rows[10]=Observation(r.date,r.adjusted_open,r.decision_at_utc,"SELL",True)
        for i in range(11,30):
            r=rows[i]
            rows[i]=Observation(r.date,r.adjusted_open,r.decision_at_utc,"WATCH",True)
        result=evaluate(rows)
        self.assertFalse(result["ledger"][25]["positions"]["flow_cta"])
    def test_fees(self):
        self.assertLess(evaluate(fake(),fee_bps=10)["strategies"]["cta"]["total_pct"],
                        evaluate(fake())["strategies"]["cta"]["total_pct"])
