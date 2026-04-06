# Curated Knowledge Base – v1 Implementation Baseline

Dieses Repository enthält den Start der technischen Umsetzung für das LLM-KB-System.

## Enthaltene v1-Bausteine
- Deterministischer Reader (`src/llm_kb/reader.py`): manifest-first, feste Ebenenpriorität, harte Limits.
- Reader-CLI (`src/llm_kb/reader_cli.py`): direkte deterministische Abfrage via Kommandozeile.
- Ingestion-Service (`src/llm_kb/ingestion_service.py`): gemeinsamer Schreibpfad für API/MCP/Batch.
- Runtime-Settings (`src/llm_kb/settings_service.py`): clientbezogene aktive KB und Provider/Modell-Auswahl.
- Lifecycle-Service (`src/llm_kb/lifecycle_service.py`): start/stop/restart für `ingestion-worker` und `sync-scheduler`.
- Delta-Sync (`src/llm_kb/sync_service.py` + `src/llm_kb/sync_cli.py`): md5-basiert, orphan-fähig, auditierbarer `sync_state`.
- Migration-CLI (`src/llm_kb/migration_cli.py`) + `db/migrations/`: versionierte DB-Migrationen.
- FastAPI-App (`src/llm_kb/api_app.py`) und MCP-Handler (`src/llm_kb/mcp_server.py`) auf gemeinsamer Service-Schicht.

## Lokale Tests
```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Migration ausführen
```bash
PYTHONPATH=src python -m llm_kb.migration_cli --db-path llm_kb.sqlite3
```
