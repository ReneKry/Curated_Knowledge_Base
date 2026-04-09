"""Integration-like tests for FastAPI endpoints and MCP handlers."""

from __future__ import annotations

import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from llm_kb.mcp_server import McpToolHandlers

FASTAPI_AVAILABLE = find_spec("fastapi") is not None


class ApiAndMcpTests(unittest.TestCase):
    @unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed in this environment")
    def test_fastapi_ingest_query_and_lifecycle(self) -> None:
        """Exercise key FastAPI routes with a client-scoped KB context."""
        from fastapi.testclient import TestClient

        from llm_kb import api_app

        with tempfile.TemporaryDirectory() as temp_dir:
            temporary_kb_root = Path(temp_dir) / "kb-a"
            api_app.kb_registry["kb-a"] = temporary_kb_root

            test_client = TestClient(api_app.app)
            headers = {"x-client-id": "client-a"}

            settings_response = test_client.put(
                "/settings/active",
                headers=headers,
                json={
                    "provider_name": "primary",
                    "model_name": "default",
                    "active_kb_id": "kb-a",
                    "max_files": 10,
                    "max_chars": 2000,
                },
            )
            self.assertEqual(settings_response.status_code, 200)

            ingest_response = test_client.post(
                "/ingest/text",
                headers=headers,
                json={
                    "kb_id": "kb-a",
                    "relative_path": "notes/example.md",
                    "content": "# Title\nHello from API",
                },
            )
            self.assertEqual(ingest_response.status_code, 200)
            self.assertEqual(ingest_response.json()["status"], "succeeded")

            query_response = test_client.post("/query", headers=headers, json={"query": "Hello"})
            self.assertEqual(query_response.status_code, 200)
            self.assertEqual(len(query_response.json()["returned_files"]), 1)

            sync_response = test_client.post("/sync/run", headers=headers)
            self.assertEqual(sync_response.status_code, 200)
            self.assertIn("run_id", sync_response.json())

            sync_detail_response = test_client.get(f"/sync/runs/{sync_response.json()['run_id']}")
            self.assertEqual(sync_detail_response.status_code, 200)

            kb_list_response = test_client.get("/kb/list")
            self.assertEqual(kb_list_response.status_code, 200)
            self.assertIn("kb-a", kb_list_response.json()["kb_ids"])

            kb_active_response = test_client.get("/kb/active", headers=headers)
            self.assertEqual(kb_active_response.status_code, 200)
            self.assertEqual(kb_active_response.json()["active_kb_id"], "kb-a")

            restart_response = test_client.post("/services/ingestion-worker/restart")
            self.assertEqual(restart_response.status_code, 200)
            self.assertEqual(restart_response.json()["status"], "running")

    def test_mcp_handlers_ingest_query_and_status(self) -> None:
        """Exercise MCP tool handlers against the same service concepts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handlers = McpToolHandlers()
            handlers.kb_registry["kb-a"] = Path(temp_dir) / "kb-a"

            handlers.kb_settings_update(
                client_id="client-a",
                provider_name="primary",
                model_name="default",
                active_kb_id="kb-a",
                max_files=10,
                max_chars=2000,
            )

            ingest_payload = handlers.kb_ingest_text(
                client_id="client-a",
                kb_id="kb-a",
                relative_path="notes/from_mcp.md",
                content="# Title\nHello from MCP",
            )
            self.assertEqual(ingest_payload["status"], "succeeded")

            status_payload = handlers.kb_ingest_status(ingest_payload["job_id"])
            self.assertEqual(status_payload["status"], "succeeded")

            query_payload = handlers.kb_query(client_id="client-a", query="Hello")
            self.assertEqual(len(query_payload["returned_files"]), 1)

            lifecycle_payload = handlers.kb_service_start("sync-scheduler")
            self.assertEqual(lifecycle_payload["status"], "running")


if __name__ == "__main__":
    unittest.main()
