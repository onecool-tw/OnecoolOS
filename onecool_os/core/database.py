"""SQLite database management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from onecool_os.core.exceptions import DatabaseError


class Database:
    """Owns the SQLite connection and schema migration lifecycle."""

    def __init__(self, path: Path, migrations_path: Path | None = None) -> None:
        self.path = path
        self.migrations_path = migrations_path or self._default_migrations_path()
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Return an active SQLite connection."""

        if self._connection is None:
            raise DatabaseError("Database is not connected.")
        return self._connection

    def connect(self) -> sqlite3.Connection:
        """Open the SQLite connection and configure safe defaults."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        self._connection = connection
        return connection

    def migrate(self) -> None:
        """Apply pending SQL migrations in filename order."""

        if self._connection is None:
            self.connect()

        migration_files = sorted(self.migrations_path.glob("*.sql"))
        if not migration_files:
            raise DatabaseError(
                f"No migration files found in {self.migrations_path}."
            )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        applied_versions = {
            row["version"]
            for row in self.connection.execute(
                "SELECT version FROM schema_migrations"
            )
        }

        for migration_file in migration_files:
            version = migration_file.stem
            if version in applied_versions:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            with self.connection:
                self.connection.executescript(sql)
                self.connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (version,),
                )

    def close(self) -> None:
        """Close the SQLite connection."""

        if self._connection is None:
            return
        self._connection.close()
        self._connection = None

    @staticmethod
    def _default_migrations_path() -> Path:
        return Path(__file__).resolve().parents[2] / "migrations"
