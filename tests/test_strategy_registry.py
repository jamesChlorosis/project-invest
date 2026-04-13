from __future__ import annotations

from datetime import datetime, timezone

from project_invest.domain.models import (
    BacktestMetrics,
    EvolutionReport,
    ExecutionMode,
    ExecutionOrder,
    OrderStatus,
    SignalAction,
    StrategyEvaluation,
    StrategyGenome,
    StrategyRegistryEntry,
    StrategyRegistryStatus,
    TradeSignal,
)
from project_invest.services.strategy_registry import StrategyRegistryService


def make_metrics(sharpe: float = 1.5, total_return: float = 0.01) -> BacktestMetrics:
    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe,
        max_drawdown=0.03,
        win_rate=0.6,
        profit_factor=1.4,
        trades=3,
        final_equity=101000.0,
    )


def make_evaluation(strategy_id: str, score: float = 2.0) -> StrategyEvaluation:
    genome = StrategyGenome(strategy_id=strategy_id)
    metrics = make_metrics()
    return StrategyEvaluation(
        genome=genome,
        metrics=metrics,
        validation_metrics=metrics,
        robustness_score=0.4,
        score=score,
    )


def test_seed_genomes_prefers_active_and_non_retired_entries() -> None:
    service = StrategyRegistryService()
    active_genome = StrategyGenome(strategy_id="active-seed")
    candidate_genome = StrategyGenome(strategy_id="candidate-seed")
    retired_genome = StrategyGenome(strategy_id="retired-seed")

    entries = [
        StrategyRegistryEntry(
            symbol="RELIANCE.NS",
            genome=retired_genome,
            status=StrategyRegistryStatus.RETIRED,
            last_score=9.0,
        ),
        StrategyRegistryEntry(
            symbol="RELIANCE.NS",
            genome=candidate_genome,
            status=StrategyRegistryStatus.CANDIDATE,
            last_score=2.5,
        ),
        StrategyRegistryEntry(
            symbol="RELIANCE.NS",
            genome=active_genome,
            status=StrategyRegistryStatus.ACTIVE,
            last_score=1.0,
        ),
    ]

    seeds = service.seed_genomes(entries, limit=3)

    assert [seed.strategy_id for seed in seeds] == ["active-seed", "candidate-seed"]


def test_update_registry_tracks_realized_sell_outcome_and_demotes_closed_strategy() -> None:
    service = StrategyRegistryService()
    finished_at = datetime(2026, 3, 14, tzinfo=timezone.utc)
    executed_genome = StrategyGenome(strategy_id="strat-executed")
    champion = make_evaluation("strat-fresh", score=2.8)
    evolution = EvolutionReport(
        symbol="RELIANCE.NS",
        population_size=8,
        generations=4,
        champion=champion,
        leaderboard=[champion],
        latest_signal=TradeSignal(
            symbol="RELIANCE.NS",
            action=SignalAction.SELL,
            confidence=0.72,
            reason="Exit",
            strategy_id=executed_genome.strategy_id,
        ),
    )
    previous = [
        StrategyRegistryEntry(
            symbol="RELIANCE.NS",
            genome=executed_genome,
            status=StrategyRegistryStatus.ACTIVE,
            last_score=1.4,
            paper_entry_count=1,
        )
    ]
    sell_order = ExecutionOrder(
        mode=ExecutionMode.PAPER,
        symbol="RELIANCE.NS",
        action=SignalAction.SELL,
        status=OrderStatus.FILLED,
        quantity=2,
        requested_price=100.0,
        fill_price=102.0,
        fee_paid=0.2,
        realized_pnl=3.8,
        note="Position closed.",
        strategy_id=executed_genome.strategy_id,
    )

    updated = service.update_registry(
        symbol="RELIANCE.NS",
        previous_entries=previous,
        evolution=evolution,
        executed_genome=executed_genome,
        latest_order=sell_order,
        position_active=False,
        finished_at=finished_at,
    )

    executed_entry = next(entry for entry in updated if entry.genome.strategy_id == "strat-executed")
    champion_entry = next(entry for entry in updated if entry.genome.strategy_id == "strat-fresh")

    assert executed_entry.paper_exit_count == 1
    assert executed_entry.win_count == 1
    assert executed_entry.cumulative_realized_pnl == 3.8
    assert executed_entry.status == StrategyRegistryStatus.CANDIDATE
    assert champion_entry.last_score == 2.8
