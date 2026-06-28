from pathlib import Path

from onecool_os.core.config import AppConfig
from onecool_os.core.engine import CoreEngine


def test_engine_starts_with_core_health_plugin(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "onecool.sqlite3")

    with CoreEngine(config) as engine:
        status = engine.status()

        assert engine.started is True
        assert status.plugins == ("core.health",)
        assert "database" in status.services
        assert "events" in status.services
        assert "health" in status.services
        assert engine.services.get("health")() == {"status": "ok"}

    assert engine.started is False


def test_engine_records_lifecycle_events(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "onecool.sqlite3")

    engine = CoreEngine(config)
    engine.start()
    topics = [
        row["topic"]
        for row in engine.database.connection.execute(
            "SELECT topic FROM event_log ORDER BY id"
        )
    ]
    engine.stop()

    assert "plugin.activated" in topics
    assert "engine.started" in topics


def test_engine_can_restart_cleanly(tmp_path: Path) -> None:
    config = AppConfig(database_path=tmp_path / "onecool.sqlite3")
    engine = CoreEngine(config)

    engine.start()
    engine.stop()
    engine.start()

    assert engine.started is True
    assert engine.services.get("health")() == {"status": "ok"}
    engine.stop()
