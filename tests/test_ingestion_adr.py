"""Tests for ADR-validated ingestion behavior.

The tests map directly to BB/ADR-Entscheidungen-v1.md:
- ADR-002: ingestion is a managed write path.
- Architekturklarstellung Ingestion: online and batch inputs share one ingestion core.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_kb.ingestion_service import IngestionService


class IngestionAdrTests(unittest.TestCase):
    def test_online_and_batch_input_use_same_ingestion_core(self) -> None:
        """Verify both write inputs persist through one service instance.

        Intent:
        - online input is represented by ingest_text
        - batch/offline input is represented by ingest_file
        Both operations must succeed and write into the same selected KB root.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            kb_root = temp_root / "kb-a"
            source_file = temp_root / "source.md"
            source_file.write_text("# Batch Source\nFrom file.", encoding="utf-8")

            ingestion_service = IngestionService(kb_registry={"kb-a": kb_root})

            online_job = ingestion_service.ingest_text(
                client_id="client-a",
                kb_id="kb-a",
                relative_path="notes/online.md",
                content="# Online Source\nFrom API/MCP path.",
            )
            batch_job = ingestion_service.ingest_file(
                client_id="client-a",
                kb_id="kb-a",
                source_file=source_file,
                relative_path="notes/batch.md",
            )

            self.assertEqual(online_job.status, "succeeded")
            self.assertEqual(batch_job.status, "succeeded")
            self.assertTrue((kb_root / "notes" / "online.md").exists())
            self.assertTrue((kb_root / "notes" / "batch.md").exists())

    def test_ingestion_job_status_is_auditable(self) -> None:
        """Ensure ingestion job status can be retrieved after write."""
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir) / "kb-a"
            ingestion_service = IngestionService(kb_registry={"kb-a": kb_root})

            job = ingestion_service.ingest_text(
                client_id="client-a",
                kb_id="kb-a",
                relative_path="notes/audit.md",
                content="# Audit",
            )

            job_status = ingestion_service.job_status(job.job_id)
            self.assertEqual(job_status["status"], "succeeded")
            self.assertEqual(job_status["client_id"], "client-a")
            self.assertEqual(job_status["kb_id"], "kb-a")


if __name__ == "__main__":
    unittest.main()
