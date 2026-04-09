"""Reader behavior tests for deterministic order and limits."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_kb.models import ReaderLimits
from llm_kb.reader import query_kb


class ReaderTests(unittest.TestCase):
    def test_manifest_first_and_deterministic_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir)
            (kb_root / "system").mkdir(parents=True)
            (kb_root / "entities").mkdir(parents=True)
            (kb_root / "topics").mkdir(parents=True)

            (kb_root / "system" / "manifest.md").write_text("manifest alpha", encoding="utf-8")
            (kb_root / "entities" / "z.md").write_text("alpha entity", encoding="utf-8")
            (kb_root / "topics" / "a.md").write_text("alpha topic", encoding="utf-8")

            result = query_kb(kb_root=kb_root, query="alpha", limits=ReaderLimits(max_files=10, max_chars=10000))

            returned_paths = [Path(match.file_path).name for match in result.returned_files]
            self.assertEqual(returned_paths[0], "manifest.md")
            self.assertEqual(returned_paths, ["manifest.md", "z.md", "a.md"])

    def test_max_chars_stops_before_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_root = Path(temp_dir)
            (kb_root / "system").mkdir(parents=True)
            (kb_root / "system" / "manifest.md").write_text("x" * 50, encoding="utf-8")
            (kb_root / "system" / "extra.md").write_text("y" * 50, encoding="utf-8")

            result = query_kb(kb_root=kb_root, query="", limits=ReaderLimits(max_files=10, max_chars=60))
            self.assertEqual(len(result.returned_files), 1)
            self.assertTrue(result.returned_files[0].file_path.endswith("manifest.md"))


if __name__ == "__main__":
    unittest.main()
