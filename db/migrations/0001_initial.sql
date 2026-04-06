-- Initial migration for LLM KB v1.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    file_path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    last_synced TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'orphan'))
);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    FOREIGN KEY(source_file) REFERENCES files(file_path)
);
CREATE INDEX IF NOT EXISTS idx_entities_source_file ON entities(source_file);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    confidence REAL NOT NULL,
    source_file TEXT NOT NULL,
    FOREIGN KEY(source_file) REFERENCES files(file_path)
);
CREATE INDEX IF NOT EXISTS idx_claims_source_file ON claims(source_file);

CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    FOREIGN KEY(source_file) REFERENCES files(file_path)
);
CREATE INDEX IF NOT EXISTS idx_relations_source_file ON relations(source_file);

CREATE TABLE IF NOT EXISTS sync_state (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    changed_files INTEGER NOT NULL,
    deleted_files INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sync_state_started_at ON sync_state(started_at);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    kb_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'succeeded', 'failed')),
    detail TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);

CREATE TABLE IF NOT EXISTS runtime_settings (
    client_id TEXT PRIMARY KEY,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    active_kb_id TEXT NOT NULL,
    max_files INTEGER NOT NULL,
    max_chars INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
