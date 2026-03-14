from __future__ import annotations

import asyncio
from contextlib import suppress

from project_invest.services.research_lab import ResearchLab


class BackgroundResearchWorker:
    def __init__(self, research_lab: ResearchLab, interval_seconds: int, symbols: list[str]) -> None:
        self.research_lab = research_lab
        self.interval_seconds = max(10, interval_seconds)
        self.symbols = symbols
        self.last_error: str | None = None
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

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
                await self.research_lab.run_cycle(self.symbols)
                self.last_error = None
            except Exception as exc:
                self.last_error = str(exc)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue
