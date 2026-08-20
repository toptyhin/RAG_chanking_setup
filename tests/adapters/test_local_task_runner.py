"""Local background runner concurrency guarantees."""

from __future__ import annotations

import asyncio
import time

import pytest

from rageval_queue_local import LocalTaskRunner


@pytest.mark.asyncio
async def test_sync_pipeline_work_does_not_block_event_loop() -> None:
    runner = LocalTaskRunner(max_workers=1)
    finished = asyncio.Event()

    async def job() -> None:
        await asyncio.to_thread(time.sleep, 0.05)
        finished.set()

    runner.submit("run_1", job)
    await asyncio.sleep(0.005)

    assert runner.is_running("run_1")
    assert not finished.is_set()
    await asyncio.wait_for(finished.wait(), timeout=1.0)
    await runner.shutdown()
