from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from scripts.check_health_gate_window import enforce_gate


@pytest.mark.parametrize("clock,enforce", [("14:17", False), ("16:29", False), ("16:30", True), ("17:50", True)])
def test_successful_taiwan_producer_obeys_existing_recovery_boundary(clock, enforce):
    now = datetime.fromisoformat(f"2026-09-17T{clock}:00").replace(tzinfo=ZoneInfo("Asia/Taipei"))
    assert enforce_gate("workflow_run", "Update Taiwan Stock Screen", "success", now) is enforce
    assert enforce_gate("workflow_run", "Update Taiwan Stock Screen", "success", now.astimezone(ZoneInfo("UTC"))) is enforce


@pytest.mark.parametrize("event,producer,result", [
    ("schedule", "", ""),
    ("workflow_dispatch", "", ""),
    ("workflow_run", "Update Taiwan Stock Screen", "failure"),
    ("workflow_run", "Update Taiwan Stock Screen", "cancelled"),
    ("workflow_run", "Update Fund NAV CTA", "success"),
    ("workflow_run", "", ""),
])
def test_other_gates_and_failed_producers_remain_strict(event, producer, result):
    now = datetime(2026, 9, 17, 14, 17, tzinfo=ZoneInfo("Asia/Taipei"))
    assert enforce_gate(event, producer, result, now)


def test_weekend_audit_remains_strict():
    now = datetime(2026, 9, 19, 14, 17, tzinfo=ZoneInfo("Asia/Taipei"))
    assert enforce_gate("workflow_run", "Update Taiwan Stock Screen", "success", now)


def test_workflow_keeps_health_truth_and_warns_before_deadline():
    from pathlib import Path
    import yaml
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/check-system-health.yml").read_text())
    steps = workflow["jobs"]["health"]["steps"]
    gate = next(s for s in steps if s.get("name") == "Fail only after recovery remains blocked")
    assert "steps.gate_window.outputs.enforce == 'true'" in gate["if"]
    assert "steps.publish.outputs.scope_status == 'BLOCKED'" in gate["if"]
    note = next(s for s in steps if s.get("name") == "Note pending Taiwan data before recovery window")
    assert "::warning::" in note["run"]
    assert "not ready" in note["run"]
