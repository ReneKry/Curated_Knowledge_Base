# API-Kurzbeschreibungen – Index

Dieses Dokument indexiert die geplanten API-Oberflächen für das LLM-Knowledge-Base-System.

## FastAPI (Application Interface)
- `GET /health`: Liveness und Readiness.
- `POST /query`: Deterministische Kontextabfrage über `llm_kb_reader`-Logik.
- `POST /sync/run`: Startet Delta-Sync-Lauf und schreibt `sync_state`.
- `GET /sync/runs/{run_id}`: Liefert Laufmetadaten inklusive geänderter und gelöschter Dateien.
- `POST /gc/evaluate`: Führt GC-Regeln auf geänderte Artefakte aus.
- `GET /gc/report`: Liefert den aktuellen GC-Report (Markdown oder JSON).

## MCP Server (Tool Interface)
- `kb.query`: Deterministische Query mit Prioritätspfaden und Limits.
- `kb.sync`: Delta-Sync für geänderte Markdown-Dateien.
- `kb.gc_report`: Zugriff auf strukturierte GC-Einträge.
- `kb.file_get`: Volltextzugriff auf selektierte KB-Dateien.

## Hinweise
- Implementierung bleibt SQLite-first.
- MCP und FastAPI greifen auf dieselbe Service-Schicht zu (DRY).
