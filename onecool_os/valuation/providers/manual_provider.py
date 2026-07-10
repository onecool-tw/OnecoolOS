"""Manual valuation provider placeholder."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.providers.base import ValuationProvider


class ManualValuationProvider(ValuationProvider):
    """Placeholder for a future manual runtime valuation provider."""

    def source_name(self) -> str:
        return "manual"

    def provider_metadata(self) -> Mapping[str, Any]:
        return {
            "provider": "Manual Runtime Valuation",
            "status": "placeholder",
            "network_enabled": False,
        }

    def search(
        self,
        query: Mapping[str, Any] | None = None,
    ) -> Sequence[Any]:
        raise NotImplementedError("Manual valuation provider is not implemented.")

    def normalize(self, raw_record: Any) -> ValuationRecord:
        raise NotImplementedError("Manual valuation provider is not implemented.")

    def validate(self, valuation_record: ValuationRecord) -> bool:
        raise NotImplementedError("Manual valuation provider is not implemented.")
