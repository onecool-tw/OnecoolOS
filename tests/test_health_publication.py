"""Verify recomputation and final outputs with real competing Git writers."""
from pathlib import Path
import subprocess

import pytest

from test_ai_evidence_publication import git, publication  # noqa: F401


PUBLISHER = Path(__file__).resolve().parents[1] / "scripts/publish_system_health.sh"


@pytest.fixture
def health_publication(publication):
    runner, remote, env = publication
    fake = Path(env["PATH"].split(":")[0]) / "python"
    fake.write_text('''#!/usr/bin/env bash
set -euo pipefail
if [[ "${FAIL_REFRESH:-}" == "1" ]]; then exit 9; fi
cat revision > data/market/system_health/system_health_latest.json
echo "scope_status=$(cat revision)" >> "$GITHUB_OUTPUT"
echo "summary=$(cat revision)" >> "$GITHUB_STEP_SUMMARY"
if [[ "${RACE:-}" == "1" && ! -e "$RACE_MARKER" ]]; then
  touch "$RACE_MARKER"
  echo new > "$COMPETITOR/revision"
  echo concurrent > "$COMPETITOR/data/market/system_health/system_health_latest.json"
  git -C "$COMPETITOR" add .
  git -C "$COMPETITOR" commit -m concurrent
  git -C "$COMPETITOR" push origin main
fi
''')
    env["GITHUB_OUTPUT"] = str(runner.parent / "outputs")
    env["GITHUB_STEP_SUMMARY"] = str(runner.parent / "summary")
    return runner, remote, env


def run(fixture, **overrides):
    runner, _, env = fixture
    return subprocess.run(["bash", str(PUBLISHER), "asia"], cwd=runner,
                          env=dict(env, **overrides), text=True, capture_output=True)


def test_race_recomputes_from_new_inputs_and_exports_only_final_status(health_publication):
    runner, remote, env = health_publication
    (runner / "revision").write_text("first")
    git(runner, "add", ".")
    git(runner, "commit", "-m", "input")
    git(runner, "push", "origin", "main")
    git(Path(env["COMPETITOR"]), "pull", "--ff-only", "origin", "main")
    result = run(health_publication, RACE="1")
    assert result.returncode == 0, result.stderr
    assert "attempt 2/3" in result.stdout
    assert git(remote, "show", "main:data/market/system_health/system_health_latest.json") == "new"
    assert git(remote, "show", "main:revision") == "new"
    assert Path(env["GITHUB_OUTPUT"]).read_text() == "scope_status=new\n"
    assert Path(env["GITHUB_STEP_SUMMARY"]).read_text() == "summary=new\n"


def test_unchanged_still_exports_gate_status(health_publication):
    _, remote, env = health_publication
    before = git(remote, "rev-parse", "main")
    result = run(health_publication)
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") == before
    assert Path(env["GITHUB_OUTPUT"]).read_text() == "scope_status=old\n"


@pytest.mark.parametrize("mode", ["dirty", "outside_actions", "refresh_failure", "push_failure"])
def test_failures_never_export_success_or_overwrite_remote(health_publication, mode):
    runner, remote, env = health_publication
    overrides = {}
    if mode == "dirty":
        (runner / "revision").write_text("user edit")
    elif mode == "outside_actions":
        overrides["GITHUB_ACTIONS"] = "false"
    elif mode == "refresh_failure":
        overrides["FAIL_REFRESH"] = "1"
    else:
        (runner / "revision").write_text("new")
        git(runner, "add", ".")
        git(runner, "commit", "-m", "input")
        git(runner, "push", "origin", "main")
        hook = remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
    before = git(remote, "rev-parse", "main")
    result = run(health_publication, **overrides)
    assert result.returncode != 0
    assert git(remote, "rev-parse", "main") == before
    assert not Path(env["GITHUB_OUTPUT"]).exists()
    if mode == "dirty":
        assert (runner / "revision").read_text() == "user edit"
    if mode == "push_failure":
        assert "attempt 3/3" in result.stdout


def test_workflow_gates_on_published_status():
    workflow = (PUBLISHER.parents[1] / ".github/workflows/check-system-health.yml").read_text()
    assert '--output "$RUNNER_TEMP/initial-health.json"' in workflow
    assert "steps.publish.outputs.scope_status == 'BLOCKED'" in workflow
    assert "steps.publish.outputs.scope_status == 'PARTIAL'" in workflow
