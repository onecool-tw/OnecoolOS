"""Validation helpers for research workbench PoC models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from onecool_os.core.exceptions import OnecoolOSError


class ResearchWorkbenchError(OnecoolOSError):
    """Raised when research workbench data is invalid."""


def require_text(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ResearchWorkbenchError(f"{field_name} must be a non-empty string.")
    return value.strip()


def optional_text(value: Any, field_name: str) -> str | None:
    """Return a stripped optional string."""

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ResearchWorkbenchError(f"{field_name} must be a string.")
    return value.strip() or None


def parse_enum(enum_class: type[StrEnum], value: Any, field_name: str) -> StrEnum:
    """Parse a StrEnum value."""

    try:
        return enum_class(str(value).upper())
    except ValueError as exc:
        raise ResearchWorkbenchError(f"Invalid {field_name}: {value}") from exc


def parse_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Parse a list/tuple of strings."""

    if value in (None, ""):
        return ()
    if not isinstance(value, (list, tuple)):
        raise ResearchWorkbenchError(f"{field_name} must be a list.")
    return tuple(require_text(item, field_name) for item in value)


def parse_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse an optional dictionary."""

    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ResearchWorkbenchError(f"{field_name} must be a dictionary.")
    return dict(value)


def parse_datetime(value: Any, field_name: str) -> datetime:
    """Parse a required ISO datetime."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ResearchWorkbenchError(f"Invalid {field_name}: {value}") from exc
    raise ResearchWorkbenchError(f"Invalid {field_name}: {value}")


def parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    """Parse an optional ISO datetime."""

    if value in (None, ""):
        return None
    return parse_datetime(value, field_name)


def parse_url(value: Any, field_name: str) -> str:
    """Parse a required HTTP(S) URL."""

    url = require_text(value, field_name)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ResearchWorkbenchError(f"Invalid {field_name}: {value}")
    return url
