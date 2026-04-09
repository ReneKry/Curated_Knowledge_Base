"""Ingestion service shared by API and external pipeline adapters."""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import asdict
from pathlib import Path
from queue import Empty, Queue
from typing import Dict, Optional
from uuid import uuid4

from llm_kb.models import IngestionJob, utc_now_iso


class IngestionService:
    """Store markdown content and track ingestion jobs.

    Intent: unify online/offline ingestion into one audited write path.
    """

    def __init__(self, kb_registry: Dict[str, Path], db_path: Optional[Path] = None) -> None:
        self._kb_registry = kb_registry
        self._jobs: Dict[str, IngestionJob] = {}
        self._db_path = db_path
        self._queued_job_ids: Queue[str] = Queue()
        if self._db_path is not None:
            self._initialize_job_storage()

    def _initialize_job_storage(self) -> None:
        """Ensure ingestion job table exists for persistent job tracking."""
        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    kb_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'succeeded', 'failed')),
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _persist_job(self, job: IngestionJob) -> None:
        """Persist one job state transition if database storage is configured."""
        if self._db_path is None:
            return

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO ingestion_jobs(job_id, client_id, kb_id, status, detail, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    detail=excluded.detail,
                    updated_at=excluded.updated_at
                """,
                (
                    job.job_id,
                    job.client_id,
                    job.kb_id,
                    job.status,
                    job.detail,
                    job.created_at,
                    job.updated_at,
                ),
            )
            connection.commit()

    def _resolve_kb_root(self, kb_id: str) -> Path:
        if kb_id not in self._kb_registry:
            raise ValueError(f"Unknown KB id: {kb_id}")
        kb_root = self._kb_registry[kb_id]
        kb_root.mkdir(parents=True, exist_ok=True)
        return kb_root

    def ingest_text(self, client_id: str, kb_id: str, relative_path: str, content: str) -> IngestionJob:
        job = IngestionJob(
            job_id=str(uuid4()),
            client_id=client_id,
            kb_id=kb_id,
            status="running",
            detail="Writing markdown content",
        )
        self._jobs[job.job_id] = job

        try:
            kb_root = self._resolve_kb_root(kb_id)
            target_path = kb_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            job.status = "succeeded"
            job.detail = f"Stored at {target_path}"
        except Exception as error:  # noqa: BLE001
            job.status = "failed"
            job.detail = str(error)
        finally:
            job.updated_at = utc_now_iso()
            self._persist_job(job)

        return job

    def ingest_file(self, client_id: str, kb_id: str, source_file: Path, relative_path: str) -> IngestionJob:
        job = IngestionJob(
            job_id=str(uuid4()),
            client_id=client_id,
            kb_id=kb_id,
            status="running",
            detail="Copying markdown file",
        )
        self._jobs[job.job_id] = job

        try:
            kb_root = self._resolve_kb_root(kb_id)
            target_path = kb_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_path)
            job.status = "succeeded"
            job.detail = f"Imported to {target_path}"
        except Exception as error:  # noqa: BLE001
            job.status = "failed"
            job.detail = str(error)
        finally:
            job.updated_at = utc_now_iso()
            self._persist_job(job)

        return job

    def job_status(self, job_id: str) -> dict:
        if job_id in self._jobs:
            return asdict(self._jobs[job_id])

        if self._db_path is None:
            raise ValueError(f"Unknown job: {job_id}")

        with sqlite3.connect(self._db_path) as connection:
            cursor = connection.cursor()
            row = cursor.execute(
                """
                SELECT job_id, client_id, kb_id, status, detail, created_at, updated_at
                FROM ingestion_jobs
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Unknown job: {job_id}")

        return {
            "job_id": row[0],
            "client_id": row[1],
            "kb_id": row[2],
            "status": row[3],
            "detail": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        }

    def queue_ingest_text(self, client_id: str, kb_id: str, relative_path: str, content: str) -> IngestionJob:
        """Queue a text ingestion job for worker-driven execution."""
        job = IngestionJob(
            job_id=str(uuid4()),
            client_id=client_id,
            kb_id=kb_id,
            status="queued",
            detail="Queued text ingestion job",
        )
        self._jobs[job.job_id] = job
        self._persist_job(job)
        self._queued_job_ids.put((job.job_id, "text", relative_path, content))
        return job

    def run_worker_once(self) -> Optional[IngestionJob]:
        """Run one queued ingestion job and return its final state.

        Intent: provide a tiny worker loop primitive for M5 without adding
        external queue infrastructure yet.
        """
        try:
            job_id, mode, relative_path, payload = self._queued_job_ids.get_nowait()
        except Empty:
            return None

        job = self._jobs[job_id]
        job.status = "running"
        job.detail = "Worker started job"
        job.updated_at = utc_now_iso()
        self._persist_job(job)

        if mode == "text":
            result = self.ingest_text(
                client_id=job.client_id,
                kb_id=job.kb_id,
                relative_path=relative_path,
                content=payload,
            )
            self._jobs[job_id] = result
            return result

        job.status = "failed"
        job.detail = f"Unsupported queue mode: {mode}"
        job.updated_at = utc_now_iso()
        self._persist_job(job)
        return job
