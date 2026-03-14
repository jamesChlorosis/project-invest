from __future__ import annotations

import argparse
import asyncio
import os
import signal
from collections.abc import Sequence

import uvicorn

from project_invest.config import settings
from project_invest.container import build_container
from project_invest.services.worker import BackgroundResearchWorker


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Project Invest runtime entrypoints.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    api_parser = subparsers.add_parser("api", help="Run the FastAPI control center.")
    api_parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    api_parser.add_argument("--port", default=int(os.getenv("PORT", "8000")), type=int)
    api_parser.add_argument("--reload", action="store_true")

    run_once_parser = subparsers.add_parser("run-once", help="Execute one research cycle.")
    run_once_parser.add_argument("--symbols", nargs="*", default=None)

    worker_parser = subparsers.add_parser("worker", help="Run the continuous research worker.")
    worker_parser.add_argument("--symbols", nargs="*", default=None)
    worker_parser.add_argument("--interval-seconds", type=int, default=None)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "api":
        run_api(host=args.host, port=args.port, reload=args.reload)
        return

    if args.command == "run-once":
        asyncio.run(run_once(args.symbols))
        return

    if args.command == "worker":
        interval_seconds = args.interval_seconds or settings.live_loop_seconds
        asyncio.run(run_worker(args.symbols, interval_seconds))


def run_api(host: str, port: int, reload: bool = False) -> None:
    uvicorn.run("project_invest.api.app:app", host=host, port=port, reload=reload)


async def run_once(symbols: list[str] | None = None) -> None:
    container = build_container(settings)
    try:
        await container.research_lab.run_cycle(symbols or None)
    finally:
        container.close()


async def run_worker(symbols: list[str] | None = None, interval_seconds: int | None = None) -> None:
    container = build_container(settings)
    active_symbols = symbols or settings.research_symbols
    worker = BackgroundResearchWorker(
        research_lab=container.research_lab,
        interval_seconds=interval_seconds or settings.live_loop_seconds,
        symbols=active_symbols,
    )
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    try:
        await worker.start()
        await stop_event.wait()
    finally:
        await worker.stop()
        container.close()
