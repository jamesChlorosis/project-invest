from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

POSITIVE_WORDS = {
    "beat",
    "upgrade",
    "strong",
    "growth",
    "record",
    "surge",
    "profit",
    "bull",
    "optimistic",
    "positive",
}

NEGATIVE_WORDS = {
    "miss",
    "downgrade",
    "weak",
    "decline",
    "drop",
    "loss",
    "bear",
    "pessimistic",
    "negative",
    "fall",
}


@dataclass(frozen=True)
class SentimentSnapshot:
    score: float
    intensity: float


class SentimentProvider:
    def get_snapshot(self, symbol: str) -> SentimentSnapshot:
        raise NotImplementedError


class NeutralSentimentProvider(SentimentProvider):
    def get_snapshot(self, symbol: str) -> SentimentSnapshot:
        return SentimentSnapshot(score=0.0, intensity=0.0)


class LocalSentimentProvider(SentimentProvider):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.fallback_root = Path("runtime/data_lake/sentiment")

    def get_snapshot(self, symbol: str) -> SentimentSnapshot:
        payload = self._load_payload(symbol)
        if payload is None:
            return SentimentSnapshot(score=0.0, intensity=0.0)

        if "score" in payload and "intensity" in payload:
            return SentimentSnapshot(
                score=float(payload.get("score", 0.0)),
                intensity=float(payload.get("intensity", 0.0)),
            )

        headlines = payload.get("headlines", [])
        if not headlines:
            return SentimentSnapshot(score=0.0, intensity=0.0)

        score = self._score_headlines(headlines)
        intensity = min(1.0, len(headlines) / 20)
        return SentimentSnapshot(score=score, intensity=intensity)

    def _load_payload(self, symbol: str) -> dict | None:
        safe_symbol = symbol.replace("/", "_")
        search_roots: list[Path] = [self.root]
        if self.fallback_root != self.root:
            search_roots.append(self.fallback_root)

        for base_root in search_roots:
            for filename in (f"{safe_symbol}.json", "default.json"):
                path = base_root / filename
                if path.exists():
                    return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _score_headlines(self, headlines: list[str]) -> float:
        if not headlines:
            return 0.0
        score = 0.0
        for headline in headlines:
            lowered = headline.lower()
            for word in POSITIVE_WORDS:
                if word in lowered:
                    score += 1.0
            for word in NEGATIVE_WORDS:
                if word in lowered:
                    score -= 1.0
        normalized = score / max(len(headlines), 1)
        return max(-1.0, min(1.0, normalized))
