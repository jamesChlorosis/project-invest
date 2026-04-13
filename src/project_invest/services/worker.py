from __future__ import annotations

import asyncio
from contextlib import suppress

from project_invest.services.research_lab import ResearchLab
from project_invest.services.trading_lab import TradingLab


class BackgroundResearchWorker:
    def __init__(
        self,
        research_lab: ResearchLab,
        interval_seconds: int,
        symbols: list[str],
        execute_trades: bool = True,
        run_lock: asyncio.Lock | None = None,
    ) -> None:
        self.research_lab = research_lab
        self.interval_seconds = max(10, interval_seconds)
        self.symbols = symbols
        self.execute_trades = execute_trades
        self.last_error: str | None = None
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._run_lock = run_lock

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._run_lock is None:
                    await self.research_lab.run_cycle(self.symbols, execute_trades=self.execute_trades)
                else:
                    async with self._run_lock:
                        await self.research_lab.run_cycle(self.symbols, execute_trades=self.execute_trades)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue


class BackgroundResearchSupervisor:
    def __init__(
        self,
        research_lab: ResearchLab,
        interval_seconds: int,
        symbol_groups: list[list[str]],
        execute_trades: bool = True,
        run_lock: asyncio.Lock | None = None,
    ) -> None:
        self.research_lab = research_lab
        self.interval_seconds = max(10, interval_seconds)
        self.symbol_groups = [group for group in symbol_groups if group]
        self.last_error: str | None = None
        self._lock = run_lock or asyncio.Lock()
        self._workers = [
            BackgroundResearchWorker(
                research_lab=research_lab,
                interval_seconds=self.interval_seconds,
                symbols=group,
                execute_trades=execute_trades,
                run_lock=self._lock,
            )
            for group in self.symbol_groups
        ]

    async def start(self) -> None:
        for worker in self._workers:
            await worker.start()

    async def stop(self) -> None:
        for worker in self._workers:
            await worker.stop()

    def refresh_last_error(self) -> None:
        for worker in self._workers:
            if worker.last_error:
                self.last_error = worker.last_error
                return
        self.last_error = None


class BackgroundTradingWorker:
    def __init__(
        self,
        trading_lab: TradingLab,
        interval_seconds: int,
        symbols: list[str],
        run_lock: asyncio.Lock | None = None,
    ) -> None:
        self.trading_lab = trading_lab
        self.interval_seconds = max(10, interval_seconds)
        self.symbols = symbols
        self.last_error: str | None = None
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._run_lock = run_lock

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._run_lock is None:
                    await self.trading_lab.run_cycle(self.symbols)
                else:
                    async with self._run_lock:
                        await self.trading_lab.run_cycle(self.symbols)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue


class BackgroundTradingSupervisor:
    def __init__(
        self,
        trading_lab: TradingLab,
        interval_seconds: int,
        symbol_groups: list[list[str]],
        run_lock: asyncio.Lock | None = None,
    ) -> None:
        self.trading_lab = trading_lab
        self.interval_seconds = max(10, interval_seconds)
        self.symbol_groups = [group for group in symbol_groups if group]
        self.last_error: str | None = None
        self._lock = run_lock or asyncio.Lock()
        self._workers = [
            BackgroundTradingWorker(
                trading_lab=trading_lab,
                interval_seconds=self.interval_seconds,
                symbols=group,
                run_lock=self._lock,
            )
            for group in self.symbol_groups
        ]

    async def start(self) -> None:
        for worker in self._workers:
            await worker.start()

    async def stop(self) -> None:
        for worker in self._workers:
            await worker.stop()

    def refresh_last_error(self) -> None:
        for worker in self._workers:
            if worker.last_error:
                self.last_error = worker.last_error
                return
        self.last_error = None
