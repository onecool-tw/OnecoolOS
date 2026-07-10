"""Gemini Research Agent valuation provider placeholder."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from onecool_os.valuation.models import ValuationRecord
from onecool_os.valuation.providers.base import ValuationProvider


class GeminiValuationProvider(ValuationProvider):
    """Placeholder for a future authorized Gemini Research Agent provider."""

    def source_name(self) -> str:
        return "gemini"

    def provider_metadata(self) -> Mapping[str, Any]:
        return {
            "provider": "Gemini Research Agent",
            "status": "placeholder",
            "network_enabled": False,
        }

    def search(
        self,
        query: Mapping[str, Any] | None = None,
    ) -> Sequence[Any]:
        raise NotImplementedError("Gemini valuation provider is not implemented.")

    def normalize(self, raw_record: Any) -> ValuationRecord:
        raise NotImplementedError("Gemini valuation provider is not implemented.")

    def validate(self, valuation_record: ValuationRecord) -> bool:
        raise NotImplementedError("Gemini valuation provider is not implemented.")
