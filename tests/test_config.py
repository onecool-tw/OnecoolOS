import json
from pathlib import Path

from onecool_os.__main__ import main
from onecool_os.core.config import AppConfig, ConfigLoader


def write_settings(config_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        """
app:
  name: Onecool OS
  version: 0.2.0
  timezone: Asia/Taipei
  language: en
database:
  path: data/default.sqlite3
paths:
  data_dir: data
  cache_dir: data/cache
  logs_dir: data/logs
  exports_dir: data/exports
runtime:
  debug: false
  environment: production
""".strip(),
        encoding="utf-8",
    )


def test_config_loads_successfully(tmp_path: Path) -> None:
    write_settings(tmp_path)

    loaded = ConfigLoader(config_dir=tmp_path).load()

    assert loaded.config.app.name == "Onecool OS"
    assert loaded.config.database.path == Path("data/default.sqlite3")
    assert loaded.config.runtime.debug is False


def test_user_yaml_overrides_settings_yaml(tmp_path: Path) -> None:
    write_settings(tmp_path)
    (tmp_path / "user.yaml").write_text(
        """
app:
  language: zh-TW
database:
  path: data/user.sqlite3
""".strip(),
        encoding="utf-8",
    )

    loaded = ConfigLoader(config_dir=tmp_path).load()

    assert loaded.config.app.language == "zh-TW"
    assert loaded.config.database.path == Path("data/user.sqlite3")


def test_environment_variables_override_yaml(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_settings(tmp_path)
    monkeypatch.setenv("ONECOOL_OS_DATABASE_PATH", "data/env.sqlite3")
    monkeypatch.setenv("ONECOOL_OS_DEBUG", "true")

    loaded = ConfigLoader(config_dir=tmp_path).load()

    assert loaded.config.database.path == Path("data/env.sqlite3")
    assert loaded.config.runtime.debug is True


def test_missing_user_yaml_does_not_crash(tmp_path: Path) -> None:
    write_settings(tmp_path)

    loaded = ConfigLoader(config_dir=tmp_path).load()

    assert loaded.config.app.version == "0.2.0"


def test_app_config_preserves_database_environment_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    write_settings(tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("ONECOOL_OS_DB_PATH", "data/legacy.sqlite3")

    config = AppConfig.from_environment()

    assert config.database_path == Path("data/legacy.sqlite3")


def test_secrets_are_not_printed_by_cli(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    write_settings(tmp_path)
    (tmp_path / "secrets.yaml").write_text(
        """
secrets:
  github_token: super-secret-token
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(tmp_path))

    assert main(["config"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert "super-secret-token" not in captured.out
    assert "secrets" not in payload
