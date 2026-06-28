"""Core Engine orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from onecool_os.core.config import AppConfig
from onecool_os.core.database import Database
from onecool_os.core.events import EventBus
from onecool_os.core.plugins import PluginContext, PluginManager
from onecool_os.core.registry import ServiceRegistry


@dataclass
class EngineStatus:
    """Public status snapshot for the Core Engine."""

    database_path: str
    plugins: tuple[str, ...]
    services: tuple[str, ...]


class CoreEngine:
    """Coordinates persistence, events, services, and plugins."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.database = Database(config.database_path)
        self.services = ServiceRegistry()
        self.events: EventBus | None = None
        self.plugins: PluginManager | None = None
        self._started = False

    @property
    def started(self) -> bool:
        """Return whether the engine is started."""

        return self._started

    def start(self) -> "CoreEngine":
        """Start the Core Engine and activate plugins."""

        if self._started:
            return self

        self.database.connect()
        self.database.migrate()
        self.events = EventBus(self.database.connection)
        self.services.register("database", self.database.connection)
        self.services.register("events", self.events)

        context = PluginContext(
            connection=self.database.connection,
            events=self.events,
            services=self.services,
        )
        self.plugins = PluginManager(
            context=context,
            plugin_paths=self.config.plugin_paths,
            load_builtin_plugins=self.config.load_builtin_plugins,
        )
        self.plugins.load_all()
        self.plugins.activate_all()
        self.events.publish("engine.started", self.status().__dict__)
        self._started = True
        return self

    def stop(self) -> None:
        """Stop the Core Engine and release resources."""

        if not self._started:
            self.database.close()
            return

        if self.plugins is not None:
            self.plugins.deactivate_all()
        if self.events is not None:
            self.events.publish("engine.stopped", {})
        self.database.close()
        self.services.clear()
        self.events = None
        self.plugins = None
        self._started = False

    def status(self) -> EngineStatus:
        """Return a stable status snapshot."""

        plugin_names: tuple[str, ...] = ()
        if self.plugins is not None:
            plugin_names = tuple(
                plugin.manifest.name for plugin in self.plugins.plugins
            )
        return EngineStatus(
            database_path=str(self.config.database_path),
            plugins=plugin_names,
            services=self.services.names(),
        )

    def __enter__(self) -> "CoreEngine":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
