"""Base classes for Onecool OS service layer."""

from __future__ import annotations

from dataclasses import dataclass

from onecool_os.core.exceptions import OnecoolOSError


class ServiceError(OnecoolOSError):
    """Raised for service layer errors."""


@dataclass
class BaseService:
    """Read-only service interface foundation."""

    service_name: str
    source_description: str | None = None
    _loaded: bool = False

    def validate_ready(self) -> None:
        """Raise if the service has not loaded source data."""

        if not self._loaded:
            raise ServiceError(f"{self.service_name} has no loaded data.")

    @property
    def is_ready(self) -> bool:
        """Return whether source data has been loaded."""

        return self._loaded

    def _mark_loaded(self, source_description: str | None = None) -> None:
        """Mark the service as ready after a successful load."""

        if source_description is not None:
            self.source_description = source_description
        self._loaded = True
