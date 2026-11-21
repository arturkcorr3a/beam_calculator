"""Tests for src/errors/detailing.py."""

from src.errors.base import BeamCalculatorError
from src.errors.detailing import (
    BeamDetailingError,
    BendPinUndefinedError,
    DetailingError,
    LapTooLongError,
    SpliceDiameterError,
    SplicePositionError,
    StirrupBendUndefinedError,
    StirrupSpacingTooSmallError,
)


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


class TestLeafMessages:
    """Each specific detailing error keeps the engine's original text."""

    def test_splice_diameter(self) -> None:
        error = SpliceDiameterError(
            run_length=1300.0, diameter_mm=40.0, max_diameter_mm=32.0
        )
        assert isinstance(error, BeamDetailingError), "it is a beam detailing error"
        assert str(error) == (
            "A 1300 cm φ40 run needs a splice, but bars above 32 mm cannot be lap "
            "spliced."
        ), "the text should match the engine's message"

    def test_lap_too_long(self) -> None:
        error = LapTooLongError(
            lap_length=1250.0, diameter_mm=10.0, max_bar_length=1200.0
        )
        assert str(error) == (
            "A 1250 cm lap of φ10 bars does not fit in a 1200 cm bar."
        ), "the text should match the engine's message"

    def test_lap_too_long_for_skin_bars(self) -> None:
        error = LapTooLongError(
            lap_length=1250.0, diameter_mm=8.0, max_bar_length=1200.0, skin=True
        )
        assert str(error) == (
            "A 1250 cm lap of φ8 skin bars does not fit in a 1200 cm bar."
        ), "the skin variant should name the skin bars"

    def test_splice_position(self) -> None:
        error = SplicePositionError(
            quantity=2, diameter_mm=10.0, window_start=0.0, window_end=600.0
        )
        assert str(error) == (
            "No splice position for 2φ10 between 0 and 600 cm keeps the bars "
            "spliced in one section within Table 9.3."
        ), "the text should match the engine's message"

    def test_stirrup_spacing_too_small(self) -> None:
        error = StirrupSpacingTooSmallError(spacing=4.0, min_spacing=5.0)
        assert str(error) == (
            "Stirrup spacing rounds down to 4 cm, below the minimum of 5 cm."
        ), "the text should match the engine's message"

    def test_stirrup_bend_undefined(self) -> None:
        error = StirrupBendUndefinedError(diameter_mm=12.5)
        assert str(error) == (
            "No stirrup bend diameter for CA-60 bars with 12.5 mm (φ_t > 10 mm)."
        ), "the text should match the engine's message"

    def test_bend_pin_undefined(self) -> None:
        error = BendPinUndefinedError(diameter_mm=20)
        assert str(error) == (
            "No bending pin for CA-60 bars with 20 mm (φ >= 20 mm)."
        ), "the text should match the engine's message"
