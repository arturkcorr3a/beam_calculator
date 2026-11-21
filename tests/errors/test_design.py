"""Tests for src/errors/design.py."""

from src.errors.base import BeamCalculatorError
from src.errors.design import (
    BeamDesignError,
    DeformationLimitExceededError,
    DesignError,
    EffectiveDepthDivergedError,
    NoReinforcementLayoutError,
    ReinforcementAreaExceededError,
    SkinReinforcementNoRoomError,
    SlabDesignError,
    SlabPreSizingDivergedError,
    SlabThicknessExceededError,
    StrutCrushingError,
)


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


class TestLeafMessages:
    """Each specific design error keeps the engine's original text."""

    def test_deformation_limit_exceeded(self) -> None:
        error = DeformationLimitExceededError(
            position=400.0,
            immediate_deflection=3.97,
            long_term_deflection=9.1,
            acceptable_deflection=3.2,
        )
        assert isinstance(error, BeamDesignError), "ELS-DEF is a beam design error"
        assert str(error) == (
            "Deformation exceeds acceptable limits at 400.00 cm. Immediate "
            "deflection: 3.97 cm, Long-term deflection: 9.10 cm, Acceptable "
            "deflection: 3.20 cm."
        ), "the text should match the engine's message"

    def test_reinforcement_area_exceeded(self) -> None:
        error = ReinforcementAreaExceededError(required_area=18.277, max_area=15.0)
        assert str(error) == (
            "Required rebar area (18.277 cm²) exceeds maximum allowable limit "
            "(15.000 cm²)."
        ), "the text should match the engine's message"

    def test_strut_crushing(self) -> None:
        error = StrutCrushingError(design_shear_force=500.0, strut_resistance=486.0)
        assert str(error) == (
            "Design shear force (V_Sd = 500.00 kN) exceeds compressed strut "
            "resistance (V_Rd2 = 486.00 kN). Design not verified."
        ), "the text should match the engine's message"

    def test_no_reinforcement_layout(self) -> None:
        assert str(NoReinforcementLayoutError()) == (
            "No valid reinforcement combination found."
        ), "the text should match the engine's message"

    def test_effective_depth_diverged(self) -> None:
        error = EffectiveDepthDivergedError(max_iterations=5)
        assert str(error) == (
            "Effective depth (d) did not converge within 5 "
            "stirrup-longitudinal reinforcement passes."
        ), "the text should match the engine's message"

    def test_slab_thickness_exceeded(self) -> None:
        error = SlabThicknessExceededError(slab_id="L1", max_thickness=20)
        assert isinstance(error, SlabDesignError), "it is a slab design error"
        assert error.slab_id == "L1", "the slab id should be kept"
        assert str(error) == (
            "Slab 'L1' cannot be stabilized; required thickness exceeds 20 cm."
        ), "the text should match the engine's message"

    def test_slab_pre_sizing_diverged(self) -> None:
        error = SlabPreSizingDivergedError(passes=3, slab_ids=["L1", "L2"])
        assert not isinstance(error, SlabDesignError), (
            "it is about several slabs, not one"
        )
        assert str(error) == (
            "Slab pre-sizing did not converge after 3 passes; still resizing: L1, L2."
        ), "the text should match the engine's message"

    def test_skin_reinforcement_no_room(self) -> None:
        message = "No room for skin reinforcement: 3 bars per face do not fit."
        error = SkinReinforcementNoRoomError(message, band_height=2.0, bars_per_face=3)
        assert isinstance(error, BeamDesignError), "it is a beam design error"
        assert str(error) == message, "the text should be the engine's message"
        assert error.band_height == 2.0, "the band height should be kept (cm)"
        assert error.bars_per_face == 3, "the bars that did not fit should be kept"
