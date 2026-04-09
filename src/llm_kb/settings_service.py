"""Client-scoped runtime settings service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from llm_kb.models import RuntimeSetting, utc_now_iso


class RuntimeSettingsService:
    """In-memory settings service for v1 bootstrap.

    Intent: keep implementation simple and swappable with DB-backed storage.
    """

    def __init__(self) -> None:
        self._settings_by_client: Dict[str, RuntimeSetting] = {}
        self._providers: Dict[str, List[str]] = {
            "primary": ["default", "reasoning-small", "reasoning-large"],
            "fallback": ["default", "balanced"],
        }

    def get_or_create(self, client_id: str) -> RuntimeSetting:
        if client_id not in self._settings_by_client:
            self._settings_by_client[client_id] = RuntimeSetting(client_id=client_id)
        return self._settings_by_client[client_id]

    def update(
        self,
        client_id: str,
        provider_name: str,
        model_name: str,
        active_kb_id: str,
        max_files: int,
        max_chars: int,
    ) -> RuntimeSetting:
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        if model_name not in self._providers[provider_name]:
            raise ValueError(f"Unknown model '{model_name}' for provider '{provider_name}'")

        setting = RuntimeSetting(
            client_id=client_id,
            provider_name=provider_name,
            model_name=model_name,
            active_kb_id=active_kb_id,
            max_files=max_files,
            max_chars=max_chars,
            updated_at=utc_now_iso(),
        )
        self._settings_by_client[client_id] = setting
        return setting

    def providers(self) -> List[str]:
        return sorted(self._providers.keys())

    def models_for_provider(self, provider_name: str) -> List[str]:
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return self._providers[provider_name]

    def as_dict(self, client_id: str) -> dict:
        return asdict(self.get_or_create(client_id))
