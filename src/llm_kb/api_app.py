"""FastAPI application for LLM KB v1 baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from llm_kb.config import load_runtime_config
from llm_kb.ingestion_service import IngestionService
from llm_kb.lifecycle_service import LifecycleService
from llm_kb.logging_config import configure_logging
from llm_kb.models import ReaderLimits
from llm_kb.reader import query_kb, result_as_json_dict
from llm_kb.settings_service import RuntimeSettingsService

runtime_config = load_runtime_config()
configure_logging(runtime_config.log_level)

app = FastAPI(title="LLM KB API", version="0.1.0")

settings_service = RuntimeSettingsService()
lifecycle_service = LifecycleService()
kb_registry: Dict[str, Path] = {"default": runtime_config.kb_root}
ingestion_service = IngestionService(kb_registry=kb_registry, db_path=runtime_config.database_path)


class QueryRequest(BaseModel):
    query: str = Field(default="")


class IngestTextRequest(BaseModel):
    kb_id: str
    relative_path: str
    content: str


class UpdateSettingsRequest(BaseModel):
    provider_name: str
    model_name: str
    active_kb_id: str
    max_files: int
    max_chars: int


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query")
def query(request: QueryRequest, x_client_id: str = Header(default="anonymous")) -> dict:
    setting = settings_service.get_or_create(x_client_id)
    kb_root = kb_registry.get(setting.active_kb_id)
    if kb_root is None:
        raise HTTPException(status_code=404, detail="Unknown active KB")

    limits = ReaderLimits(max_files=setting.max_files, max_chars=setting.max_chars)
    result = query_kb(kb_root=kb_root, query=request.query, limits=limits)
    return result_as_json_dict(result)


@app.post("/ingest/text")
def ingest_text(request: IngestTextRequest, x_client_id: str = Header(default="anonymous")) -> dict:
    try:
        job = ingestion_service.ingest_text(
            client_id=x_client_id,
            kb_id=request.kb_id,
            relative_path=request.relative_path,
            content=request.content,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"job_id": job.job_id, "status": job.status, "detail": job.detail}


@app.get("/ingest/jobs/{job_id}")
def ingest_status(job_id: str) -> dict:
    try:
        return ingestion_service.job_status(job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/settings/providers")
def providers() -> dict:
    return {"providers": settings_service.providers()}


@app.get("/settings/providers/{provider_name}/models")
def provider_models(provider_name: str) -> dict:
    try:
        return {"provider": provider_name, "models": settings_service.models_for_provider(provider_name)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/settings/active")
def active_settings(x_client_id: str = Header(default="anonymous")) -> dict:
    return settings_service.as_dict(x_client_id)


@app.put("/settings/active")
def update_settings(request: UpdateSettingsRequest, x_client_id: str = Header(default="anonymous")) -> dict:
    try:
        updated = settings_service.update(
            client_id=x_client_id,
            provider_name=request.provider_name,
            model_name=request.model_name,
            active_kb_id=request.active_kb_id,
            max_files=request.max_files,
            max_chars=request.max_chars,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "client_id": updated.client_id,
        "provider_name": updated.provider_name,
        "model_name": updated.model_name,
        "active_kb_id": updated.active_kb_id,
        "max_files": updated.max_files,
        "max_chars": updated.max_chars,
        "updated_at": updated.updated_at,
    }


@app.post("/services/{service_name}/start")
def start_service(service_name: str) -> dict:
    try:
        service = lifecycle_service.start(service_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"name": service.name, "status": service.status, "updated_at": service.updated_at}


@app.post("/services/{service_name}/stop")
def stop_service(service_name: str) -> dict:
    try:
        service = lifecycle_service.stop(service_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"name": service.name, "status": service.status, "updated_at": service.updated_at}


@app.post("/services/{service_name}/restart")
def restart_service(service_name: str) -> dict:
    try:
        service = lifecycle_service.restart(service_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"name": service.name, "status": service.status, "updated_at": service.updated_at}


@app.get("/services/status")
def services_status() -> dict:
    return lifecycle_service.status()
