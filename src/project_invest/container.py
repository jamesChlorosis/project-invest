from __future__ import annotations

from dataclasses import dataclass

from project_invest.config import Settings, settings
from project_invest.domain.models import ExecutionMode, PortfolioSnapshot, RiskLimits
from project_invest.execution.base import ExecutionEngine
from project_invest.execution.live import LiveExecutionEngine
from project_invest.execution.paper import PaperExecutionEngine
from project_invest.providers.mock import MockMarketDataProvider
from project_invest.providers.yahoo import YahooFinanceProvider
from project_invest.services.analytics import AnalyticsService
from project_invest.services.backtesting import BacktestingEngine
from project_invest.services.feature_engineering import FeatureEngineeringEngine
from project_invest.services.ingestion import MarketDataIngestionService
from project_invest.services.paper_trading import PaperBroker
from project_invest.services.portfolio_optimization import PortfolioOptimizer
from project_invest.services.research_lab import ResearchLab
from project_invest.services.risk import RiskManager
from project_invest.services.strategy_evolution import StrategyEvolutionEngine
from project_invest.services.strategy_signals import StrategySignalEngine
from project_invest.storage.factory import build_storage
from project_invest.storage.repositories import ResearchStorage


@dataclass
class ServiceContainer:
    settings: Settings
    storage: ResearchStorage
    ingestion: MarketDataIngestionService
    feature_engine: FeatureEngineeringEngine
    signal_engine: StrategySignalEngine
    backtester: BacktestingEngine
    evolution_engine: StrategyEvolutionEngine
    execution_engine: ExecutionEngine
    research_lab: ResearchLab
    optimizer: PortfolioOptimizer
    analytics: AnalyticsService

    def close(self) -> None:
        self.storage.close()


def build_container(active_settings: Settings | None = None) -> ServiceContainer:
    current_settings = active_settings or settings
    storage = build_storage(current_settings)

    primary_provider = _build_market_provider(current_settings.market_data_provider)
    fallback_provider = MockMarketDataProvider() if current_settings.market_data_provider != "mock" else None
    ingestion = MarketDataIngestionService(primary_provider, storage, fallback_provider=fallback_provider)

    feature_engine = FeatureEngineeringEngine()
    signal_engine = StrategySignalEngine()

    effective_risk = current_settings.max_risk_per_trade
    if current_settings.execution_mode == ExecutionMode.LIVE.value:
        effective_risk = min(effective_risk, current_settings.live_max_risk_per_trade)

    risk_limits = RiskLimits(
        max_risk_per_trade=effective_risk,
        max_daily_loss=current_settings.max_daily_loss,
        max_positions=current_settings.max_positions,
        max_gross_exposure=current_settings.max_gross_exposure,
    )
    risk_manager = RiskManager(risk_limits)

    backtester = BacktestingEngine(
        signal_engine=signal_engine,
        slippage_bps=current_settings.order_slippage_bps,
        fee_bps=current_settings.fee_bps,
        max_risk_per_trade=effective_risk,
    )
    evolution_engine = StrategyEvolutionEngine(
        backtester=backtester,
        signal_engine=signal_engine,
        population_size=current_settings.population_size,
        generations=current_settings.generations,
        seed=current_settings.evolution_seed,
        initial_capital=current_settings.starting_capital,
    )

    paper_broker = PaperBroker(
        portfolio_repository=storage,
        trade_repository=storage,
        risk_manager=risk_manager,
        starting_capital=current_settings.starting_capital,
        slippage_bps=current_settings.order_slippage_bps,
        fee_bps=current_settings.fee_bps,
    )
    execution_engine = _build_execution_engine(current_settings, paper_broker)

    research_lab = ResearchLab(
        ingestion=ingestion,
        feature_engine=feature_engine,
        evolution_engine=evolution_engine,
        execution_engine=execution_engine,
        feature_repository=storage,
        report_repository=storage,
        interval=current_settings.research_interval,
        lookback_bars=current_settings.lookback_bars,
        default_symbols=current_settings.research_symbols,
    )

    optimizer = PortfolioOptimizer()
    analytics = AnalyticsService(optimizer)
    return ServiceContainer(
        settings=current_settings,
        storage=storage,
        ingestion=ingestion,
        feature_engine=feature_engine,
        signal_engine=signal_engine,
        backtester=backtester,
        evolution_engine=evolution_engine,
        execution_engine=execution_engine,
        research_lab=research_lab,
        optimizer=optimizer,
        analytics=analytics,
    )


def _build_market_provider(provider_name: str):
    if provider_name == "yahoo":
        return YahooFinanceProvider()
    return MockMarketDataProvider()


def _build_execution_engine(settings: Settings, paper_broker: PaperBroker) -> ExecutionEngine:
    if settings.execution_mode == ExecutionMode.LIVE.value:
        fallback = PortfolioSnapshot.bootstrap(settings.starting_capital)
        return LiveExecutionEngine(adapter=None, fallback_portfolio=fallback)
    return PaperExecutionEngine(paper_broker)
