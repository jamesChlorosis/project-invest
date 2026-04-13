from __future__ import annotations

from datetime import datetime

from project_invest.domain.models import (
    EvolutionReport,
    ExecutionOrder,
    OrderStatus,
    SignalAction,
    StrategyEvaluation,
    StrategyGenome,
    StrategyRegistryEntry,
    StrategyRegistryStatus,
)


class StrategyRegistryService:
    def __init__(
        self,
        max_seed_genomes: int = 6,
        max_entries_per_symbol: int = 18,
        retire_after_stale_cycles: int = 10,
    ) -> None:
        self.max_seed_genomes = max(2, max_seed_genomes)
        self.max_entries_per_symbol = max(6, max_entries_per_symbol)
        self.retire_after_stale_cycles = max(3, retire_after_stale_cycles)

    def seed_genomes(
        self,
        entries: list[StrategyRegistryEntry],
        limit: int | None = None,
    ) -> list[StrategyGenome]:
        requested_limit = max(1, limit or self.max_seed_genomes)
        ordered = sorted(
            (entry for entry in entries if entry.status != StrategyRegistryStatus.RETIRED),
            key=self._seed_key,
            reverse=True,
        )

        seeds: list[StrategyGenome] = []
        seen: set[str] = set()
        for entry in ordered:
            strategy_id = entry.genome.strategy_id
            if strategy_id in seen:
                continue
            seeds.append(entry.genome)
            seen.add(strategy_id)
            if len(seeds) >= requested_limit:
                break
        return seeds

    def update_registry(
        self,
        symbol: str,
        previous_entries: list[StrategyRegistryEntry],
        evolution: EvolutionReport,
        executed_genome: StrategyGenome | None,
        latest_order: ExecutionOrder,
        position_active: bool,
        finished_at: datetime,
    ) -> list[StrategyRegistryEntry]:
        entries_by_id = {
            entry.genome.strategy_id: entry.model_copy(deep=True)
            for entry in previous_entries
        }
        touched_ids: set[str] = set()

        for evaluation in self._dedupe_evaluations([evolution.champion, *evolution.leaderboard]):
            entry = entries_by_id.get(evaluation.genome.strategy_id) or StrategyRegistryEntry(
                symbol=symbol,
                genome=evaluation.genome,
            )
            entry = self._apply_evaluation(entry, evaluation, finished_at)
            entries_by_id[entry.genome.strategy_id] = entry
            touched_ids.add(entry.genome.strategy_id)

        active_strategy_id = executed_genome.strategy_id if position_active and executed_genome is not None else None
        if executed_genome is not None:
            entry = entries_by_id.get(executed_genome.strategy_id) or StrategyRegistryEntry(
                symbol=symbol,
                genome=executed_genome,
            )
            entry.genome = executed_genome
            entry.last_signal_action = latest_order.action
            entry.last_order_status = latest_order.status
            entry.last_order_at = latest_order.timestamp
            entry.last_seen_at = finished_at
            entry.times_selected += 1
            entry.stale_cycles = 0

            if latest_order.status == OrderStatus.FILLED:
                if latest_order.action == SignalAction.BUY:
                    entry.paper_entry_count += 1
                elif latest_order.action == SignalAction.SELL:
                    entry.paper_exit_count += 1
                    entry.cumulative_realized_pnl = round(
                        entry.cumulative_realized_pnl + latest_order.realized_pnl,
                        4,
                    )
                    if latest_order.realized_pnl >= 0:
                        entry.win_count += 1
                    else:
                        entry.loss_count += 1

            entries_by_id[entry.genome.strategy_id] = entry
            touched_ids.add(entry.genome.strategy_id)

        for strategy_id, entry in entries_by_id.items():
            if strategy_id not in touched_ids:
                entry.stale_cycles += 1
            if active_strategy_id is not None and strategy_id == active_strategy_id:
                entry.status = StrategyRegistryStatus.ACTIVE
            elif entry.status == StrategyRegistryStatus.ACTIVE:
                entry.status = StrategyRegistryStatus.CANDIDATE

        self._retire_weak_entries(entries_by_id, active_strategy_id)

        ordered_entries = sorted(entries_by_id.values(), key=self._entry_rank, reverse=True)
        keep_ids = {
            entry.genome.strategy_id
            for entry in ordered_entries[: self.max_entries_per_symbol]
        }
        if active_strategy_id is not None:
            keep_ids.add(active_strategy_id)

        trimmed_entries: list[StrategyRegistryEntry] = []
        for entry in ordered_entries:
            if entry.genome.strategy_id not in keep_ids and entry.status != StrategyRegistryStatus.ACTIVE:
                entry.status = StrategyRegistryStatus.RETIRED
            trimmed_entries.append(entry)

        return trimmed_entries[: max(self.max_entries_per_symbol, len(keep_ids))]

    def _apply_evaluation(
        self,
        entry: StrategyRegistryEntry,
        evaluation: StrategyEvaluation,
        finished_at: datetime,
    ) -> StrategyRegistryEntry:
        validation_metrics = evaluation.validation_metrics or evaluation.metrics
        entry.genome = evaluation.genome
        entry.last_score = round(evaluation.score, 6)
        entry.last_validation_sharpe = round(validation_metrics.sharpe_ratio, 6)
        entry.last_validation_return = round(validation_metrics.total_return, 6)
        entry.last_seen_at = finished_at
        entry.stale_cycles = 0
        if entry.status == StrategyRegistryStatus.RETIRED:
            entry.status = StrategyRegistryStatus.CANDIDATE
        return entry

    def _retire_weak_entries(
        self,
        entries_by_id: dict[str, StrategyRegistryEntry],
        active_strategy_id: str | None,
    ) -> None:
        for strategy_id, entry in entries_by_id.items():
            if active_strategy_id is not None and strategy_id == active_strategy_id:
                continue

            persistent_loser = (
                entry.paper_exit_count >= 2
                and entry.loss_count >= entry.win_count
                and entry.cumulative_realized_pnl < 0
            )
            too_stale = entry.stale_cycles >= self.retire_after_stale_cycles and entry.paper_entry_count == 0
            no_edge = entry.last_score < 0 and entry.last_validation_sharpe <= 0 and entry.stale_cycles >= 3
            if persistent_loser or too_stale or no_edge:
                entry.status = StrategyRegistryStatus.RETIRED

    def _dedupe_evaluations(self, evaluations: list[StrategyEvaluation]) -> list[StrategyEvaluation]:
        deduped: list[StrategyEvaluation] = []
        seen: set[str] = set()
        for evaluation in evaluations:
            strategy_id = evaluation.genome.strategy_id
            if strategy_id in seen:
                continue
            deduped.append(evaluation)
            seen.add(strategy_id)
        return deduped

    def _seed_key(self, entry: StrategyRegistryEntry) -> tuple[float, ...]:
        active_bonus = 1.0 if entry.status == StrategyRegistryStatus.ACTIVE else 0.0
        trade_quality = (entry.win_count - entry.loss_count) * 0.2
        pnl_component = entry.cumulative_realized_pnl * 0.02
        staleness_penalty = entry.stale_cycles * 0.05
        return (
            active_bonus,
            entry.last_score,
            entry.last_validation_sharpe,
            entry.last_validation_return,
            pnl_component + trade_quality - staleness_penalty,
            float(entry.times_selected),
        )

    def _entry_rank(self, entry: StrategyRegistryEntry) -> tuple[float, ...]:
        status_rank = {
            StrategyRegistryStatus.ACTIVE: 2.0,
            StrategyRegistryStatus.CANDIDATE: 1.0,
            StrategyRegistryStatus.RETIRED: 0.0,
        }[entry.status]
        quality_component = (entry.win_count - entry.loss_count) * 0.2
        return (
            status_rank,
            entry.last_score,
            entry.last_validation_sharpe,
            entry.cumulative_realized_pnl * 0.02 + quality_component,
            -float(entry.stale_cycles),
            float(entry.times_selected),
        )
