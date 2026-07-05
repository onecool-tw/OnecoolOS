"""Validation helpers for Radar Engine models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from onecool_os.core.exceptions import OnecoolOSError


class RadarError(OnecoolOSError):
    """Raised when radar data is invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise RadarError(f"{field_name} must be a non-empty string.")
    return value.strip()


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse or validate a datetime."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise RadarError(f"Invalid {field_name}: {value}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise RadarError(f"Invalid {field_name}: {value}") from exc


def parse_enum(
    enum_class: type[StrEnum],
    value: Any,
    field_name: str,
) -> StrEnum:
    """Parse a StrEnum from a string."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise RadarError(f"Invalid {field_name}: {value}") from exc


def parse_optional_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise RadarError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_signal_tuple(value: Any, field_name: str) -> tuple[Any, ...]:
    """Parse a tuple/list of signals."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise RadarError(f"{field_name} must be a list or tuple.")
    return tuple(value)
