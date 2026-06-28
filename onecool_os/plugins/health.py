"""Built-in health plugin."""

from __future__ import annotations

from onecool_os.core.plugins import PluginContext, PluginManifest


class HealthPlugin:
    """Registers a simple health service for Core Engine checks."""

    manifest = PluginManifest(
        name="core.health",
        version="0.1.0",
        description="Core Engine health checks.",
    )

    def activate(self, context: PluginContext) -> None:
        """Register health service."""

        context.services.register("health", self.health)

    def deactivate(self, context: PluginContext) -> None:
        """Unregister health service."""

        context.services.unregister("health")

    def health(self) -> dict[str, str]:
        """Return health status."""

        return {"status": "ok"}


def create_plugin() -> HealthPlugin:
    """Return the plugin instance."""

    return HealthPlugin()
