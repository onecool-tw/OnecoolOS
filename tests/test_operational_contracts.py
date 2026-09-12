from pathlib import Path

import onecool_os
from onecool_os.cli.launcher import ONECOOL_VERSION


def test_runtime_version_is_consistent_across_user_facing_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    settings = (root / "config" / "settings.yaml").read_text(encoding="utf-8")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")

    assert onecool_os.__version__ == "0.6.1"
    assert ONECOOL_VERSION == "v0.6.1"
    assert "Current Runtime Version: v0.6.1" in readme
    assert "version: 0.6.1" in settings
    assert 'version = "0.6.1"' in pyproject


def test_ai_review_workflow_refreshes_fund_validation() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (
        root / ".github" / "workflows" / "update-ai-revolution.yml"
    ).read_text(encoding="utf-8")

    assert '"config/ai_revolution_review.json"' in workflow
    assert "bash scripts/publish_ai_revolution.sh" in workflow
    publisher = (root / "scripts/publish_ai_revolution.sh").read_text(encoding="utf-8")
    assert "python scripts/validate_fund_intelligence.py" in publisher
    assert "data/market/fund_intelligence" in publisher
    assert "python scripts/check_system_health.py --scope weekly" in publisher
