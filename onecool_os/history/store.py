"""Append-only local JSON store for portfolio history."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from onecool_os.history.enums import HistoryWriteStatus
from onecool_os.history.models import PortfolioHistoryIndexEntry
from onecool_os.history.models import PortfolioHistorySnapshot
from onecool_os.history.models import PortfolioHistoryWriteResult
from onecool_os.history.serialization import canonical_payload
from onecool_os.history.serialization import read_snapshot_json
from onecool_os.history.serialization import snapshot_checksum
from onecool_os.history.serialization import write_snapshot_json
from onecool_os.history.validation import PortfolioHistoryError

DEFAULT_HISTORY_ROOT = Path("data/history/portfolio")


class PortfolioHistoryStore:
    """Append-only JSON portfolio history store."""

    def __init__(self, root: str | Path = DEFAULT_HISTORY_ROOT) -> None:
        self.root = Path(root)
        self.index_path = self.root / "index.jsonl"

    def write_snapshot(
        self,
        snapshot: PortfolioHistorySnapshot,
        *,
        force_new: bool = False,
    ) -> PortfolioHistoryWriteResult:
        """Write a snapshot append-only unless it is an exact duplicate."""

        checksum = snapshot_checksum(snapshot)
        existing = self._entry_by_snapshot_id(snapshot.history_snapshot_id)
        if existing and existing.checksum == checksum and not force_new:
            return PortfolioHistoryWriteResult(
                status=HistoryWriteStatus.DUPLICATE,
                snapshot=snapshot,
                file_path=existing.file_path,
                index_entry=existing,
                checksum=checksum,
            )
        if existing and existing.checksum != checksum and not force_new:
            return PortfolioHistoryWriteResult(
                status=HistoryWriteStatus.REJECTED,
                snapshot=snapshot,
                file_path=None,
                index_entry=existing,
                checksum=checksum,
                warnings=(
                    "Snapshot id already exists with a different checksum. "
                    "Use force_new=True to write an explicit new record.",
                ),
            )
        file_path = self._snapshot_path(snapshot, force_new=force_new and existing is not None)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)
        write_snapshot_json(file_path, snapshot, checksum)
        reread, reread_checksum = read_snapshot_json(file_path)
        if reread.to_dict() != snapshot.to_dict() or reread_checksum != checksum:
            raise PortfolioHistoryError("Stored snapshot failed checksum validation.")
        entry = PortfolioHistoryIndexEntry(
            history_snapshot_id=snapshot.history_snapshot_id,
            snapshot_date=snapshot.snapshot_date,
            snapshot_type=snapshot.snapshot_type,
            reference_datetime=snapshot.reference_datetime,
            currencies=snapshot.currencies,
            total_assets=snapshot.total_assets,
            valuation_record_count=snapshot.valuation_record_count,
            valuation_coverage_percent=snapshot.valuation_coverage_percent,
            status=snapshot.status,
            file_path=str(file_path),
            checksum=checksum,
            created_at=snapshot.generated_at,
        )
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return PortfolioHistoryWriteResult(
            status=HistoryWriteStatus.CREATED,
            snapshot=snapshot,
            file_path=str(file_path),
            index_entry=entry,
            checksum=checksum,
        )

    def list_snapshots(self) -> tuple[PortfolioHistoryIndexEntry, ...]:
        """List index entries in deterministic order."""

        return tuple(sorted(self._read_index(), key=lambda item: (item.reference_datetime, item.history_snapshot_id)))

    def load_snapshot(self, snapshot_id: str) -> PortfolioHistorySnapshot:
        """Load a snapshot by id."""

        entry = self._entry_by_snapshot_id(snapshot_id)
        if entry is None:
            raise PortfolioHistoryError(f"Snapshot not found: {snapshot_id}")
        snapshot, _ = read_snapshot_json(Path(entry.file_path))
        return snapshot

    def latest_snapshot(self) -> PortfolioHistorySnapshot | None:
        """Return the latest stored snapshot."""

        entries = self.list_snapshots()
        if not entries:
            return None
        return self.load_snapshot(entries[-1].history_snapshot_id)

    def snapshots_between(self, start_date: date, end_date: date) -> tuple[PortfolioHistorySnapshot, ...]:
        """Return snapshots in a date range."""

        return tuple(
            self.load_snapshot(entry.history_snapshot_id)
            for entry in self.list_snapshots()
            if start_date <= entry.snapshot_date <= end_date
        )

    def snapshots_for_currency(self, currency: str) -> tuple[PortfolioHistorySnapshot, ...]:
        """Return snapshots containing a currency."""

        target = currency.upper()
        return tuple(
            self.load_snapshot(entry.history_snapshot_id)
            for entry in self.list_snapshots()
            if target in entry.currencies
        )

    def snapshot_exists(self, fingerprint: str) -> bool:
        """Return whether a snapshot fingerprint exists."""

        for entry in self.list_snapshots():
            snapshot = self.load_snapshot(entry.history_snapshot_id)
            if snapshot.fingerprint == fingerprint:
                return True
        return False

    def _snapshot_path(self, snapshot: PortfolioHistorySnapshot, *, force_new: bool) -> Path:
        suffix = f"_{snapshot.generated_at.strftime('%H%M%S')}" if force_new else ""
        filename = f"portfolio_daily_{snapshot.history_snapshot_id.replace(':', '_')}{suffix}.json"
        return self.root / f"{snapshot.snapshot_date.year:04d}" / snapshot.snapshot_date.isoformat() / filename

    def _entry_by_snapshot_id(self, snapshot_id: str) -> PortfolioHistoryIndexEntry | None:
        for entry in self._read_index():
            if entry.history_snapshot_id == snapshot_id:
                return entry
        return None

    def _read_index(self) -> tuple[PortfolioHistoryIndexEntry, ...]:
        if not self.index_path.exists():
            return ()
        entries = []
        try:
            lines = self.index_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise PortfolioHistoryError("History index cannot be read.") from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                entries.append(PortfolioHistoryIndexEntry(**json.loads(line)))
            except json.JSONDecodeError as exc:
                raise PortfolioHistoryError("Malformed history index JSON.") from exc
        return tuple(entries)
