"""Tests for src/errors/precondition.py."""

from src.errors.base import BeamCalculatorError
from src.errors.precondition import EnginePreconditionError


class TestEnginePreconditionError:
    """EnginePreconditionError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(EnginePreconditionError, BeamCalculatorError), (
            "EnginePreconditionError should derive from BeamCalculatorError"
        )
        assert issubclass(EnginePreconditionError, ValueError), (
            "EnginePreconditionError should still be caught as ValueError"
        )
