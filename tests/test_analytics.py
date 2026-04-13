from __future__ import annotations

from datetime import datetime, timezone

from project_invest.domain.models import (
    MarketRegime,
    StrategyFamily,
    StrategyGenome,
    StrategyRegistryEntry,
    StrategyRegistryStatus,
    TradeMemoryOutcome,
    TradeMemoryRecord,
    TradeMemoryStatus,
)
from project_invest.services.analytics import AnalyticsService
from project_invest.services.portfolio_optimization import PortfolioOptimizer


def test_learning_summary_surfaces_registry_leaders_and_totals() -> None:
    analytics = AnalyticsService(PortfolioOptimizer())
    summary = analytics.build_learning_summary(
        ["RELIANCE.NS", "TCS.NS"],
        {
            "RELIANCE.NS": [
                StrategyRegistryEntry(
                    symbol="RELIANCE.NS",
                    genome=StrategyGenome(strategy_id="strat-rel", family="trend_following"),
                    status=StrategyRegistryStatus.CANDIDATE,
                    last_score=1.8,
                    last_validation_sharpe=0.9,
                    times_selected=4,
                    paper_entry_count=1,
                    paper_exit_count=1,
                    win_count=1,
                    cumulative_realized_pnl=125.5,
                ),
                StrategyRegistryEntry(
                    symbol="RELIANCE.NS",
                    genome=StrategyGenome(strategy_id="strat-old"),
                    status=StrategyRegistryStatus.RETIRED,
                    last_score=0.7,
                ),
            ],
            "TCS.NS": [],
        },
    )

    assert summary["symbols_tracked"] == 2
    assert summary["candidate_strategies"] == 1
    assert summary["retired_strategies"] == 1

    scoreboard = summary["scoreboard"]
    assert scoreboard[0]["symbol"] == "RELIANCE.NS"
    assert scoreboard[0]["strategy_id"] == "strat-rel"
    assert scoreboard[0]["paper_entries"] == 1
    assert scoreboard[0]["realized_pnl"] == 125.5
    assert scoreboard[1]["status"] == "no-registry"


def test_trade_memory_summary_surfaces_patterns_and_win_rate() -> None:
    analytics = AnalyticsService(PortfolioOptimizer())
    summary = analytics.build_trade_memory_summary(
        [
            TradeMemoryRecord(
                symbol="RELIANCE.NS",
                market="NSE",
                strategy_id="strat-a",
                strategy_family=StrategyFamily.MEAN_REVERSION,
                entry_trade_id="order-1",
                exit_trade_id="order-2",
                status=TradeMemoryStatus.CLOSED,
                outcome=TradeMemoryOutcome.WIN,
                opened_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                closed_at=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
                quantity=2,
                entry_price=100.0,
                exit_price=104.0,
                realized_pnl=8.0,
                return_pct=4.0,
                success_label=1,
                entry_regime=MarketRegime.LOW_VOL,
                sentiment_score=0.8,
                news_intensity=0.7,
            ),
            TradeMemoryRecord(
                symbol="TCS.NS",
                market="NSE",
                strategy_id="strat-b",
                strategy_family=StrategyFamily.BREAKOUT,
                entry_trade_id="order-3",
                exit_trade_id="order-4",
                status=TradeMemoryStatus.CLOSED,
                outcome=TradeMemoryOutcome.LOSS,
                opened_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
                closed_at=datetime(2025, 1, 2, 1, 0, tzinfo=timezone.utc),
                quantity=1,
                entry_price=200.0,
                exit_price=196.0,
                realized_pnl=-4.0,
                return_pct=-2.0,
                success_label=0,
                entry_regime=MarketRegime.HIGH_VOL,
                sentiment_score=-0.8,
                news_intensity=0.8,
            ),
        ]
    )

    assert summary["closed_records"] == 2
    assert summary["open_records"] == 0
    assert summary["win_rate"] == 0.5
    assert summary["total_realized_pnl"] == 4.0
    assert summary["best_pattern"]["family"] == "mean_reversion"
    assert summary["worst_pattern"]["family"] == "breakout"
    assert summary["best_sentiment_pattern"]["sentiment_bucket"] == "positive"
    assert summary["worst_sentiment_pattern"]["sentiment_bucket"] == "negative"
