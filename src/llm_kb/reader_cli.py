"""CLI for deterministic KB query operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_kb.config import load_runtime_config
from llm_kb.logging_config import configure_logging
from llm_kb.models import ReaderLimits
from llm_kb.reader import query_kb, result_as_json_dict



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic markdown KB reader")
    parser.add_argument("--query", default="", help="Search query")
    parser.add_argument("--kb-root", default=None, help="KB root path")
    parser.add_argument("--max-files", type=int, default=None, help="Maximum number of returned files")
    parser.add_argument("--max-chars", type=int, default=None, help="Maximum total characters in output")
    parser.add_argument("--format", choices=["text", "json"], default="json", help="Output format")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    config = load_runtime_config()
    configure_logging(config.log_level)

    kb_root = Path(args.kb_root) if args.kb_root else config.kb_root
    limits = ReaderLimits(
        max_files=args.max_files if args.max_files is not None else config.default_max_files,
        max_chars=args.max_chars if args.max_chars is not None else config.default_max_chars,
    )
    result = query_kb(kb_root=kb_root, query=args.query, limits=limits)

    if args.format == "json":
        print(json.dumps(result_as_json_dict(result), ensure_ascii=False, indent=2))
        return

    for match in result.returned_files:
        print(f"# {match.file_path}")
        print(match.content)
        print()


if __name__ == "__main__":
    main()
