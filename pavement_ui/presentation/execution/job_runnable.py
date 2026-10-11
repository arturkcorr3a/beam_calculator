"""Run one engine job on a pool thread and emit its outcome."""

from PySide6.QtCore import QObject, QRunnable, Signal

from pavement_ui.core.ports import Job


class JobSignals(QObject):
    """Signals of a ``JobRunnable`` (a QRunnable cannot emit signals itself)

    Attributes:
        finished: (ticket, outcome) — the ticket identifies the submission.
    """

    finished = Signal(int, object)


class JobRunnable(QRunnable):
    """Execute ``job.run()`` and emit the outcome with the submission ticket"""

    def __init__(self, job: Job[object], ticket: int, signals: JobSignals) -> None:
        super().__init__()
        self._job = job
        self._ticket = ticket
        self._signals = signals

    def run(self) -> None:
        self._signals.finished.emit(self._ticket, self._job.run())
