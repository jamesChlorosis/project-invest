from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import project_invest.api.app as app_module
from project_invest.config import Settings


class _DummyStorage:
    backend_name = "local"

    def load_latest_report(self, stream: str = "research"):
        return None

    def close(self) -> None:
        return None


def test_health_endpoint_starts_even_when_embedded_loops_are_enabled(monkeypatch) -> None:
    dummy_settings = Settings(
        research_symbols="RELIANCE.NS,TCS.NS",
        use_market_universes=False,
        market_universes="NSE",
        research_loop_enabled=True,
        trading_loop_enabled=True,
        live_loop_enabled=False,
    )
    dummy_container = SimpleNamespace(
        settings=dummy_settings,
        storage=_DummyStorage(),
        research_lab=object(),
        trading_lab=object(),
        close=lambda: None,
    )

    async def fake_boot(app, container, resolved_symbols):
        app.state.worker_boot_status = "running"

    monkeypatch.setattr(app_module, "build_container", lambda _: dummy_container)
    monkeypatch.setattr(app_module, "_boot_embedded_workers", fake_boot)

    with TestClient(app_module.app) as client:
        response = client.get("/health")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["embedded_loops_enabled"] is True
    assert payload["worker_launch_mode"] == "embedded"
    assert payload["embedded_worker_boot_status"] in {"scheduled", "running"}
    assert "API owns" in payload["launch_hint"]


def test_health_endpoint_shows_api_only_launch_hint_when_workers_are_not_running(monkeypatch) -> None:
    dummy_settings = Settings(
        research_symbols="RELIANCE.NS,TCS.NS",
        use_market_universes=False,
        market_universes="NSE",
        research_loop_enabled=False,
        trading_loop_enabled=False,
        live_loop_enabled=False,
    )
    dummy_container = SimpleNamespace(
        settings=dummy_settings,
        storage=_DummyStorage(),
        research_lab=object(),
        trading_lab=object(),
        close=lambda: None,
    )

    monkeypatch.setattr(app_module, "build_container", lambda _: dummy_container)

    with TestClient(app_module.app) as client:
        response = client.get("/health")

    payload = response.json()
    assert response.status_code == 200
    assert payload["worker_launch_mode"] == "standalone"
    assert payload["worker_running"] is False
    assert "run-project-invest.cmd" in payload["launch_hint"]


def test_run_trading_returns_detail_when_cycle_fails(monkeypatch) -> None:
    dummy_settings = Settings(
        research_symbols="RELIANCE.NS,TCS.NS",
        use_market_universes=False,
        market_universes="NSE",
    )

    async def failing_trade_cycle(symbols=None):
        raise RuntimeError("kaboom")

    async def ok_research_cycle(symbols=None, execute_trades=False):
        return {"ok": True}

    dummy_container = SimpleNamespace(
        settings=dummy_settings,
        storage=_DummyStorage(),
        research_lab=SimpleNamespace(run_cycle=ok_research_cycle),
        trading_lab=SimpleNamespace(run_cycle=failing_trade_cycle),
        close=lambda: None,
    )

    monkeypatch.setattr(app_module, "build_container", lambda _: dummy_container)

    with TestClient(app_module.app) as client:
        response = client.post("/api/trading/run", json={})

    payload = response.json()
    assert response.status_code == 500
    assert payload["detail"] == "Trading cycle failed: kaboom"


def test_run_research_returns_detail_when_cycle_fails(monkeypatch) -> None:
    dummy_settings = Settings(
        research_symbols="RELIANCE.NS,TCS.NS",
        use_market_universes=False,
        market_universes="NSE",
    )

    async def failing_research_cycle(symbols=None, execute_trades=False):
        raise RuntimeError("broken-research")

    async def ok_trading_cycle(symbols=None):
        return {"ok": True}

    dummy_container = SimpleNamespace(
        settings=dummy_settings,
        storage=_DummyStorage(),
        research_lab=SimpleNamespace(run_cycle=failing_research_cycle),
        trading_lab=SimpleNamespace(run_cycle=ok_trading_cycle),
        close=lambda: None,
    )

    monkeypatch.setattr(app_module, "build_container", lambda _: dummy_container)

    with TestClient(app_module.app) as client:
        response = client.post("/api/research/run", json={})

    payload = response.json()
    assert response.status_code == 500
    assert payload["detail"] == "Research cycle failed: broken-research"
