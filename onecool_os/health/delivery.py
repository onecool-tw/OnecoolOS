"""Evidence-based report delivery monitoring, separate from market data health."""
from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

# Local scheduled start, plus two hours to finish the report.
SCHEDULES = {
    'taiwan': (set(range(5)), 18, 0),
    'us': ({1, 2, 3, 4, 5}, 16, 0),
    'fund': (set(range(6)), 11, 30),
    'cards': ({5}, 7, 0),
    'home': (set(range(7)), 8, 0),
}


def _verified_channel(channel: dict, due: datetime, now: datetime) -> bool:
    if not isinstance(channel, dict) or channel.get('status') != 'DELIVERED':
        return False
    digest = channel.get('evidence_sha256')
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        return False
    try:
        observed = datetime.fromisoformat(channel['observed_at'].replace('Z', '+00:00'))
        return observed.tzinfo is not None and due <= observed <= now
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def build_delivery_health(root: str | Path, now: datetime) -> dict:
    local = now.astimezone(ZoneInfo('Asia/Taipei'))
    reports = []
    for name, (weekdays, hour, minute) in SCHEDULES.items():
        due = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        while due + timedelta(hours=2) > local or due.weekday() not in weekdays or (name == 'home' and due.day not in {2, 12, 22}):
            due -= timedelta(days=1)
        expected = due.date().isoformat()
        path = Path(root) / 'data/operations/report_delivery' / name / f'{expected}.json'
        channel_status = {}
        status, reason = 'UNKNOWN', 'No verifiable receipt for the latest completed reporting window'
        try:
            receipt = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(receipt, dict):
                raise ValueError('receipt must be an object')
            if receipt.get('report_id') != name or receipt.get('report_date') != expected:
                raise ValueError('receipt identity mismatch')
            generated = datetime.fromisoformat(receipt['generated_at'].replace('Z', '+00:00'))
            if generated.tzinfo is None or generated > local or generated < due:
                raise ValueError('invalid receipt timestamp')
            channels = receipt.get('channels')
            if channels is not None:
                if not isinstance(channels, dict):
                    raise ValueError('invalid channels')
                required = ('conversation', 'email') if name == 'taiwan' else ('conversation',)
                for channel in required:
                    value = channels.get(channel, {})
                    channel_status[channel] = 'DELIVERED' if _verified_channel(value, due, local) else 'UNKNOWN'
                verified = sum(v == 'DELIVERED' for v in channel_status.values())
                status = 'DELIVERED' if verified == len(required) and receipt.get('writeback_status') == 'VERIFIED' else 'PARTIAL' if verified else 'UNKNOWN'
                reason = 'Per-channel evidence checked; missing channels remain unverified'
                reports.append({'report_id': name, 'expected_report_date': expected, 'status': status, 'channels': channel_status, 'reason': reason})
                continue
            status = receipt.get('delivery_status', 'UNKNOWN')
            if status not in {'DELIVERED', 'PREPARED', 'FAILED', 'UNKNOWN'}:
                raise ValueError('invalid delivery status')
            if status == 'DELIVERED' and (not receipt.get('delivery_evidence_sha256') or len(receipt['delivery_evidence_sha256']) != 64 or any(c not in '0123456789abcdef' for c in receipt['delivery_evidence_sha256']) or receipt.get('writeback_status') != 'VERIFIED'):
                raise ValueError('delivery requires acknowledged evidence and verified writeback')
            reason = 'Acknowledged delivery and verified writeback' if status == 'DELIVERED' else 'Report delivery has not been verified'
        except FileNotFoundError:
            pass
        except (ValueError, KeyError, TypeError, AttributeError, OSError):
            status, reason = 'UNKNOWN', 'Invalid or unverifiable receipt'
        reports.append({'report_id': name, 'expected_report_date': expected, 'status': status, 'reason': reason})
    return {'status': 'READY' if all(r['status'] == 'DELIVERED' for r in reports) else 'UNVERIFIED', 'reports': reports, 'policy': 'Data readiness does not prove report delivery. Never infer email success from a generated draft.'}
