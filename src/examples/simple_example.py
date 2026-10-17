"""Common interface for the runnable examples in ``src/examples``."""

from abc import ABC, abstractmethod


class SimpleExample(ABC):
    """Runnable example, discovered and executed by ``src.main``

    Each example module defines exactly one subclass. Logging is configured by
    the runner, so examples must not call ``configure_logger``; they may still
    set other ``APP_CONFIG`` fields inside ``run``.
    """

    @abstractmethod
    def run(self) -> None:
        """Execute the example end to end"""
