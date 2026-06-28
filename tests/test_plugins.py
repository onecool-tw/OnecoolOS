from pathlib import Path

from onecool_os.core.config import AppConfig
from onecool_os.core.engine import CoreEngine


def test_external_plugin_file_can_register_service(tmp_path: Path) -> None:
    plugin_file = tmp_path / "sample_plugin.py"
    plugin_file.write_text(
        """
from onecool_os.core.plugins import PluginManifest


class SamplePlugin:
    manifest = PluginManifest(
        name="sample.plugin",
        version="1.0.0",
        description="Sample test plugin.",
    )

    def activate(self, context):
        context.services.register("sample", lambda: "ready")

    def deactivate(self, context):
        pass


def create_plugin():
    return SamplePlugin()
""".strip(),
        encoding="utf-8",
    )
    config = AppConfig(
        database_path=tmp_path / "onecool.sqlite3",
        plugin_paths=(plugin_file,),
    )

    with CoreEngine(config) as engine:
        assert engine.services.get("sample")() == "ready"
        assert tuple(
            plugin.manifest.name for plugin in engine.plugins.plugins
        ) == ("core.health", "sample.plugin")
