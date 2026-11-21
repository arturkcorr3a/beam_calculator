"""Tests for src/errors/detailing.py."""

from src.errors.base import BeamCalculatorError
from src.errors.detailing import BeamDetailingError, DetailingError


class TestDetailingError:
    """DetailingError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(DetailingError, BeamCalculatorError), (
            "DetailingError should derive from BeamCalculatorError"
        )
        assert issubclass(DetailingError, ValueError), (
            "DetailingError should still be caught as ValueError"
        )


class TestBeamDetailingError:
    """BeamDetailingError names the beam once it is known."""

    def test_is_a_detailing_error(self) -> None:
        assert issubclass(BeamDetailingError, DetailingError), (
            "BeamDetailingError should be a DetailingError"
        )

    def test_with_beam(self) -> None:
        error = BeamDetailingError("Stirrup spacing is too small.", beam_id="V3")
        assert str(error) == "Beam 'V3': Stirrup spacing is too small.", (
            "the beam id should prefix the text"
        )
