"""Plugin loading and lifecycle management."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Protocol

from onecool_os.core.events import EventBus
from onecool_os.core.exceptions import PluginError
from onecool_os.core.registry import ServiceRegistry


@dataclass(frozen=True)
class PluginManifest:
    """Metadata supplied by a plugin."""

    name: str
    version: str
    description: str = ""


@dataclass(frozen=True)
class PluginContext:
    """Runtime dependencies exposed to plugins."""

    connection: sqlite3.Connection
    events: EventBus
    services: ServiceRegistry


class Plugin(Protocol):
    """Runtime contract every plugin must implement."""

    manifest: PluginManifest

    def activate(self, context: PluginContext) -> None:
        """Activate the plugin."""

    def deactivate(self, context: PluginContext) -> None:
        """Deactivate the plugin."""


class PluginManager:
    """Discovers, loads, and manages plugin lifecycle."""

    def __init__(
        self,
        context: PluginContext,
        plugin_paths: tuple[Path, ...] = (),
        load_builtin_plugins: bool = True,
    ) -> None:
        self.context = context
        self.plugin_paths = plugin_paths
        self.load_builtin_plugins = load_builtin_plugins
        self._plugins: dict[str, Plugin] = {}

    @property
    def plugins(self) -> tuple[Plugin, ...]:
        """Return loaded plugins in stable name order."""

        return tuple(self._plugins[name] for name in sorted(self._plugins))

    def load_all(self) -> None:
        """Load built-in and configured external plugins."""

        if self.load_builtin_plugins:
            self.load_module("onecool_os.plugins.health")

        for plugin_path in self.plugin_paths:
            self.load_path(plugin_path)

    def load_module(self, module_name: str) -> Plugin:
        """Load a plugin from an importable module name."""

        module = importlib.import_module(module_name)
        return self._create_and_register(module)

    def load_path(self, path: Path) -> None:
        """Load plugins from a file or directory path."""

        if not path.exists():
            raise PluginError(f"Plugin path does not exist: {path}")
        if path.is_file() and path.suffix == ".py":
            self._load_python_file(path)
            return
        if path.is_dir():
            self._load_plugin_directory(path)
            return
        raise PluginError(f"Unsupported plugin path: {path}")

    def activate_all(self) -> None:
        """Activate all loaded plugins."""

        for plugin in self.plugins:
            plugin.activate(self.context)
            self._record_plugin(plugin)
            self.context.events.publish(
                "plugin.activated",
                {
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                },
            )

    def deactivate_all(self) -> None:
        """Deactivate all loaded plugins in reverse name order."""

        for plugin in reversed(self.plugins):
            plugin.deactivate(self.context)
            self.context.events.publish(
                "plugin.deactivated",
                {"name": plugin.manifest.name},
            )

    def _load_plugin_directory(self, path: Path) -> None:
        manifest_path = path / "plugin.json"
        if manifest_path.exists():
            config = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not config.get("enabled", True):
                return
            module_name = config.get("module")
            if not module_name:
                raise PluginError(f"Missing module in {manifest_path}.")
            search_paths = (str(path), str(path.parent))
            inserted_paths: list[str] = []
            for search_path in search_paths:
                if search_path not in sys.path:
                    sys.path.insert(0, search_path)
                    inserted_paths.append(search_path)
            try:
                self.load_module(module_name)
            finally:
                for search_path in inserted_paths:
                    sys.path.remove(search_path)
            return

        for python_file in sorted(path.glob("*.py")):
            if python_file.name == "__init__.py":
                continue
            self._load_python_file(python_file)

    def _load_python_file(self, path: Path) -> Plugin:
        module_name = f"onecool_external_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise PluginError(f"Cannot load plugin file: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return self._create_and_register(module)

    def _create_and_register(self, module: ModuleType) -> Plugin:
        factory = getattr(module, "create_plugin", None)
        if factory is None:
            raise PluginError(f"Missing create_plugin in {module.__name__}.")

        plugin = factory()
        manifest = getattr(plugin, "manifest", None)
        if not isinstance(manifest, PluginManifest):
            raise PluginError(
                f"Invalid manifest for plugin module {module.__name__}."
            )
        if manifest.name in self._plugins:
            raise PluginError(f"Duplicate plugin name: {manifest.name}")

        self._plugins[manifest.name] = plugin
        return plugin

    def _record_plugin(self, plugin: Plugin) -> None:
        with self.context.connection:
            self.context.connection.execute(
                """
                INSERT INTO plugins (
                    name, version, description, enabled, loaded_at, updated_at
                )
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    version = excluded.version,
                    description = excluded.description,
                    enabled = 1,
                    loaded_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    plugin.manifest.name,
                    plugin.manifest.version,
                    plugin.manifest.description,
                ),
            )
