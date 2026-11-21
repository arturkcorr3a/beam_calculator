"""The root of the engine's errors"""

from typing import Any


class BeamCalculatorError(Exception):
    """Base of every error the engine raises by its own rules

    Attributes:
        message: The engine's original (English) text, without any beam prefix.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __reduce__(self) -> tuple[Any, ...]:
        """Pickle without calling ``__init__``, whose arguments differ per subclass"""
        return (_restore, (type(self), self.args, self.__dict__))


def _restore(
    cls: type[BeamCalculatorError], args: tuple[object, ...], state: dict[str, Any]
) -> BeamCalculatorError:
    error = cls.__new__(cls)
    error.args = args
    error.__dict__.update(state)
    return error


def beam_prefixed(beam_id: str | None, message: str) -> str:
    """Return the message prefixed with the beam, once the beam is known"""
    return message if beam_id is None else f"Beam '{beam_id}': {message}"
