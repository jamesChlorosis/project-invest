from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle, SignalAction, TradeSignal
from project_invest.services.multi_timeframe import MultiTimeframeGate


def make_candles(symbol: str, closes: list[float]) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        previous_close = closes[index - 1] if index > 0 else close
        candles.append(
            Candle(
                symbol=symbol,
                timestamp=start + timedelta(hours=index),
                open=previous_close,
                high=max(close, previous_close) * 1.01,
                low=min(close, previous_close) * 0.99,
                close=close,
                volume=10_000.0,
            )
        )
    return candles


def test_multitimeframe_gate_blocks_buy_on_downtrend() -> None:
    gate = MultiTimeframeGate(intervals=["1h"], short_window=3, long_window=6, min_trend_strength=0.001)
    downtrend = make_candles("TEST", [105, 104, 103, 102, 101, 100, 99])
    signal = TradeSignal(
        symbol="TEST",
        action=SignalAction.BUY,
        confidence=0.6,
        reason="Candidate entry",
        strategy_id="strat-test",
    )

    gated_signal, alignments = gate.apply(signal, {"1h": downtrend})

    assert alignments[0].direction == "down"
    assert gated_signal.action == SignalAction.HOLD


def test_multitimeframe_gate_allows_buy_on_uptrend() -> None:
    gate = MultiTimeframeGate(intervals=["1h"], short_window=3, long_window=6, min_trend_strength=0.001)
    uptrend = make_candles("TEST", [95, 96, 97, 98, 99, 100, 101])
    signal = TradeSignal(
        symbol="TEST",
        action=SignalAction.BUY,
        confidence=0.6,
        reason="Candidate entry",
        strategy_id="strat-test",
    )

    gated_signal, alignments = gate.apply(signal, {"1h": uptrend})

    assert alignments[0].direction == "up"
    assert gated_signal.action == SignalAction.BUY


def test_multitimeframe_gate_softens_mixed_buy_instead_of_blocking() -> None:
    gate = MultiTimeframeGate(intervals=["30m", "1h"], short_window=3, long_window=6, min_trend_strength=0.001)
    uptrend = make_candles("TEST", [95, 96, 97, 98, 99, 100, 101])
    downtrend = make_candles("TEST", [105, 104, 103, 102, 101, 100, 99])
    signal = TradeSignal(
        symbol="TEST",
        action=SignalAction.BUY,
        confidence=0.6,
        reason="Candidate entry",
        strategy_id="strat-test",
    )

    gated_signal, alignments = gate.apply(signal, {"30m": uptrend, "1h": downtrend})

    assert len(alignments) == 2
    assert gated_signal.action == SignalAction.BUY
    assert gated_signal.confidence < signal.confidence
    assert "reduced confidence" in gated_signal.reason
