from pathlib import Path


def test_fund_nav_publish_rebases_and_retries_concurrent_writers() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root / ".github" / "workflows" / "update-fund-nav-cta.yml"
    ).read_text(encoding="utf-8")

    assert "bash scripts/push_cache_commit.sh" in workflow
    workflow = (root / "scripts/push_cache_commit.sh").read_text()
    assert "for attempt in 1 2 3" in workflow
    assert "git pull --rebase origin main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "push failed after 3 synchronized attempts" in workflow


def test_completed_producer_refresh_selects_its_own_health_scope(tmp_path):
    import os
    import subprocess
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/check-system-health.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["workflow_run"]["workflows"] == [
        "Update Fund NAV CTA",
        "Update Taiwan Stock Screen",
    ]
    assert triggers["workflow_run"]["types"] == ["completed"]
    step = next(step for step in workflow["jobs"]["health"]["steps"] if step.get("id") == "mode")
    for producer, expected_scope in (
        ("Update Fund NAV CTA", "morning"),
        ("Update Taiwan Stock Screen", "asia"),
    ):
        output = tmp_path / producer.replace(" ", "-")
        env = {
            **os.environ,
            "EVENT_NAME": "workflow_run",
            "PRODUCER_NAME": producer,
            "GITHUB_OUTPUT": str(output),
        }
        subprocess.run(["bash", "-eu", "-c", step["run"]], env=env, check=True)
        assert output.read_text().splitlines() == [
            f"scope={expected_scope}",
            "phase=verify",
        ]


def test_push_health_audit_recovers_without_transient_failure() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/check-system-health.yml").read_text()
    )
    steps = workflow["jobs"]["health"]["steps"]
    dispatch = next(
        step
        for step in steps
        if step.get("name") == "Dispatch one safe recovery cycle"
    )
    gate = next(
        step
        for step in steps
        if step.get("name") == "Fail only after recovery remains blocked"
    )

    assert "github.event_name == 'push'" in dispatch["if"]
    assert "workflow_id === 'update-taiwan-stock-screen.yml'" in dispatch["with"]["script"]
    assert "{ run_mode: 'recovery' }" in dispatch["with"]["script"]
    assert "github.event_name != 'push'" in gate["if"]
