"""Lifecycle manager for ingestion and sync services."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

from llm_kb.models import utc_now_iso


@dataclass
class ManagedService:
    """State for a managed background service."""

    name: str
    status: str = "stopped"
    updated_at: str = utc_now_iso()


class LifecycleService:
    """Simple lifecycle state machine.

    Intent: provide start/stop/restart semantics before adding process supervisor.
    """

    def __init__(self) -> None:
        self._services: Dict[str, ManagedService] = {
            "ingestion-worker": ManagedService(name="ingestion-worker"),
            "sync-scheduler": ManagedService(name="sync-scheduler"),
        }

    def _set(self, service_name: str, status: str) -> ManagedService:
        if service_name not in self._services:
            raise ValueError(f"Unknown service: {service_name}")
        service = self._services[service_name]
        service.status = status
        service.updated_at = utc_now_iso()
        return service

    def start(self, service_name: str) -> ManagedService:
        return self._set(service_name, "running")

    def stop(self, service_name: str) -> ManagedService:
        return self._set(service_name, "stopped")

    def restart(self, service_name: str) -> ManagedService:
        return self._set(service_name, "running")

    def status(self) -> Dict[str, dict]:
        return {name: asdict(service) for name, service in sorted(self._services.items())}
