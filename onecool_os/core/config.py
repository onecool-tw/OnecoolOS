"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the Core Engine."""

    database_path: Path = Path("data/onecool_os.sqlite3")
    plugin_paths: tuple[Path, ...] = field(default_factory=tuple)
    load_builtin_plugins: bool = True

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """Build configuration from environment variables."""

        database_path = Path(
            os.environ.get("ONECOOL_OS_DB_PATH", "data/onecool_os.sqlite3")
        )
        raw_plugin_paths = os.environ.get("ONECOOL_OS_PLUGIN_PATHS", "")
        plugin_paths = tuple(
            Path(item)
            for item in raw_plugin_paths.split(os.pathsep)
            if item.strip()
        )
        return cls(database_path=database_path, plugin_paths=plugin_paths)
