"""Deterministic markdown reader with manifest-first behavior."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List

from llm_kb.models import ReaderLimits, ReaderMatch, ReaderResult

PRIORITY_FOLDERS = ["system", "entities", "topics", "notes", "outputs", "sources"]
MANIFEST_FILE = "system/manifest.md"


def _markdown_files(folder: Path) -> List[Path]:
    """Return markdown files in deterministic lexical order."""
    if not folder.exists() or not folder.is_dir():
        return []
    return sorted([path for path in folder.rglob("*.md") if path.is_file()])


def _contains_query(text: str, query: str) -> bool:
    """Simple case-insensitive containment check.

    Intent: keep v1 transparent and deterministic; no ranking heuristics.
    """
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    return normalized_query in text.lower()


def collect_candidate_files(kb_root: Path) -> List[Path]:
    """Collect candidate files by folder priority and manifest-first rule."""
    candidates: List[Path] = []
    manifest_path = kb_root / MANIFEST_FILE
    if manifest_path.exists():
        candidates.append(manifest_path)

    for folder_name in PRIORITY_FOLDERS:
        folder_path = kb_root / folder_name
        for path in _markdown_files(folder_path):
            if path != manifest_path:
                candidates.append(path)
    return candidates


def query_kb(kb_root: Path, query: str, limits: ReaderLimits) -> ReaderResult:
    """Return deterministic full-text matches respecting hard limits."""
    candidates = collect_candidate_files(kb_root)
    matches: List[ReaderMatch] = []
    accumulated_chars = 0

    for file_path in candidates:
        if len(matches) >= limits.max_files:
            break

        content = file_path.read_text(encoding="utf-8")
        if not _contains_query(content, query):
            continue

        # Intent: prevent context overflow while keeping whole-file semantics.
        if accumulated_chars + len(content) > limits.max_chars:
            break

        matches.append(ReaderMatch(file_path=str(file_path), content=content))
        accumulated_chars += len(content)

    return ReaderResult(
        query=query,
        total_files_considered=len(candidates),
        returned_files=matches,
    )


def result_as_json_dict(result: ReaderResult) -> dict:
    """Serialize result for JSON responses without hidden transformations."""
    payload = asdict(result)
    payload["returned_files"] = [asdict(item) for item in result.returned_files]
    return payload
