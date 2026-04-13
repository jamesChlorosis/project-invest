from __future__ import annotations

from project_invest.domain.models import (
    ExecutionOrder,
    ResearchCycleReport,
    StrategyRegistryEntry,
    StrategyRegistryStatus,
    TradeMemoryOutcome,
    TradeMemoryRecord,
    TradeMemoryStatus,
)
from project_invest.services.portfolio_optimization import PortfolioOptimizer


class AnalyticsService:
    def __init__(self, optimizer: PortfolioOptimizer) -> None:
        self.optimizer = optimizer

    def build_summary(
        self,
        report: ResearchCycleReport | None,
        recent_orders: list[ExecutionOrder],
    ) -> dict[str, object]:
        if report is None:
            return {
                "status": "no-data",
                "portfolio_value": None,
                "cash": None,
                "realized_pnl": 0.0,
                "open_positions": 0,
                "top_strategies": [],
                "allocation_plan": {},
                "recent_orders": [],
                "mode": None,
                "last_run": None,
            }

        ranked_results = sorted(
            report.results,
            key=lambda item: (item.evolution.meta_selected or item.evolution.champion).score,
            reverse=True,
        )
        allocation_plan = self.optimizer.recommend_allocations(report.results)

        top_strategies = [
            {
                "symbol": result.symbol,
                "strategy_id": (result.evolution.meta_selected or result.evolution.champion).genome.strategy_id,
                "family": (result.evolution.meta_selected or result.evolution.champion).genome.family.value,
                "score": (result.evolution.meta_selected or result.evolution.champion).score,
                "total_return": (result.evolution.meta_selected or result.evolution.champion).metrics.total_return,
                "sharpe_ratio": (result.evolution.meta_selected or result.evolution.champion).metrics.sharpe_ratio,
                "drawdown": (result.evolution.meta_selected or result.evolution.champion).metrics.max_drawdown,
                "trades": (result.evolution.meta_selected or result.evolution.champion).metrics.trades,
                "profit_factor": (result.evolution.meta_selected or result.evolution.champion).metrics.profit_factor,
                "validation_total_return": (
                    (result.evolution.meta_selected or result.evolution.champion).validation_metrics.total_return
                    if (result.evolution.meta_selected or result.evolution.champion).validation_metrics is not None
                    else None
                ),
                "validation_sharpe_ratio": (
                    (result.evolution.meta_selected or result.evolution.champion).validation_metrics.sharpe_ratio
                    if (result.evolution.meta_selected or result.evolution.champion).validation_metrics is not None
                    else None
                ),
                "robustness_score": (result.evolution.meta_selected or result.evolution.champion).robustness_score,
                "signal": result.evolution.latest_signal.action.value,
                "meta_reason": result.evolution.meta_reason,
            }
            for result in ranked_results[:5]
        ]

        return {
            "status": "ok",
            "portfolio_value": report.portfolio.total_equity,
            "cash": report.portfolio.cash,
            "realized_pnl": report.portfolio.realized_pnl,
            "open_positions": len(report.portfolio.positions),
            "top_strategies": top_strategies,
            "allocation_plan": allocation_plan,
            "recent_orders": [order.model_dump(mode="json") for order in recent_orders[-10:]],
            "mode": ranked_results[0].latest_order.mode.value if ranked_results else None,
            "last_run": report.finished_at,
        }

    def build_learning_summary(
        self,
        symbols: list[str],
        registries_by_symbol: dict[str, list[StrategyRegistryEntry]],
    ) -> dict[str, object]:
        scoreboard: list[dict[str, object]] = []
        total_retired = 0
        total_active = 0
        total_candidates = 0

        for symbol in symbols:
            entries = registries_by_symbol.get(symbol, [])
            if not entries:
                scoreboard.append(
                    {
                        "symbol": symbol,
                        "status": "no-registry",
                        "strategy_id": None,
                        "family": None,
                        "score": None,
                        "validation_sharpe": None,
                        "times_selected": 0,
                        "paper_entries": 0,
                        "paper_exits": 0,
                        "wins": 0,
                        "losses": 0,
                        "realized_pnl": 0.0,
                        "retired_count": 0,
                    }
                )
                continue

            retired_count = sum(1 for entry in entries if entry.status == StrategyRegistryStatus.RETIRED)
            active_entries = [entry for entry in entries if entry.status == StrategyRegistryStatus.ACTIVE]
            candidate_entries = [entry for entry in entries if entry.status == StrategyRegistryStatus.CANDIDATE]
            total_retired += retired_count
            total_active += len(active_entries)
            total_candidates += len(candidate_entries)

            ranked_entries = sorted(
                entries,
                key=lambda entry: (
                    1 if entry.status == StrategyRegistryStatus.ACTIVE else 0,
                    entry.last_score,
                    entry.last_validation_sharpe,
                    entry.times_selected,
                    entry.cumulative_realized_pnl,
                ),
                reverse=True,
            )
            leader = ranked_entries[0]

            scoreboard.append(
                {
                    "symbol": symbol,
                    "status": leader.status.value,
                    "strategy_id": leader.genome.strategy_id,
                    "family": leader.genome.family.value,
                    "score": leader.last_score,
                    "validation_sharpe": leader.last_validation_sharpe,
                    "times_selected": leader.times_selected,
                    "paper_entries": leader.paper_entry_count,
                    "paper_exits": leader.paper_exit_count,
                    "wins": leader.win_count,
                    "losses": leader.loss_count,
                    "realized_pnl": leader.cumulative_realized_pnl,
                    "retired_count": retired_count,
                }
            )

        return {
            "symbols_tracked": len(symbols),
            "active_strategies": total_active,
            "candidate_strategies": total_candidates,
            "retired_strategies": total_retired,
            "scoreboard": scoreboard,
        }

    def build_trade_memory_summary(self, records: list[TradeMemoryRecord]) -> dict[str, object]:
        open_records = [record for record in records if record.status == TradeMemoryStatus.OPEN]
        closed_records = [record for record in records if record.status == TradeMemoryStatus.CLOSED]
        wins = [record for record in closed_records if record.outcome == TradeMemoryOutcome.WIN]

        total_realized = sum(record.realized_pnl for record in closed_records)
        avg_pnl = total_realized / len(closed_records) if closed_records else 0.0
        avg_return = (
            sum(record.return_pct for record in closed_records if record.return_pct is not None) / len(closed_records)
            if closed_records
            else 0.0
        )
        win_rate = (len(wins) / len(closed_records)) if closed_records else None

        pattern_rows: list[dict[str, object]] = []
        sentiment_pattern_rows: list[dict[str, object]] = []
        grouped: dict[tuple[str, str], list[TradeMemoryRecord]] = {}
        sentiment_grouped: dict[tuple[str, str], list[TradeMemoryRecord]] = {}
        for record in closed_records:
            family = record.strategy_family.value if record.strategy_family is not None else "unknown"
            regime = record.entry_regime.value if record.entry_regime is not None else "unknown"
            grouped.setdefault((family, regime), []).append(record)
            sentiment_bucket = self._sentiment_bucket(record.sentiment_score, record.news_intensity)
            if sentiment_bucket != "neutral":
                sentiment_grouped.setdefault((family, sentiment_bucket), []).append(record)

        for (family, regime), bucket in grouped.items():
            bucket_wins = sum(1 for record in bucket if record.outcome == TradeMemoryOutcome.WIN)
            bucket_avg_return = sum(record.return_pct or 0.0 for record in bucket) / len(bucket)
            bucket_avg_pnl = sum(record.realized_pnl for record in bucket) / len(bucket)
            pattern_rows.append(
                {
                    "family": family,
                    "regime": regime,
                    "trades": len(bucket),
                    "wins": bucket_wins,
                    "win_rate": bucket_wins / len(bucket),
                    "avg_return_pct": bucket_avg_return,
                    "avg_pnl": bucket_avg_pnl,
                }
            )

        for (family, sentiment_bucket), bucket in sentiment_grouped.items():
            bucket_wins = sum(1 for record in bucket if record.outcome == TradeMemoryOutcome.WIN)
            bucket_avg_return = sum(record.return_pct or 0.0 for record in bucket) / len(bucket)
            bucket_avg_pnl = sum(record.realized_pnl for record in bucket) / len(bucket)
            sentiment_pattern_rows.append(
                {
                    "family": family,
                    "sentiment_bucket": sentiment_bucket,
                    "trades": len(bucket),
                    "wins": bucket_wins,
                    "win_rate": bucket_wins / len(bucket),
                    "avg_return_pct": bucket_avg_return,
                    "avg_pnl": bucket_avg_pnl,
                }
            )

        def pattern_rank_key(item: dict[str, object]) -> tuple[float, float, int]:
            return (
                float(item["win_rate"]),
                float(item["avg_return_pct"]),
                int(item["trades"]),
            )

        best_pattern = max(pattern_rows, key=pattern_rank_key) if pattern_rows else None
        worst_pattern = min(pattern_rows, key=pattern_rank_key) if pattern_rows else None
        best_sentiment_pattern = max(sentiment_pattern_rows, key=pattern_rank_key) if sentiment_pattern_rows else None
        worst_sentiment_pattern = min(sentiment_pattern_rows, key=pattern_rank_key) if sentiment_pattern_rows else None

        recent_closed = [
            {
                "symbol": record.symbol,
                "family": record.strategy_family.value if record.strategy_family is not None else None,
                "outcome": record.outcome.value if record.outcome is not None else None,
                "realized_pnl": record.realized_pnl,
                "return_pct": record.return_pct,
                "closed_at": record.closed_at,
            }
            for record in closed_records[-5:]
        ]

        return {
            "records": len(records),
            "open_records": len(open_records),
            "closed_records": len(closed_records),
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "avg_return_pct": avg_return,
            "total_realized_pnl": total_realized,
            "best_pattern": best_pattern,
            "worst_pattern": worst_pattern,
            "best_sentiment_pattern": best_sentiment_pattern,
            "worst_sentiment_pattern": worst_sentiment_pattern,
            "recent_closed": recent_closed,
        }

    def _sentiment_bucket(self, score: float | None, intensity: float | None) -> str:
        if score is None or intensity is None:
            return "neutral"
        weighted = max(-1.0, min(1.0, score)) * max(0.0, min(1.0, intensity))
        if weighted >= 0.12:
            return "positive"
        if weighted <= -0.12:
            return "negative"
        return "neutral"
