"""FastAPI application for LLM KB v1 baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from llm_kb.config import load_runtime_config
from llm_kb.gc_rules import append_gc_report, entries_as_dict, evaluate_gc_entries
from llm_kb.ingestion_service import IngestionService
from llm_kb.lifecycle_service import LifecycleService
from llm_kb.logging_config import configure_logging
from llm_kb.models import ReaderLimits
from llm_kb.reader import query_kb, result_as_json_dict
from llm_kb.settings_service import RuntimeSettingsService
from llm_kb.sync_service import DeltaSyncService

runtime_config = load_runtime_config()
configure_logging(runtime_config.log_level)

app = FastAPI(title="LLM KB API", version="0.1.0")

settings_service = RuntimeSettingsService()
lifecycle_service = LifecycleService()
kb_registry: Dict[str, Path] = {"default": runtime_config.kb_root}
ingestion_service = IngestionService(kb_registry=kb_registry, db_path=runtime_config.database_path)
sync_service = DeltaSyncService(db_path=runtime_config.database_path)
sync_runs: Dict[str, dict] = {}


class QueryRequest(BaseModel):
    query: str = Field(default="")


class IngestTextRequest(BaseModel):
    kb_id: str
    relative_path: str
    content: str


class IngestFileRequest(BaseModel):
    kb_id: str
    source_file: str
    relative_path: str


class UpdateSettingsRequest(BaseModel):
    provider_name: str
    model_name: str
    active_kb_id: str
    max_files: int
    max_chars: int


class GcEvaluateRequest(BaseModel):
    kb_id: str
    file_paths: list[str] = Field(default_factory=list)


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


@app.post("/ingest/file")
def ingest_file(request: IngestFileRequest, x_client_id: str = Header(default="anonymous")) -> dict:
    try:
        job = ingestion_service.ingest_file(
            client_id=x_client_id,
            kb_id=request.kb_id,
            source_file=Path(request.source_file),
            relative_path=request.relative_path,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"job_id": job.job_id, "status": job.status, "detail": job.detail}


@app.get("/settings/providers")
def providers() -> dict:
    return {"providers": settings_service.providers()}


@app.post("/gc/evaluate")
def gc_evaluate(request: GcEvaluateRequest) -> dict:
    if request.kb_id not in kb_registry:
        raise HTTPException(status_code=404, detail="Unknown KB id")

    kb_root = kb_registry[request.kb_id]
    if request.file_paths:
        candidate_paths = [kb_root / relative_path for relative_path in request.file_paths]
    else:
        candidate_paths = sorted(kb_root.rglob("*.md"))

    entries = evaluate_gc_entries(candidate_paths)
    report_path = Path("BB/KB-Garbage-Collection-Report.md")
    append_gc_report(report_path=report_path, entries=entries)
    return {"entry_count": len(entries), "entries": entries_as_dict(entries)}


@app.get("/gc/report")
def gc_report() -> dict:
    report_path = Path("BB/KB-Garbage-Collection-Report.md")
    if not report_path.exists():
        return {"exists": False, "content": ""}
    return {"exists": True, "content": report_path.read_text(encoding="utf-8")}


@app.post("/sync/run")
def sync_run(x_client_id: str = Header(default="anonymous")) -> dict:
    _ = x_client_id  # Explicitly accepted for client tracing parity.
    setting = settings_service.get_or_create(x_client_id)
    if setting.active_kb_id not in kb_registry:
        raise HTTPException(status_code=404, detail="Unknown active KB")

    summary = sync_service.run(kb_root=kb_registry[setting.active_kb_id])
    payload = {
        "run_id": summary.run_id,
        "changed_files": summary.changed_files,
        "deleted_files": summary.deleted_files,
    }
    sync_runs[summary.run_id] = payload
    return payload


@app.get("/sync/runs/{run_id}")
def sync_run_detail(run_id: str) -> dict:
    if run_id not in sync_runs:
        raise HTTPException(status_code=404, detail="Unknown run_id")
    return sync_runs[run_id]


@app.get("/settings/providers/{provider_name}/models")
def provider_models(provider_name: str) -> dict:
    try:
        return {"provider": provider_name, "models": settings_service.models_for_provider(provider_name)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/settings/active")
def active_settings(x_client_id: str = Header(default="anonymous")) -> dict:
    return settings_service.as_dict(x_client_id)


@app.get("/kb/list")
def kb_list() -> dict:
    return {"kb_ids": sorted(kb_registry.keys())}


@app.get("/kb/active")
def kb_active(x_client_id: str = Header(default="anonymous")) -> dict:
    setting = settings_service.get_or_create(x_client_id)
    return {"client_id": x_client_id, "active_kb_id": setting.active_kb_id}


@app.put("/kb/active/{kb_id}")
def kb_set_active(kb_id: str, x_client_id: str = Header(default="anonymous")) -> dict:
    if kb_id not in kb_registry:
        raise HTTPException(status_code=404, detail="Unknown kb_id")

    current_setting = settings_service.get_or_create(x_client_id)
    updated = settings_service.update(
        client_id=x_client_id,
        provider_name=current_setting.provider_name,
        model_name=current_setting.model_name,
        active_kb_id=kb_id,
        max_files=current_setting.max_files,
        max_chars=current_setting.max_chars,
    )
    return {"client_id": updated.client_id, "active_kb_id": updated.active_kb_id}


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
