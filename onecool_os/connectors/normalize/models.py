"""Canonical normalizer models for connector data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class NormalizationError(ValueError):
    """Raised when a normalized connector record is invalid."""


@dataclass(frozen=True)
class NormalizedRecord:
    """Canonical record emitted by a connector normalizer."""

    external_source: str
    external_id: str
    record_type: str
    payload: dict[str, Any]
    raw_payload: dict[str, Any] | None = None
    normalized_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    def __post_init__(self) -> None:
        if (
            not isinstance(self.external_source, str)
            or not self.external_source
        ):
            raise NormalizationError(
                "external_source must be a non-empty string."
            )
        if not isinstance(self.external_id, str) or not self.external_id:
            raise NormalizationError("external_id must be a non-empty string.")
        if not isinstance(self.record_type, str) or not self.record_type:
            raise NormalizationError("record_type must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise NormalizationError("payload must be a dictionary.")
        if self.raw_payload is not None and not isinstance(
            self.raw_payload,
            dict,
        ):
            raise NormalizationError("raw_payload must be a dictionary.")
        if not isinstance(self.normalized_at, datetime):
            raise NormalizationError("normalized_at must be a datetime.")


class BaseNormalizer(ABC):
    """Base interface for canonical connector normalizers."""

    @abstractmethod
    def source_name(self) -> str:
        """Return the external source name handled by this normalizer."""

    @abstractmethod
    def normalize(self, raw_record: dict[str, Any]) -> NormalizedRecord:
        """Normalize one raw connector record."""

    def validate(self, normalized_record: NormalizedRecord) -> None:
        """Validate one normalized connector record."""

        if not isinstance(normalized_record, NormalizedRecord):
            raise NormalizationError(
                "normalized_record must be a NormalizedRecord."
            )
        if normalized_record.external_source != self.source_name():
            raise NormalizationError(
                "normalized_record external_source does not match normalizer."
            )
