from __future__ import annotations

from project_invest.domain.models import FeatureRow, SignalAction, TradeSignal
from project_invest.services.trade_memory import SentimentMemoryEdge


class SentimentSignalAdjuster:
    def __init__(
        self,
        min_intensity: float = 0.2,
        confidence_boost: float = 0.16,
        confidence_penalty: float = 0.24,
        reversal_block_threshold: float = 0.42,
    ) -> None:
        self.min_intensity = max(0.0, min(min_intensity, 1.0))
        self.confidence_boost = max(0.0, confidence_boost)
        self.confidence_penalty = max(0.0, confidence_penalty)
        self.reversal_block_threshold = max(0.0, min(reversal_block_threshold, 1.0))

    def apply(
        self,
        signal: TradeSignal,
        latest_feature: FeatureRow | None,
        memory_edge: SentimentMemoryEdge | None = None,
    ) -> TradeSignal:
        if latest_feature is None:
            return signal

        sentiment_score = latest_feature.sentiment_score
        news_intensity = latest_feature.news_intensity
        if sentiment_score is None or news_intensity is None:
            return signal

        intensity = max(0.0, min(news_intensity, 1.0))
        score = max(-1.0, min(sentiment_score, 1.0))
        weighted = score * intensity

        if intensity < self.min_intensity or abs(weighted) < 0.04:
            return signal

        if signal.action == SignalAction.BUY:
            adjusted = self._adjust_buy(signal, score, intensity, weighted)
            return self._apply_memory_edge(adjusted, memory_edge)

        if signal.action == SignalAction.SELL:
            return self._adjust_sell(signal, score, intensity, weighted)

        adjusted = self._annotate_hold(signal, score, intensity, weighted)
        return self._apply_hold_memory_note(adjusted, memory_edge)

    def _adjust_buy(
        self,
        signal: TradeSignal,
        score: float,
        intensity: float,
        weighted: float,
    ) -> TradeSignal:
        if weighted <= -self.reversal_block_threshold and signal.confidence < 0.72:
            return signal.model_copy(
                update={
                    "action": SignalAction.HOLD,
                    "confidence": round(max(0.0, signal.confidence * 0.35), 4),
                    "reason": (
                        f"{signal.reason} Blocked by bearish sentiment "
                        f"(score {score:+.2f}, news {intensity:.2f})."
                    ),
                }
            )

        if weighted >= 0:
            adjusted_confidence = min(0.99, signal.confidence + (self.confidence_boost * weighted))
            note = f"Sentiment tailwind (score {score:+.2f}, news {intensity:.2f})."
        else:
            adjusted_confidence = max(0.0, signal.confidence + (self.confidence_penalty * weighted))
            note = f"Sentiment headwind (score {score:+.2f}, news {intensity:.2f})."

        return signal.model_copy(
            update={
                "confidence": round(adjusted_confidence, 4),
                "reason": f"{signal.reason} {note}",
            }
        )

    def _adjust_sell(
        self,
        signal: TradeSignal,
        score: float,
        intensity: float,
        weighted: float,
    ) -> TradeSignal:
        directional_weight = -weighted
        if directional_weight <= -self.reversal_block_threshold and signal.confidence < 0.72:
            return signal.model_copy(
                update={
                    "action": SignalAction.HOLD,
                    "confidence": round(max(0.0, signal.confidence * 0.35), 4),
                    "reason": (
                        f"{signal.reason} Blocked by bullish sentiment "
                        f"(score {score:+.2f}, news {intensity:.2f})."
                    ),
                }
            )

        if directional_weight >= 0:
            adjusted_confidence = min(0.99, signal.confidence + (self.confidence_boost * directional_weight))
            note = f"Sentiment supports the exit (score {score:+.2f}, news {intensity:.2f})."
        else:
            adjusted_confidence = max(0.0, signal.confidence + (self.confidence_penalty * directional_weight))
            note = f"Sentiment resists the exit (score {score:+.2f}, news {intensity:.2f})."

        return signal.model_copy(
            update={
                "confidence": round(adjusted_confidence, 4),
                "reason": f"{signal.reason} {note}",
            }
        )

    def _annotate_hold(
        self,
        signal: TradeSignal,
        score: float,
        intensity: float,
        weighted: float,
    ) -> TradeSignal:
        if abs(weighted) < max(0.14, self.reversal_block_threshold * 0.5):
            return signal

        bias = "bullish" if weighted > 0 else "bearish"
        return signal.model_copy(
            update={
                "reason": f"{signal.reason} Sentiment is currently {bias} (score {score:+.2f}, news {intensity:.2f}).",
                "confidence": round(min(0.99, signal.confidence + min(0.08, abs(weighted) * 0.08)), 4),
            }
        )

    def _apply_memory_edge(
        self,
        signal: TradeSignal,
        memory_edge: SentimentMemoryEdge | None,
    ) -> TradeSignal:
        if memory_edge is None or signal.action != SignalAction.BUY:
            return signal

        note = (
            f"Trade memory {memory_edge.scope} edge on {memory_edge.bucket} sentiment: "
            f"{memory_edge.sample_size} trades, win rate {memory_edge.win_rate:.0%}, "
            f"avg return {memory_edge.avg_return_pct:.2f}%."
        )

        if (
            memory_edge.sample_size >= 6
            and memory_edge.win_rate <= 0.34
            and memory_edge.avg_return_pct <= -0.2
            and signal.confidence < 0.82
        ):
            return signal.model_copy(
                update={
                    "action": SignalAction.HOLD,
                    "confidence": round(max(0.0, signal.confidence * 0.3), 4),
                    "reason": f"{signal.reason} {note} Memory gate blocked the entry.",
                }
            )

        if memory_edge.win_rate >= 0.58 and memory_edge.avg_return_pct > 0:
            boost = min(0.12, 0.02 * memory_edge.sample_size)
            return signal.model_copy(
                update={
                    "confidence": round(min(0.99, signal.confidence + boost), 4),
                    "reason": f"{signal.reason} {note} Memory supports the setup.",
                }
            )

        if memory_edge.win_rate < 0.45 or memory_edge.avg_return_pct < 0:
            penalty = min(0.22, 0.03 * memory_edge.sample_size)
            return signal.model_copy(
                update={
                    "confidence": round(max(0.0, signal.confidence - penalty), 4),
                    "reason": f"{signal.reason} {note} Memory is cautious on this setup.",
                }
            )

        return signal.model_copy(update={"reason": f"{signal.reason} {note}"})

    def _apply_hold_memory_note(
        self,
        signal: TradeSignal,
        memory_edge: SentimentMemoryEdge | None,
    ) -> TradeSignal:
        if memory_edge is None:
            return signal

        suffix = (
            f" Trade memory {memory_edge.scope} edge on {memory_edge.bucket} sentiment: "
            f"{memory_edge.sample_size} trades, win rate {memory_edge.win_rate:.0%}, "
            f"avg return {memory_edge.avg_return_pct:.2f}%."
        )
        return signal.model_copy(update={"reason": f"{signal.reason}{suffix}"})
