"""Research workbench CLI commands."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC
from datetime import datetime
from pathlib import Path

from onecool_os.assets.master import AssetMasterError
from onecool_os.assets.master import AssetMasterLoader
from onecool_os.cli.launcher import DEFAULT_ASSET_MASTER_CSV_PATH
from onecool_os.cli.launcher import DEFAULT_ASSET_MASTER_XLSX_PATH
from onecool_os.cli.launcher import DEFAULT_PSA_COLLECTION_PATH
from onecool_os.connectors.collectibles import PSACollectionImporter
from onecool_os.connectors.collectibles import PSAImportError
from onecool_os.research.workbench import ResearchRequestExporter
from onecool_os.research.workbench import ResearchResultImporter
from onecool_os.research.workbench import ResearchWorkbenchError
from onecool_os.research.pipeline import DEFAULT_CERT_NUMBER
from onecool_os.research.pipeline import DEFAULT_REPORT_OUTPUT
from onecool_os.research.pipeline import DEFAULT_REQUEST_OUTPUT
from onecool_os.research.pipeline import DEFAULT_RESULT_INPUT
from onecool_os.research.pipeline import SingleAssetResearchPipeline
from onecool_os.research.pipeline import pipeline_report_lines
from onecool_os.runtime import RuntimeSession

DEFAULT_EBAY_RESEARCH_REQUEST_PATH = Path("imports/research/ebay_url_requests.json")
DEFAULT_RESEARCH_RESULT_PATH = Path("imports/research/ebay_url_results.json")


def add_research_parsers(subparsers: argparse._SubParsersAction) -> None:
    """Add research workbench PoC commands."""

    export_parser = subparsers.add_parser(
        "export-ebay-research-requests",
        help="Export READY eBay Sold URL research requests.",
    )
    export_parser.add_argument("--limit", type=int)
    export_parser.add_argument("--asset-id")
    export_parser.add_argument("--cert-number")
    export_parser.add_argument(
        "--output",
        default=str(DEFAULT_EBAY_RESEARCH_REQUEST_PATH),
    )
    export_parser.set_defaults(command_handler=handle_export_ebay_research_requests)

    import_parser = subparsers.add_parser(
        "import-research-results",
        help="Import ORF-compatible provider research JSON.",
    )
    import_parser.add_argument(
        "--input",
        default=str(DEFAULT_RESEARCH_RESULT_PATH),
    )
    import_parser.set_defaults(command_handler=handle_import_research_results)

    single_asset_parser = subparsers.add_parser(
        "run-single-asset-research",
        help="Run the single-asset eBay Sold research pipeline.",
    )
    single_asset_parser.add_argument("--cert-number", default=DEFAULT_CERT_NUMBER)
    single_asset_parser.add_argument(
        "--request-output",
        default=str(DEFAULT_REQUEST_OUTPUT),
    )
    single_asset_parser.add_argument(
        "--result-input",
        default=str(DEFAULT_RESULT_INPUT),
    )
    single_asset_parser.add_argument(
        "--report-output",
        default=str(DEFAULT_REPORT_OUTPUT),
    )
    single_asset_parser.set_defaults(command_handler=handle_run_single_asset_research)


def handle_export_ebay_research_requests(args: argparse.Namespace) -> int:
    """Export READY eBay Sold URL research requests."""

    reference = datetime.now(UTC)
    try:
        session = _load_runtime_session(reference)
    except (PSAImportError, AssetMasterError) as exc:
        print(f"Research request export failed: {exc}")
        return 1

    exporter = ResearchRequestExporter()
    export = exporter.export(
        session,
        limit=args.limit,
        asset_id=args.asset_id,
        cert_number=args.cert_number,
        reference_datetime=reference,
        generated_at=reference,
    )
    output = exporter.write_json(export, args.output)
    snapshot = session.research_queue_snapshot()
    print("eBay URL Research Request Export")
    print("--------------------------------")
    print(f"Total READY queue items: {snapshot.ready_items}")
    print(f"Blocked queue items: {snapshot.blocked_items}")
    print(f"Exported requests: {len(export.requests)}")
    print(f"Output: {output}")
    print("Provider calls: 0")
    print("HTTP calls: 0")
    return 0


def handle_import_research_results(args: argparse.Namespace) -> int:
    """Import ORF-compatible provider research JSON."""

    try:
        result = ResearchResultImporter().import_json(args.input)
    except ResearchWorkbenchError as exc:
        print(f"Research result import failed: {exc}")
        return 1

    statuses = Counter(evidence.status.value for evidence in result.evidence)
    print("Research Result Import")
    print("----------------------")
    print(f"Research batches: {len(result.batches)}")
    print(f"Evidence batches: {len(result.evidence_batches)}")
    print(f"Evidence records: {result.evidence_count}")
    for status, count in sorted(statuses.items()):
        print(f"{status}: {count}")
    print("Valuation records created: 0")
    return 0


def handle_run_single_asset_research(args: argparse.Namespace) -> int:
    """Run the single-asset research pipeline."""

    outcome = SingleAssetResearchPipeline().run(
        cert_number=args.cert_number,
        request_output=args.request_output,
        result_input=args.result_input,
        report_output=args.report_output,
    )
    for line in pipeline_report_lines(outcome.result):
        print(line)
    if not outcome.result.provider_result_loaded:
        print("")
        print("Research request exported. Provider result is not available yet.")
    print("")
    print(f"Request output: {outcome.request_output_path}")
    print(f"Provider result input: {outcome.provider_result_path}")
    print("Fair Value: Not calculated")
    print("NAV: Not updated")
    print("Recommendation: Not generated")
    return 0 if outcome.result.status.value in {"COMPLETED", "PARTIAL"} else 1


def _load_runtime_session(reference_datetime: datetime) -> RuntimeSession:
    psa_path = DEFAULT_PSA_COLLECTION_PATH
    if not psa_path.exists():
        raise PSAImportError(
            "PSA Collection file not found. Please place CSV at imports/psa/collection.csv"
        )
    psa_result = PSACollectionImporter().import_csv(
        psa_path,
        reference_datetime=reference_datetime,
    )
    asset_master_records = ()
    asset_master_path = _select_asset_master_path()
    if asset_master_path is not None:
        asset_master_records = AssetMasterLoader().load(
            asset_master_path,
            reference_datetime=reference_datetime,
        ).records
    return RuntimeSession(
        imported_records=psa_result.records,
        asset_master_records=asset_master_records,
        generated_at=reference_datetime,
    )


def _select_asset_master_path() -> Path | None:
    if DEFAULT_ASSET_MASTER_XLSX_PATH.exists():
        return DEFAULT_ASSET_MASTER_XLSX_PATH
    if DEFAULT_ASSET_MASTER_CSV_PATH.exists():
        return DEFAULT_ASSET_MASTER_CSV_PATH
    return None
