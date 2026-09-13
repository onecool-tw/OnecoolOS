import json
from datetime import datetime, timezone
from onecool_os.health.delivery import build_delivery_health

NOW = datetime(2026, 9, 13, 6, tzinfo=timezone.utc)


def test_missing_receipts_are_unknown_and_weekend_uses_last_window(tmp_path):
    health = build_delivery_health(tmp_path, NOW)
    assert health['status'] == 'UNVERIFIED'
    dates = {r['report_id']: r['expected_report_date'] for r in health['reports']}
    assert dates == {'taiwan': '2026-09-11', 'us': '2026-09-12', 'fund': '2026-09-12', 'cards': '2026-09-12', 'home': '2026-09-12'}
    assert all(r['status'] == 'UNKNOWN' for r in health['reports'])


def test_delivery_requires_receipt_evidence_and_verified_writeback(tmp_path):
    path = tmp_path / 'data/operations/report_delivery/taiwan/2026-09-11.json'
    path.parent.mkdir(parents=True)
    receipt = dict(report_id='taiwan', report_date='2026-09-11', generated_at='2026-09-11T18:30:00+08:00', delivery_status='DELIVERED', writeback_status='VERIFIED')
    path.write_text(json.dumps(receipt))
    assert build_delivery_health(tmp_path, NOW)['reports'][0]['status'] == 'UNKNOWN'
    receipt['delivery_evidence_sha256'] = 'a' * 64
    path.write_text(json.dumps(receipt))
    assert build_delivery_health(tmp_path, NOW)['reports'][0]['status'] == 'DELIVERED'
    receipt['generated_at'] = '2026-09-14T18:30:00+08:00'
    path.write_text(json.dumps(receipt))
    assert build_delivery_health(tmp_path, NOW)['reports'][0]['status'] == 'UNKNOWN'
