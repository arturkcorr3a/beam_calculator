"""QtSessionBridge: the session's events as Qt signals."""

from PySide6.QtCore import QObject, Signal, SignalInstance

from pavement_ui.core.events import EventBus, SessionEvent


class QtSessionBridge(QObject):
    """Re-emit every ``SessionEvent`` as the matching Qt signal

    Session operations run on the UI thread, so the signals are emitted there.
    Widgets observe these signals and re-read the session state.
    """

    records_changed = Signal()
    config_changed = Signal()
    validation_changed = Signal()
    design_started = Signal()
    design_finished = Signal()
    file_changed = Signal()

    def __init__(self, bus: EventBus, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._signals: dict[SessionEvent, SignalInstance] = {
            SessionEvent.RECORDS_CHANGED: self.records_changed,
            SessionEvent.CONFIG_CHANGED: self.config_changed,
            SessionEvent.VALIDATION_CHANGED: self.validation_changed,
            SessionEvent.DESIGN_STARTED: self.design_started,
            SessionEvent.DESIGN_FINISHED: self.design_finished,
            SessionEvent.FILE_CHANGED: self.file_changed,
        }
        self._unsubscribe = bus.subscribe(self._on_event)

    def _on_event(self, event: SessionEvent) -> None:
        self._signals[event].emit()
