from __future__ import annotations

from statistics import fmean

from project_invest.domain.models import Candle, SignalAction, StrategyGenome, TradeSignal


class StrategySignalEngine:
    def generate_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool = False,
    ) -> TradeSignal:
        genome = self.normalize_genome(genome)
        if len(candles) < genome.long_window + 1:
            return TradeSignal(
                symbol=candles[-1].symbol if candles else "UNKNOWN",
                action=SignalAction.HOLD,
                confidence=0.0,
                reason="Insufficient history for the strategy windows.",
                strategy_id=genome.strategy_id,
            )

        closes = [candle.close for candle in candles]
        symbol = candles[-1].symbol
        short_ma = fmean(closes[-genome.short_window :])
        long_ma = fmean(closes[-genome.long_window :])
        spread = ((short_ma - long_ma) / long_ma) if long_ma else 0.0

        lookback_index = max(0, len(closes) - genome.short_window)
        anchor_price = closes[lookback_index]
        momentum = ((closes[-1] / anchor_price) - 1) if anchor_price else 0.0
        confidence = min(0.99, max(0.05, abs(spread) * 14 + abs(momentum) * 8))

        bullish = short_ma > long_ma and momentum >= genome.momentum_threshold
        bearish = short_ma < long_ma or momentum <= -(genome.momentum_threshold / 2)

        if not has_position and bullish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=round(confidence, 4),
                reason=f"Bullish crossover with {momentum:.2%} momentum.",
                strategy_id=genome.strategy_id,
            )

        if has_position and bearish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=round(confidence, 4),
                reason=f"Trend weakened with {momentum:.2%} momentum.",
                strategy_id=genome.strategy_id,
            )

        return TradeSignal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=round(confidence / 2, 4),
            reason="No actionable edge after applying the current genome.",
            strategy_id=genome.strategy_id,
        )

    def normalize_genome(self, genome: StrategyGenome) -> StrategyGenome:
        short_window = max(3, min(genome.short_window, 60))
        long_window = max(short_window + 2, min(genome.long_window, 150))
        return genome.model_copy(
            update={
                "short_window": short_window,
                "long_window": long_window,
                "momentum_threshold": max(0.0, min(genome.momentum_threshold, 0.1)),
                "stop_loss_pct": max(0.005, min(genome.stop_loss_pct, 0.15)),
                "take_profit_pct": max(0.01, min(genome.take_profit_pct, 0.25)),
                "risk_fraction": max(0.01, min(genome.risk_fraction, 0.35)),
            }
        )

