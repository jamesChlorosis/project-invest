from __future__ import annotations

from statistics import mean, pstdev

from project_invest.domain.models import Candle, MarketRegime


class MarketRegimeDetector:
    def __init__(
        self,
        trend_threshold: float = 0.012,
        high_vol_threshold: float = 0.02,
        low_vol_threshold: float = 0.004,
        lookback: int = 80,
    ) -> None:
        self.trend_threshold = trend_threshold
        self.high_vol_threshold = high_vol_threshold
        self.low_vol_threshold = low_vol_threshold
        self.lookback = max(20, lookback)

    def detect(self, candles: list[Candle]) -> MarketRegime:
        if len(candles) < 20:
            return MarketRegime.SIDEWAYS

        window = candles[-self.lookback :]
        closes = [candle.close for candle in window]
        returns = self._returns(closes)

        if returns:
            vol = pstdev(returns)
        else:
            vol = 0.0

        trend_strength = self._trend_strength(closes)

        if vol >= self.high_vol_threshold:
            return MarketRegime.HIGH_VOL
        if vol <= self.low_vol_threshold:
            return MarketRegime.LOW_VOL
        if abs(trend_strength) >= self.trend_threshold:
            return MarketRegime.TRENDING
        return MarketRegime.SIDEWAYS

    def _returns(self, closes: list[float]) -> list[float]:
        returns: list[float] = []
        for prev, current in zip(closes, closes[1:]):
            if prev <= 0:
                continue
            returns.append((current - prev) / prev)
        return returns

    def _trend_strength(self, closes: list[float]) -> float:
        if len(closes) < 2:
            return 0.0
        start = closes[0]
        end = closes[-1]
        if start <= 0:
            return 0.0
        return (end - start) / start
