"""Tests for GC rule detection and report writing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_kb.gc_rules import append_gc_report, evaluate_gc_entries


class GcRulesTests(unittest.TestCase):
    def test_detects_redundant_and_conflict_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir)
            system_file = kb_root / "system" / "a.md"
            notes_file = kb_root / "notes" / "b.md"
            topics_file = kb_root / "topics" / "c.md"

            system_file.parent.mkdir(parents=True)
            notes_file.parent.mkdir(parents=True)
            topics_file.parent.mkdir(parents=True)

            system_file.write_text("Service is available", encoding="utf-8")
            notes_file.write_text("Service is available", encoding="utf-8")
            topics_file.write_text("not service is available", encoding="utf-8")

            entries = evaluate_gc_entries([system_file, notes_file, topics_file])
            entry_types = sorted(entry.entry_type for entry in entries)

            self.assertEqual(entry_types, ["conflict", "redundant"])

    def test_appends_report_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.md"
            source_file = Path(temp_dir) / "system" / "a.md"
            source_file.parent.mkdir(parents=True)
            source_file.write_text("Service is available", encoding="utf-8")

            entries = evaluate_gc_entries([source_file])
            append_gc_report(report_path=report_path, entries=entries)

            report_content = report_path.read_text(encoding="utf-8")
            self.assertIn("KB Garbage Collection Report", report_content)


if __name__ == "__main__":
    unittest.main()
