import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.export_taiwan_family_snapshot import SOURCES, OUTPUT, export_snapshot


@pytest.fixture
def root(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    for relative in SOURCES.values():
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / relative, dest)
    return tmp_path


def change(root, source, mutate):
    path = root / SOURCES[source]
    obj = json.loads(path.read_text())
    mutate(obj)
    path.write_text(json.dumps(obj))


def test_projection_is_lossless_readonly_and_deterministic(root):
    before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in SOURCES.values()}
    result = export_snapshot(root)
    ctx = json.loads((root / SOURCES['context']).read_text())
    screen = json.loads((root / SOURCES['screen']).read_text())
    assert result['market_pressure'] == ctx['market_pressure']
    assert [r['symbol'] for r in result['top5']] == [r['symbol'] for r in screen['top5']]
    first = (root / OUTPUT).read_bytes()
    export_snapshot(root)
    assert (root / OUTPUT).read_bytes() == first
    assert before == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in SOURCES.values()}
    assert 'master_prompt' not in result


def test_mismatch_does_not_replace_last_valid_snapshot(root):
    export_snapshot(root)
    before = (root / OUTPUT).read_bytes()
    change(root, 'context', lambda c: c['top5'].reverse())
    with pytest.raises(ValueError, match='mismatch'):
        export_snapshot(root)
    assert (root / OUTPUT).read_bytes() == before


def test_duplicate_cta_rejected(root):
    change(root, 'cta', lambda c: c['results'].append(c['results'][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        export_snapshot(root)


def test_check_detects_source_change(root):
    export_snapshot(root)
    change(root, 'context', lambda c: c['market_pressure'].update(reason=['new_formal_reason']))
    with pytest.raises(ValueError, match='does not match'):
        export_snapshot(root, check=True)


def test_pressure_persistence_to_public_snapshot_end_to_end(root):
    repo = Path(__file__).resolve().parents[1]
    payload = {
        'as_of': '2026-09-04', 'status': 'CURRENT', 'light': 'RED',
        'reason': ['test_formal_result'], 'confirmed_inputs': {}, 'input_data_as_of': {},
    }
    from scripts.persist_taiwan_market_pressure import persist
    persist(root, payload)
    result = export_snapshot(root)
    assert result['market_pressure']['reason'] == ['test_formal_result']
    assert result['market_pressure']['action'] == 'PAUSE_NEW_EXPOSURE'
    export_snapshot(root, check=True)
