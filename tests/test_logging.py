from pathlib import Path

from onecool_os.core.config import (
    ApplicationSettings,
    DatabaseSettings,
    LoggingSettings,
    PathSettings,
    RuntimeSettings,
    SystemConfig,
)
from onecool_os.core.logging import LoggingSystem


def build_config(tmp_path: Path, level: str | None = "INFO") -> SystemConfig:
    return SystemConfig(
        app=ApplicationSettings(
            name="Onecool OS",
            version="0.2.1",
            timezone="Asia/Taipei",
            language="en",
        ),
        database=DatabaseSettings(path=tmp_path / "onecool.sqlite3"),
        paths=PathSettings(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            logs_dir=tmp_path / "logs",
            exports_dir=tmp_path / "exports",
        ),
        runtime=RuntimeSettings(debug=False, environment="test"),
        logging=LoggingSettings(level=level),
    )


def test_logger_initializes_successfully(tmp_path: Path) -> None:
    logging_system = LoggingSystem(build_config(tmp_path))
    status = logging_system.initialize()

    assert status.level == "INFO"
    assert status.logs_dir == str(tmp_path / "logs")
    assert len(status.log_files) == 3


def test_logs_directory_is_created_if_missing(tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"

    LoggingSystem(build_config(tmp_path)).initialize()

    assert logs_dir.is_dir()


def test_system_log_is_created(tmp_path: Path) -> None:
    logging_system = LoggingSystem(build_config(tmp_path))

    logging_system.system_logger().info("system ready")

    assert (tmp_path / "logs" / "system.log").is_file()
    assert "system ready" in (tmp_path / "logs" / "system.log").read_text(
        encoding="utf-8"
    )


def test_module_logger_writes_to_correct_file(tmp_path: Path) -> None:
    logging_system = LoggingSystem(build_config(tmp_path))

    logging_system.get_logger("market").warning("market warning")

    market_log = tmp_path / "logs" / "market.log"
    assert market_log.is_file()
    assert "market warning" in market_log.read_text(encoding="utf-8")


def test_repeated_initialization_does_not_duplicate_handlers(
    tmp_path: Path,
) -> None:
    logging_system = LoggingSystem(build_config(tmp_path))

    logger = logging_system.get_logger("decision")
    first_count = len(logger.handlers)
    logger = logging_system.get_logger("decision")
    second_count = len(logger.handlers)

    assert first_count == 2
    assert second_count == first_count


def test_debug_runtime_sets_debug_level_when_logging_level_missing(
    tmp_path: Path,
) -> None:
    config = build_config(tmp_path, level=None)
    config = SystemConfig(
        app=config.app,
        database=config.database,
        paths=config.paths,
        runtime=RuntimeSettings(debug=True, environment="test"),
        logging=config.logging,
    )

    status = LoggingSystem(config).initialize()

    assert status.level == "DEBUG"
