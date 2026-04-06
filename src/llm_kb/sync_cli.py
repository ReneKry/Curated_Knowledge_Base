"""CLI entry point for delta sync."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm_kb.config import load_runtime_config
from llm_kb.logging_config import configure_logging
from llm_kb.sync_service import DeltaSyncService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run delta sync for markdown KB")
    parser.add_argument("--kb-root", required=False, default=None, help="Path to the KB root")
    parser.add_argument("--db-path", required=False, default=None, help="Path to SQLite database file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_runtime_config()
    configure_logging(config.log_level)

    kb_root = Path(args.kb_root) if args.kb_root else config.kb_root
    db_path = Path(args.db_path) if args.db_path else config.database_path

    service = DeltaSyncService(db_path=db_path)
    summary = service.run(kb_root=kb_root)
    print(
        f"run_id={summary.run_id} changed_files={summary.changed_files} deleted_files={summary.deleted_files}"
    )


if __name__ == "__main__":
    main()
