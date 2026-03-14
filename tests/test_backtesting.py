from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project_invest.domain.models import Candle, StrategyGenome
from project_invest.services.backtesting import BacktestingEngine
from project_invest.services.strategy_signals import StrategySignalEngine


def make_trending_candles(count: int) -> list[Candle]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[Candle] = []
    price = 100.0
    for index in range(count):
        close = price * 1.01
        candles.append(
            Candle(
                symbol="TREND",
                timestamp=start + timedelta(days=index),
                open=price,
                high=close * 1.01,
                low=price * 0.995,
                close=close,
                volume=10_000 + index,
            )
        )
        price = close
    return candles


def test_backtester_finds_positive_result_on_clean_trend() -> None:
    signal_engine = StrategySignalEngine()
    backtester = BacktestingEngine(
        signal_engine=signal_engine,
        slippage_bps=0,
        fee_bps=0,
        max_risk_per_trade=0.05,
    )
    genome = StrategyGenome(
        short_window=3,
        long_window=8,
        momentum_threshold=0.0,
        stop_loss_pct=0.02,
        take_profit_pct=0.2,
        risk_fraction=0.25,
    )

    result = backtester.run("TREND", make_trending_candles(40), genome, initial_capital=100000.0)

    assert result.metrics.trades >= 1
    assert result.metrics.final_equity >= 100000.0
    assert result.metrics.total_return >= 0

