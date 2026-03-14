from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from project_invest.domain.models import (
    Candle,
    ExecutionOrder,
    FeatureRow,
    PortfolioSnapshot,
    ResearchCycleReport,
)


class LocalDataLake:
    backend_name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root
        for name in ("raw", "processed", "features", "reports", "state", "trades"):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def _sanitize(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _dataset_path(self, stage: str, symbol: str, interval: str) -> Path:
        safe_symbol = self._sanitize(symbol)
        safe_interval = self._sanitize(interval)
        return self.root / stage / f"{safe_symbol}-{safe_interval}.json"

    def store_candles(self, symbol: str, interval: str, candles: list[Candle], stage: str) -> None:
        path = self._dataset_path(stage, symbol, interval)
        payload = [candle.model_dump(mode="json") for candle in candles]
        self._write_json(path, payload)

    def load_candles(self, symbol: str, interval: str, stage: str) -> list[Candle]:
        path = self._dataset_path(stage, symbol, interval)
        if not path.exists():
            return []
        return [Candle.model_validate(item) for item in self._read_json(path)]

    def store_features(self, symbol: str, interval: str, rows: list[FeatureRow]) -> None:
        path = self._dataset_path("features", symbol, interval)
        payload = [row.model_dump(mode="json") for row in rows]
        self._write_json(path, payload)

    def load_features(self, symbol: str, interval: str) -> list[FeatureRow]:
        path = self._dataset_path("features", symbol, interval)
        if not path.exists():
            return []
        return [FeatureRow.model_validate(item) for item in self._read_json(path)]

    def save_portfolio(self, portfolio: PortfolioSnapshot) -> None:
        path = self.root / "state" / "portfolio.json"
        self._write_json(path, portfolio.model_dump(mode="json"))

    def load_portfolio(self) -> PortfolioSnapshot | None:
        path = self.root / "state" / "portfolio.json"
        if not path.exists():
            return None
        return PortfolioSnapshot.model_validate(self._read_json(path))

    def append_trade(self, trade: ExecutionOrder) -> None:
        path = self.root / "trades" / "history.json"
        payload: list[dict[str, Any]] = []
        if path.exists():
            payload = self._read_json(path)
        payload.append(trade.model_dump(mode="json"))
        self._write_json(path, payload)

    def load_trades(self, limit: int | None = None) -> list[ExecutionOrder]:
        path = self.root / "trades" / "history.json"
        if not path.exists():
            return []
        payload = [ExecutionOrder.model_validate(item) for item in self._read_json(path)]
        if limit is None:
            return payload
        return payload[-limit:]

    def save_latest_report(self, report: ResearchCycleReport) -> None:
        latest_path = self.root / "reports" / "latest.json"
        historical_name = report.finished_at.strftime("%Y%m%dT%H%M%S")
        historical_path = self.root / "reports" / f"{historical_name}.json"
        payload = report.model_dump(mode="json")
        self._write_json(latest_path, payload)
        self._write_json(historical_path, payload)

    def load_latest_report(self) -> ResearchCycleReport | None:
        path = self.root / "reports" / "latest.json"
        if not path.exists():
            return None
        return ResearchCycleReport.model_validate(self._read_json(path))

    def close(self) -> None:
        return None
