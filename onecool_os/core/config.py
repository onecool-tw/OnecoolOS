"""Application configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from onecool_os.core.exceptions import ConfigurationError


ConfigDict = dict[str, Any]


@dataclass(frozen=True)
class ApplicationSettings:
    """Application metadata settings."""

    name: str
    version: str
    timezone: str
    language: str


@dataclass(frozen=True)
class DatabaseSettings:
    """Database settings."""

    path: Path


@dataclass(frozen=True)
class PathSettings:
    """Runtime filesystem paths."""

    data_dir: Path
    cache_dir: Path
    logs_dir: Path
    exports_dir: Path


@dataclass(frozen=True)
class RuntimeSettings:
    """Runtime behavior settings."""

    debug: bool
    environment: str


@dataclass(frozen=True)
class LoggingSettings:
    """Logging settings."""

    level: str | None = None


@dataclass(frozen=True)
class MarketSettings:
    """Market Engine settings."""

    default_provider: str = "mock"
    providers: ConfigDict = field(default_factory=dict)


@dataclass(frozen=True)
class SystemConfig:
    """Validated centralized Onecool OS configuration."""

    app: ApplicationSettings
    database: DatabaseSettings
    paths: PathSettings
    runtime: RuntimeSettings
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    market: MarketSettings = field(default_factory=MarketSettings)

    def to_sanitized_dict(self) -> ConfigDict:
        """Return configuration safe for CLI output."""

        return _stringify_paths(asdict(self))


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the Core Engine."""

    database_path: Path = Path("data/onecool_os.sqlite3")
    plugin_paths: tuple[Path, ...] = field(default_factory=tuple)
    load_builtin_plugins: bool = True

    @classmethod
    def from_environment(cls) -> "AppConfig":
        """Build configuration from environment variables."""

        system_config = ConfigLoader.from_environment().load().config
        database_path = system_config.database.path
        raw_plugin_paths = os.environ.get("ONECOOL_OS_PLUGIN_PATHS", "")
        plugin_paths = tuple(
            Path(item)
            for item in raw_plugin_paths.split(os.pathsep)
            if item.strip()
        )
        return cls(database_path=database_path, plugin_paths=plugin_paths)


@dataclass(frozen=True)
class LoadedConfig:
    """Loaded configuration and any optional secret placeholders."""

    config: SystemConfig
    secrets: ConfigDict = field(default_factory=dict)

    def to_sanitized_dict(self) -> ConfigDict:
        """Return configuration safe for display."""

        return self.config.to_sanitized_dict()


@dataclass(frozen=True)
class ConfigLoader:
    """Loads settings, user overrides, environment overrides, and secrets."""

    config_dir: Path = Path("config")
    settings_file: str = "settings.yaml"
    user_file: str = "user.yaml"
    secrets_file: str = "secrets.yaml"

    @classmethod
    def from_environment(cls) -> "ConfigLoader":
        """Build loader using environment-selected config directory."""

        config_dir = Path(os.environ.get("ONECOOL_OS_CONFIG_DIR", "config"))
        return cls(config_dir=config_dir)

    def load(self) -> LoadedConfig:
        """Load and validate configuration."""

        settings_path = self.config_dir / self.settings_file
        if not settings_path.exists():
            raise ConfigurationError(f"Missing settings file: {settings_path}")

        config_data = _read_yaml_mapping(settings_path)
        user_data = _read_optional_yaml_mapping(self.config_dir / self.user_file)
        secrets_data = _read_optional_yaml_mapping(
            self.config_dir / self.secrets_file
        )
        merged_data = _deep_merge(config_data, user_data)
        merged_data = _deep_merge(merged_data, self._environment_overrides())
        return LoadedConfig(
            config=_build_system_config(merged_data),
            secrets=secrets_data,
        )

    @staticmethod
    def _environment_overrides() -> ConfigDict:
        mapping = {
            "ONECOOL_OS_APP_NAME": ("app", "name"),
            "ONECOOL_OS_APP_VERSION": ("app", "version"),
            "ONECOOL_OS_TIMEZONE": ("app", "timezone"),
            "ONECOOL_OS_LANGUAGE": ("app", "language"),
            "ONECOOL_OS_DATABASE_PATH": ("database", "path"),
            "ONECOOL_OS_DB_PATH": ("database", "path"),
            "ONECOOL_OS_DATA_DIR": ("paths", "data_dir"),
            "ONECOOL_OS_CACHE_DIR": ("paths", "cache_dir"),
            "ONECOOL_OS_LOGS_DIR": ("paths", "logs_dir"),
            "ONECOOL_OS_EXPORTS_DIR": ("paths", "exports_dir"),
            "ONECOOL_OS_DEBUG": ("runtime", "debug"),
            "ONECOOL_OS_ENVIRONMENT": ("runtime", "environment"),
            "ONECOOL_OS_LOG_LEVEL": ("logging", "level"),
        }
        overrides: ConfigDict = {}
        for env_name, keys in mapping.items():
            if env_name not in os.environ:
                continue
            section, key = keys
            overrides.setdefault(section, {})[key] = _parse_scalar(
                os.environ[env_name]
            )
        return overrides


def _build_system_config(data: Mapping[str, Any]) -> SystemConfig:
    required_sections = ("app", "database", "paths", "runtime")
    for section in required_sections:
        if not isinstance(data.get(section), Mapping):
            raise ConfigurationError(f"Missing config section: {section}")

    app = data["app"]
    database = data["database"]
    paths = data["paths"]
    runtime = data["runtime"]
    logging = data.get("logging", {})
    market = data.get("market", {})
    _validate_required(app, "app", ("name", "version", "timezone", "language"))
    _validate_required(database, "database", ("path",))
    _validate_required(
        paths,
        "paths",
        ("data_dir", "cache_dir", "logs_dir", "exports_dir"),
    )
    _validate_required(runtime, "runtime", ("debug", "environment"))

    debug = runtime["debug"]
    if not isinstance(debug, bool):
        raise ConfigurationError("runtime.debug must be a boolean.")
    if logging and not isinstance(logging, Mapping):
        raise ConfigurationError("logging must be a mapping.")
    if market and not isinstance(market, Mapping):
        raise ConfigurationError("market must be a mapping.")

    log_level = logging.get("level") if isinstance(logging, Mapping) else None
    if log_level is not None:
        log_level = str(log_level).upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level not in valid_levels:
            raise ConfigurationError(
                "logging.level must be DEBUG, INFO, WARNING, ERROR, "
                "or CRITICAL."
            )

    return SystemConfig(
        app=ApplicationSettings(
            name=str(app["name"]),
            version=str(app["version"]),
            timezone=str(app["timezone"]),
            language=str(app["language"]),
        ),
        database=DatabaseSettings(path=Path(str(database["path"]))),
        paths=PathSettings(
            data_dir=Path(str(paths["data_dir"])),
            cache_dir=Path(str(paths["cache_dir"])),
            logs_dir=Path(str(paths["logs_dir"])),
            exports_dir=Path(str(paths["exports_dir"])),
        ),
        runtime=RuntimeSettings(
            debug=debug,
            environment=str(runtime["environment"]),
        ),
        logging=LoggingSettings(level=log_level),
        market=MarketSettings(
            default_provider=str(market.get("default_provider", "mock")),
            providers=dict(market.get("providers", {})),
        ),
    )


def _validate_required(
    section: Mapping[str, Any],
    section_name: str,
    keys: tuple[str, ...],
) -> None:
    for key in keys:
        value = section.get(key)
        if value is None or value == "":
            raise ConfigurationError(
                f"Missing required config value: {section_name}.{key}"
            )


def _read_optional_yaml_mapping(path: Path) -> ConfigDict:
    if not path.exists():
        return {}
    return _read_yaml_mapping(path)


def _read_yaml_mapping(path: Path) -> ConfigDict:
    data: ConfigDict = {}
    stack: list[tuple[int, ConfigDict]] = [(-1, data)]

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2:
            raise ConfigurationError(
                f"Invalid indentation in {path}:{line_number}"
            )
        if ":" not in line:
            raise ConfigurationError(f"Invalid YAML line in {path}:{line_number}")

        key, raw_value = line.strip().split(":", 1)
        if not key:
            raise ConfigurationError(f"Missing YAML key in {path}:{line_number}")

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ConfigurationError(f"Invalid YAML nesting in {path}:{line_number}")

        current = stack[-1][1]
        value = raw_value.strip()
        if value == "":
            child: ConfigDict = {}
            current[key] = child
            stack.append((indent, child))
        else:
            current[key] = _parse_scalar(value)

    return data


def _parse_scalar(value: str) -> Any:
    normalized = value.strip()
    if normalized in {"true", "True", "yes", "Yes"}:
        return True
    if normalized in {"false", "False", "no", "No"}:
        return False
    if normalized in {"null", "Null", "~"}:
        return None
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {"'", '"'}
    ):
        return normalized[1:-1]
    return normalized


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> ConfigDict:
    merged: ConfigDict = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _stringify_paths(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stringify_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_stringify_paths(item) for item in value]
    return value
