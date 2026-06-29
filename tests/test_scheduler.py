import json
from pathlib import Path

import pytest

from onecool_os.__main__ import main
from onecool_os.core.config import (
    ApplicationSettings,
    DatabaseSettings,
    LoggingSettings,
    PathSettings,
    RuntimeSettings,
    SystemConfig,
)
from onecool_os.core.scheduler import (
    JobStatus,
    ScheduleType,
    ScheduledJob,
    Scheduler,
    SchedulerError,
)


def build_config(tmp_path: Path) -> SystemConfig:
    return SystemConfig(
        app=ApplicationSettings(
            name="Onecool OS",
            version="0.2.2",
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
        logging=LoggingSettings(level="INFO"),
    )


def write_settings(config_dir: Path, root_dir: Path) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "settings.yaml").write_text(
        f"""
app:
  name: Onecool OS
  version: 0.2.2
  timezone: Asia/Taipei
  language: en
database:
  path: {root_dir / "onecool.sqlite3"}
paths:
  data_dir: {root_dir / "data"}
  cache_dir: {root_dir / "cache"}
  logs_dir: {root_dir / "logs"}
  exports_dir: {root_dir / "exports"}
runtime:
  debug: false
  environment: test
logging:
  level: INFO
""".strip(),
        encoding="utf-8",
    )


def test_scheduler_initializes_successfully(tmp_path: Path) -> None:
    scheduler = Scheduler(build_config(tmp_path)).initialize()

    jobs = scheduler.list_jobs()

    assert len(jobs) == 1
    assert jobs[0].job_id == "core.health"


def test_job_can_be_registered(tmp_path: Path) -> None:
    scheduler = Scheduler(build_config(tmp_path))

    scheduler.register_job(
        ScheduledJob(
            job_id="sample",
            name="Sample",
            schedule_type=ScheduleType.DAILY,
            action=lambda: None,
        )
    )

    assert scheduler.get_job("sample").next_run_at is not None


def test_duplicate_job_id_is_rejected(tmp_path: Path) -> None:
    scheduler = Scheduler(build_config(tmp_path))
    job = ScheduledJob(
        job_id="sample",
        name="Sample",
        schedule_type=ScheduleType.MANUAL,
        action=lambda: None,
    )

    scheduler.register_job(job)
    with pytest.raises(SchedulerError):
        scheduler.register_job(job)


def test_disabled_job_does_not_run(tmp_path: Path) -> None:
    calls = {"count": 0}
    scheduler = Scheduler(build_config(tmp_path))
    scheduler.register_job(
        ScheduledJob(
            job_id="disabled",
            name="Disabled",
            schedule_type=ScheduleType.MANUAL,
            action=lambda: calls.update(count=calls["count"] + 1),
            enabled=False,
        )
    )

    job = scheduler.run_job("disabled")

    assert calls["count"] == 0
    assert job.status == JobStatus.SKIPPED


def test_manual_job_can_run(tmp_path: Path) -> None:
    calls = {"count": 0}
    scheduler = Scheduler(build_config(tmp_path))
    scheduler.register_job(
        ScheduledJob(
            job_id="manual",
            name="Manual",
            schedule_type=ScheduleType.MANUAL,
            action=lambda: calls.update(count=calls["count"] + 1),
        )
    )

    job = scheduler.run_job("manual")

    assert calls["count"] == 1
    assert job.status == JobStatus.SUCCESS
    assert job.last_run_at is not None


def test_failed_job_records_error_message(tmp_path: Path) -> None:
    def fail() -> None:
        raise RuntimeError("planned failure")

    scheduler = Scheduler(build_config(tmp_path))
    scheduler.register_job(
        ScheduledJob(
            job_id="failing",
            name="Failing",
            schedule_type=ScheduleType.MANUAL,
            action=fail,
        )
    )

    job = scheduler.run_job("failing")

    assert job.status == JobStatus.FAILED
    assert job.error_message == "planned failure"


def test_cli_list_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["scheduler", "list"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload[0]["job_id"] == "core.health"


def test_cli_run_works(tmp_path: Path, monkeypatch, capsys) -> None:
    config_dir = tmp_path / "config"
    write_settings(config_dir, tmp_path)
    monkeypatch.setenv("ONECOOL_OS_CONFIG_DIR", str(config_dir))

    assert main(["scheduler", "run", "core.health"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["job_id"] == "core.health"
    assert payload["status"] == "success"
