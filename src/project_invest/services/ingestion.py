from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle
from project_invest.providers.base import MarketDataProvider, MarketDataProviderError
from project_invest.storage.repositories import CandleRepository


class MarketDataIngestionService:
    def __init__(
        self,
        primary_provider: MarketDataProvider,
        candle_repository: CandleRepository,
        fallback_provider: MarketDataProvider | None = None,
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.candle_repository = candle_repository

    async def ingest_symbol(self, symbol: str, interval: str, lookback_bars: int) -> tuple[str, list[Candle]]:
        cached_candles = self._load_cached_candles(symbol, interval, lookback_bars)
        if self._cache_is_fresh(cached_candles, interval):
            return "cache", cached_candles[-lookback_bars:]

        provider_name = getattr(self.primary_provider, "name", "unknown")
        try:
            candles = await self.primary_provider.fetch_candles(symbol, interval, lookback_bars)
        except MarketDataProviderError as primary_error:
            if cached_candles:
                return "cache", cached_candles[-lookback_bars:]

            if self.fallback_provider is None:
                raise MarketDataProviderError(
                    f"{symbol} {interval}: {primary_error}"
                ) from primary_error
            provider_name = getattr(self.fallback_provider, "name", "fallback")
            try:
                candles = await self.fallback_provider.fetch_candles(symbol, interval, lookback_bars)
            except MarketDataProviderError as fallback_error:
                raise MarketDataProviderError(
                    f"{symbol} {interval}: primary provider failed ({primary_error}); "
                    f"fallback provider failed ({fallback_error})"
                ) from fallback_error

        normalized = self._normalize(candles)
        self.candle_repository.store_candles(symbol, interval, normalized, stage="raw")
        self.candle_repository.store_candles(symbol, interval, normalized, stage="processed")
        return provider_name, normalized

    def _normalize(self, candles: list[Candle]) -> list[Candle]:
        deduped: dict[str, Candle] = {}
        for candle in candles:
            if candle.close <= 0:
                continue
            normalized = candle.model_copy(
                update={
                    "high": max(candle.high, candle.open, candle.close),
                    "low": min(candle.low, candle.open, candle.close),
                    "volume": max(candle.volume, 0.0),
                }
            )
            deduped[normalized.timestamp.isoformat()] = normalized
        return sorted(deduped.values(), key=lambda item: item.timestamp)

    def _load_cached_candles(self, symbol: str, interval: str, lookback_bars: int) -> list[Candle]:
        processed = self.candle_repository.load_candles(symbol, interval, stage="processed")
        if processed:
            normalized = self._normalize(processed)
            return normalized[-lookback_bars:]

        raw = self.candle_repository.load_candles(symbol, interval, stage="raw")
        if raw:
            normalized = self._normalize(raw)
            return normalized[-lookback_bars:]
        return []

    def _cache_is_fresh(self, candles: list[Candle], interval: str) -> bool:
        if not candles:
            return False

        last_timestamp = candles[-1].timestamp
        max_age = self._interval_to_timedelta(interval) * 1.15
        max_age = max(max_age, timedelta(minutes=1))
        return datetime.now(timezone.utc) - last_timestamp <= max_age

    def _interval_to_timedelta(self, interval: str) -> timedelta:
        if interval.endswith("m") and interval[:-1].isdigit():
            return timedelta(minutes=max(1, int(interval[:-1])))
        if interval.endswith("h") and interval[:-1].isdigit():
            return timedelta(hours=max(1, int(interval[:-1])))
        if interval.endswith("d") and interval[:-1].isdigit():
            return timedelta(days=max(1, int(interval[:-1])))
        return timedelta(minutes=5)
