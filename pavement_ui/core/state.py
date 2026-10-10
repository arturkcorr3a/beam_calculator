"""Validation and design state of the session."""

from dataclasses import dataclass
from enum import Enum, auto

from pavement_ui.core.results.outcomes import DesignOutcome


class ValidationStatus(Enum):
    NOT_VALIDATED = auto()
    VALID = auto()
    INVALID = auto()


@dataclass(frozen=True, slots=True)
class ValidationState:
    """Result of the last validation

    Attributes:
        message: The engine's first error (original text) when INVALID.
    """

    status: ValidationStatus = ValidationStatus.NOT_VALIDATED
    message: str | None = None


@dataclass(frozen=True, slots=True)
class DesignState:
    """Whether a design is running, and the outcome of the last one"""

    running: bool = False
    last_outcome: DesignOutcome | None = None
