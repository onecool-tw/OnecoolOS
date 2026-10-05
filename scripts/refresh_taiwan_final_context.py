"""Idempotently merge existing formal Taiwan inputs; no signal calculation."""
import json
from pathlib import Path

from onecool_os.market.taiwan_stock_intelligence import build_taiwan_stock_daily_context, CONTEXT_PATH
from scripts.export_taiwan_family_snapshot import export_snapshot


def refresh(root: Path):
    destination = root / CONTEXT_PATH
    previous = json.loads(destination.read_text()) if destination.exists() else {}
    payload = build_taiwan_stock_daily_context(root)
    def stable(value):
        return {k: v for k, v in value.items() if k != 'generated_at'}
    if stable(payload) != stable(previous):
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        temporary.replace(destination)
    try:
        return export_snapshot(root, check=True)
    except (FileNotFoundError, ValueError):
        return export_snapshot(root)


if __name__ == '__main__':
    result = refresh(Path('.'))
    print(json.dumps({'screen_as_of': result['screen_as_of'],
                      'readiness': result['final_delivery_readiness']}))
