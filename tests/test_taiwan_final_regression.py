import gzip
import json
from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys

import pytest

from scripts.check_taiwan_regression import BASELINE, verify
from scripts.export_taiwan_family_snapshot import build_snapshot, SOURCES
from scripts.refresh_taiwan_final_context import refresh
from onecool_os.market.taiwan_stock_intelligence import build_taiwan_stock_daily_context

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def frozen(tmp_path):
    data = json.loads(gzip.decompress((ROOT / BASELINE).read_bytes()))
    for path, text in data['inputs'].items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return tmp_path


def test_delivered_formal_day_replays_without_signal_or_ranking_changes():
    assert verify(ROOT)['status'] == 'PASS'


def test_production_module_entrypoint_without_pythonpath(tmp_path):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    output = tmp_path / 'regression.json'
    result = subprocess.run([sys.executable, '-m', 'scripts.check_taiwan_regression',
                             '--output', str(output)], cwd=ROOT, env=env,
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())['status'] == 'PASS'


def test_tampered_baseline_is_rejected(tmp_path):
    path = tmp_path / BASELINE
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / BASELINE).read_bytes() + b'tampered')
    with pytest.raises(ValueError, match='baseline changed'):
        verify(tmp_path)


def test_unknown_input_cannot_pass_email_gate(frozen):
    path = frozen / SOURCES['context']
    data = json.loads(path.read_text())
    data['market_pressure_input_readiness']['status'] = 'UPDATE_INCOMPLETE'
    path.write_text(json.dumps(data))
    result = build_snapshot(frozen)
    assert result['final_delivery_readiness']['status'] == 'UPDATE_INCOMPLETE'
    assert 'MARKET_PRESSURE_INPUTS_NOT_READY' in result['final_delivery_readiness']['issues']


def test_pressure_current_for_expected_day_but_old_screen_fails_closed(frozen):
    for source in ('screen', 'context'):
        path = frozen / SOURCES[source]
        data = json.loads(path.read_text())
        data['expected_as_of' if source == 'screen' else 'screen_as_of'] = '2026-10-02'
        path.write_text(json.dumps(data))
    result = build_snapshot(frozen)
    assert result['market_pressure_freshness']['status'] == 'STALE_LAST_KNOWN'
    assert result['market_pressure_freshness']['consumer_action'] == 'PAUSE_NEW_EXPOSURE'
    assert result['final_delivery_readiness']['status'] == 'UPDATE_INCOMPLETE'


def test_late_dashboard_merge_fixes_readiness_preserves_pressure_and_is_idempotent(frozen, monkeypatch):
    path = frozen / SOURCES['context']
    data = json.loads(path.read_text())
    pressure = data['market_pressure']
    data['report_readiness']['status'] = 'UPDATE_INCOMPLETE'
    data['report_readiness']['taiwan_cta_dates']['0050'] = '2026-10-02'
    path.write_text(json.dumps(data))
    monkeypatch.setattr('scripts.refresh_taiwan_final_context.build_taiwan_stock_daily_context',
        lambda root: build_taiwan_stock_daily_context(root, generated_at=datetime.fromisoformat('2026-10-05T11:03:09.357135+00:00')))
    result = refresh(frozen)
    assert result['report_readiness']['status'] == 'READY'
    assert result['market_pressure'] == pressure
    before = {p: (frozen / p).read_bytes() for p in [SOURCES['context'], 'data/public/taiwan_stock_family_latest.json']}
    refresh(frozen)
    assert before == {p: (frozen / p).read_bytes() for p in before}
