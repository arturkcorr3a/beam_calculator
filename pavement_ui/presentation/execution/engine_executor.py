"""EngineExecutor: run engine jobs in a separate worker process, one at a time."""

import multiprocessing
import traceback
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor
from itertools import count
from typing import Any, cast

from PySide6.QtCore import QObject, Signal, Slot

from pavement_ui.core.ports import Job
from pavement_ui.presentation.execution.result_relay import ResultRelay

type _Done = Callable[[Any], None]
type ErrorCallback = Callable[[str, str], None]


def _ready() -> bool:
    """Trivial task that makes the pool start its worker process."""
    return True


class EngineExecutor(QObject):
    """Serialize engine jobs on a single long-lived worker process

    The engine is pure Python: on a thread it would hold the GIL that every Qt
    callback into Python needs, freezing the window. In its own process it also
    keeps its global configuration and logger apart from the UI. Jobs must
    pickle (frozen dataclasses of records).

    Results come back queued on the UI thread through ``ResultRelay``.

    Attributes:
        busy_changed: True when a job is submitted and nothing was running,
            False when the last pending job is done.
    """

    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool: ProcessPoolExecutor | None = None
        self._relay = ResultRelay(self)
        self._relay.finished.connect(self._on_finished)
        self._relay.failed.connect(self._on_failed)
        self._tickets = count(1)
        self._pending: dict[int, tuple[_Done, ErrorCallback]] = {}

    @property
    def busy(self) -> bool:
        return bool(self._pending)

    def _get_pool(self) -> ProcessPoolExecutor:
        if self._pool is None:
            # spawn, not fork: forking a process that runs Qt is unsafe
            context = multiprocessing.get_context("spawn")
            self._pool = ProcessPoolExecutor(max_workers=1, mp_context=context)
        return self._pool

    def warm_up(self) -> None:
        """Start the worker now, so the first job does not wait for the engine to load"""
        self._get_pool().submit(_ready)

    def submit[T](
        self, job: Job[T], on_done: Callable[[T], None], on_error: ErrorCallback
    ) -> None:
        """Queue job in the worker; on_done(outcome) or on_error(message, details) on the UI thread"""
        ticket = next(self._tickets)
        was_busy = self.busy
        self._pending[ticket] = (cast(_Done, on_done), on_error)
        if not was_busy:
            self.busy_changed.emit(True)
        future = self._get_pool().submit(job.run)
        future.add_done_callback(lambda f: self._relay_result(ticket, f))

    def _relay_result(self, ticket: int, future: Future[Any]) -> None:
        """Runs on the pool's callback thread: only emit, never touch widgets."""
        if future.cancelled():  # only when the pool is torn down without waiting
            return
        error = future.exception()
        if error is None:
            self._relay.finished.emit(ticket, future.result())
            return
        details = "".join(traceback.format_exception(error))
        self._relay.failed.emit(ticket, str(error) or type(error).__name__, details)

    def shutdown(self) -> None:
        """Wait for the running job, then stop the worker (when the application quits)"""
        if self._pool is not None:
            self._pool.shutdown(wait=True)
            self._pool = None

    @Slot(int, object)
    def _on_finished(self, ticket: int, outcome: object) -> None:
        on_done, _ = self._pending.pop(ticket)
        try:
            on_done(outcome)
        finally:
            self._emit_idle()

    @Slot(int, str, str)
    def _on_failed(self, ticket: int, message: str, details: str) -> None:
        _, on_error = self._pending.pop(ticket)
        try:
            on_error(message, details)
        finally:
            self._emit_idle()

    def _emit_idle(self) -> None:
        if not self.busy:
            self.busy_changed.emit(False)
