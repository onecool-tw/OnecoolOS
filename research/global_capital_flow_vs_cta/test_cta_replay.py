"""Research replay parity tests against frozen production CTA implementation."""
import unittest
from datetime import date, timedelta
from pathlib import Path
from onecool_os.market.etf_cta import (
    DailyBar, ETFCTAError, InsufficientCTAHistory, calculate_cta, read_history,
)
from .cta_replay import replay_signal

def fabricated(start, count):
    # Synthetic days: allows testing no leakage independently from live prices.
    dates = []
    d = start
    while len(dates) < count:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    return [DailyBar(trading_date=dt,open=100,high=100,low=100,
                     close=100,volume=100,adjusted_close=100+idx*.02)
            for idx,dt in enumerate(dates)]

class ReplayParityTests(unittest.TestCase):
    def test_complete_friday_matches_frozen_cta(self):
        bars = fabricated(date(2020, 1, 6), 310)
        friday = next(b.trading_date for b in reversed(bars) if b.trading_date.weekday()==4)
        sample = [b for b in bars if b.trading_date <= friday]
        expected = calculate_cta("SYN", sample)
        actual = replay_signal("SYN", sample, friday)
        self.assertEqual(actual["cta"], expected.cta)
        self.assertEqual(actual["reason"], expected.reason)
        self.assertEqual(actual["daily_cross"], expected.daily_cross)
        self.assertEqual(actual["weekly_cross"], expected.weekly_cross)
    def test_monday_does_not_consume_provisional_week(self):
        bars = fabricated(date(2020, 1, 6), 311)
        monday = next(b.trading_date for b in reversed(bars) if b.trading_date.weekday()==0)
        result = replay_signal("SYN", bars, monday)
        self.assertLess(result["last_complete_week"], monday.isoformat())
    def test_future_price_cannot_change_prior_signal(self):
        bars = fabricated(date(2020, 1, 6), 310)
        friday = next(b.trading_date for b in reversed(bars) if b.trading_date.weekday()==4)
        old = replay_signal("SYN", bars, friday)
        future = fabricated(friday + timedelta(days=3), 25)
        future = [DailyBar(trading_date=b.trading_date,open=999,high=999,
                           low=999,close=999,volume=100,adjusted_close=999) for b in future]
        new = replay_signal("SYN", bars+future, friday)
        self.assertEqual(old,new)
    def test_unverified_cutoff_rejected(self):
        bars = fabricated(date(2020, 1, 6), 310)
        with self.assertRaises(ETFCTAError):
            replay_signal("SYN", bars, bars[-1].trading_date+timedelta(days=3))
    def test_price_history_parity_on_real_fridays(self):
        root = Path(__file__).resolve().parents[2]
        for symbol in ("QQQ","SOXX","0050"):
            bars = read_history(root / "data" / "market" / "dashboard" /
                                "history" / (symbol+".csv"))
            fridays = [b.trading_date for b in bars if b.trading_date.weekday()==4]
            comparable=0
            for cutoff in fridays:
                sample=[b for b in bars if b.trading_date<=cutoff]
                try:
                    expected=calculate_cta(symbol,sample)
                except InsufficientCTAHistory:
                    continue
                actual=replay_signal(symbol,bars,cutoff)
                self.assertEqual(actual["cta"],expected.cta, (symbol,cutoff))
                self.assertEqual(actual["daily_cross"],expected.daily_cross)
                self.assertEqual(actual["weekly_cross"],expected.weekly_cross)
                comparable+=1
            self.assertGreater(comparable,100,symbol)

if __name__ == "__main__":
    unittest.main()
