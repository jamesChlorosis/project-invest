from __future__ import annotations

from typing import Protocol

from project_invest.domain.models import Candle, ExecutionOrder, FeatureRow, PortfolioSnapshot, ResearchCycleReport


class CandleRepository(Protocol):
    def store_candles(self, symbol: str, interval: str, candles: list[Candle], stage: str) -> None:
        """Persist candles for a symbol and interval."""

    def load_candles(self, symbol: str, interval: str, stage: str) -> list[Candle]:
        """Load candles for a symbol and interval."""


class FeatureRepository(Protocol):
    def store_features(self, symbol: str, interval: str, rows: list[FeatureRow]) -> None:
        """Persist engineered features."""

    def load_features(self, symbol: str, interval: str) -> list[FeatureRow]:
        """Load engineered features."""


class PortfolioRepository(Protocol):
    def save_portfolio(self, portfolio: PortfolioSnapshot) -> None:
        """Persist the latest portfolio state."""

    def load_portfolio(self) -> PortfolioSnapshot | None:
        """Load the latest portfolio state."""


class TradeRepository(Protocol):
    def append_trade(self, trade: ExecutionOrder) -> None:
        """Persist an executed order."""

    def load_trades(self, limit: int | None = None) -> list[ExecutionOrder]:
        """Load recent or full trade history."""


class ReportRepository(Protocol):
    def save_latest_report(self, report: ResearchCycleReport) -> None:
        """Persist the latest research report and any historical copy."""

    def load_latest_report(self) -> ResearchCycleReport | None:
        """Load the latest research report."""


class ResearchStorage(
    CandleRepository,
    FeatureRepository,
    PortfolioRepository,
    TradeRepository,
    ReportRepository,
    Protocol,
):
    backend_name: str

    def close(self) -> None:
        """Release any resources held by the storage backend."""

