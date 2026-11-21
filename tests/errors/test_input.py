"""Tests for src/errors/input.py."""

from src.errors.base import BeamCalculatorError
from src.errors.input import InputError


class TestInputError:
    """InputError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(InputError, BeamCalculatorError), (
            "InputError should derive from BeamCalculatorError"
        )
        assert issubclass(InputError, ValueError), (
            "InputError should still be caught as ValueError"
        )
