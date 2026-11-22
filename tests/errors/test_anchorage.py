"""Tests for src/errors/anchorage.py."""

from src.errors.anchorage import (
    AnchorageError,
    AnchorageLengthError,
    ClampsDoNotFitError,
    HookDoesNotFitError,
    SupportBarsShortError,
)
from src.errors.design import BeamDesignError


class TestAnchorageError:
    """Every anchorage failure is a beam design error."""

    def test_is_a_beam_design_error(self) -> None:
        assert issubclass(AnchorageError, BeamDesignError), (
            "an anchorage failure is a beam design error"
        )

    def test_leaves_are_anchorage_errors(self) -> None:
        for leaf in (
            AnchorageLengthError,
            ClampsDoNotFitError,
            HookDoesNotFitError,
            SupportBarsShortError,
        ):
            assert issubclass(leaf, AnchorageError), (
                f"{leaf.__name__} should be an AnchorageError"
            )


class TestLeafMessages:
    """Each anchorage error keeps the engine's original text and its fields."""

    def test_length(self) -> None:
        message = "Not enough space for anchorage - even with hooks."
        error = AnchorageLengthError(
            message, available_length=10.0, required_length=25.0
        )
        assert str(error) == message, "the text should be the engine's message"
        assert error.available_length == 10.0, "the room should be kept (cm)"
        assert error.required_length == 25.0, "the need should be kept (cm)"

    def test_hook(self) -> None:
        error = HookDoesNotFitError(hook_height=25.0, room=22.0)
        assert str(error) == (
            "Hooks do not fit in the section height. "
            "Hook height: 25.00 cm, Room: 22.00 cm."
        ), "the text should match the engine's message"

    def test_clamps(self) -> None:
        error = ClampsDoNotFitError(required_area=3.5)
        assert str(error) == (
            "No clamp arrangement fits in the section for 3.50 cm^2."
        ), "the text should match the engine's message"

    def test_support_bars(self) -> None:
        error = SupportBarsShortError(
            support_index=1, carried_area=0.5, share=0.333, required_area=1.0
        )
        assert str(error) == (
            "Bars carried to support 1 (0.500 cm²) are below 0.333 of the span's "
            "area (1.000 cm²)."
        ), "the text should match the engine's message"
