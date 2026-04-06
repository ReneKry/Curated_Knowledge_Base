# API-Kurzbeschreibungen – Index

Dieses Dokument indexiert die geplanten API-Oberflächen für das LLM-Knowledge-Base-System.

## FastAPI (Application Interface)
- `GET /health`: Liveness und Readiness.
- `POST /query`: Deterministische Kontextabfrage über `llm_kb_reader`-Logik.
- `POST /sync/run`: Startet Delta-Sync-Lauf und schreibt `sync_state`.
- `GET /sync/runs/{run_id}`: Liefert Laufmetadaten inklusive geänderter und gelöschter Dateien.
- `POST /gc/evaluate`: Führt GC-Regeln auf geänderte Artefakte aus.
- `GET /gc/report`: Liefert den aktuellen GC-Report (Markdown oder JSON).
- `POST /ingest/text`: Nimmt Markdown/Text entgegen und schreibt in die aktive oder explizit gewählte KB.
- `POST /ingest/file`: Importiert eine Datei in die gewählte KB und startet optional Nachverarbeitung.
- `GET /ingest/jobs/{job_id}`: Liefert Status und Fehlerdetails eines Ingestion-Jobs.
- `GET /settings/providers`: Listet konfigurierte LLM-Provider.
- `GET /settings/providers/{provider}/models`: Liefert live verfügbare Modelle des Providers.
- `GET /settings/active`: Liefert aktuelle Runtime-Einstellungen (Provider, Modell, aktive KB).
- `PUT /settings/active`: Aktualisiert Runtime-Einstellungen dynamisch ohne Redeploy.
- `GET /kb/list`: Listet registrierte Knowledge Bases auf der Maschine.
- `GET /kb/active`: Liefert die aktuell aktive Knowledge Base.
- `PUT /kb/active/{kb_id}`: Wechselt die aktive Knowledge Base dynamisch.
- `POST /services/{service_name}/start`: Startet einen verwalteten Hintergrunddienst.
- `POST /services/{service_name}/stop`: Stoppt einen verwalteten Hintergrunddienst.
- `POST /services/{service_name}/restart`: Startet einen verwalteten Hintergrunddienst neu.
- `GET /services/status`: Liefert den Laufstatus aller verwalteten Dienste.

## MCP Server (Tool Interface)
- `kb.query`: Deterministische Query mit Prioritätspfaden und Limits.
- `kb.sync`: Delta-Sync für geänderte Markdown-Dateien.
- `kb.gc_report`: Zugriff auf strukturierte GC-Einträge.
- `kb.file_get`: Volltextzugriff auf selektierte KB-Dateien.
- `kb.ingest_text`: Fügt Wissen als Text/Markdown hinzu.
- `kb.ingest_file`: Fügt Wissen aus einer Datei hinzu.
- `kb.ingest_status`: Liefert den Status von Ingestion-Jobs.
- `kb.settings_get`: Liest aktive Runtime-Einstellungen.
- `kb.settings_update`: Aktualisiert Provider, Modell und Limits dynamisch.
- `kb.provider_models`: Fragt live Modelle eines Providers ab.
- `kb.kb_select`: Wechselt die aktive Knowledge Base.
- `kb.service_start|kb.service_stop|kb.service_restart`: Steuerung der Lifecycle-Aktionen.
- `kb.service_status`: Gibt den Laufzustand verwalteter Dienste zurück.

## Hinweise
- Implementierung bleibt SQLite-first.
- MCP und FastAPI greifen auf dieselbe Service-Schicht zu (DRY).
- Schreibzugriffe laufen über eine einheitliche Ingestion-Pipeline (KISS).
