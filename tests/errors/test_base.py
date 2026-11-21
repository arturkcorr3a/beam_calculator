"""Tests for src/errors/base.py."""

import pickle

from src.errors.base import BeamCalculatorError, beam_prefixed
from src.errors.design import BeamDesignError


class _ValueWithFields(BeamDesignError):
    """A subclass whose constructor takes keyword fields, like the specific errors"""

    def __init__(self, *, value: float) -> None:
        super().__init__(f"Value {value:.2f} is too high.")
        self.value = value


class TestBeamCalculatorError:
    """The root keeps the engine's text and no element id."""

    def test_text_is_the_message(self) -> None:
        error = BeamCalculatorError("Something failed.")
        assert str(error) == "Something failed.", "the text should be unchanged"
        assert error.message == "Something failed.", "message should keep the text"
        assert not hasattr(error, "beam_id"), "only element errors carry an id"


class TestBeamPrefixed:
    """beam_prefixed names the beam only once it is known."""

    def test_without_beam(self) -> None:
        assert beam_prefixed(None, "Failed.") == "Failed.", (
            "without a beam the text should be unchanged"
        )

    def test_with_beam(self) -> None:
        assert beam_prefixed("V1", "Failed.") == "Beam 'V1': Failed.", (
            "the beam id should prefix the text"
        )


class TestPickle:
    """Errors survive a round trip to a worker process."""

    def test_keeps_type_fields_and_beam(self) -> None:
        error = _ValueWithFields(value=3.0)
        error.beam_id = "V2"
        restored = pickle.loads(pickle.dumps(error))
        assert type(restored) is _ValueWithFields, "the type should be kept"
        assert restored.value == 3.0, "the fields should be kept"
        assert str(restored) == "Beam 'V2': Value 3.00 is too high.", (
            "the text and beam should be kept"
        )
