"""Garbage-collection rules for redundancy and conflict detection.

Intent:
- Keep GC logic deterministic and auditable.
- Prefer simple transparent heuristics over opaque semantics in v1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

PRIORITY_FOLDERS = ["system", "entities", "topics", "notes", "outputs", "sources", "raw"]


@dataclass(frozen=True)
class GcEntry:
    """A structured GC finding for report output."""

    source_path: str
    entry_type: str
    why_collected: str
    canonical_source: str
    timestamp_utc: str
    needs_review: bool = False



def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()



def _folder_priority(file_path: Path) -> int:
    """Resolve folder priority from path parts.

    Unknown folders are treated as lowest priority.
    """
    parts = set(file_path.parts)
    for index, folder_name in enumerate(PRIORITY_FOLDERS):
        if folder_name in parts:
            return index
    return len(PRIORITY_FOLDERS)



def _claim_lines(content: str) -> List[str]:
    """Extract claim-like lines from markdown content.

    Headings and blank lines are ignored to keep comparisons stable.
    """
    claims: List[str] = []
    for line in content.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        claims.append(text)
    return claims



def _conflict_key(claim_text: str) -> Tuple[str, bool]:
    """Build a simple conflict key and polarity.

    v1 heuristic:
    - "not <statement>" is treated as negative polarity.
    - other statements are treated as positive polarity.
    """
    normalized = " ".join(claim_text.lower().split())
    if normalized.startswith("not "):
        return normalized[4:], False
    return normalized, True



def evaluate_gc_entries(file_paths: Iterable[Path]) -> List[GcEntry]:
    """Evaluate redundancy and conflict entries for the given markdown files."""
    sorted_files = sorted(
        [path for path in file_paths if path.exists() and path.suffix == ".md"],
        key=lambda path: (_folder_priority(path), str(path)),
    )

    canonical_claim_by_text: Dict[str, Path] = {}
    canonical_polarity_by_key: Dict[str, Tuple[bool, Path]] = {}
    gc_entries: List[GcEntry] = []

    for file_path in sorted_files:
        claims = _claim_lines(file_path.read_text(encoding="utf-8"))
        for claim_text in claims:
            claim_text_normalized = " ".join(claim_text.split())
            conflict_key, polarity = _conflict_key(claim_text_normalized)

            if claim_text_normalized in canonical_claim_by_text:
                canonical_source = canonical_claim_by_text[claim_text_normalized]
                gc_entries.append(
                    GcEntry(
                        source_path=str(file_path),
                        entry_type="redundant",
                        why_collected="Claim already present in higher-priority source.",
                        canonical_source=str(canonical_source),
                        timestamp_utc=_utc_now(),
                        needs_review=False,
                    )
                )
                continue

            if conflict_key in canonical_polarity_by_key:
                existing_polarity, canonical_source = canonical_polarity_by_key[conflict_key]
                if existing_polarity != polarity:
                    gc_entries.append(
                        GcEntry(
                            source_path=str(file_path),
                            entry_type="conflict",
                            why_collected="Opposing claim polarity for same statement key.",
                            canonical_source=str(canonical_source),
                            timestamp_utc=_utc_now(),
                            needs_review=True,
                        )
                    )
                    continue

            canonical_claim_by_text[claim_text_normalized] = file_path
            canonical_polarity_by_key[conflict_key] = (polarity, file_path)

    return gc_entries



def append_gc_report(report_path: Path, entries: List[GcEntry]) -> None:
    """Append structured GC entries to markdown report file."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not report_path.exists():
        report_path.write_text("# KB Garbage Collection Report\n\n## Einträge\n", encoding="utf-8")

    with report_path.open("a", encoding="utf-8") as report_file:
        for entry in entries:
            report_file.write("\n### Collected\n")
            report_file.write(f"- Quelle: `{entry.source_path}`\n")
            report_file.write(f"- Typ: `{entry.entry_type}`\n")
            report_file.write(f"- Warum collected: {entry.why_collected}\n")
            report_file.write(f"- Kanonische Referenz: `{entry.canonical_source}`\n")
            report_file.write(f"- Zeitstempel (UTC): `{entry.timestamp_utc}`\n")
            if entry.needs_review:
                report_file.write("- needs_review: `true`\n")



def entries_as_dict(entries: List[GcEntry]) -> List[dict]:
    """Serialize entries into plain dictionaries for API/MCP output."""
    return [asdict(entry) for entry in entries]
