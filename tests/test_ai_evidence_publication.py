"""Exercise the real publisher against local Git remotes and competing writers."""

import os
from pathlib import Path
import subprocess

import pytest


PUBLISHER = Path(__file__).resolve().parents[1] / "scripts/publish_ai_revolution.sh"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def publication(tmp_path):
    remote, runner, competitor = [tmp_path / name for name in ("remote", "runner", "competitor")]
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(runner)], check=True, capture_output=True)
    git(runner, "checkout", "-b", "main")
    git(runner, "config", "user.name", "Test")
    git(runner, "config", "user.email", "test@example.invalid")
    (runner / "revision").write_text("old")
    for directory, filename in (("ai_revolution", "evidence"), ("fund_intelligence", "validation"), ("system_health", "system_health_latest.json")):
        path = runner / "data/market" / directory / filename
        path.parent.mkdir(parents=True)
        path.write_text("old")
    git(runner, "add", ".")
    git(runner, "commit", "-m", "fixture")
    git(runner, "push", "origin", "main")
    subprocess.run(["git", "clone", "-b", "main", str(remote), str(competitor)], check=True, capture_output=True)
    git(competitor, "config", "user.name", "Other writer")
    git(competitor, "config", "user.email", "other@example.invalid")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_python = bindir / "python"
    fake_python.write_text('''#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  scripts/update_ai_revolution.py)
    if [[ "${FAIL_REFRESH:-}" == "1" ]]; then exit 9; fi
    cat revision > data/market/ai_revolution/evidence
    if [[ "${RACE:-}" == "1" && ! -e "$RACE_MARKER" ]]; then
      touch "$RACE_MARKER"
      echo new > "$COMPETITOR/revision"
      echo competing-evidence > "$COMPETITOR/data/market/ai_revolution/evidence"
      git -C "$COMPETITOR" add .
      git -C "$COMPETITOR" commit -m concurrent
      git -C "$COMPETITOR" push origin main
    fi
    ;;
  scripts/validate_fund_intelligence.py)
    cp data/market/ai_revolution/evidence data/market/fund_intelligence/validation ;;
  scripts/check_system_health.py)
    cp data/market/fund_intelligence/validation data/market/system_health/system_health_latest.json ;;
  *) exit 8 ;;
esac
''')
    fake_python.chmod(0o755)
    env = dict(os.environ, GITHUB_ACTIONS="true", PATH=f"{bindir}:{os.environ['PATH']}", COMPETITOR=str(competitor), RACE_MARKER=str(tmp_path / "raced"))
    return runner, remote, env


def run_publication(publication, **overrides):
    runner, _, env = publication
    return subprocess.run(["bash", str(PUBLISHER)], cwd=runner, env=dict(env, **overrides), text=True, capture_output=True)


def test_concurrent_same_file_writer_recomputes_all_caches(publication):
    runner, remote, _ = publication
    (runner / "revision").write_text("first refresh")
    git(runner, "add", "revision")
    git(runner, "commit", "-m", "source awaiting refresh")
    git(runner, "push", "origin", "main")
    git(Path(publication[2]["COMPETITOR"]), "pull", "--ff-only", "origin", "main")
    result = run_publication(publication, RACE="1")
    assert result.returncode == 0, result.stderr
    assert "attempt 2/3" in result.stdout
    for path in ("ai_revolution/evidence", "fund_intelligence/validation", "system_health/system_health_latest.json"):
        assert git(remote, "show", f"main:data/market/{path}") == "new"
    assert git(remote, "show", "main:revision") == "new"
    assert "concurrent" in git(remote, "log", "main", "--format=%s")
    assert git(runner, "status", "--porcelain") == ""


def test_unchanged_caches_do_not_create_commit(publication):
    _, remote, _ = publication
    before = git(remote, "rev-parse", "main")
    result = run_publication(publication)
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "main") == before


@pytest.mark.parametrize("mode", ["outside_actions", "dirty", "refresh_failure", "push_failure"])
def test_failure_does_not_publish_partial_or_discard_user_changes(publication, mode):
    runner, remote, _ = publication
    before = git(remote, "rev-parse", "main")
    overrides = {}
    if mode == "outside_actions":
        overrides["GITHUB_ACTIONS"] = "false"
    elif mode == "dirty":
        (runner / "revision").write_text("user edit")
    elif mode == "refresh_failure":
        overrides["FAIL_REFRESH"] = "1"
    else:
        # A tracked source update makes a real cache commit necessary.
        (runner / "revision").write_text("new")
        git(runner, "add", "revision")
        git(runner, "commit", "-m", "new source")
        git(runner, "push", "origin", "main")
        before = git(remote, "rev-parse", "main")
        hook = remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
    result = run_publication(publication, **overrides)
    assert result.returncode != 0
    assert git(remote, "rev-parse", "main") == before
    if mode == "dirty":
        assert (runner / "revision").read_text() == "user edit"
    if mode == "push_failure":
        assert "attempt 3/3" in result.stdout
