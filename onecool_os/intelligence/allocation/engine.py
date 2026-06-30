"""Allocation calculation engine."""

from __future__ import annotations

from decimal import Decimal

from onecool_os.intelligence.allocation.models import AllocationResult
from onecool_os.intelligence.valuation.models import ValuationResult


class AllocationEngine:
    """Calculate allocation percentages from valuation results."""

    def calculate(
        self,
        valuations: list[ValuationResult],
    ) -> tuple[AllocationResult, ...]:
        """Return allocation results for valuation results."""

        portfolio_total = self.portfolio_total(valuations)
        if portfolio_total <= Decimal("0"):
            return tuple(
                self._allocation_result(valuation, Decimal("0"))
                for valuation in valuations
            )

        return tuple(
            self._allocation_result(
                valuation,
                (valuation.estimated_value / portfolio_total)
                * Decimal("100"),
            )
            for valuation in valuations
        )

    def portfolio_total(self, valuations: list[ValuationResult]) -> Decimal:
        """Return the total market value for valuation results."""

        return sum(
            (valuation.estimated_value for valuation in valuations),
            Decimal("0"),
        )

    def _allocation_result(
        self,
        valuation: ValuationResult,
        allocation_percent: Decimal,
    ) -> AllocationResult:
        return AllocationResult(
            asset_type=valuation.asset_type,
            asset_name=valuation.asset_id,
            market_value=valuation.estimated_value,
            allocation_percent=allocation_percent,
        )
