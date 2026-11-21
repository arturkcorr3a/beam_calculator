"""Errors for engine objects used out of order"""

from src.errors.base import BeamCalculatorError


class EnginePreconditionError(BeamCalculatorError, ValueError):
    """An engine object was used before the step it depends on, or with arguments it never accepts

    It signals a bug in the calling code, not a property of the structure.
    """


class UnknownNameError(EnginePreconditionError, KeyError):
    """A name the engine looks up in its own tables is not there (e.g. a drawing layer)

    Caught as ``KeyError``, as the engine raised it before.

    Attributes:
        name: The name that was not found.
    """

    def __init__(self, message: str, *, name: str) -> None:
        super().__init__(message)
        self.name = name


class NumericalError(BeamCalculatorError, ArithmeticError):
    """A calculation has no real solution for the values it was given

    Like a precondition, it signals a bug rather than a property of the
    structure; it stays an ``ArithmeticError``, as the engine raised it before.
    """
