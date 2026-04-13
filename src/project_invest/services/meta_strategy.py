from __future__ import annotations

from collections import defaultdict

from project_invest.domain.models import MarketRegime, StrategyEvaluation, StrategyRegistryEntry, StrategyRegistryStatus


class MetaStrategySelector:
    def __init__(self) -> None:
        self._regime_weights = {
            MarketRegime.TRENDING: {"trend_following": 1.2, "breakout": 1.1, "mean_reversion": 0.8},
            MarketRegime.SIDEWAYS: {"mean_reversion": 1.2, "trend_following": 0.9, "breakout": 0.8},
            MarketRegime.HIGH_VOL: {"breakout": 1.2, "trend_following": 1.0, "mean_reversion": 0.85},
            MarketRegime.LOW_VOL: {"mean_reversion": 1.15, "trend_following": 0.95, "breakout": 0.85},
        }

    def select(
        self,
        evaluations: list[StrategyEvaluation],
        registry: list[StrategyRegistryEntry],
        regime: MarketRegime | None,
    ) -> tuple[StrategyEvaluation | None, str | None]:
        if not evaluations:
            return None, None

        family_bias = self._family_bias_from_registry(registry)
        regime_bias = self._regime_weights.get(regime, {}) if regime else {}

        best: StrategyEvaluation | None = None
        best_score = float("-inf")
        for evaluation in evaluations:
            family = evaluation.genome.family.value
            weight = 1.0
            weight *= regime_bias.get(family, 1.0)
            weight *= family_bias.get(family, 1.0)
            adjusted = evaluation.score * weight
            if adjusted > best_score:
                best_score = adjusted
                best = evaluation

        if best is None:
            return None, None

        reason = "Meta selection used regime and registry weighting."
        if regime is None:
            reason = "Meta selection used registry weighting."
        return best, reason

    def _family_bias_from_registry(self, registry: list[StrategyRegistryEntry]) -> dict[str, float]:
        if not registry:
            return {}

        family_scores: dict[str, list[float]] = defaultdict(list)
        for entry in registry:
            if entry.status == StrategyRegistryStatus.RETIRED:
                continue
            family_scores[entry.genome.family.value].append(
                entry.last_score + (entry.cumulative_realized_pnl * 0.01)
            )

        bias: dict[str, float] = {}
        for family, scores in family_scores.items():
            if not scores:
                continue
            avg_score = sum(scores) / len(scores)
            bias[family] = 0.9 + min(0.4, max(-0.2, avg_score * 0.1))
        return bias
