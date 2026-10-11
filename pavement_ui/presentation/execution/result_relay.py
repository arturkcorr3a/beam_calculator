"""Carry job results from the pool's callback thread to the UI thread."""

from PySide6.QtCore import QObject, Signal


class ResultRelay(QObject):
    """Signals emitted from any thread and delivered, queued, where the relay lives

    Signals:
        finished: (ticket, outcome) when a job returned.
        failed: (ticket, message, details) when it could not run or raised.
    """

    finished = Signal(int, object)
    failed = Signal(int, str, str)
