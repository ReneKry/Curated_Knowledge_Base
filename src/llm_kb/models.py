"""Data models used across reader, ingestion, and API layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


def utc_now_iso() -> str:
    """Return an RFC3339-like UTC timestamp for auditable records."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ReaderLimits:
    """Query limits that keep response size deterministic and bounded."""

    max_files: int = 10
    max_chars: int = 20_000


@dataclass(frozen=True)
class ReaderMatch:
    """A matched markdown file plus its full text content."""

    file_path: str
    content: str


@dataclass(frozen=True)
class ReaderResult:
    """Deterministic result payload for context retrieval."""

    query: str
    total_files_considered: int
    returned_files: List[ReaderMatch]


@dataclass
class RuntimeSetting:
    """Client-scoped runtime setting profile."""

    client_id: str
    provider_name: str = "primary"
    model_name: str = "default"
    active_kb_id: str = "default"
    max_files: int = 10
    max_chars: int = 20_000
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass
class IngestionJob:
    """Ingestion job state for API and MCP polling."""

    job_id: str
    client_id: str
    kb_id: str
    status: str
    detail: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
