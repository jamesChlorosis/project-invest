from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from project_invest.api.dashboard import render_dashboard
from project_invest.api.schemas import ResearchRunRequest
from project_invest.config import settings
from project_invest.container import ServiceContainer, build_container
from project_invest.services.worker import BackgroundResearchWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = build_container(settings)
    app.state.container = container
    app.state.worker = None

    if container.settings.live_loop_enabled:
        worker = BackgroundResearchWorker(
            research_lab=container.research_lab,
            interval_seconds=container.settings.live_loop_seconds,
            symbols=container.settings.research_symbols,
        )
        await worker.start()
        app.state.worker = worker

    yield

    worker = getattr(app.state, "worker", None)
    if worker is not None:
        await worker.stop()
    container.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return render_dashboard(settings.app_name)


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    container = get_container(request)
    worker = getattr(request.app.state, "worker", None)
    return {
        "status": "ok",
        "execution_mode": container.settings.execution_mode,
        "market_data_provider": container.settings.market_data_provider,
        "storage_backend": container.storage.backend_name,
        "research_symbols": container.settings.research_symbols,
        "interval": container.settings.research_interval,
        "worker_running": worker is not None,
        "worker_last_error": getattr(worker, "last_error", None),
    }


@app.get("/api/config")
async def config_snapshot(request: Request) -> dict[str, object]:
    container = get_container(request)
    return {
        "execution_mode": container.settings.execution_mode,
        "market_data_provider": container.settings.market_data_provider,
        "storage_backend": container.settings.storage_backend,
        "storage_cache_enabled": container.settings.storage_cache_enabled,
        "postgres_schema": container.settings.postgres_schema,
        "starting_capital": container.settings.starting_capital,
        "max_risk_per_trade": container.settings.max_risk_per_trade,
        "live_max_risk_per_trade": container.settings.live_max_risk_per_trade,
        "population_size": container.settings.population_size,
        "generations": container.settings.generations,
    }


@app.post("/api/research/run")
async def run_research(request: Request, payload: ResearchRunRequest | None = None):
    container = get_container(request)
    symbols = payload.symbols if payload and payload.symbols else None
    return await container.research_lab.run_cycle(symbols)


@app.get("/api/research/latest")
async def latest_report(request: Request):
    container = get_container(request)
    report = container.storage.load_latest_report()
    if report is None:
        raise HTTPException(status_code=404, detail="No research report available yet.")
    return report


@app.get("/api/portfolio")
async def portfolio(request: Request):
    container = get_container(request)
    return container.execution_engine.get_portfolio()


@app.get("/api/trades")
async def trades(request: Request, limit: int = Query(default=20, ge=1, le=200)):
    container = get_container(request)
    return container.storage.load_trades(limit=limit)


@app.get("/api/market/{symbol}")
async def market_data(symbol: str, request: Request):
    container = get_container(request)
    candles = container.storage.load_candles(symbol, container.settings.research_interval, stage="processed")
    if not candles:
        _, candles = await container.ingestion.ingest_symbol(
            symbol,
            container.settings.research_interval,
            container.settings.lookback_bars,
        )
    return candles[-100:]


@app.get("/api/features/{symbol}")
async def features(symbol: str, request: Request):
    container = get_container(request)
    rows = container.storage.load_features(symbol, container.settings.research_interval)
    if not rows:
        candles = container.storage.load_candles(symbol, container.settings.research_interval, stage="processed")
        if not candles:
            _, candles = await container.ingestion.ingest_symbol(
                symbol,
                container.settings.research_interval,
                container.settings.lookback_bars,
            )
        rows = container.feature_engine.build_feature_rows(candles)
        container.storage.store_features(symbol, container.settings.research_interval, rows)
    return rows[-100:]


@app.get("/api/analytics/summary")
async def analytics_summary(request: Request):
    container = get_container(request)
    report = container.storage.load_latest_report()
    orders = container.storage.load_trades(limit=20)
    return container.analytics.build_summary(report, orders)
