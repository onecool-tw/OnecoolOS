"""Validation helpers for single-asset research pipelines."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from onecool_os.core.exceptions import OnecoolOSError


class SingleAssetPipelineError(OnecoolOSError):
    """Raised when a single asset research pipeline cannot proceed."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise SingleAssetPipelineError(f"{field_name} must be a non-empty string.")
    return value.strip()


def parse_bool(value: Any, field_name: str) -> bool:
    """Parse a required boolean."""

    if isinstance(value, bool):
        return value
    raise SingleAssetPipelineError(f"{field_name} must be a boolean.")


def parse_non_negative_int(value: Any, field_name: str) -> int:
    """Parse a non-negative integer."""

    if isinstance(value, bool):
        raise SingleAssetPipelineError(f"Invalid {field_name}: {value}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise SingleAssetPipelineError(f"Invalid {field_name}: {value}") from exc
    if parsed < 0:
        raise SingleAssetPipelineError(f"{field_name} must not be negative.")
    return parsed


def parse_enum(enum_class: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a StrEnum value."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise SingleAssetPipelineError(f"Invalid {field_name}: {value}") from exc


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse an optional list/tuple of strings."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise SingleAssetPipelineError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise SingleAssetPipelineError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse a required ISO datetime."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise SingleAssetPipelineError(f"Invalid {field_name}: {value}") from exc
    raise SingleAssetPipelineError(f"Invalid {field_name}: {value}")


def parse_url(value: Any, field_name: str) -> str:
    """Parse a required HTTP(S) URL."""

    url = require_text(value, field_name)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SingleAssetPipelineError(f"Invalid {field_name}: {value}")
    return url
