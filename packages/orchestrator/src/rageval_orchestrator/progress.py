"""Progress reporting helpers for Lab orchestrators."""

from __future__ import annotations

from typing import Any, Protocol


class ProgressSink(Protocol):
    async def set_progress(
        self,
        run_id: str,
        *,
        done: int,
        total: int,
        current_config: dict[str, Any] | None = None,
    ) -> Any: ...


async def report_progress(
    sink: ProgressSink | None,
    run_id: str,
    *,
    done: int,
    total: int,
    current_config: dict[str, Any] | None = None,
) -> None:
    if sink is None:
        return
    await sink.set_progress(
        run_id, done=done, total=total, current_config=current_config
    )
