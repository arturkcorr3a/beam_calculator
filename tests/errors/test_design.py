"""Tests for src/errors/design.py."""

from src.errors.base import BeamCalculatorError
from src.errors.design import BeamDesignError, DesignError, SlabDesignError


class TestDesignError:
    """DesignError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(DesignError, BeamCalculatorError), (
            "DesignError should derive from BeamCalculatorError"
        )
        assert issubclass(DesignError, ValueError), (
            "DesignError should still be caught as ValueError"
        )


class TestBeamDesignError:
    """BeamDesignError names the beam once it is known."""

    def test_is_a_design_error(self) -> None:
        assert issubclass(BeamDesignError, DesignError), (
            "BeamDesignError should be a DesignError"
        )

    def test_without_beam(self) -> None:
        error = BeamDesignError("No valid reinforcement combination found.")
        assert str(error) == "No valid reinforcement combination found.", (
            "without a beam the text should be unchanged"
        )
        assert error.beam_id is None, "no beam should be set on creation"

    def test_with_beam(self) -> None:
        error = BeamDesignError("No valid reinforcement combination found.")
        error.beam_id = "V1"
        assert str(error) == "Beam 'V1': No valid reinforcement combination found.", (
            "the beam id should prefix the text"
        )
        assert error.message == "No valid reinforcement combination found.", (
            "message should keep the text without the prefix"
        )


class TestSlabDesignError:
    """SlabDesignError keeps its slab id without prefixing the text."""

    def test_is_a_design_error(self) -> None:
        assert issubclass(SlabDesignError, DesignError), (
            "SlabDesignError should be a DesignError"
        )

    def test_keeps_id_without_prefix(self) -> None:
        message = "Slab 'L1' cannot be stabilized; required thickness exceeds 20 cm."
        error = SlabDesignError(message, slab_id="L1")
        assert error.slab_id == "L1", "the slab id should be kept"
        assert str(error) == message, "the slab message already names the slab"
