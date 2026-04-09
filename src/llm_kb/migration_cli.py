"""CLI for applying SQLite schema migrations."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from llm_kb.config import load_runtime_config
from llm_kb.logging_config import configure_logging



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply LLM KB database migrations")
    parser.add_argument("--db-path", default=None, help="Path to SQLite database")
    parser.add_argument("--migrations-path", default="db/migrations", help="Path to migration SQL files")
    return parser.parse_args()



def apply_migrations(db_path: Path, migrations_path: Path) -> None:
    migration_files = sorted(migrations_path.glob("*.sql"))

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

        applied_versions = {
            row[0] for row in cursor.execute("SELECT version FROM schema_migrations")
        }

        for migration_file in migration_files:
            version = migration_file.stem
            if version in applied_versions:
                continue

            sql_script = migration_file.read_text(encoding="utf-8")
            cursor.executescript(sql_script)
            cursor.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                (version, _utc_now()),
            )

        connection.commit()



def main() -> None:
    args = parse_args()
    config = load_runtime_config()
    configure_logging(config.log_level)

    db_path = Path(args.db_path) if args.db_path else config.database_path
    migrations_path = Path(args.migrations_path)
    apply_migrations(db_path=db_path, migrations_path=migrations_path)


if __name__ == "__main__":
    main()
