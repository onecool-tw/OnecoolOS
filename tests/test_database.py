from pathlib import Path

from onecool_os.core.database import Database


def test_database_migrations_are_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "onecool.sqlite3")

    database.connect()
    database.migrate()
    database.migrate()

    versions = [
        row["version"]
        for row in database.connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
    ]
    assert versions == ["001_core"]
    database.close()
