"""Tests for src/errors/input.py."""

from src.errors.base import BeamCalculatorError
from src.errors.input import (
    BeamInputError,
    BeamTooNarrowError,
    ConcreteClassTooLowError,
    DuplicateElementError,
    InputError,
    MaterialError,
    PillarInputError,
    PillarTooSmallError,
    SkinSteelError,
    SlabInputError,
    SlabLoweredTooMuchError,
    UnknownPillarError,
)


class TestInputError:
    """InputError is an engine error still caught as ValueError."""

    def test_hierarchy(self) -> None:
        assert issubclass(InputError, BeamCalculatorError), (
            "InputError should derive from BeamCalculatorError"
        )
        assert issubclass(InputError, ValueError), (
            "InputError should still be caught as ValueError"
        )


class TestElementInputErrors:
    """Element input errors keep their element's id and the engine's text."""

    def test_beam_without_id(self) -> None:
        error = BeamTooNarrowError(width=10.0, min_width=12.0)
        assert isinstance(error, BeamInputError), "it is a beam input error"
        assert error.beam_id is None, "a bare section has no beam id"
        assert str(error) == "Beam width must be at least 12.0 cm. Got 10.0 cm.", (
            "the text should match the engine's message"
        )

    def test_beam_with_id(self) -> None:
        error = BeamTooNarrowError(width=10.0, min_width=12.0, beam_id="V1")
        assert error.beam_id == "V1", "the beam id should be kept"
        assert str(error) == (
            "Beam 'V1' width must be at least 12.0 cm. Got 10.0 cm."
        ), "the message names the beam, with no extra prefix"

    def test_pillar_too_small(self) -> None:
        message = "Pillar dimensions must be at least 14.0 cm. Got 12×30 cm."
        error = PillarTooSmallError(message, pillar_id="P1", width=12.0, depth=30.0)
        assert isinstance(error, PillarInputError), "it is a pillar input error"
        assert error.pillar_id == "P1", "the pillar id should be kept"
        assert str(error) == message, "the text should be the engine's message"

    def test_slab_lowered_too_much(self) -> None:
        error = SlabLoweredTooMuchError(
            slab_id="L1",
            lowered=21,
            max_lowered=20.0,
            beam_id="V2",
            beam_height=30.0,
            thickness=10,
        )
        assert isinstance(error, SlabInputError), "it is a slab input error"
        assert str(error) == (
            "Slab 'L1' is lowered 21 cm, but the maximum is 20 cm (beam 'V2' height "
            "30 cm minus slab thickness 10 cm)."
        ), "the text should match the engine's message"

    def test_duplicate_element(self) -> None:
        error = DuplicateElementError(kind="Beam", element_id="V1")
        assert str(error) == "Beam 'V1' already exists.", (
            "the text should match the engine's message"
        )

    def test_unknown_pillar(self) -> None:
        error = UnknownPillarError(owner_kind="Slab", owner_id="L1", pillar_id="P9")
        assert error.pillar_id == "P9", "the unknown pillar should be kept"
        assert str(error) == (
            "Slab 'L1': pillar 'P9' does not exist in the registry."
        ), "the text should match the engine's message"


class TestMaterialErrors:
    """Material errors keep the materials that broke the rule."""

    def test_concrete_class_too_low(self) -> None:
        error = ConcreteClassTooLowError(
            concrete="C20", minimum_fck=25, exposure_class=2
        )
        assert isinstance(error, MaterialError), "it is a material error"
        assert str(error) == (
            "Concrete C20 is below the minimum C25 required for exposure class 2."
        ), "the text should match the engine's message"

    def test_skin_steel(self) -> None:
        error = SkinSteelError(beam_height=70.0, min_height=60.0, steel_grade=25)
        assert isinstance(error, MaterialError), "it is a material error"
        assert str(error) == (
            "A beam with h = 70 cm > 60 cm needs skin reinforcement in CA-50 or "
            "CA-60, but the project steel is CA-25. Change the project steel to "
            "CA-50 or CA-60."
        ), "the text should match the engine's message"
        assert error.beam_id is None, "no beam should be set on creation"

    def test_skin_steel_with_beam(self) -> None:
        error = SkinSteelError(beam_height=70.0, min_height=60.0, steel_grade=25)
        error.beam_id = "V1"
        assert str(error).startswith("Beam 'V1': A beam with h = 70 cm"), (
            "the beam id should prefix the text once it is known"
        )
