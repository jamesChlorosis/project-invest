from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from project_invest.domain.models import Candle
from project_invest.providers.base import MarketDataProviderError


class YahooFinanceProvider:
    name = "yahoo"

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_candles(self, symbol: str, interval: str, lookback_bars: int) -> list[Candle]:
        step = self._interval_to_delta(interval)
        now = datetime.now(timezone.utc)
        period1 = int((now - step * lookback_bars).timestamp())
        period2 = int(now.timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": interval,
            "includePrePost": "false",
            "events": "div,splits",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        chart = payload.get("chart", {})
        error = chart.get("error")
        if error:
            raise MarketDataProviderError(str(error))

        results = chart.get("result") or []
        if not results:
            raise MarketDataProviderError(f"No Yahoo data returned for {symbol}.")

        result = results[0]
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        candles: list[Candle] = []
        for index, ts in enumerate(timestamps):
            try:
                open_price = float(opens[index])
                high_price = float(highs[index])
                low_price = float(lows[index])
                close_price = float(closes[index])
                volume = float(volumes[index] or 0.0)
            except (IndexError, TypeError, ValueError):
                continue

            candles.append(
                Candle(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )

        if not candles:
            raise MarketDataProviderError(f"Yahoo returned only empty bars for {symbol}.")

        return candles[-lookback_bars:]

    def _interval_to_delta(self, interval: str) -> timedelta:
        if interval.endswith("m"):
            return timedelta(minutes=int(interval[:-1]))
        if interval.endswith("h"):
            return timedelta(hours=int(interval[:-1]))
        if interval.endswith("d") and interval[:-1].isdigit():
            return timedelta(days=int(interval[:-1]))
        return timedelta(days=1)

