"""Centralized logging for Onecool OS."""

from __future__ import annotations

import logging as stdlib_logging
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from onecool_os.core.config import SystemConfig


LOG_FILES = {
    "system": "system.log",
    "market": "market.log",
    "decision": "decision.log",
}
LOGGER_PREFIX = "onecool_os"
HANDLER_MARKER = "_onecool_os_managed"
DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_BACKUP_COUNT = 5


@dataclass(frozen=True)
class LoggingStatus:
    """Public logging status for CLI output."""

    logs_dir: str
    log_files: tuple[str, ...]
    level: str


class LoggingSystem:
    """Configures and returns Onecool OS loggers."""

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self.logs_dir = config.paths.logs_dir
        self.level_name = resolve_log_level(config)
        self.level = stdlib_logging.getLevelName(self.level_name)

    def initialize(self) -> LoggingStatus:
        """Create log directory and configure required loggers."""

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for module_name in LOG_FILES:
            self.get_logger(module_name)
        return self.status()

    def get_logger(self, module_name: str) -> stdlib_logging.Logger:
        """Return a configured module logger."""

        logger_name = f"{LOGGER_PREFIX}.{module_name}"
        logger = stdlib_logging.getLogger(logger_name)
        logger.setLevel(self.level)
        logger.propagate = False
        self._clear_handlers(logger)
        logger.addHandler(self._file_handler(module_name))
        logger.addHandler(self._console_handler())
        return logger

    def system_logger(self) -> stdlib_logging.Logger:
        """Return the system logger."""

        return self.get_logger("system")

    def status(self) -> LoggingStatus:
        """Return logging status for CLI output."""

        return LoggingStatus(
            logs_dir=str(self.logs_dir),
            log_files=tuple(
                str(self.logs_dir / filename)
                for filename in LOG_FILES.values()
            ),
            level=self.level_name,
        )

    def _file_handler(self, module_name: str) -> RotatingFileHandler:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_dir / LOG_FILES.get(
            module_name,
            f"{module_name}.log",
        )
        handler = RotatingFileHandler(
            log_file,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(self.level)
        handler.setFormatter(self._formatter())
        setattr(handler, HANDLER_MARKER, True)
        return handler

    def _console_handler(self) -> stdlib_logging.StreamHandler:
        handler = stdlib_logging.StreamHandler()
        handler.setLevel(self.level)
        handler.setFormatter(self._formatter())
        setattr(handler, HANDLER_MARKER, True)
        return handler

    @staticmethod
    def _clear_handlers(logger: stdlib_logging.Logger) -> None:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    @staticmethod
    def _formatter() -> stdlib_logging.Formatter:
        return stdlib_logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )


def initialize_logging(config: SystemConfig) -> LoggingSystem:
    """Initialize centralized logging and return the logging system."""

    logging_system = LoggingSystem(config)
    logging_system.initialize()
    return logging_system


def get_system_logger(config: SystemConfig) -> stdlib_logging.Logger:
    """Initialize logging and return the system logger."""

    return initialize_logging(config).system_logger()


def get_module_logger(
    config: SystemConfig,
    module_name: str,
) -> stdlib_logging.Logger:
    """Initialize logging and return a module-specific logger."""

    return initialize_logging(config).get_logger(module_name)


def resolve_log_level(config: SystemConfig) -> str:
    """Resolve log level from config, falling back to runtime debug."""

    configured_level = config.logging.level
    if configured_level:
        return configured_level.upper()
    if config.runtime.debug:
        return "DEBUG"
    return "INFO"
