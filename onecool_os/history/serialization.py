"""Deterministic history JSON serialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from onecool_os.history.models import PortfolioHistorySnapshot
from onecool_os.history.validation import PortfolioHistoryError


def canonical_payload(snapshot: PortfolioHistorySnapshot) -> dict[str, Any]:
    """Return canonical snapshot payload."""

    return snapshot.to_dict()


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize deterministic JSON."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def checksum_payload(payload: dict[str, Any]) -> str:
    """Return SHA-256 checksum for canonical payload."""

    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def snapshot_checksum(snapshot: PortfolioHistorySnapshot) -> str:
    """Return SHA-256 checksum for a snapshot."""

    return checksum_payload(canonical_payload(snapshot))


def write_snapshot_json(path: Path, snapshot: PortfolioHistorySnapshot, checksum: str) -> None:
    """Write pretty deterministic snapshot file."""

    payload = {
        "checksum": checksum,
        "snapshot": canonical_payload(snapshot),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def read_snapshot_json(path: Path) -> tuple[PortfolioHistorySnapshot, str]:
    """Read and validate one history snapshot file."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioHistoryError(f"Malformed history JSON: {path}") from exc
    if not isinstance(payload, dict) or "snapshot" not in payload or "checksum" not in payload:
        raise PortfolioHistoryError("History file must include snapshot and checksum.")
    checksum = str(payload["checksum"])
    expected = checksum_payload(payload["snapshot"])
    if checksum != expected:
        raise PortfolioHistoryError("checksum mismatch")
    snapshot = PortfolioHistorySnapshot(**payload["snapshot"])
    return snapshot, checksum
