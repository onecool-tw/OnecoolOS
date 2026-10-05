"""Real Git races must rebuild merged state, not rebase an old Snapshot."""
from pathlib import Path
import subprocess

import pytest

from test_ai_evidence_publication import git, publication  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / 'scripts/publish_taiwan_final_context.sh'


@pytest.fixture
def final_publication(publication):
    runner, remote, env = publication
    fake = Path(env['PATH'].split(':')[0]) / 'python'
    fake.write_text('''#!/usr/bin/env bash
set -euo pipefail
mkdir -p data/market/taiwan_stock_intelligence data/public
if [[ "$1" == "-m" ]]; then shift; fi
case "$1" in
  scripts.check_taiwan_regression)
    if [[ "${FAIL_REGRESSION:-}" == "1" ]]; then exit 9; fi
    echo PASS > data/market/taiwan_stock_intelligence/regression_latest.json ;;
  scripts.refresh_taiwan_final_context)
    cat revision > data/market/taiwan_stock_intelligence/daily_context_latest.json
    cp data/market/taiwan_stock_intelligence/daily_context_latest.json data/public/taiwan_stock_family_latest.json
    if [[ "${RACE:-}" == "1" && ! -e "$RACE_MARKER" ]]; then
      touch "$RACE_MARKER"
      echo new > "$COMPETITOR/revision"
      git -C "$COMPETITOR" add revision
      git -C "$COMPETITOR" commit -m concurrent
      git -C "$COMPETITOR" push origin main
    fi ;;
  scripts/export_taiwan_family_snapshot.py)
    if [[ "${FAIL_SNAPSHOT:-}" == "1" ]]; then exit 8; fi
    cp data/market/taiwan_stock_intelligence/daily_context_latest.json data/public/taiwan_stock_family_latest.json ;;
  scripts/check_system_health.py)
    cat revision > data/market/system_health/system_health_latest.json
    echo "scope_status=$(cat revision)" >> "$GITHUB_OUTPUT" ;;
  *) exit 7 ;;
esac
''')
    env['GITHUB_OUTPUT'] = str(runner.parent / 'outputs')
    return runner, remote, env


def run(fixture, **overrides):
    runner, _, env = fixture
    return subprocess.run(['bash', str(PUBLISHER)], cwd=runner,
                          env=dict(env, **overrides), text=True, capture_output=True)


def test_dashboard_race_rebuilds_context_snapshot_and_health(final_publication):
    runner, remote, env = final_publication
    result = run(final_publication, RACE='1')
    assert result.returncode == 0, result.stderr
    assert 'attempt 2/3' in result.stdout
    for path in ('data/market/taiwan_stock_intelligence/daily_context_latest.json',
                 'data/public/taiwan_stock_family_latest.json',
                 'data/market/system_health/system_health_latest.json'):
        assert git(remote, 'show', 'main:' + path) == 'new'
    assert Path(env['GITHUB_OUTPUT']).read_text() == 'scope_status=new\n'


@pytest.mark.parametrize('mode', ['dirty', 'outside_actions', 'regression', 'snapshot', 'push'])
def test_failure_never_publishes_or_discards_user_edits(final_publication, mode):
    runner, remote, env = final_publication
    overrides = {}
    if mode == 'dirty':
        (runner / 'revision').write_text('user edit')
    elif mode == 'outside_actions':
        overrides['GITHUB_ACTIONS'] = 'false'
    elif mode == 'regression':
        overrides['FAIL_REGRESSION'] = '1'
    elif mode == 'snapshot':
        overrides['FAIL_SNAPSHOT'] = '1'
    else:
        hook = remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
    before = git(remote, 'rev-parse', 'main')
    assert run(final_publication, **overrides).returncode != 0
    assert git(remote, 'rev-parse', 'main') == before
    assert not Path(env['GITHUB_OUTPUT']).exists()
    if mode == 'dirty':
        assert (runner / 'revision').read_text() == 'user edit'


def test_producer_refresh_cannot_trigger_signal_recalculation_or_email():
    text = PUBLISHER.read_text()
    assert 'update_taiwan_stock_cta.py' not in text
    assert 'update_taiwan_stock_screen.py' not in text
    assert 'update_market_dashboard.py' not in text
    assert 'persist_taiwan_market_pressure.py' not in text
    assert 'send_email' not in text
    workflow = (ROOT / '.github/workflows/refresh-taiwan-final-context.yml').read_text()
    assert 'group: update-taiwan-stock-screen' in workflow
    for name in ('Update Market Dashboard', 'Update Taiwan Stock Screen', 'Persist Taiwan Market Pressure'):
        assert name in workflow
