"""Tests for src/errors/precondition.py."""

from src.errors.base import BeamCalculatorError
from src.errors.precondition import (
    EnginePreconditionError,
    NumericalError,
    UnknownNameError,
)


class TestEnginePreconditionError:
    """EnginePreconditionError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(EnginePreconditionError, BeamCalculatorError), (
            "EnginePreconditionError should derive from BeamCalculatorError"
        )
        assert issubclass(EnginePreconditionError, ValueError), (
            "EnginePreconditionError should still be caught as ValueError"
        )


class TestUnknownNameError:
    """An unknown name is a precondition error still caught as KeyError."""

    def test_hierarchy_and_text(self) -> None:
        error = UnknownNameError("Unknown drawing layer 'NOPE'.", name="NOPE")
        assert isinstance(error, EnginePreconditionError), "it is a precondition"
        assert isinstance(error, KeyError), "it should still be caught as KeyError"
        assert str(error) == "Unknown drawing layer 'NOPE'.", (
            "unlike KeyError, the text should not be wrapped in quotes"
        )
        assert error.name == "NOPE", "the unknown name should be kept"


class TestNumericalError:
    """A numerical error stays an ArithmeticError, not a ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(NumericalError, BeamCalculatorError), (
            "NumericalError should derive from BeamCalculatorError"
        )
        assert issubclass(NumericalError, ArithmeticError), (
            "NumericalError should still be caught as ArithmeticError"
        )
        assert not issubclass(NumericalError, ValueError), (
            "a ValueError catch should not swallow it, as before"
        )
