"""Delta-sync service with md5 hashing and orphan detection."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from uuid import uuid4


@dataclass(frozen=True)
class SyncSummary:
    """Result summary for one sync run."""

    run_id: str
    changed_files: int
    deleted_files: int


def _md5(path: Path) -> str:
    """Compute stable md5 hash for file content."""
    digest = hashlib.md5()  # noqa: S324 - md5 is an explicit product requirement.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeltaSyncService:
    """Sync markdown files into SQLite state.

    Intent: keep v1 sync deterministic, auditable, and file-based.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def run(self, kb_root: Path) -> SyncSummary:
        run_id = str(uuid4())
        started_at = _utc_now()
        changed_files = 0
        deleted_files = 0

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO sync_state(run_id, started_at, finished_at, changed_files, deleted_files) VALUES(?, ?, NULL, 0, 0)",
                (run_id, started_at),
            )

            existing = {
                row[0]: row[1]
                for row in cursor.execute("SELECT file_path, content_hash FROM files WHERE status = 'active'")
            }
            seen_paths: Dict[str, str] = {}

            for file_path in sorted(kb_root.rglob("*.md")):
                normalized_path = str(file_path)
                hash_value = _md5(file_path)
                seen_paths[normalized_path] = hash_value

                if existing.get(normalized_path) == hash_value:
                    continue

                changed_files += 1
                cursor.execute(
                    """
                    INSERT INTO files(file_path, content_hash, last_synced, status)
                    VALUES(?, ?, ?, 'active')
                    ON CONFLICT(file_path) DO UPDATE SET
                        content_hash=excluded.content_hash,
                        last_synced=excluded.last_synced,
                        status='active'
                    """,
                    (normalized_path, hash_value, _utc_now()),
                )

            for existing_path in existing:
                if existing_path in seen_paths:
                    continue
                deleted_files += 1
                cursor.execute(
                    "UPDATE files SET status='orphan', last_synced=? WHERE file_path=?",
                    (_utc_now(), existing_path),
                )

            cursor.execute(
                "UPDATE sync_state SET finished_at=?, changed_files=?, deleted_files=? WHERE run_id=?",
                (_utc_now(), changed_files, deleted_files, run_id),
            )
            connection.commit()

        return SyncSummary(run_id=run_id, changed_files=changed_files, deleted_files=deleted_files)
