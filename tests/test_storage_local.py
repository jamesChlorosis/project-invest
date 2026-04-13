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
    ResearchEvent,
    SignalAction,
    StrategyEvaluation,
    StrategyGenome,
    StrategyRegistryEntry,
    StrategyRegistryStatus,
    SymbolResearchResult,
    TradeMemoryRecord,
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

    genome = StrategyGenome(strategy_id="strat-demo", short_window=5, long_window=21)
    storage.save_active_strategy("RELIANCE.NS", genome)
    loaded_genome = storage.load_active_strategy("RELIANCE.NS")
    assert loaded_genome is not None
    assert loaded_genome.strategy_id == "strat-demo"
    storage.delete_active_strategy("RELIANCE.NS")
    assert storage.load_active_strategy("RELIANCE.NS") is None

    registry_entry = StrategyRegistryEntry(
        symbol="RELIANCE.NS",
        genome=genome,
        status=StrategyRegistryStatus.ACTIVE,
        last_score=1.8,
        last_validation_sharpe=1.2,
        paper_entry_count=1,
    )
    storage.save_strategy_registry("RELIANCE.NS", [registry_entry])
    loaded_registry = storage.load_strategy_registry("RELIANCE.NS")
    assert len(loaded_registry) == 1
    assert loaded_registry[0].status == StrategyRegistryStatus.ACTIVE

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

    event = ResearchEvent(
        symbol="RELIANCE.NS",
        strategy_id="strat-demo",
        signal_action=SignalAction.BUY,
        signal_confidence=0.55,
        signal_reason="Test",
        order_action=SignalAction.BUY,
        order_status=OrderStatus.FILLED,
        price=2500.0,
    )
    storage.append_event(event)
    events = storage.load_events()
    assert events
    assert events[0].symbol == "RELIANCE.NS"

    memory = TradeMemoryRecord(
        symbol="RELIANCE.NS",
        market="NSE",
        strategy_id="strat-demo",
        entry_trade_id="order-demo",
        opened_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        quantity=2,
        entry_price=2501.0,
    )
    storage.save_trade_memory(memory)
    loaded_memory = storage.load_trade_memory()
    assert len(loaded_memory) == 1
    assert loaded_memory[0].symbol == "RELIANCE.NS"
    assert storage.load_open_trade_memory("RELIANCE.NS") is not None


def test_local_storage_recovers_from_trailing_json_garbage(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    event = ResearchEvent(
        symbol="RELIANCE.NS",
        strategy_id="strat-demo",
        signal_action=SignalAction.BUY,
        signal_confidence=0.55,
        signal_reason="Test",
        order_action=SignalAction.BUY,
        order_status=OrderStatus.FILLED,
        price=2500.0,
    )
    storage.append_event(event)
    events_path = tmp_path / "lake" / "events" / "events.json"
    events_path.write_text(events_path.read_text(encoding="utf-8") + 'broken-tail', encoding="utf-8")

    events = storage.load_events()

    assert len(events) == 1
    assert events[0].symbol == "RELIANCE.NS"


def test_local_storage_treats_empty_event_history_as_empty_list(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    events_path = tmp_path / "lake" / "events" / "events.json"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    events = storage.load_events()

    assert events == []


def test_local_storage_treats_null_byte_event_history_as_empty_list(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    events_path = tmp_path / "lake" / "events" / "events.json"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_bytes(b"\x00" * 128)

    events = storage.load_events()

    assert events == []


def test_local_storage_keeps_research_and_trading_latest_reports_separate(tmp_path: Path) -> None:
    storage = LocalDataLake(tmp_path / "lake")
    portfolio = PortfolioSnapshot.bootstrap(100000.0)
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
    research_report = ResearchCycleReport(
        started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        finished_at=datetime(2025, 1, 1, 0, 5, tzinfo=timezone.utc),
        provider="yahoo",
        interval="15m",
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
                        reason="Research signal",
                        strategy_id="strat-demo",
                    ),
                ),
                latest_order=ExecutionOrder(
                    mode=ExecutionMode.PAPER,
                    symbol="RELIANCE.NS",
                    action=SignalAction.HOLD,
                    status=OrderStatus.SKIPPED,
                    quantity=0,
                    requested_price=2500.0,
                    fill_price=2500.0,
                    fee_paid=0.0,
                    note="research",
                    strategy_id="strat-demo",
                ),
            )
        ],
        portfolio=portfolio,
    )
    trading_report = research_report.model_copy(
        update={
            "interval": "5m",
            "provider": "cache",
            "finished_at": datetime(2025, 1, 1, 0, 10, tzinfo=timezone.utc),
        }
    )

    storage.save_latest_report(research_report, stream="research")
    storage.save_latest_report(trading_report, stream="trading")

    loaded_research = storage.load_latest_report(stream="research")
    loaded_trading = storage.load_latest_report(stream="trading")

    assert loaded_research is not None
    assert loaded_trading is not None
    assert loaded_research.interval == "15m"
    assert loaded_trading.interval == "5m"
    assert loaded_research.provider == "yahoo"
    assert loaded_trading.provider == "cache"
