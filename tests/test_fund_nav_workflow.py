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


def test_completed_fund_refresh_selects_health_verification(tmp_path):
    import os
    import subprocess
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/check-system-health.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["workflow_run"]["workflows"] == ["Update Fund NAV CTA"]
    assert triggers["workflow_run"]["types"] == ["completed"]
    step = next(step for step in workflow["jobs"]["health"]["steps"] if step.get("id") == "mode")
    output = tmp_path / "output"
    env = {**os.environ, "EVENT_NAME": "workflow_run", "GITHUB_OUTPUT": str(output)}
    subprocess.run(["bash", "-eu", "-c", step["run"]], env=env, check=True)
    assert output.read_text().splitlines() == ["scope=all", "phase=verify"]
