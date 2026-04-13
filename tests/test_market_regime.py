from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle, MarketRegime
from project_invest.services.market_regime import MarketRegimeDetector


def make_candles(count: int, step: float, volatility: float = 0.0) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    price = 100.0
    for index in range(count):
        noise = ((-1) ** index) * volatility
        close = price + step + noise
        candles.append(
            Candle(
                symbol="TEST",
                timestamp=start + timedelta(days=index),
                open=price,
                high=max(price, close) + 0.5,
                low=min(price, close) - 0.5,
                close=close,
                volume=1000 + index,
            )
        )
        price = close
    return candles


def test_detects_trending_regime() -> None:
    detector = MarketRegimeDetector(trend_threshold=0.02, high_vol_threshold=0.5, low_vol_threshold=0.0)
    regime = detector.detect(make_candles(100, step=0.6))
    assert regime == MarketRegime.TRENDING


def test_detects_high_vol_regime() -> None:
    detector = MarketRegimeDetector(trend_threshold=1.0, high_vol_threshold=0.02, low_vol_threshold=0.0)
    regime = detector.detect(make_candles(100, step=0.0, volatility=3.0))
    assert regime == MarketRegime.HIGH_VOL
