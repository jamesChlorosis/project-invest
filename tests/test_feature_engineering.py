from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle
from project_invest.services.feature_engineering import FeatureEngineeringEngine


def make_candles(count: int, base_price: float = 100.0) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    price = base_price
    for index in range(count):
        close = price + 1.5 + (index % 3)
        candles.append(
            Candle(
                symbol="TEST",
                timestamp=start + timedelta(days=index),
                open=price,
                high=close + 1,
                low=price - 1,
                close=close,
                volume=1000 + (index * 25),
            )
        )
        price = close
    return candles


def test_feature_engine_builds_expected_indicators() -> None:
    engine = FeatureEngineeringEngine()
    rows = engine.build_feature_rows(make_candles(30))

    assert len(rows) == 30
    assert rows[-1].sma_5 is not None
    assert rows[-1].sma_20 is not None
    assert rows[-1].ema_12 is not None
    assert rows[-1].ema_26 is not None
    assert rows[-1].rsi_14 is not None
    assert rows[-1].momentum_5 is not None
    assert rows[-1].volatility_10 is not None
    assert rows[-1].volume_zscore_20 is not None

