"""EngineExecutor: run engine jobs in the background, one at a time."""

from collections.abc import Callable
from itertools import count
from typing import Any, cast

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from pavement_ui.core.ports import Job
from pavement_ui.presentation.execution.job_runnable import JobRunnable, JobSignals

type _Callback = Callable[[Any], None]


class EngineExecutor(QObject):
    """Serialize every engine job on a private single-thread pool

    The engine uses a global configuration and logger, so jobs must never run
    concurrently (docs/UI_SPEC.md §3, decision 6). ``on_done`` is called on the
    UI thread: the worker's signal is delivered, queued, to this object.

    Attributes:
        busy_changed: Emitted with True when a job starts and False when the
            last pending job finishes.
    """

    busy_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._signals = JobSignals(self)
        self._signals.finished.connect(self._on_finished)
        self._tickets = count(1)
        self._pending: dict[int, _Callback] = {}

    @property
    def busy(self) -> bool:
        return bool(self._pending)

    def submit[T](self, job: Job[T], on_done: Callable[[T], None]) -> None:
        """Queue job; on_done receives its outcome on the UI thread"""
        ticket = next(self._tickets)
        was_busy = self.busy
        self._pending[ticket] = cast(_Callback, on_done)
        if not was_busy:
            self.busy_changed.emit(True)
        self._pool.start(JobRunnable(cast(Job[object], job), ticket, self._signals))

    def wait_for_done(self) -> None:
        """Block until every queued job ran (used when the application quits)"""
        self._pool.waitForDone()

    @Slot(int, object)
    def _on_finished(self, ticket: int, outcome: object) -> None:
        callback = self._pending.pop(ticket)
        try:
            callback(outcome)
        finally:
            if not self.busy:
                self.busy_changed.emit(False)
