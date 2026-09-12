from pathlib import Path


def test_market_dashboard_publish_rebases_and_retries_concurrent_writers() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root / ".github" / "workflows" / "update-market-dashboard.yml"
    ).read_text(encoding="utf-8")

    assert "for attempt in 1 2 3" in workflow
    assert "git pull --rebase origin main" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "push failed after 3 synchronized attempts" in workflow


def test_market_dashboard_uses_health_driven_recovery_instead_of_constant_retries() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root / ".github" / "workflows" / "update-market-dashboard.yml"
    ).read_text(encoding="utf-8")

    assert workflow.count("- cron:") == 4
    assert 'cron: "30 0 * * 2-6"' in workflow
    assert 'cron: "30 1 * * 2-6"' in workflow
    assert 'cron: "17 8 * * 1-5"' in workflow
    assert 'cron: "30 9 * * 1-5"' in workflow
