"""Replay a frozen, delivered Taiwan SSOT without recalculating investment signals."""
from __future__ import annotations

import argparse
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from onecool_os.market.taiwan_stock_intelligence import build_taiwan_stock_daily_context
from scripts.export_taiwan_family_snapshot import build_snapshot, SOURCES

BASELINE = Path("tests/fixtures/taiwan_final_regression_v1.json.gz")
BASELINE_SHA256 = "be1b1fe80f7f8fac8916ad7a42c8649e5dc6d9c7e470f50b1132516175f56b6a"


def decision_view(snapshot):
    # Publication timestamps and provenance change on a deterministic replay;
    # every displayed value, date, signal, ranking and gate must stay identical.
    return {k: v for k, v in snapshot.items()
            if k not in {"sources", "source_generated_at"}}


def verify(root: Path):
    raw = (root / BASELINE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError("Golden baseline changed without a reviewed version")
    frozen = json.loads(gzip.decompress(raw))
    with tempfile.TemporaryDirectory() as directory:
        replay = Path(directory)
        for path, content in frozen["inputs"].items():
            target = replay / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        expected = frozen["expected_snapshot"]
        for name, path in SOURCES.items():
            digest = hashlib.sha256((replay / path).read_bytes()).hexdigest()
            if digest != expected["sources"][name]["sha256"]:
                raise ValueError("Frozen source hash mismatch: " + name)
        if build_snapshot(replay) != expected:
            raise ValueError("Frozen Snapshot no longer matches formal SSOT")
        context = build_taiwan_stock_daily_context(
            replay, generated_at=datetime.fromisoformat("2026-10-05T11:03:09.357135+00:00")
        )
        (replay / SOURCES["context"]).write_text(json.dumps(context), encoding="utf-8")
        if decision_view(build_snapshot(replay)) != decision_view(expected):
            raise ValueError("Unexpected Taiwan context/Snapshot regression")
    return {
        "schema_version": 1, "status": "PASS", "baseline_as_of": frozen["as_of"],
        "baseline_sha256": BASELINE_SHA256,
        "verified_snapshot_sha256": frozen["snapshot_sha256"],
        "verified_artifact_sha256": frozen["artifact_sha256"],
        "scope": "FORMAL_SSOT_CONTEXT_AND_SNAPSHOT_REPLAY_NO_SIGNAL_RECALCULATION",
        "code_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in (
            "onecool_os/market/taiwan_stock_intelligence.py",
            "scripts/export_taiwan_family_snapshot.py",
            "scripts/check_taiwan_regression.py",
            "scripts/refresh_taiwan_final_context.py",
            "config/taiwan_stock_intelligence_master_prompt.md",
        )},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = verify(args.root)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content)
