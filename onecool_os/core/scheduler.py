"""Lightweight scheduler for Onecool OS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from onecool_os.core.config import AppConfig, SystemConfig
from onecool_os.core.engine import CoreEngine
from onecool_os.core.exceptions import OnecoolOSError
from onecool_os.core.logging import LoggingSystem


JobAction = Callable[[], None]


class ScheduleType(StrEnum):
    """Supported scheduler types."""

    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class JobStatus(StrEnum):
    """Runtime job status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduledJob:
    """A registered scheduler job."""

    job_id: str
    name: str
    schedule_type: ScheduleType
    action: JobAction
    enabled: bool = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    status: JobStatus = JobStatus.PENDING
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe job details."""

        payload = asdict(self)
        payload.pop("action")
        payload["schedule_type"] = self.schedule_type.value
        payload["status"] = self.status.value
        payload["last_run_at"] = _format_datetime(self.last_run_at)
        payload["next_run_at"] = _format_datetime(self.next_run_at)
        return payload


class SchedulerError(OnecoolOSError):
    """Raised for scheduler registration and execution errors."""


class Scheduler:
    """Registers and runs lightweight jobs."""

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self.logging_system = LoggingSystem(config)
        self.logger = self.logging_system.get_logger("system")
        self._jobs: dict[str, ScheduledJob] = {}

    def initialize(self) -> "Scheduler":
        """Register built-in jobs and return the scheduler."""

        self.register_job(
            ScheduledJob(
                job_id="core.health",
                name="Core Health",
                schedule_type=ScheduleType.MANUAL,
                action=self._core_health_job,
            )
        )
        return self

    def register_job(self, job: ScheduledJob) -> None:
        """Register a job."""

        if job.job_id in self._jobs:
            raise SchedulerError(f"Duplicate job_id: {job.job_id}")
        job.next_run_at = calculate_next_run(job.schedule_type)
        self._jobs[job.job_id] = job

    def list_jobs(self) -> tuple[ScheduledJob, ...]:
        """Return all jobs in stable order."""

        return tuple(self._jobs[job_id] for job_id in sorted(self._jobs))

    def get_job(self, job_id: str) -> ScheduledJob:
        """Return a job by id."""

        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise SchedulerError(f"Unknown job_id: {job_id}") from exc

    def run_job(self, job_id: str) -> ScheduledJob:
        """Run a job manually and update status."""

        job = self.get_job(job_id)
        if not job.enabled:
            job.status = JobStatus.SKIPPED
            job.error_message = "Job is disabled."
            self.logger.info("Skipped disabled job %s", job.job_id)
            return job

        started_at = datetime.now(UTC)
        job.last_run_at = started_at
        job.error_message = None
        self.logger.info("Starting job %s", job.job_id)
        try:
            job.action()
        except Exception as exc:  # noqa: BLE001 - scheduler must isolate jobs.
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.next_run_at = calculate_next_run(job.schedule_type, started_at)
            self.logger.exception("Job %s failed", job.job_id)
            return job

        job.status = JobStatus.SUCCESS
        job.next_run_at = calculate_next_run(job.schedule_type, started_at)
        self.logger.info("Finished job %s", job.job_id)
        return job

    def _core_health_job(self) -> None:
        app_config = AppConfig(database_path=self.config.database.path)
        with CoreEngine(app_config) as engine:
            health = engine.services.get("health")()
        if health.get("status") != "ok":
            raise SchedulerError("Core health check failed.")
        self.logger.info("Core health check passed.")


def create_scheduler(config: SystemConfig) -> Scheduler:
    """Create and initialize the scheduler."""

    return Scheduler(config).initialize()


def calculate_next_run(
    schedule_type: ScheduleType,
    from_time: datetime | None = None,
) -> datetime | None:
    """Calculate next run time for a schedule type."""

    base = from_time or datetime.now(UTC)
    if schedule_type == ScheduleType.MANUAL:
        return None
    if schedule_type == ScheduleType.DAILY:
        return base + timedelta(days=1)
    if schedule_type == ScheduleType.WEEKLY:
        return base + timedelta(days=7)
    if schedule_type == ScheduleType.MONTHLY:
        return _add_month(base)
    raise SchedulerError(f"Unsupported schedule type: {schedule_type}")


def _add_month(value: datetime) -> datetime:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, _days_in_month(year, month))
    return value.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=UTC)
    this_month = datetime(year, month, 1, tzinfo=UTC)
    return (next_month - this_month).days


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
