"""Separate an early successful producer audit from the final health gate."""
from datetime import datetime
import os
from zoneinfo import ZoneInfo


def enforce_gate(event, producer, conclusion, now):
    local = now.astimezone(ZoneInfo("Asia/Taipei"))
    early_taiwan_audit = (
        event == "workflow_run"
        and producer == "Update Taiwan Stock Screen"
        and conclusion == "success"
        and local.weekday() < 5
        and (local.hour, local.minute) < (16, 30)
    )
    return not early_taiwan_audit


if __name__ == "__main__":
    enforce = enforce_gate(
        os.environ.get("EVENT_NAME"),
        os.environ.get("PRODUCER_NAME"),
        os.environ.get("PRODUCER_CONCLUSION"),
        datetime.now(ZoneInfo("Asia/Taipei")),
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"enforce={'true' if enforce else 'false'}\n")
