"""Refresh official SEC evidence for the Onecool AI Revolution Monitor."""

from __future__ import annotations

import json
import os
from pathlib import Path

from onecool_os.market.ai_revolution import (
    OfficialIRClient,
    SecClient,
    refresh_ai_revolution,
)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update(
    root: Path,
    *,
    client: SecClient | None = None,
    ir_client: OfficialIRClient | None = None,
) -> dict:
    destination = (
        root / "data" / "market" / "ai_revolution" / "ai_revolution_latest.json"
    )
    review_path = root / "config" / "ai_revolution_review.json"
    user_agent = os.environ.get(
        "SEC_USER_AGENT",
        "OnecoolOS research onecool-tw@users.noreply.github.com",
    )
    payload = refresh_ai_revolution(
        client or SecClient(user_agent),
        _read_json(destination),
        _read_json(review_path),
        ir_client=ir_client or OfficialIRClient(user_agent),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    update(Path("."))
