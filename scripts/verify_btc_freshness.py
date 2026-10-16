"""Fail the updater heartbeat when published BTC is stale; never alter CTA."""
from datetime import UTC, datetime, time, timedelta
import json
from pathlib import Path


def verify(payload, now=None):
    now = (now or datetime.now(UTC)).astimezone(UTC)
    expected = now.date() - timedelta(days=1)
    allowed = {expected.isoformat()}
    if now.time() < time(0, 30):
        allowed.add((expected - timedelta(days=1)).isoformat())
    rows = [row for row in payload.get("results", []) if row.get("symbol") == "BTC"]
    if len(rows) != 1 or rows[0].get("as_of") not in allowed or rows[0].get("cta") not in {"BUY", "HOLD", "WATCH", "SELL"}:
        actual = rows[0].get("as_of") if len(rows) == 1 else "UNKNOWN"
        raise RuntimeError(f"BTC freshness failed: expected UTC completed day {expected}; actual {actual}. Existing cache retained; recovery required.")
    return rows[0]["as_of"]


if __name__ == "__main__":
    payload = json.loads(Path("data/market/dashboard/dashboard_latest.json").read_text())
    print("Bitcoin completed-day freshness verified:", verify(payload))
