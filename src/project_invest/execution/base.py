from __future__ import annotations

from typing import Protocol

from project_invest.domain.models import ExecutionMode, ExecutionOrder, PortfolioSnapshot, StrategyGenome, TradeSignal


class ExecutionEngine(Protocol):
    mode: ExecutionMode

    def execute(self, signal: TradeSignal, market_price: float, genome: StrategyGenome) -> ExecutionOrder:
        """Execute or simulate the order."""

    def get_portfolio(self, market_prices: dict[str, float] | None = None) -> PortfolioSnapshot:
        """Return the latest portfolio snapshot for the active mode."""

