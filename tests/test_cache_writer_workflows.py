from pathlib import Path

import yaml


def test_cache_writers_checkout_latest_main_before_recomputing() -> None:
    root = Path(__file__).resolve().parents[1]
    workflows = root / ".github" / "workflows"

    writers = []
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "bash scripts/push_cache_commit.sh" not in text:
            continue
        writers.append(path.name)
        document = yaml.safe_load(text)
        steps = next(iter(document["jobs"].values()))["steps"]
        checkout = next(
            step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")
        )
        assert checkout.get("with", {}).get("ref") == "main", path.name

    assert writers == [
        "persist-taiwan-market-pressure.yml",
        "update-etf-cta.yml",
        "update-fund-alpha.yml",
        "update-fund-nav-cta.yml",
        "update-fund-weekly-analytics.yml",
        "update-market-dashboard.yml",
        "update-stockq-rotation.yml",
        "update-taiwan-cta.yml",
        "update-taiwan-stock-screen.yml",
    ]
