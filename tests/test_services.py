"""Service-level tests for settings, ingestion, and lifecycle."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_kb.ingestion_service import IngestionService
from llm_kb.lifecycle_service import LifecycleService
from llm_kb.settings_service import RuntimeSettingsService


class ServiceTests(unittest.TestCase):
    def test_settings_are_client_scoped(self) -> None:
        service = RuntimeSettingsService()
        service.update(
            client_id="client-a",
            provider_name="primary",
            model_name="default",
            active_kb_id="kb-a",
            max_files=5,
            max_chars=1000,
        )
        other = service.get_or_create("client-b")
        self.assertEqual(other.active_kb_id, "default")
        self.assertEqual(service.get_or_create("client-a").active_kb_id, "kb-a")

    def test_ingest_text_writes_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir) / "kb-a"
            db_path = Path(temp_dir) / "llm_kb.sqlite3"
            ingestion = IngestionService(kb_registry={"kb-a": kb_root}, db_path=db_path)
            job = ingestion.ingest_text(
                client_id="client-a",
                kb_id="kb-a",
                relative_path="notes/new.md",
                content="# Title\nBody",
            )
            self.assertEqual(job.status, "succeeded")
            self.assertTrue((kb_root / "notes" / "new.md").exists())
            self.assertEqual(ingestion.job_status(job.job_id)["status"], "succeeded")

    def test_queue_worker_processes_text_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir) / "kb-a"
            db_path = Path(temp_dir) / "llm_kb.sqlite3"
            ingestion = IngestionService(kb_registry={"kb-a": kb_root}, db_path=db_path)

            queued_job = ingestion.queue_ingest_text(
                client_id="client-a",
                kb_id="kb-a",
                relative_path="notes/queued.md",
                content="# Queued\nBody",
            )
            self.assertEqual(queued_job.status, "queued")

            processed_job = ingestion.run_worker_once()
            self.assertIsNotNone(processed_job)
            assert processed_job is not None
            self.assertEqual(processed_job.status, "succeeded")
            self.assertTrue((kb_root / "notes" / "queued.md").exists())

    def test_lifecycle_start_stop_restart(self) -> None:
        service = LifecycleService()
        self.assertEqual(service.start("ingestion-worker").status, "running")
        self.assertEqual(service.stop("ingestion-worker").status, "stopped")
        self.assertEqual(service.restart("ingestion-worker").status, "running")


if __name__ == "__main__":
    unittest.main()
