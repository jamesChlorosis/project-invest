from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from project_invest.domain.models import Candle
from project_invest.providers.base import MarketDataProviderError
from project_invest.services.ingestion import MarketDataIngestionService
from project_invest.storage.data_lake import LocalDataLake


class _ProviderSpy:
    name = "spy"

    def __init__(self, candles: list[Candle] | None = None, error: Exception | None = None) -> None:
        self.candles = candles or []
        self.error = error
        self.calls = 0

    async def fetch_candles(self, symbol: str, interval: str, lookback_bars: int) -> list[Candle]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.candles


def _candle(symbol: str, minutes_ago: int) -> Candle:
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return Candle(
        symbol=symbol,
        timestamp=ts,
        open=100.0,
        high=101.0,
        low=99.5,
        close=100.5,
        volume=1200.0,
    )


def test_ingestion_uses_fresh_cache_before_calling_provider(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    cached = [_candle("RELIANCE.NS", minutes_ago=2)]
    storage.store_candles("RELIANCE.NS", "5m", cached, stage="processed")
    provider = _ProviderSpy(error=AssertionError("provider should not be called when cache is fresh"))
    service = MarketDataIngestionService(provider, storage)

    provider_name, candles = asyncio.run(service.ingest_symbol("RELIANCE.NS", "5m", 20))

    assert provider_name == "cache"
    assert provider.calls == 0
    assert len(candles) == 1
    assert candles[0].symbol == "RELIANCE.NS"


def test_ingestion_falls_back_to_cache_when_provider_fails(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    stale_cached = [_candle("TCS.NS", minutes_ago=55)]
    storage.store_candles("TCS.NS", "5m", stale_cached, stage="processed")
    provider = _ProviderSpy(error=MarketDataProviderError("Yahoo request failed with status 429"))
    service = MarketDataIngestionService(provider, storage)

    provider_name, candles = asyncio.run(service.ingest_symbol("TCS.NS", "5m", 20))

    assert provider_name == "cache"
    assert provider.calls == 1
    assert len(candles) == 1
    assert candles[0].symbol == "TCS.NS"
