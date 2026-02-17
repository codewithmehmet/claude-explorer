"""In-memory data cache to avoid re-parsing on every screen switch."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .models import DailyStats, Plan, Project, Prompt, Session
from . import parsers


@dataclass
class CacheEntry:
    data: Any = None
    timestamp: float = 0.0
    ttl: float = 300.0  # 5 minutes default

    @property
    def is_valid(self) -> bool:
        return self.data is not None and (time.time() - self.timestamp) < self.ttl


class DataCache:
    """Singleton cache for all parsed .claude data."""

    _instance: DataCache | None = None

    def __new__(cls) -> DataCache:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._entries = {}
        return cls._instance

    def _get_or_load(self, key: str, loader, ttl: float = 300.0):
        entry = self._entries.get(key)
        if entry and entry.is_valid:
            return entry.data
        data = loader()
        self._entries[key] = CacheEntry(data=data, timestamp=time.time(), ttl=ttl)
        return data

    def history(self) -> list[Prompt]:
        return self._get_or_load("history", parsers.parse_history)

    def stats(self) -> list[DailyStats]:
        return self._get_or_load("stats", parsers.parse_stats)

    def projects(self) -> list[Project]:
        return self._get_or_load("projects", parsers.discover_projects)

    def sessions(self) -> list[Session]:
        return self._get_or_load("sessions", parsers.discover_all_sessions)

    def plans(self) -> list[Plan]:
        return self._get_or_load("plans", parsers.parse_plans)

    def global_stats(self) -> dict:
        return self._get_or_load("global_stats", parsers.get_global_stats)

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate a specific key or all cache entries."""
        if key:
            self._entries.pop(key, None)
        else:
            self._entries.clear()

    def invalidate_all(self) -> None:
        self._entries.clear()
