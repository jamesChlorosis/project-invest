from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from project_invest.domain.models import Candle, SignalAction, TradeSignal


@dataclass(frozen=True)
class TimeframeAlignment:
    interval: str
    direction: str
    strength: float


class MultiTimeframeGate:
    def __init__(
        self,
        intervals: list[str],
        short_window: int = 10,
        long_window: int = 30,
        min_trend_strength: float = 0.0015,
    ) -> None:
        self.intervals = [interval for interval in intervals if interval]
        self.short_window = max(3, short_window)
        self.long_window = max(self.short_window + 2, long_window)
        self.min_trend_strength = max(0.0, min_trend_strength)

    def apply(
        self,
        signal: TradeSignal,
        candles_by_interval: dict[str, list[Candle]],
    ) -> tuple[TradeSignal, list[TimeframeAlignment]]:
        alignments: list[TimeframeAlignment] = []

        for interval in self.intervals:
            candles = candles_by_interval.get(interval, [])
            direction, strength = self._trend_direction(candles)
            alignments.append(
                TimeframeAlignment(
                    interval=interval,
                    direction=direction,
                    strength=round(strength, 6),
                )
            )

        if signal.action == SignalAction.BUY:
            down_alignments = [alignment for alignment in alignments if alignment.direction == "down"]
            up_alignments = [alignment for alignment in alignments if alignment.direction == "up"]
            strong_down_alignments = [
                alignment
                for alignment in down_alignments
                if abs(alignment.strength) >= max(self.min_trend_strength * 2.5, 0.003)
            ]
            majority_down = len(down_alignments) > (len(alignments) / 2)
            should_block = (
                (len(alignments) <= 1 and down_alignments)
                or majority_down
                or (bool(strong_down_alignments) and not up_alignments)
            )
            if should_block:
                blockers = [alignment.interval for alignment in (strong_down_alignments or down_alignments)]
                reason = f"Multi-timeframe gate blocked buy: downtrend on {', '.join(blockers)}."
                return (
                    signal.model_copy(
                        update={
                            "action": SignalAction.HOLD,
                            "confidence": 0.0,
                            "reason": reason,
                        }
                    ),
                    alignments,
                )
            if down_alignments:
                blockers = ", ".join(alignment.interval for alignment in down_alignments)
                return (
                    signal.model_copy(
                        update={
                            "confidence": round(max(0.12, signal.confidence * 0.55), 4),
                            "reason": f"Multi-timeframe check is mixed; buy allowed with reduced confidence despite weakness on {blockers}.",
                        }
                    ),
                    alignments,
                )

        return signal, alignments

    def _trend_direction(self, candles: list[Candle]) -> tuple[str, float]:
        if len(candles) < self.long_window:
            return "flat", 0.0

        closes = [candle.close for candle in candles]
        short_ma = fmean(closes[-self.short_window :])
        long_ma = fmean(closes[-self.long_window :])
        if long_ma == 0:
            return "flat", 0.0
        strength = (short_ma - long_ma) / long_ma
        if strength > self.min_trend_strength:
            return "up", strength
        if strength < -self.min_trend_strength:
            return "down", strength
        return "flat", strength
