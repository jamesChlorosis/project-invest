from __future__ import annotations

from project_invest.domain.models import Candle, ExecutionOrder, FeatureRow, PortfolioSnapshot, ResearchCycleReport
from project_invest.storage.cache import JsonCache
from project_invest.storage.repositories import ResearchStorage


class CachedResearchStorage:
    def __init__(self, durable_storage: ResearchStorage, cache: JsonCache) -> None:
        self.durable_storage = durable_storage
        self.cache = cache
        self.backend_name = f"{durable_storage.backend_name}+{cache.backend_name}"

    def store_candles(self, symbol: str, interval: str, candles: list[Candle], stage: str) -> None:
        self.durable_storage.store_candles(symbol, interval, candles, stage)
        key = self._candles_key(stage, symbol, interval)
        payload = [candle.model_dump(mode="json") for candle in candles]
        self.cache.set(key, payload)

    def load_candles(self, symbol: str, interval: str, stage: str) -> list[Candle]:
        key = self._candles_key(stage, symbol, interval)
        cached = self.cache.get(key)
        if cached is not None:
            return [Candle.model_validate(item) for item in cached]
        candles = self.durable_storage.load_candles(symbol, interval, stage)
        if candles:
            payload = [candle.model_dump(mode="json") for candle in candles]
            self.cache.set(key, payload)
        return candles

    def store_features(self, symbol: str, interval: str, rows: list[FeatureRow]) -> None:
        self.durable_storage.store_features(symbol, interval, rows)
        key = self._features_key(symbol, interval)
        payload = [row.model_dump(mode="json") for row in rows]
        self.cache.set(key, payload)

    def load_features(self, symbol: str, interval: str) -> list[FeatureRow]:
        key = self._features_key(symbol, interval)
        cached = self.cache.get(key)
        if cached is not None:
            return [FeatureRow.model_validate(item) for item in cached]
        rows = self.durable_storage.load_features(symbol, interval)
        if rows:
            payload = [row.model_dump(mode="json") for row in rows]
            self.cache.set(key, payload)
        return rows

    def save_portfolio(self, portfolio: PortfolioSnapshot) -> None:
        self.durable_storage.save_portfolio(portfolio)
        self.cache.set("portfolio:latest", portfolio.model_dump(mode="json"))

    def load_portfolio(self) -> PortfolioSnapshot | None:
        cached = self.cache.get("portfolio:latest")
        if cached is not None:
            return PortfolioSnapshot.model_validate(cached)
        portfolio = self.durable_storage.load_portfolio()
        if portfolio is not None:
            self.cache.set("portfolio:latest", portfolio.model_dump(mode="json"))
        return portfolio

    def append_trade(self, trade: ExecutionOrder) -> None:
        self.durable_storage.append_trade(trade)
        history = self.cache.get("trades:history")
        if history is None:
            return
        history.append(trade.model_dump(mode="json"))
        self.cache.set("trades:history", history)

    def load_trades(self, limit: int | None = None) -> list[ExecutionOrder]:
        history = self.cache.get("trades:history")
        if history is None:
            trades = self.durable_storage.load_trades()
            history = [trade.model_dump(mode="json") for trade in trades]
            self.cache.set("trades:history", history)
        trades = [ExecutionOrder.model_validate(item) for item in history]
        if limit is None:
            return trades
        return trades[-limit:]

    def save_latest_report(self, report: ResearchCycleReport) -> None:
        self.durable_storage.save_latest_report(report)
        self.cache.set("reports:latest", report.model_dump(mode="json"))

    def load_latest_report(self) -> ResearchCycleReport | None:
        cached = self.cache.get("reports:latest")
        if cached is not None:
            return ResearchCycleReport.model_validate(cached)
        report = self.durable_storage.load_latest_report()
        if report is not None:
            self.cache.set("reports:latest", report.model_dump(mode="json"))
        return report

    def close(self) -> None:
        self.durable_storage.close()
        self.cache.close()

    def _candles_key(self, stage: str, symbol: str, interval: str) -> str:
        return f"candles:{stage}:{symbol}:{interval}"

    def _features_key(self, symbol: str, interval: str) -> str:
        return f"features:{symbol}:{interval}"

