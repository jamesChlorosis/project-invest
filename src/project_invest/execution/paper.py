from __future__ import annotations

from project_invest.domain.models import ExecutionMode, ExecutionOrder, PortfolioSnapshot, StrategyGenome, TradeSignal
from project_invest.execution.base import ExecutionEngine
from project_invest.services.paper_trading import PaperBroker


class PaperExecutionEngine(ExecutionEngine):
    mode = ExecutionMode.PAPER

    def __init__(self, broker: PaperBroker) -> None:
        self.broker = broker

    def execute(self, signal: TradeSignal, market_price: float, genome: StrategyGenome) -> ExecutionOrder:
        return self.broker.execute_signal(signal, market_price, genome)

    def get_portfolio(self, market_prices: dict[str, float] | None = None) -> PortfolioSnapshot:
        return self.broker.get_portfolio(market_prices)

