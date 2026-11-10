"""Execution correctness tests independent of published return numbers."""
import unittest
from datetime import date, timedelta
from onecool_os.market.etf_cta import DailyBar
from .price_cta_comparison import adjusted_open, run_symbol


def synthetic(count=350):
    bars = []
    d = date(2020, 1, 6)
    while len(bars) < count:
        if d.weekday() < 5:
            i = len(bars)
            v = 100 + i * .05
            bars.append(DailyBar(trading_date=d, open=v, high=v + 1,
                                 low=v - 1, close=v, volume=100,
                                 adjusted_close=v))
        d += timedelta(days=1)
    return bars


class PriceStrategyTests(unittest.TestCase):
    def test_price_proxy(self):
        bar = synthetic()[0]
        self.assertEqual(adjusted_open(bar), bar.open)
    def test_common_dates_and_cost_decrease(self):
        bars=synthetic()
        zero=run_symbol("SYN",bars,one_way_bps=0)
        costly=run_symbol("SYN",bars,one_way_bps=10)
        self.assertEqual(zero["sessions"],costly["sessions"])
        self.assertEqual(zero["first_execution"],costly["first_execution"])
        for arm in ("rolling","confirmed"):
            self.assertLessEqual(costly["strategies"][arm]["total_pct"],
                                 zero["strategies"][arm]["total_pct"])
    def test_duplicate_dates_blocked(self):
        rows=synthetic()
        with self.assertRaises(ValueError):
            run_symbol("SYN",rows + [rows[-1]])
    def test_insufficient_history_blocked(self):
        with self.assertRaises(ValueError):
            run_symbol("SYN",synthetic(200))
