from __future__ import annotations

from datetime import datetime, timezone

from project_invest.domain.models import FeatureRow, SignalAction, TradeSignal
from project_invest.services.sentiment_overlay import SentimentSignalAdjuster


def _feature(score: float, intensity: float) -> FeatureRow:
    return FeatureRow(
        symbol="RELIANCE.NS",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        close=100.0,
        sentiment_score=score,
        news_intensity=intensity,
    )


def test_positive_sentiment_boosts_buy_confidence() -> None:
    adjuster = SentimentSignalAdjuster()
    signal = TradeSignal(
        symbol="RELIANCE.NS",
        action=SignalAction.BUY,
        confidence=0.40,
        reason="Base signal.",
        strategy_id="strat-1",
    )

    adjusted = adjuster.apply(signal, _feature(0.8, 0.7))

    assert adjusted.action == SignalAction.BUY
    assert adjusted.confidence > signal.confidence
    assert "tailwind" in adjusted.reason


def test_strong_negative_sentiment_can_block_buy() -> None:
    adjuster = SentimentSignalAdjuster()
    signal = TradeSignal(
        symbol="RELIANCE.NS",
        action=SignalAction.BUY,
        confidence=0.35,
        reason="Base signal.",
        strategy_id="strat-1",
    )

    adjusted = adjuster.apply(signal, _feature(-0.9, 0.8))

    assert adjusted.action == SignalAction.HOLD
    assert "Blocked by bearish sentiment" in adjusted.reason


def test_negative_sentiment_supports_sell_confidence() -> None:
    adjuster = SentimentSignalAdjuster()
    signal = TradeSignal(
        symbol="RELIANCE.NS",
        action=SignalAction.SELL,
        confidence=0.45,
        reason="Base exit.",
        strategy_id="strat-2",
    )

    adjusted = adjuster.apply(signal, _feature(-0.7, 0.6))

    assert adjusted.action == SignalAction.SELL
    assert adjusted.confidence > signal.confidence
    assert "supports the exit" in adjusted.reason
