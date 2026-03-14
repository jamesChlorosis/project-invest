from __future__ import annotations

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
        provider_name = getattr(self.primary_provider, "name", "unknown")
        try:
            candles = await self.primary_provider.fetch_candles(symbol, interval, lookback_bars)
        except MarketDataProviderError:
            if self.fallback_provider is None:
                raise
            provider_name = getattr(self.fallback_provider, "name", "fallback")
            candles = await self.fallback_provider.fetch_candles(symbol, interval, lookback_bars)

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
