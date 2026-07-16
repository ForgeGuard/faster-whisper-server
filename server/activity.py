"""Lightweight admission control + live activity counters.

Transcription is CPU/GPU-bound and effectively serial on a single GPU. This gate
bounds how many requests run at once (default one), makes additional requests
wait briefly in a bounded queue, and sheds load with a 503 rather than building
an unbounded backlog. Its ``active``/``waiting`` counters feed the /system
activity meter and the web console's monitor.

A client disconnect cancels the waiting task, which releases its slot
immediately (FastAPI cancels the request coroutine on disconnect).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class QueueFullError(Exception):
    """Too many requests already waiting for a slot."""


class QueueTimeoutError(Exception):
    """Waited longer than the configured queue timeout."""


class RequestGate:
    def __init__(
        self,
        *,
        concurrency: int = 1,
        max_waiting: int = 32,
        wait_timeout_s: float = 120.0,
    ) -> None:
        self.concurrency = max(1, concurrency)
        self.max_waiting = max(0, max_waiting)
        self.wait_timeout_s = wait_timeout_s
        self._sem: asyncio.Semaphore | None = None
        self._sem_loop: asyncio.AbstractEventLoop | None = None
        self._waiting = 0
        self._active = 0

    @property
    def waiting(self) -> int:
        return self._waiting

    @property
    def active(self) -> int:
        return self._active

    def _semaphore(self) -> asyncio.Semaphore:
        """A semaphore bound to the current running loop.

        Bound lazily (and rebuilt if the running loop changes) so a Semaphore
        created under one event loop is never awaited under another — which the
        test client, spinning a fresh loop per request, would otherwise trip.
        In the server there is a single long-lived loop, so this builds once.
        """
        loop = asyncio.get_running_loop()
        if self._sem is None or self._sem_loop is not loop:
            self._sem = asyncio.Semaphore(self.concurrency)
            self._sem_loop = loop
        return self._sem

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Acquire a slot, or raise QueueFull/QueueTimeout under load."""
        if self._waiting >= self.max_waiting:
            raise QueueFullError(
                f"queue is full ({self.max_waiting} requests already waiting)"
            )
        sem = self._semaphore()
        self._waiting += 1
        try:
            try:
                await asyncio.wait_for(sem.acquire(), timeout=self.wait_timeout_s)
            except (TimeoutError, asyncio.TimeoutError):
                raise QueueTimeoutError(
                    f"timed out after {self.wait_timeout_s:.0f}s waiting for a slot"
                ) from None
        finally:
            self._waiting -= 1
        self._active += 1
        try:
            yield
        finally:
            self._active -= 1
            sem.release()


# Process-wide singleton, built from config at import time. Inference routes
# acquire a slot around the blocking transcription call; /system reads the
# counters.
from server import config  # noqa: E402

gate = RequestGate(
    concurrency=config.MAX_CONCURRENCY,
    max_waiting=config.QUEUE_SIZE,
    wait_timeout_s=config.QUEUE_TIMEOUT_S,
)


def activity_info() -> dict[str, int]:
    """Live queue depth: running vs. waiting requests."""
    return {"active": gate.active, "waiting": gate.waiting}
