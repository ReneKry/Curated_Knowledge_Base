"""MCP tool handlers bound to shared services.

This module intentionally avoids transport-specific MCP setup details.
It focuses on deterministic business handlers that can be mapped to MCP tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from llm_kb.config import load_runtime_config
from llm_kb.ingestion_service import IngestionService
from llm_kb.lifecycle_service import LifecycleService
from llm_kb.logging_config import configure_logging
from llm_kb.models import ReaderLimits
from llm_kb.reader import query_kb, result_as_json_dict
from llm_kb.settings_service import RuntimeSettingsService

runtime_config = load_runtime_config()
configure_logging(runtime_config.log_level)


class McpToolHandlers:
    """Shared handler class for MCP tools in v1."""

    def __init__(self) -> None:
        self.settings_service = RuntimeSettingsService()
        self.lifecycle_service = LifecycleService()
        self.kb_registry: Dict[str, Path] = {"default": runtime_config.kb_root}
        self.ingestion_service = IngestionService(kb_registry=self.kb_registry, db_path=runtime_config.database_path)

    def kb_query(self, client_id: str, query: str) -> dict:
        setting = self.settings_service.get_or_create(client_id)
        kb_root = self.kb_registry[setting.active_kb_id]
        limits = ReaderLimits(max_files=setting.max_files, max_chars=setting.max_chars)
        return result_as_json_dict(query_kb(kb_root=kb_root, query=query, limits=limits))

    def kb_ingest_text(self, client_id: str, kb_id: str, relative_path: str, content: str) -> dict:
        job = self.ingestion_service.ingest_text(
            client_id=client_id,
            kb_id=kb_id,
            relative_path=relative_path,
            content=content,
        )
        return {"job_id": job.job_id, "status": job.status, "detail": job.detail}

    def kb_ingest_status(self, job_id: str) -> dict:
        return self.ingestion_service.job_status(job_id)

    def kb_provider_models(self, provider_name: str) -> dict:
        models = self.settings_service.models_for_provider(provider_name)
        return {"provider": provider_name, "models": models}

    def kb_settings_get(self, client_id: str) -> dict:
        return self.settings_service.as_dict(client_id)

    def kb_settings_update(
        self,
        client_id: str,
        provider_name: str,
        model_name: str,
        active_kb_id: str,
        max_files: int,
        max_chars: int,
    ) -> dict:
        updated = self.settings_service.update(
            client_id=client_id,
            provider_name=provider_name,
            model_name=model_name,
            active_kb_id=active_kb_id,
            max_files=max_files,
            max_chars=max_chars,
        )
        return {
            "client_id": updated.client_id,
            "provider_name": updated.provider_name,
            "model_name": updated.model_name,
            "active_kb_id": updated.active_kb_id,
            "max_files": updated.max_files,
            "max_chars": updated.max_chars,
            "updated_at": updated.updated_at,
        }

    def kb_kb_select(self, client_id: str, kb_id: str) -> dict:
        current = self.settings_service.get_or_create(client_id)
        updated = self.settings_service.update(
            client_id=client_id,
            provider_name=current.provider_name,
            model_name=current.model_name,
            active_kb_id=kb_id,
            max_files=current.max_files,
            max_chars=current.max_chars,
        )
        return {"client_id": updated.client_id, "active_kb_id": updated.active_kb_id}

    def kb_service_start(self, service_name: str) -> dict:
        service = self.lifecycle_service.start(service_name)
        return {"name": service.name, "status": service.status, "updated_at": service.updated_at}

    def kb_service_stop(self, service_name: str) -> dict:
        service = self.lifecycle_service.stop(service_name)
        return {"name": service.name, "status": service.status, "updated_at": service.updated_at}

    def kb_service_restart(self, service_name: str) -> dict:
        service = self.lifecycle_service.restart(service_name)
        return {"name": service.name, "status": service.status, "updated_at": service.updated_at}

    def kb_service_status(self) -> dict:
        return self.lifecycle_service.status()
