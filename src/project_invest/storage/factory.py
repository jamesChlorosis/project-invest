from __future__ import annotations

from project_invest.config import Settings
from project_invest.storage.cache import RedisJsonCache
from project_invest.storage.cached import CachedResearchStorage
from project_invest.storage.data_lake import LocalDataLake
from project_invest.storage.postgres import PostgresResearchStorage
from project_invest.storage.repositories import ResearchStorage


def build_storage(settings: Settings) -> ResearchStorage:
    if settings.storage_backend == "postgres":
        if not settings.postgres_dsn:
            raise RuntimeError(
                "PROJECT_INVEST_STORAGE_BACKEND is 'postgres' but PROJECT_INVEST_POSTGRES_DSN is not set."
            )
        durable_storage: ResearchStorage = PostgresResearchStorage(
            dsn=settings.postgres_dsn,
            schema=settings.postgres_schema,
        )
    else:
        durable_storage = LocalDataLake(settings.data_root)

    if settings.storage_cache_enabled and settings.redis_url:
        cache = RedisJsonCache(
            url=settings.redis_url,
            prefix=settings.redis_key_prefix,
            default_ttl_seconds=settings.redis_default_ttl_seconds,
        )
        return CachedResearchStorage(durable_storage, cache)

    return durable_storage
