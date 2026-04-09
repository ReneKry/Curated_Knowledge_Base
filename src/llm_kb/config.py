"""Central runtime configuration for the LLM KB services.

Intent:
- Keep environment parsing in one place (KISS).
- Avoid duplicate configuration logic across API/MCP/CLI (DRY).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    """Application runtime configuration loaded from environment variables."""

    database_path: Path
    kb_root: Path
    log_level: str
    default_max_files: int
    default_max_chars: int



def _int_from_env(variable_name: str, default_value: int) -> int:
    raw_value = os.getenv(variable_name)
    if raw_value is None:
        return default_value
    return int(raw_value)



def load_runtime_config() -> RuntimeConfig:
    """Load runtime config from environment with explicit defaults."""
    return RuntimeConfig(
        database_path=Path(os.getenv("LLM_KB_DB_PATH", "llm_kb.sqlite3")),
        kb_root=Path(os.getenv("LLM_KB_ROOT", "LLM_KB")),
        log_level=os.getenv("LLM_KB_LOG_LEVEL", "INFO"),
        default_max_files=_int_from_env("LLM_KB_DEFAULT_MAX_FILES", 10),
        default_max_chars=_int_from_env("LLM_KB_DEFAULT_MAX_CHARS", 20_000),
    )
