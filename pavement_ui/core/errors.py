"""Errors raised by the core and the engine adapters."""

from enum import Enum, auto


class EngineRuleError(Exception):
    """The engine refused an operation by one of its rules

    Attributes:
        message: The engine's original (English) text; translated by the presentation.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SessionBusyError(Exception):
    """A change was requested while a design is running"""


class PersistenceErrorKind(Enum):
    """Why a project file could not be opened or saved"""

    NOT_FOUND = auto()
    INVALID_YAML = auto()
    INVALID_CONTENT = auto()


class PersistenceError(Exception):
    """A project file could not be opened or saved; the session is left unchanged

    Attributes:
        detail: Extra information: the path, the YAML line, or the engine's text.
    """

    def __init__(self, kind: PersistenceErrorKind, detail: str) -> None:
        super().__init__(f"{kind.name}: {detail}")
        self.kind = kind
        self.detail = detail
