"""Service registry shared by Core Engine plugins."""

from __future__ import annotations

from typing import Any


class ServiceRegistry:
    """A small typed-name service registry."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service by name."""

        if name in self._services:
            raise KeyError(f"Service already registered: {name}")
        self._services[name] = service

    def unregister(self, name: str) -> None:
        """Unregister a service by name when it exists."""

        self._services.pop(name, None)

    def clear(self) -> None:
        """Remove all services."""

        self._services.clear()

    def get(self, name: str) -> Any:
        """Return a registered service by name."""

        return self._services[name]

    def has(self, name: str) -> bool:
        """Return whether a service exists."""

        return name in self._services

    def names(self) -> tuple[str, ...]:
        """Return registered service names."""

        return tuple(sorted(self._services))
