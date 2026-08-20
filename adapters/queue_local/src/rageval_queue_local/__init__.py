"""In-process background task runner (no Celery/Redis)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

JobFactory = Callable[[], Awaitable[Any]]


class LocalTaskRunner:
    """Track asyncio tasks started inside the API process."""

    def __init__(self, *, max_workers: int = 2) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be positive")
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="rageval-worker",
        )
        self._bound_loop: asyncio.AbstractEventLoop | None = None

    def submit(self, job_id: str, factory: JobFactory) -> None:
        """Schedule ``factory()`` on the running event loop; return immediately."""
        if job_id in self._tasks and not self._tasks[job_id].done():
            raise RuntimeError(f"job already running: {job_id}")
        loop = asyncio.get_running_loop()
        if self._bound_loop is None:
            loop.set_default_executor(self._executor)
            self._bound_loop = loop
        elif self._bound_loop is not loop:
            raise RuntimeError("LocalTaskRunner cannot span event loops")

        async def _runner() -> None:
            try:
                await factory()
            except Exception:  # noqa: BLE001 — logged; job owns status updates
                logger.exception("background job failed: %s", job_id)
            finally:
                self._tasks.pop(job_id, None)

        self._tasks[job_id] = asyncio.create_task(_runner(), name=f"rageval-job-{job_id}")

    async def shutdown(self) -> None:
        """Wait for submitted jobs and release the bounded worker pool."""
        tasks = list(self._tasks.values())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._executor.shutdown(wait=True, cancel_futures=False)

    def is_running(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        return task is not None and not task.done()

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if not t.done())


__all__ = ["LocalTaskRunner"]
