"""Session events and a minimal synchronous publish/subscribe bus."""

from collections.abc import Callable
from enum import Enum, auto

type Listener = Callable[[SessionEvent], None]


class SessionEvent(Enum):
    RECORDS_CHANGED = auto()
    CONFIG_CHANGED = auto()
    VALIDATION_CHANGED = auto()
    DESIGN_STARTED = auto()
    DESIGN_FINISHED = auto()
    FILE_CHANGED = auto()


class EventBus:
    """Deliver each published event to every subscriber, in subscription order"""

    def __init__(self) -> None:
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Register a listener

        Returns:
            A function that removes the listener.
        """
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def publish(self, event: SessionEvent) -> None:
        """Call every listener with event"""
        for listener in tuple(self._listeners):
            listener(event)
