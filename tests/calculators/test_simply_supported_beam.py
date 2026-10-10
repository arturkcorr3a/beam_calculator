"""Tests for src/calculators/simply_supported_beam.py."""

import pytest

from src.calculators.simply_supported_beam import (
    SimplySupportedBeamDesign,
    design_simply_supported_beam,
)
from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

# 20 × 50 cm, 5 m: g = 25 kN/m³ × 0.20 m × 0.50 m = 2.5 kN/m
_LENGTH_CM = 500.0
_SELF_WEIGHT_KN_M = 2.5


@pytest.fixture
def design(monkeypatch: pytest.MonkeyPatch) -> SimplySupportedBeamDesign:
    """Dimension a 20 × 50 cm, 5 m, C30/CA50 beam under its own weight."""
    monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)
    section = RectangularBeam(_LENGTH_CM, 20.0, 50.0, Concrete.C30, Steel.CA50)
    return design_simply_supported_beam(section)


class TestSufficientSection:
    """A sufficient section is dimensioned with consistent loads and forces."""

    def test_self_weight(self, design: SimplySupportedBeamDesign) -> None:
        assert_approx(
            design.self_weight, _SELF_WEIGHT_KN_M, "self-weight should be 25·b·h (kN/m)"
        )

    def test_moment_at_midspan(self, design: SimplySupportedBeamDesign) -> None:
        assert_approx(
            design.calculator.bending_moment,
            _SELF_WEIGHT_KN_M * (_LENGTH_CM / 100) ** 2 / 8,
            "design moment should be qL²/8 (kN.m)",
            abs_tol=1e-3,
        )
        assert_approx(
            design.calculator.bending_moment_position,
            _LENGTH_CM / 2,
            "the greatest moment should be at mid-span (cm)",
            abs_tol=1e-3,
        )

    def test_shear_at_supports(self, design: SimplySupportedBeamDesign) -> None:
        assert_approx(
            design.characteristic_shear_force,
            _SELF_WEIGHT_KN_M * (_LENGTH_CM / 100) / 2,
            "greatest shear should be qL/2 (kN)",
            abs_tol=1e-3,
        )

    def test_reinforcement_is_chosen(self, design: SimplySupportedBeamDesign) -> None:
        assert design.calculator.tensioned_reinforcement.area > 0, (
            "a tensioned reinforcement should be chosen (cm²)"
        )
        assert design.calculator.tensioned_reinforcement.is_bottom_reinforcement, (
            "a sagging moment should tension the bottom face"
        )
        assert design.stirrups.diameter is not None, "stirrups should be chosen"


class TestUndersizedSection:
    """A section that cannot carry its own weight is reported as not verified."""

    def test_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", ExposureClass.MODERATE)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C20)
        section = RectangularBeam(3000.0, 12.0, 25.0, Concrete.C20, Steel.CA50)
        with pytest.raises(ValueError, match="exceeds maximum allowable limit"):
            design_simply_supported_beam(section)
