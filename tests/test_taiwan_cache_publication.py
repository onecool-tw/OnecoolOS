"""Exercise snapshot regeneration against actual competing Git commits."""
from pathlib import Path
import subprocess

import pytest

from test_ai_evidence_publication import git, publication  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / 'scripts/push_cache_commit.sh'
SNAPSHOT = 'data/public/taiwan_stock_family_latest.json'
CONTEXT = 'data/market/taiwan_stock_intelligence/daily_context_latest.json'


@pytest.fixture
def snapshot_publication(publication):
    runner, remote, env = publication
    for name, value in [(SNAPSHOT, 'old'), (CONTEXT, 'formal-pressure'), ('screen', 'old')]:
        path = runner / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    git(runner, 'add', '.')
    git(runner, 'commit', '-m', 'snapshot fixture')
    git(runner, 'push', 'origin', 'main')
    git(Path(env['COMPETITOR']), 'pull', '--ff-only', 'origin', 'main')
    fake = Path(env['PATH'].split(':')[0]) / 'python'
    fake.write_text('''#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == -m && "$2" == scripts.refresh_taiwan_final_context ]]; then
  if [[ "${FAIL_REBUILD:-}" == 1 ]]; then exit 9; fi
  # A projection must include both writers' current sources and formal pressure.
  cat screen revision data/market/taiwan_stock_intelligence/daily_context_latest.json > data/public/taiwan_stock_family_latest.json
elif [[ "$1" == scripts/export_taiwan_family_snapshot.py && "$2" == --check ]]; then
  if [[ "${FAIL_VALIDATION:-}" == 1 ]]; then exit 8; fi
  cmp data/public/taiwan_stock_family_latest.json <(cat screen revision data/market/taiwan_stock_intelligence/daily_context_latest.json)
else
  exit 7
fi
''')
    return runner, remote, env


def race(fixture, conflict='snapshot'):
    runner, remote, env = fixture
    competitor = Path(env['COMPETITOR'])
    (runner / 'screen').write_text('new-screen')
    (runner / SNAPSHOT).write_text('local-projection')
    git(runner, 'add', '.')
    git(runner, 'commit', '-m', 'screen cache')
    (competitor / 'revision').write_text('new-dashboard')
    if conflict == 'snapshot':
        (competitor / SNAPSHOT).write_text('remote-projection')
    elif conflict == 'source':
        (competitor / 'screen').write_text('competing-screen')
    elif conflict == 'pressure':
        (runner / CONTEXT).write_text('local-pressure')
        git(runner, 'add', CONTEXT)
        git(runner, 'commit', '--amend', '--no-edit')
        (competitor / CONTEXT).write_text('remote-pressure')
    git(competitor, 'add', '.')
    git(competitor, 'commit', '-m', 'concurrent formal inputs')
    git(competitor, 'push', 'origin', 'main')
    return git(remote, 'rev-parse', 'main')


@pytest.mark.parametrize('conflict', ['snapshot', 'none'])
def test_rebuilds_projection_from_both_writers_even_after_clean_rebase(snapshot_publication, conflict):
    runner, remote, env = snapshot_publication
    race(snapshot_publication, conflict)
    result = subprocess.run(['bash', str(PUBLISHER)], cwd=runner, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert git(remote, 'show', 'main:screen') == 'new-screen'
    assert git(remote, 'show', 'main:revision') == 'new-dashboard'
    assert git(remote, 'show', 'main:' + CONTEXT) == 'formal-pressure'
    assert git(remote, 'show', 'main:' + SNAPSHOT) == 'new-screennew-dashboardformal-pressure'
    assert git(runner, 'status', '--porcelain') == ''


@pytest.mark.parametrize('mode', ['source', 'pressure', 'rebuild', 'validation', 'outside_actions'])
def test_never_publishes_source_conflicts_or_unverified_projection(snapshot_publication, mode):
    runner, remote, env = snapshot_publication
    before = race(snapshot_publication, mode if mode in {'source', 'pressure'} else 'snapshot')
    env = dict(env)
    if mode == 'rebuild':
        env['FAIL_REBUILD'] = '1'
    elif mode == 'validation':
        env['FAIL_VALIDATION'] = '1'
    elif mode == 'outside_actions':
        env['GITHUB_ACTIONS'] = 'false'
    result = subprocess.run(['bash', str(PUBLISHER)], cwd=runner, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert git(remote, 'rev-parse', 'main') == before
    if mode in {'source', 'pressure', 'outside_actions'}:
        assert git(runner, 'show', 'HEAD:screen') == 'new-screen'
