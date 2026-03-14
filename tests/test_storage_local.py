from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from project_invest.domain.models import (
    BacktestMetrics,
    EvolutionReport,
    ExecutionMode,
    ExecutionOrder,
    FeatureRow,
    OrderStatus,
    PortfolioSnapshot,
    ResearchCycleReport,
    SignalAction,
    StrategyEvaluation,
    StrategyGenome,
    SymbolResearchResult,
    TradeSignal,
)
from project_invest.storage.data_lake import LocalDataLake


def test_local_storage_round_trips_core_datasets(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")

    feature = FeatureRow(
        symbol="RELIANCE.NS",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        close=2500.0,
        sma_5=2495.0,
    )
    storage.store_features("RELIANCE.NS", "1d", [feature])
    loaded_features = storage.load_features("RELIANCE.NS", "1d")
    assert loaded_features[0].symbol == "RELIANCE.NS"

    portfolio = PortfolioSnapshot.bootstrap(100000.0)
    storage.save_portfolio(portfolio)
    assert storage.load_portfolio() is not None

    order = ExecutionOrder(
        mode=ExecutionMode.PAPER,
        symbol="RELIANCE.NS",
        action=SignalAction.BUY,
        status=OrderStatus.FILLED,
        quantity=2,
        requested_price=2500.0,
        fill_price=2501.0,
        fee_paid=3.0,
        note="Filled in paper mode.",
        strategy_id="strat-demo",
    )
    storage.append_trade(order)
    trades = storage.load_trades()
    assert len(trades) == 1
    assert trades[0].symbol == "RELIANCE.NS"

    metrics = BacktestMetrics(
        total_return=0.1,
        sharpe_ratio=1.2,
        max_drawdown=0.05,
        win_rate=0.6,
        profit_factor=1.5,
        trades=4,
        final_equity=110000.0,
    )
    evaluation = StrategyEvaluation(
        genome=StrategyGenome(strategy_id="strat-demo"),
        metrics=metrics,
        score=1.0,
    )
    report = ResearchCycleReport(
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc),
        provider="mock",
        interval="1d",
        symbols=["RELIANCE.NS"],
        results=[
            SymbolResearchResult(
                symbol="RELIANCE.NS",
                candles_collected=120,
                feature_rows=120,
                evolution=EvolutionReport(
                    symbol="RELIANCE.NS",
                    population_size=8,
                    generations=4,
                    champion=evaluation,
                    leaderboard=[evaluation],
                    latest_signal=TradeSignal(
                        symbol="RELIANCE.NS",
                        action=SignalAction.BUY,
                        confidence=0.8,
                        reason="Test signal",
                        strategy_id="strat-demo",
                    ),
                ),
                latest_order=order,
            )
        ],
        portfolio=portfolio,
    )
    storage.save_latest_report(report)

    latest = storage.load_latest_report()
    assert latest is not None
    assert latest.provider == "mock"
    assert latest.results[0].latest_order.symbol == "RELIANCE.NS"
