from __future__ import annotations

from project_invest.domain.models import SymbolResearchResult


class PortfolioOptimizer:
    def recommend_allocations(self, results: list[SymbolResearchResult]) -> dict[str, float]:
        if not results:
            return {}

        raw_scores: dict[str, float] = {}
        for result in results:
            metrics = result.evolution.champion.metrics
            quality = max(result.evolution.champion.score, 0.0) + 0.05
            stability = max(0.05, 1 - metrics.max_drawdown)
            raw_scores[result.symbol] = quality * stability

        total = sum(raw_scores.values())
        if total <= 0:
            equal_weight = round(1 / len(results), 4)
            return {result.symbol: equal_weight for result in results}

        return {
            symbol: round(score / total, 4)
            for symbol, score in sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)
        }

