from __future__ import annotations

import random

from project_invest.domain.models import Candle, EvolutionReport, StrategyEvaluation, StrategyGenome
from project_invest.services.backtesting import BacktestingEngine
from project_invest.services.strategy_signals import StrategySignalEngine


class StrategyEvolutionEngine:
    def __init__(
        self,
        backtester: BacktestingEngine,
        signal_engine: StrategySignalEngine,
        population_size: int,
        generations: int,
        seed: int,
        initial_capital: float,
    ) -> None:
        self.backtester = backtester
        self.signal_engine = signal_engine
        self.population_size = max(6, population_size)
        self.generations = max(1, generations)
        self.initial_capital = initial_capital
        self.random = random.Random(seed)

    def evolve(self, symbol: str, candles: list[Candle]) -> EvolutionReport:
        population = [self._random_genome() for _ in range(self.population_size)]
        champion: StrategyEvaluation | None = None
        leaderboard: list[StrategyEvaluation] = []

        for _ in range(self.generations):
            evaluations = [self._evaluate(symbol, candles, genome) for genome in population]
            evaluations.sort(key=lambda item: item.score, reverse=True)

            if champion is None or evaluations[0].score > champion.score:
                champion = evaluations[0]
            leaderboard = evaluations[: min(5, len(evaluations))]

            elite_count = max(2, self.population_size // 4)
            elites = [evaluation.genome for evaluation in evaluations[:elite_count]]
            next_population = elites.copy()

            selection_pool = evaluations[: max(3, len(evaluations) // 2)]
            while len(next_population) < self.population_size:
                parent_a = self.random.choice(selection_pool).genome
                parent_b = self.random.choice(selection_pool).genome
                child = self._crossover(parent_a, parent_b)
                if self.random.random() < 0.35:
                    child = self._mutate(child)
                next_population.append(self.signal_engine.normalize_genome(child))

            population = next_population

        if champion is None:
            champion = self._evaluate(symbol, candles, self._random_genome())
            leaderboard = [champion]

        latest_signal = self.signal_engine.generate_signal(champion.genome, candles, has_position=False)
        return EvolutionReport(
            symbol=symbol,
            population_size=self.population_size,
            generations=self.generations,
            champion=champion,
            leaderboard=leaderboard,
            latest_signal=latest_signal,
        )

    def _evaluate(self, symbol: str, candles: list[Candle], genome: StrategyGenome) -> StrategyEvaluation:
        backtest = self.backtester.run(symbol, candles, genome, self.initial_capital)
        metrics = backtest.metrics
        trade_penalty = 0.15 if metrics.trades == 0 else 0.0
        score = (
            (metrics.total_return * 2.6)
            + (metrics.sharpe_ratio * 0.8)
            + (metrics.win_rate * 0.4)
            - (metrics.max_drawdown * 1.4)
            - trade_penalty
        )
        return StrategyEvaluation(genome=backtest.genome, metrics=metrics, score=round(score, 6))

    def _random_genome(self) -> StrategyGenome:
        short_window = self.random.randint(4, 25)
        long_window = self.random.randint(short_window + 3, 90)
        return StrategyGenome(
            short_window=short_window,
            long_window=long_window,
            momentum_threshold=round(self.random.uniform(0.0, 0.04), 4),
            stop_loss_pct=round(self.random.uniform(0.01, 0.05), 4),
            take_profit_pct=round(self.random.uniform(0.02, 0.12), 4),
            risk_fraction=round(self.random.uniform(0.04, 0.2), 4),
        )

    def _crossover(self, left: StrategyGenome, right: StrategyGenome) -> StrategyGenome:
        return StrategyGenome(
            short_window=self.random.choice([left.short_window, right.short_window]),
            long_window=self.random.choice([left.long_window, right.long_window]),
            momentum_threshold=round((left.momentum_threshold + right.momentum_threshold) / 2, 4),
            stop_loss_pct=round(self.random.choice([left.stop_loss_pct, right.stop_loss_pct]), 4),
            take_profit_pct=round(self.random.choice([left.take_profit_pct, right.take_profit_pct]), 4),
            risk_fraction=round((left.risk_fraction + right.risk_fraction) / 2, 4),
        )

    def _mutate(self, genome: StrategyGenome) -> StrategyGenome:
        mutations = {
            "short_window": max(3, genome.short_window + self.random.randint(-3, 3)),
            "long_window": max(genome.short_window + 3, genome.long_window + self.random.randint(-8, 8)),
            "momentum_threshold": round(max(0.0, genome.momentum_threshold + self.random.uniform(-0.01, 0.01)), 4),
            "stop_loss_pct": round(max(0.005, genome.stop_loss_pct + self.random.uniform(-0.01, 0.01)), 4),
            "take_profit_pct": round(max(0.01, genome.take_profit_pct + self.random.uniform(-0.02, 0.02)), 4),
            "risk_fraction": round(max(0.01, genome.risk_fraction + self.random.uniform(-0.04, 0.04)), 4),
        }
        mutated = genome.model_copy(update=mutations)
        return self.signal_engine.normalize_genome(mutated)
