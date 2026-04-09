"""Delta-sync tests for create/update/delete scenarios."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from llm_kb.sync_service import DeltaSyncService


class DeltaSyncServiceTests(unittest.TestCase):
    def test_create_update_delete_flow(self) -> None:
        """Validate delta sync handles create/update/delete deterministically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            kb_root = workspace / "LLM_KB"
            kb_root.mkdir(parents=True)
            db_path = workspace / "llm_kb.sqlite3"

            schema_sql = Path("db/schema.sql").read_text(encoding="utf-8")
            with sqlite3.connect(db_path) as connection:
                connection.executescript(schema_sql)
                connection.commit()

            file_path = kb_root / "notes" / "a.md"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("alpha", encoding="utf-8")

            sync_service = DeltaSyncService(db_path=db_path)

            first = sync_service.run(kb_root=kb_root)
            self.assertEqual(first.changed_files, 1)
            self.assertEqual(first.deleted_files, 0)

            file_path.write_text("alpha-updated", encoding="utf-8")
            second = sync_service.run(kb_root=kb_root)
            self.assertEqual(second.changed_files, 1)
            self.assertEqual(second.deleted_files, 0)

            file_path.unlink()
            third = sync_service.run(kb_root=kb_root)
            self.assertEqual(third.changed_files, 0)
            self.assertEqual(third.deleted_files, 1)


if __name__ == "__main__":
    unittest.main()
