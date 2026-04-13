from __future__ import annotations

import json

from project_invest.services.sentiment import LocalSentimentProvider


def test_local_sentiment_provider_uses_fallback_root(tmp_path) -> None:
    configured_root = tmp_path / "runtime" / "sentiment"
    fallback_root = tmp_path / "runtime" / "data_lake" / "sentiment"
    fallback_root.mkdir(parents=True)
    (fallback_root / "default.json").write_text(
        json.dumps({"score": 0.25, "intensity": 0.4}),
        encoding="utf-8",
    )

    provider = LocalSentimentProvider(configured_root)
    provider.fallback_root = fallback_root

    snapshot = provider.get_snapshot("RELIANCE.NS")

    assert snapshot.score == 0.25
    assert snapshot.intensity == 0.4
