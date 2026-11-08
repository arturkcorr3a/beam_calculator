"""Common interface for the runnable examples in ``src/examples``."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.pavement_elements.pavement import Pavement


class SimpleExample(ABC):
    """Runnable example, discovered and executed by ``src.main``

    Each example module defines exactly one subclass. Logging is configured by
    the runner, so examples must not call ``configure_logger``; they may still
    set other ``APP_CONFIG`` fields inside ``run``.
    """

    @abstractmethod
    def run(self) -> Pavement | None:
        """Execute the example end to end

        Returns:
            The pavement the example built, so the runner can draw it, or None when the example has no detailed pavement.
        """
