from __future__ import annotations

from dataclasses import dataclass

from project_invest.domain.models import (
    ExecutionOrder,
    OrderStatus,
    ResearchEvent,
    SignalAction,
    StrategyFamily,
    TradeMemoryOutcome,
    TradeMemoryRecord,
    TradeMemoryStatus,
)
from project_invest.services.universe import market_for_symbol
from project_invest.storage.repositories import TradeMemoryRepository


@dataclass(frozen=True)
class SentimentMemoryEdge:
    scope: str
    bucket: str
    sample_size: int
    win_rate: float
    avg_return_pct: float
    avg_pnl: float


class TradeMemoryService:
    def __init__(self, repository: TradeMemoryRepository) -> None:
        self.repository = repository

    def capture(self, event: ResearchEvent, order: ExecutionOrder) -> TradeMemoryRecord | None:
        if order.status != OrderStatus.FILLED:
            return None
        if order.action == SignalAction.BUY:
            record = self._build_entry_record(event, order)
            self.repository.save_trade_memory(record)
            return record
        if order.action == SignalAction.SELL:
            record = self._close_existing_record(event, order)
            if record is not None:
                self.repository.save_trade_memory(record)
            return record
        return None

    def evaluate_sentiment_edge(
        self,
        symbol: str,
        strategy_family: StrategyFamily | None,
        sentiment_score: float | None,
        news_intensity: float | None,
        lookback: int = 500,
        min_records: int = 4,
    ) -> SentimentMemoryEdge | None:
        bucket = self._sentiment_bucket(sentiment_score, news_intensity)
        if bucket == "neutral" or strategy_family is None:
            return None

        closed_records = [
            record
            for record in self.repository.load_trade_memory(limit=lookback)
            if record.status == TradeMemoryStatus.CLOSED
            and record.strategy_family == strategy_family
            and self._sentiment_bucket(record.sentiment_score, record.news_intensity) == bucket
            and record.return_pct is not None
        ]
        if not closed_records:
            return None

        symbol_records = [record for record in closed_records if record.symbol == symbol]
        if len(symbol_records) >= min_records:
            return self._build_edge("symbol", bucket, symbol_records)

        if len(closed_records) >= min_records:
            return self._build_edge("family", bucket, closed_records)

        return None

    def _build_entry_record(self, event: ResearchEvent, order: ExecutionOrder) -> TradeMemoryRecord:
        return TradeMemoryRecord(
            symbol=event.symbol,
            market=market_for_symbol(event.symbol),
            strategy_id=event.strategy_id,
            strategy_family=event.strategy_family,
            entry_trade_id=order.trade_id,
            opened_at=order.timestamp,
            quantity=order.quantity,
            entry_price=order.fill_price,
            entry_fee=order.fee_paid,
            entry_confidence=event.signal_confidence,
            entry_reason=event.signal_reason,
            entry_note=event.order_note,
            entry_regime=event.regime,
            meta_reason=event.meta_reason,
            timeframe_alignment=event.timeframe_alignment,
            rsi_14=event.rsi_14,
            momentum_5=event.momentum_5,
            volatility_10=event.volatility_10,
            sma_20=event.sma_20,
            ema_12=event.ema_12,
            sentiment_score=event.sentiment_score,
            news_intensity=event.news_intensity,
        )

    def _close_existing_record(self, event: ResearchEvent, order: ExecutionOrder) -> TradeMemoryRecord | None:
        open_record = self.repository.load_open_trade_memory(event.symbol)
        if open_record is None:
            return None

        entry_notional = open_record.entry_price * max(open_record.quantity, 1)
        return_pct = (order.realized_pnl / entry_notional) * 100 if entry_notional else None
        outcome = TradeMemoryOutcome.FLAT
        success_label = 0
        if order.realized_pnl > 0:
            outcome = TradeMemoryOutcome.WIN
            success_label = 1
        elif order.realized_pnl < 0:
            outcome = TradeMemoryOutcome.LOSS

        holding_minutes = max(0.0, (order.timestamp - open_record.opened_at).total_seconds() / 60)

        return open_record.model_copy(
            update={
                "exit_trade_id": order.trade_id,
                "status": TradeMemoryStatus.CLOSED,
                "outcome": outcome,
                "closed_at": order.timestamp,
                "holding_minutes": round(holding_minutes, 2),
                "exit_price": order.fill_price,
                "exit_fee": order.fee_paid,
                "realized_pnl": round(order.realized_pnl, 4),
                "return_pct": round(return_pct, 4) if return_pct is not None else None,
                "success_label": success_label,
                "close_confidence": event.signal_confidence,
                "close_reason": event.signal_reason,
                "close_note": event.order_note,
                "close_regime": event.regime,
            }
        )

    def _sentiment_bucket(self, score: float | None, intensity: float | None) -> str:
        if score is None or intensity is None:
            return "neutral"
        weighted = max(-1.0, min(1.0, score)) * max(0.0, min(1.0, intensity))
        if weighted >= 0.12:
            return "positive"
        if weighted <= -0.12:
            return "negative"
        return "neutral"

    def _build_edge(
        self,
        scope: str,
        bucket: str,
        records: list[TradeMemoryRecord],
    ) -> SentimentMemoryEdge:
        wins = sum(1 for record in records if record.outcome == TradeMemoryOutcome.WIN)
        avg_return_pct = sum(record.return_pct or 0.0 for record in records) / len(records)
        avg_pnl = sum(record.realized_pnl for record in records) / len(records)
        return SentimentMemoryEdge(
            scope=scope,
            bucket=bucket,
            sample_size=len(records),
            win_rate=wins / len(records),
            avg_return_pct=avg_return_pct,
            avg_pnl=avg_pnl,
        )
