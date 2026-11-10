"""Standalone PIT guard tests; no market access or network needed."""
from datetime import datetime, timezone, date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from .pit_guard import load_verified_vintages, visible_as_of, require_common_sample

HEADER = "factor,observation_date,available_at_utc,value,vintage_id,source_url,evidence_id\n"
ROWS = ("WALCL,2024-01-03,2024-01-04T21:30:00Z,8000000,v1,https://example.org/w,archiveW\n"
        "BAMLH0A0HYM2,2024-01-03,2024-01-05T14:00:00Z,3.4,v1,https://example.org/h,archiveH\n")

def parsed(content):
    with TemporaryDirectory() as folder:
        path = Path(folder) / "factor.csv"
        path.write_text(content, encoding="utf-8")
        return load_verified_vintages(path)

class TestPITGuard(unittest.TestCase):
    def rejects(self, content):
        with self.assertRaises(ValueError):
            parsed(content)
    def test_valid_records(self):
        self.assertEqual(len(parsed(HEADER + ROWS)), 2)
    def test_missing_evidence(self):
        self.rejects(HEADER + ROWS.replace("archiveW", ""))
    def test_bad_release(self):
        self.rejects(HEADER + ROWS.replace("2024-01-04T21:30:00Z", "2024-01-02T21:30:00Z"))
    def test_naive_time(self):
        self.rejects(HEADER + ROWS.replace("2024-01-04T21:30:00Z", "2024-01-04T21:30:00"))
    def test_duplicate_vintage(self):
        self.rejects(HEADER + ROWS + ROWS.splitlines()[0] + "\n")
    def test_nonfinite(self):
        self.rejects(HEADER + ROWS.replace("8000000", "nan"))
    def test_missing_factor(self):
        self.rejects(HEADER + ROWS.splitlines()[0] + "\n")
    def test_release_gate(self):
        records = parsed(HEADER + ROWS)
        early = datetime(2024, 1, 4, 20, tzinfo=timezone.utc)
        late = datetime(2024, 1, 4, 22, tzinfo=timezone.utc)
        self.assertEqual(visible_as_of(records, "WALCL", early), [])
        self.assertEqual(len(visible_as_of(records, "WALCL", late)), 1)
    def test_common_sample(self):
        with self.assertRaises(ValueError):
            require_common_sample([date(2024, 1, 1)])
