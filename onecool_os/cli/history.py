"""CLI helpers for Portfolio History snapshots."""

from __future__ import annotations

from argparse import _SubParsersAction
from datetime import datetime
from pathlib import Path

from onecool_os.history import HistorySnapshotType
from onecool_os.history import HistoryWriteStatus
from onecool_os.history import PortfolioHistorySnapshotBuilder
from onecool_os.history import PortfolioHistoryStore
from onecool_os.history import PortfolioHistoryError
from onecool_os.research.pipeline.single_asset import load_local_runtime_session


def add_history_parser(subparsers: _SubParsersAction) -> None:
    """Register Portfolio History commands."""

    parser = subparsers.add_parser(
        "record-portfolio-snapshot",
        help="Record an append-only local Portfolio History snapshot.",
    )
    parser.add_argument(
        "--snapshot-type",
        default=HistorySnapshotType.PORTFOLIO_DAILY.value,
        choices=[item.value for item in HistorySnapshotType],
        help="Portfolio history snapshot type.",
    )
    parser.add_argument(
        "--reference-datetime",
        help="Reference datetime in ISO format. Defaults to current runtime clock.",
    )
    parser.add_argument(
        "--output-root",
        default="data/history/portfolio",
        help="Local append-only history root.",
    )
    parser.add_argument(
        "--source-commit",
        help="Optional source commit hash to store with the snapshot.",
    )
    parser.add_argument(
        "--force-new",
        action="store_true",
        help="Write an explicit new record when the snapshot id already exists.",
    )
    parser.set_defaults(command_handler=record_portfolio_snapshot)


def record_portfolio_snapshot(args) -> int:
    """Build and store a Portfolio History snapshot from local runtime data."""

    try:
        reference_datetime = _parse_datetime(args.reference_datetime)
        runtime = load_local_runtime_session(reference_datetime)
        snapshot = PortfolioHistorySnapshotBuilder().build(
            runtime,
            snapshot_type=args.snapshot_type,
            reference_datetime=reference_datetime,
            source_commit=args.source_commit,
        )
        result = PortfolioHistoryStore(Path(args.output_root)).write_snapshot(
            snapshot,
            force_new=args.force_new,
        )
    except (OSError, PortfolioHistoryError, ValueError) as exc:
        print(f"Portfolio snapshot failed: {exc}")
        return 1

    for line in _snapshot_result_lines(result):
        print(line)
    return 0


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _snapshot_result_lines(result) -> tuple[str, ...]:
    snapshot = result.snapshot
    currencies = ", ".join(snapshot.currencies)
    nav_status = ", ".join(
        f"{currency}: {status}"
        for currency, status in sorted(snapshot.nav_status_by_currency.items())
    )
    return (
        "Onecool Portfolio History Snapshot",
        f"Snapshot Date: {snapshot.snapshot_date.isoformat()}",
        f"Snapshot ID: {snapshot.history_snapshot_id}",
        f"Type: {snapshot.snapshot_type.value}",
        f"Total Assets: {snapshot.total_assets}",
        f"Fair Values: {snapshot.fair_value_count}",
        f"Valuation Records: {snapshot.valuation_record_count}",
        f"Valuation Coverage: {snapshot.valuation_coverage_percent}%",
        f"Verified Coverage: {snapshot.verified_coverage_percent}%",
        f"Currencies: {currencies}",
        f"NAV Status: {nav_status}",
        f"Collection Health: {snapshot.collection_health}",
        f"Research Queue Ready: {snapshot.research_queue_ready}",
        f"Research Queue Blocked: {snapshot.research_queue_blocked}",
        f"Warnings: {snapshot.warning_count}",
        f"History File: {result.file_path or 'N/A'}",
        f"Index Updated: {'Yes' if result.status == HistoryWriteStatus.CREATED else 'No'}",
        f"Write Status: {result.status.value}",
    )
