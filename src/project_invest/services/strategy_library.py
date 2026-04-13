from __future__ import annotations

from statistics import fmean

from project_invest.domain.models import Candle, SignalAction, StrategyFamily, StrategyGenome, TradeSignal


class StrategyLibrary:
    def required_bars(self, genome: StrategyGenome) -> int:
        if genome.family == StrategyFamily.MEAN_REVERSION:
            return max(genome.long_window + 1, 20)
        if genome.family == StrategyFamily.BREAKOUT:
            return max(genome.long_window + 1, genome.breakout_lookback + 2, 20)
        return max(genome.long_window + 1, 15)

    def generate_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool,
    ) -> TradeSignal:
        if genome.family == StrategyFamily.MEAN_REVERSION:
            return self._mean_reversion_signal(genome, candles, has_position)
        if genome.family == StrategyFamily.BREAKOUT:
            return self._breakout_signal(genome, candles, has_position)
        return self._trend_following_signal(genome, candles, has_position)

    def _trend_following_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool,
    ) -> TradeSignal:
        closes = [candle.close for candle in candles]
        symbol = candles[-1].symbol
        short_ma = fmean(closes[-genome.short_window :])
        long_ma = fmean(closes[-genome.long_window :])
        spread = ((short_ma - long_ma) / long_ma) if long_ma else 0.0

        anchor_price = closes[max(0, len(closes) - genome.short_window)]
        momentum = ((closes[-1] / anchor_price) - 1) if anchor_price else 0.0
        confidence = min(0.99, max(0.05, abs(spread) * 16 + abs(momentum) * 8))

        bullish = (
            short_ma > long_ma * (1 + (genome.momentum_threshold / 28))
            and momentum >= max(0.0, genome.momentum_threshold * 0.08)
        )
        bearish = (
            short_ma < long_ma * (1 - (genome.momentum_threshold / 26))
            or momentum <= -max(0.0006, genome.momentum_threshold * 0.1)
        )

        if not has_position and bullish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=round(confidence, 4),
                reason=f"Trend following buy on bullish crossover with {momentum:.2%} momentum.",
                strategy_id=genome.strategy_id,
            )

        if has_position and bearish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=round(confidence, 4),
                reason=f"Trend following exit as crossover weakened to {momentum:.2%} momentum.",
                strategy_id=genome.strategy_id,
            )

        return TradeSignal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=round(confidence / 2, 4),
            reason="Trend following setup has no actionable edge right now.",
            strategy_id=genome.strategy_id,
        )

    def _mean_reversion_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool,
    ) -> TradeSignal:
        closes = [candle.close for candle in candles]
        symbol = candles[-1].symbol
        current_close = closes[-1]
        short_ma = fmean(closes[-genome.short_window :])
        long_ma = fmean(closes[-genome.long_window :])
        rsi = self._rsi(closes, 14)
        deviation = ((current_close - short_ma) / short_ma) if short_ma else 0.0

        trend_ok = current_close >= long_ma * 0.9
        oversold = rsi is not None and rsi <= (genome.rsi_entry_threshold + 10.0)
        recovered = rsi is not None and rsi >= genome.rsi_exit_threshold
        entry_deviation = -max(0.0005, genome.mean_reversion_threshold * 0.25)
        confidence = min(
            0.99,
            max(
                0.05,
                abs(deviation) * 18
                + (max(0.0, (genome.rsi_entry_threshold - (rsi or genome.rsi_entry_threshold)) / 25) * 1.8),
            ),
        )

        bullish = trend_ok and oversold and deviation <= entry_deviation
        bearish = recovered or current_close >= short_ma * 0.992 or deviation >= -(genome.mean_reversion_threshold * 0.02)

        if not has_position and bullish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=round(confidence, 4),
                reason=f"Mean reversion buy with RSI {rsi:.1f} and {deviation:.2%} pullback.",
                strategy_id=genome.strategy_id,
            )

        if has_position and bearish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=round(confidence, 4),
                reason=f"Mean reversion exit as price normalized with RSI {rsi:.1f}.",
                strategy_id=genome.strategy_id,
            )

        return TradeSignal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=round(confidence / 2, 4),
            reason="Mean reversion setup is waiting for a deeper or cleaner pullback.",
            strategy_id=genome.strategy_id,
        )

    def _breakout_signal(
        self,
        genome: StrategyGenome,
        candles: list[Candle],
        has_position: bool,
    ) -> TradeSignal:
        closes = [candle.close for candle in candles]
        volumes = [candle.volume for candle in candles]
        symbol = candles[-1].symbol
        current_close = closes[-1]
        lookback = genome.breakout_lookback
        prior_closes = closes[-lookback - 1 : -1]
        prior_volumes = volumes[-lookback - 1 : -1]
        breakout_level = max(prior_closes)
        average_volume = fmean(prior_volumes) if prior_volumes else 0.0
        volume_ratio = (volumes[-1] / average_volume) if average_volume else 1.0
        anchor_price = closes[max(0, len(closes) - genome.short_window)]
        momentum = ((current_close / anchor_price) - 1) if anchor_price else 0.0
        short_ma = fmean(closes[-genome.short_window :])

        breakout_distance = ((current_close - breakout_level) / breakout_level) if breakout_level else 0.0
        confidence = min(
            0.99,
            max(0.05, max(0.0, breakout_distance) * 40 + max(0.0, volume_ratio - 1) * 0.35 + abs(momentum) * 5),
        )

        bullish = (
            current_close >= breakout_level * (1 + (genome.breakout_buffer * 0.08))
            and volume_ratio >= max(0.7, genome.volume_confirmation * 0.5)
            and momentum >= max(0.0, genome.momentum_threshold / 8)
        )
        bearish = current_close < short_ma * 0.997 or momentum <= -max(0.0006, genome.momentum_threshold / 8)

        if not has_position and bullish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.BUY,
                confidence=round(confidence, 4),
                reason=f"Breakout buy above {breakout_level:.2f} with {volume_ratio:.2f}x volume.",
                strategy_id=genome.strategy_id,
            )

        if has_position and bearish:
            return TradeSignal(
                symbol=symbol,
                action=SignalAction.SELL,
                confidence=round(confidence, 4),
                reason="Breakout exit as follow-through faded below the short trend filter.",
                strategy_id=genome.strategy_id,
            )

        return TradeSignal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=round(confidence / 2, 4),
            reason="Breakout setup has not confirmed with enough price and volume expansion.",
            strategy_id=genome.strategy_id,
        )

    def _rsi(self, closes: list[float], window: int) -> float | None:
        if len(closes) <= window:
            return None

        deltas = [closes[index] - closes[index - 1] for index in range(len(closes) - window, len(closes))]
        gains = [delta for delta in deltas if delta > 0]
        losses = [-delta for delta in deltas if delta < 0]
        average_gain = sum(gains) / window if gains else 0.0
        average_loss = sum(losses) / window if losses else 0.0

        if average_loss == 0:
            return 100.0
        relative_strength = average_gain / average_loss
        return 100 - (100 / (1 + relative_strength))
