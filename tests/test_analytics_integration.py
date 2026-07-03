from decimal import Decimal

from onecool_os.business_logic import AnalyticsSnapshotBuilder
from onecool_os.business_logic import BusinessLogicContext
from onecool_os.business_logic import BusinessLogicPipelineResult
from onecool_os.business_logic import BusinessLogicResult


def test_analytics_integration_empty_pipeline_result() -> None:
    context = BusinessLogicContext(
        context_id="context-empty",
        portfolio_id="portfolio-1",
        base_currency="TWD",
        metadata={"snapshot_date": "2026-01-01"},
    )
    pipeline = pipeline_result("pipeline-empty", "context-empty")

    snapshot = AnalyticsSnapshotBuilder().build(pipeline, context)

    assert snapshot["snapshot_id"] == "pipeline-empty-analytics"
    assert snapshot["portfolio_id"] == "portfolio-1"
    assert snapshot["base_currency"] == "TWD"
    assert snapshot["snapshot_date"] == "2026-01-01"
    assert snapshot["total_cost"] is None
    assert snapshot["asset_class_weights"] == {}


def test_analytics_integration_cash_flow_mapping() -> None:
    pipeline = pipeline_result(
        "pipeline-cash",
        "context-cash",
        results=[
            engine_result(
                "cash_flow",
                "CASH_FLOW",
                {
                    "cash_inflow": Decimal("100"),
                    "cash_outflow": Decimal("40"),
                    "net_cash_flow": Decimal("60"),
                },
            )
        ],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-cash"),
    )

    assert snapshot["cash_inflow"] == Decimal("100")
    assert snapshot["cash_outflow"] == Decimal("40")
    assert snapshot["net_cash_flow"] == Decimal("60")


def test_analytics_integration_allocation_mapping() -> None:
    pipeline = pipeline_result(
        "pipeline-allocation",
        "context-allocation",
        results=[
            engine_result(
                "allocation",
                "ALLOCATION",
                {"weights": {"Cash": Decimal("0.25"), "ETF": Decimal("0.75")}},
            )
        ],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-allocation"),
    )

    assert snapshot["asset_class_weights"] == {
        "Cash": Decimal("0.25"),
        "ETF": Decimal("0.75"),
    }


def test_analytics_integration_performance_mapping() -> None:
    pipeline = pipeline_result(
        "pipeline-performance",
        "context-performance",
        results=[
            engine_result(
                "performance",
                "PERFORMANCE",
                {
                    "cost_basis": Decimal("100"),
                    "market_value": Decimal("120"),
                    "unrealized_gain": Decimal("20"),
                    "unrealized_return": Decimal("0.2"),
                },
            )
        ],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-performance"),
    )

    assert snapshot["total_cost"] == Decimal("100")
    assert snapshot["total_market_value"] == Decimal("120")
    assert snapshot["unrealized_gain"] == Decimal("20")
    assert snapshot["unrealized_return"] == Decimal("0.2")


def test_analytics_integration_risk_mapping() -> None:
    pipeline = pipeline_result(
        "pipeline-risk",
        "context-risk",
        results=[
            engine_result(
                "risk",
                "RISK",
                {
                    "risk_score": Decimal("40"),
                    "risk_level": "MEDIUM",
                },
            )
        ],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-risk"),
    )

    assert snapshot["risk_score"] == Decimal("40")
    assert snapshot["risk_level"] == "MEDIUM"


def test_analytics_integration_missing_metrics() -> None:
    pipeline = pipeline_result(
        "pipeline-missing",
        "context-missing",
        results=[
            engine_result("allocation", "ALLOCATION", {}),
            engine_result("unknown", "CASH_FLOW", {"ignored": True}),
        ],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-missing"),
    )

    assert snapshot["cash_inflow"] is None
    assert snapshot["asset_class_weights"] == {}
    assert snapshot["risk_score"] is None


def test_analytics_integration_metadata_mapping() -> None:
    pipeline = pipeline_result(
        "pipeline-meta",
        "context-meta",
        executed=["cash_flow:calculator"],
        skipped=["risk:evaluator:missing"],
        errors=["performance:calculator:error"],
    )

    snapshot = AnalyticsSnapshotBuilder().build(
        pipeline,
        BusinessLogicContext(context_id="context-meta"),
    )

    assert snapshot["metadata"] == {
        "source_pipeline_id": "pipeline-meta",
        "executed_engines": ["cash_flow:calculator"],
        "skipped_engines": ["risk:evaluator:missing"],
        "errors": ["performance:calculator:error"],
    }


def test_analytics_integration_no_mutation_behavior() -> None:
    context = BusinessLogicContext(
        context_id="context-read-only",
        metadata={"snapshot_date": "2026-01-02"},
    )
    pipeline = pipeline_result(
        "pipeline-read-only",
        "context-read-only",
        executed=["cash_flow:calculator"],
    )
    original_metadata = dict(context.metadata)
    original_executed = pipeline.executed_engines

    AnalyticsSnapshotBuilder().build(pipeline, context)

    assert context.metadata == original_metadata
    assert pipeline.executed_engines == original_executed


def pipeline_result(
    pipeline_id: str,
    context_id: str,
    results: list[BusinessLogicResult] | None = None,
    executed: list[str] | None = None,
    skipped: list[str] | None = None,
    errors: list[str] | None = None,
) -> BusinessLogicPipelineResult:
    return BusinessLogicPipelineResult(
        pipeline_id=pipeline_id,
        context_id=context_id,
        engine_results=results or [],
        signal_results=[],
        executed_engines=executed or [],
        skipped_engines=skipped or [],
        errors=errors or [],
    )


def engine_result(
    engine_name: str,
    metric_type: str,
    payload: dict,
) -> BusinessLogicResult:
    return BusinessLogicResult(
        result_id=f"{engine_name}-result",
        engine_name=engine_name,
        engine_version="v1",
        metric_type=metric_type,
        payload=payload,
    )
