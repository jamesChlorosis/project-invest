from __future__ import annotations

from project_invest.domain.models import ExecutionOrder, ResearchCycleReport
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
            key=lambda item: item.evolution.champion.score,
            reverse=True,
        )
        allocation_plan = self.optimizer.recommend_allocations(report.results)

        top_strategies = [
            {
                "symbol": result.symbol,
                "strategy_id": result.evolution.champion.genome.strategy_id,
                "score": result.evolution.champion.score,
                "total_return": result.evolution.champion.metrics.total_return,
                "sharpe_ratio": result.evolution.champion.metrics.sharpe_ratio,
                "drawdown": result.evolution.champion.metrics.max_drawdown,
                "signal": result.evolution.latest_signal.action.value,
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
