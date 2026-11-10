"""Read-only published snapshot parity audit against the frozen shared engine.

Run from repo root: python -m unittest research.global_capital_flow_vs_cta.test_published_parity
These are production *latest-snapshot* checks, not historical PIT evidence.
"""
import json
import unittest
from pathlib import Path
from onecool_os.market.etf_cta import calculate_cta, read_history

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data/market/dashboard/history"
CACHE = ROOT / "data/market/dashboard/dashboard_latest.json"
TAIWAN = ROOT / "data/market/taiwan_cta/cta_latest.json"

class PublishedCacheParity(unittest.TestCase):
    def test_latest_official_outputs(self):
        dashboard=json.loads(CACHE.read_text(encoding="utf-8"))
        taiwan=json.loads(TAIWAN.read_text(encoding="utf-8"))
        for symbol in ("QQQ", "SOXX", "0050"):
            with self.subTest(symbol=symbol):
                bars=read_history(HISTORY / (symbol+".csv"))
                self.assertGreaterEqual(len(bars),200)
                official=next(x for x in (taiwan if symbol=="0050" else dashboard)["results"]
                              if x["symbol"]==symbol)
                observed=calculate_cta(symbol,bars)
                self.assertEqual(observed.as_of,official["as_of"])
                self.assertEqual(observed.cta,official["cta"])
                self.assertEqual(observed.reason,official["reason"])
                self.assertEqual(observed.daily_cross.__dict__,official["daily_cross"])
                self.assertEqual(observed.weekly_cross.__dict__,official["weekly_cross"])
