"""Separate an early successful producer audit from the final health gate."""
from datetime import datetime
import os
from zoneinfo import ZoneInfo


def enforce_gate(event, producer, conclusion, now):
    local = now.astimezone(ZoneInfo("Asia/Taipei"))
    early_successful_producer_audit = (
        event == "workflow_run"
        and conclusion == "success"
        and (
            (
                producer == "Update Fund NAV CTA"
                and local.weekday() < 6
                and (local.hour, local.minute) < (15, 30)
            )
            or (
                producer == "Update Taiwan Stock Screen"
                and local.weekday() < 5
                and (local.hour, local.minute) < (16, 30)
            )
        )
    )
    return not early_successful_producer_audit


if __name__ == "__main__":
    enforce = enforce_gate(
        os.environ.get("EVENT_NAME"),
        os.environ.get("PRODUCER_NAME"),
        os.environ.get("PRODUCER_CONCLUSION"),
        datetime.now(ZoneInfo("Asia/Taipei")),
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"enforce={'true' if enforce else 'false'}\n")
