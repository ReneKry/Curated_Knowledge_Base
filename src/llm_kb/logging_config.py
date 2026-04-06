"""Central logging setup used by API, CLI, and workers."""

from __future__ import annotations

import logging



def configure_logging(log_level: str) -> None:
    """Configure process-wide logging once with an explicit format."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
