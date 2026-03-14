from __future__ import annotations

from typing import Protocol

from project_invest.domain.models import Candle


class MarketDataProviderError(RuntimeError):
    """Raised when a provider cannot supply market data."""


class MarketDataProvider(Protocol):
    name: str

    async def fetch_candles(self, symbol: str, interval: str, lookback_bars: int) -> list[Candle]:
        """Fetch normalized candles for the requested symbol."""

