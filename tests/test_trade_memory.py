from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from project_invest.domain.models import (
    ExecutionMode,
    ExecutionOrder,
    MarketRegime,
    OrderStatus,
    ResearchEvent,
    SignalAction,
    StrategyFamily,
    TradeMemoryOutcome,
    TradeMemoryRecord,
    TradeMemoryStatus,
)
from project_invest.services.trade_memory import TradeMemoryService
from project_invest.storage.data_lake import LocalDataLake


def test_trade_memory_captures_entry_and_exit(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    service = TradeMemoryService(storage)

    entry_order = ExecutionOrder(
        trade_id="order-buy",
        mode=ExecutionMode.PAPER,
        symbol="RELIANCE.NS",
        action=SignalAction.BUY,
        status=OrderStatus.FILLED,
        quantity=3,
        requested_price=2500.0,
        fill_price=2502.0,
        fee_paid=2.5,
        note="Approved.",
        strategy_id="strat-demo",
        timestamp=datetime(2025, 1, 1, 9, 15, tzinfo=timezone.utc),
    )
    entry_event = ResearchEvent(
        symbol="RELIANCE.NS",
        strategy_id="strat-demo",
        regime=MarketRegime.LOW_VOL,
        strategy_family=StrategyFamily.MEAN_REVERSION,
        signal_action=SignalAction.BUY,
        signal_confidence=0.61,
        signal_reason="Dip in uptrend.",
        order_action=SignalAction.BUY,
        order_status=OrderStatus.FILLED,
        order_note="Approved.",
        price=2500.0,
        rsi_14=31.2,
    )

    open_record = service.capture(entry_event, entry_order)
    assert open_record is not None
    assert open_record.status == TradeMemoryStatus.OPEN
    assert open_record.entry_trade_id == "order-buy"

    exit_order = ExecutionOrder(
        trade_id="order-sell",
        mode=ExecutionMode.PAPER,
        symbol="RELIANCE.NS",
        action=SignalAction.SELL,
        status=OrderStatus.FILLED,
        quantity=3,
        requested_price=2520.0,
        fill_price=2518.0,
        fee_paid=2.4,
        realized_pnl=45.6,
        note="Position closed.",
        strategy_id="strat-demo",
        timestamp=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    exit_event = ResearchEvent(
        symbol="RELIANCE.NS",
        strategy_id="strat-demo",
        regime=MarketRegime.TRENDING,
        strategy_family=StrategyFamily.MEAN_REVERSION,
        signal_action=SignalAction.SELL,
        signal_confidence=0.58,
        signal_reason="Target reached.",
        order_action=SignalAction.SELL,
        order_status=OrderStatus.FILLED,
        order_note="Position closed.",
        price=2520.0,
    )

    closed_record = service.capture(exit_event, exit_order)
    assert closed_record is not None
    assert closed_record.status == TradeMemoryStatus.CLOSED
    assert closed_record.outcome == TradeMemoryOutcome.WIN
    assert closed_record.success_label == 1
    assert closed_record.exit_trade_id == "order-sell"
    assert closed_record.realized_pnl == 45.6
    assert closed_record.holding_minutes == 45.0
    assert storage.load_open_trade_memory("RELIANCE.NS") is None


def test_trade_memory_builds_sentiment_edge_from_closed_records(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    service = TradeMemoryService(storage)

    for index, pnl in enumerate([12.0, 8.0, -3.0, 5.0], start=1):
        storage.save_trade_memory(
            TradeMemoryRecord(
                symbol="RELIANCE.NS",
                market="NSE",
                strategy_id=f"strat-{index}",
                strategy_family=StrategyFamily.MEAN_REVERSION,
                entry_trade_id=f"entry-{index}",
                exit_trade_id=f"exit-{index}",
                status=TradeMemoryStatus.CLOSED,
                outcome=TradeMemoryOutcome.WIN if pnl > 0 else TradeMemoryOutcome.LOSS,
                opened_at=datetime(2025, 1, index, tzinfo=timezone.utc),
                closed_at=datetime(2025, 1, index, 1, 0, tzinfo=timezone.utc),
                quantity=1,
                entry_price=100.0,
                exit_price=101.0,
                realized_pnl=pnl,
                return_pct=pnl / 100,
                success_label=1 if pnl > 0 else 0,
                sentiment_score=0.8,
                news_intensity=0.7,
            )
        )

    edge = service.evaluate_sentiment_edge(
        symbol="RELIANCE.NS",
        strategy_family=StrategyFamily.MEAN_REVERSION,
        sentiment_score=0.7,
        news_intensity=0.8,
        lookback=20,
        min_records=3,
    )

    assert edge is not None
    assert edge.scope == "symbol"
    assert edge.bucket == "positive"
    assert edge.sample_size == 4
    assert edge.win_rate == 0.75
