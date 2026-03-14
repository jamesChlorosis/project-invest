from __future__ import annotations

import json
from typing import Any, Protocol


class JsonCache(Protocol):
    backend_name: str

    def get(self, key: str) -> Any | None:
        """Return cached JSON-decoded data if present."""

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store JSON-serializable data."""

    def delete(self, key: str) -> None:
        """Delete a cached key if it exists."""

    def close(self) -> None:
        """Release any resources held by the cache backend."""


class NullJsonCache:
    backend_name = "none"

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def close(self) -> None:
        return None


class RedisJsonCache:
    backend_name = "redis"

    def __init__(self, url: str, prefix: str = "project_invest", default_ttl_seconds: int | None = 900) -> None:
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError(
                "Redis cache selected but the 'redis' package is not installed. "
                "Install project dependencies or disable storage caching."
            ) from exc

        self.client = Redis.from_url(url, decode_responses=True)
        self.prefix = prefix
        self.default_ttl_seconds = default_ttl_seconds

    def _format_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Any | None:
        payload = self.client.get(self._format_key(key))
        if payload is None:
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        payload = json.dumps(value)
        if ttl is None:
            self.client.set(self._format_key(key), payload)
            return
        self.client.set(self._format_key(key), payload, ex=ttl)

    def delete(self, key: str) -> None:
        self.client.delete(self._format_key(key))

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()
