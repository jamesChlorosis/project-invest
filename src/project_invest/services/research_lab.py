from __future__ import annotations

from project_invest.domain.models import ResearchCycleReport, SymbolResearchResult, utc_now
from project_invest.execution.base import ExecutionEngine
from project_invest.services.feature_engineering import FeatureEngineeringEngine
from project_invest.services.ingestion import MarketDataIngestionService
from project_invest.services.strategy_evolution import StrategyEvolutionEngine
from project_invest.storage.repositories import FeatureRepository, ReportRepository


class ResearchLab:
    def __init__(
        self,
        ingestion: MarketDataIngestionService,
        feature_engine: FeatureEngineeringEngine,
        evolution_engine: StrategyEvolutionEngine,
        execution_engine: ExecutionEngine,
        feature_repository: FeatureRepository,
        report_repository: ReportRepository,
        interval: str,
        lookback_bars: int,
        default_symbols: list[str],
    ) -> None:
        self.ingestion = ingestion
        self.feature_engine = feature_engine
        self.evolution_engine = evolution_engine
        self.execution_engine = execution_engine
        self.feature_repository = feature_repository
        self.report_repository = report_repository
        self.interval = interval
        self.lookback_bars = lookback_bars
        self.default_symbols = default_symbols

    async def run_cycle(self, symbols: list[str] | None = None) -> ResearchCycleReport:
        active_symbols = symbols or self.default_symbols
        started_at = utc_now()
        results: list[SymbolResearchResult] = []
        latest_prices: dict[str, float] = {}
        provider_name = getattr(self.ingestion.primary_provider, "name", "unknown")

        for symbol in active_symbols:
            provider_name, candles = await self.ingestion.ingest_symbol(symbol, self.interval, self.lookback_bars)
            features = self.feature_engine.build_feature_rows(candles)
            self.feature_repository.store_features(symbol, self.interval, features)

            evolution = self.evolution_engine.evolve(symbol, candles)
            latest_price = candles[-1].close
            latest_prices[symbol] = latest_price
            order = self.execution_engine.execute(evolution.latest_signal, latest_price, evolution.champion.genome)

            results.append(
                SymbolResearchResult(
                    symbol=symbol,
                    candles_collected=len(candles),
                    feature_rows=len(features),
                    evolution=evolution,
                    latest_order=order,
                )
            )

        portfolio = self.execution_engine.get_portfolio(latest_prices)
        report = ResearchCycleReport(
            started_at=started_at,
            finished_at=utc_now(),
            provider=provider_name,
            interval=self.interval,
            symbols=active_symbols,
            results=results,
            portfolio=portfolio,
        )
        self.report_repository.save_latest_report(report)
        return report
