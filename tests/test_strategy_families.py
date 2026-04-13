from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle, SignalAction, StrategyFamily, StrategyGenome
from project_invest.services.strategy_signals import StrategySignalEngine


def make_candles(symbol: str, closes: list[float], volumes: list[float] | None = None) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    volume_series = volumes or [10_000.0] * len(closes)

    for index, close in enumerate(closes):
        previous_close = closes[index - 1] if index > 0 else close
        high = max(close, previous_close) * 1.01
        low = min(close, previous_close) * 0.99
        candles.append(
            Candle(
                symbol=symbol,
                timestamp=start + timedelta(days=index),
                open=previous_close,
                high=high,
                low=low,
                close=close,
                volume=volume_series[index],
            )
        )

    return candles


def test_trend_following_family_buys_on_clean_uptrend() -> None:
    signal_engine = StrategySignalEngine()
    candles = make_candles("TREND", [100 + (index * 1.5) for index in range(25)])
    genome = StrategyGenome(
        family=StrategyFamily.TREND_FOLLOWING,
        short_window=5,
        long_window=12,
        momentum_threshold=0.0,
    )

    signal = signal_engine.generate_signal(genome, candles, has_position=False)

    assert signal.action == SignalAction.BUY


def test_mean_reversion_family_buys_after_deep_pullback() -> None:
    signal_engine = StrategySignalEngine()
    closes = [
        100,
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        110,
        111,
        112,
        113,
        114,
        115,
        115,
        115,
        114,
        113,
        111,
        109,
        108,
        107,
    ]
    candles = make_candles("MEAN", closes)
    genome = StrategyGenome(
        family=StrategyFamily.MEAN_REVERSION,
        short_window=5,
        long_window=20,
        mean_reversion_threshold=0.01,
        rsi_entry_threshold=45.0,
        rsi_exit_threshold=58.0,
    )

    signal = signal_engine.generate_signal(genome, candles, has_position=False)

    assert signal.action == SignalAction.BUY


def test_breakout_family_buys_on_volume_confirmed_breakout() -> None:
    signal_engine = StrategySignalEngine()
    closes = [
        100.0,
        100.3,
        99.9,
        100.2,
        100.1,
        100.0,
        100.4,
        100.2,
        99.8,
        100.1,
        100.0,
        100.3,
        100.1,
        100.2,
        100.4,
        100.1,
        100.3,
        100.2,
        100.4,
        100.3,
        103.5,
    ]
    volumes = [10_000.0] * 20 + [24_000.0]
    candles = make_candles("BRK", closes, volumes=volumes)
    genome = StrategyGenome(
        family=StrategyFamily.BREAKOUT,
        short_window=5,
        long_window=12,
        momentum_threshold=0.0,
        breakout_lookback=15,
        breakout_buffer=0.001,
        volume_confirmation=1.2,
    )

    signal = signal_engine.generate_signal(genome, candles, has_position=False)

    assert signal.action == SignalAction.BUY
