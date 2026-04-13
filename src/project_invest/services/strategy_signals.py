from __future__ import annotations

from project_invest.domain.models import Candle, SignalAction, StrategyGenome, TradeSignal
from project_invest.services.strategy_library import StrategyLibrary


class StrategySignalEngine:
    def __init__(self) -> None:
        self.library = StrategyLibrary()

    def generate_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool = False,
    ) -> TradeSignal:
        genome = self.normalize_genome(genome)
        if len(candles) < self.required_bars(genome):
            return TradeSignal(
                symbol=candles[-1].symbol if candles else "UNKNOWN",
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Insufficient history for the selected strategy family.",
                strategy_id=genome.strategy_id,
            )
        return self.library.generate_signal(genome, candles, has_position)

    def required_bars(self, genome: StrategyGenome) -> int:
        genome = self.normalize_genome(genome)
        return self.library.required_bars(genome)

    def normalize_genome(self, genome: StrategyGenome) -> StrategyGenome:
        short_window = max(3, min(genome.short_window, 42))
        long_window = max(short_window + 2, min(genome.long_window, 96))
        rsi_entry_threshold = max(15.0, min(genome.rsi_entry_threshold, 65.0))
        rsi_exit_threshold = max(rsi_entry_threshold + 4.0, min(genome.rsi_exit_threshold, 85.0))
        return genome.model_copy(
            update={
                "short_window": short_window,
                "long_window": long_window,
                "momentum_threshold": max(0.0, min(genome.momentum_threshold, 0.045)),
                "mean_reversion_threshold": max(0.0005, min(genome.mean_reversion_threshold, 0.04)),
                "rsi_entry_threshold": rsi_entry_threshold,
                "rsi_exit_threshold": rsi_exit_threshold,
                "breakout_lookback": max(6, min(genome.breakout_lookback, 72)),
                "breakout_buffer": max(0.0, min(genome.breakout_buffer, 0.02)),
                "volume_confirmation": max(0.55, min(genome.volume_confirmation, 2.1)),
                "stop_loss_pct": max(0.005, min(genome.stop_loss_pct, 0.15)),
                "take_profit_pct": max(0.01, min(genome.take_profit_pct, 0.25)),
                "risk_fraction": max(0.01, min(genome.risk_fraction, 0.35)),
            }
        )
