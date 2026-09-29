"""Unit tests for the Rebar reinforcement bar dataclass."""

import pytest

from src.properties.steel import Steel
from src.structural_elements.rebar import Rebar
from tests.helpers import assert_approx


@pytest.fixture
def rebar_ca50_10mm() -> Rebar:
    """Build a CA50 10 mm rebar for reuse across tests."""
    return Rebar(diameter_mm=10, steel=Steel.CA50)


class TestPostInit:
    """Tests for the diameter-availability validation in __post_init__."""

    def test_valid_diameter_constructs(self) -> None:
        rebar = Rebar(diameter_mm=10, steel=Steel.CA50)
        assert rebar.diameter_mm == 10, "A 10 mm bar is available for CA50"

    def test_invalid_diameter_raises(self) -> None:
        with pytest.raises(ValueError, match="not available"):
            Rebar(diameter_mm=7.5, steel=Steel.CA50)


class TestEffectiveCovering:
    """Tests for the effective covering (max of bar diameter in cm and nominal)."""

    def test_diameter_governs(self, rebar_ca50_10mm: Rebar) -> None:
        expected_covering = 1.0  # cm (max(10/10, 0.5) -> bar diameter wins)
        assert rebar_ca50_10mm.effective_covering(0.5) == expected_covering, (
            "A 10 mm bar (1.0 cm) should govern over a 0.5 cm nominal cover"
        )

    def test_nominal_governs(self, rebar_ca50_10mm: Rebar) -> None:
        expected_covering = 2.0  # cm (max(10/10, 2.0) -> nominal cover wins)
        assert rebar_ca50_10mm.effective_covering(2.0) == expected_covering, (
            "A 2.0 cm nominal cover should govern over a 10 mm bar (1.0 cm)"
        )


class TestAreaCm2:
    """Tests for the rebar cross-sectional area."""

    def test_10mm_bar(self, rebar_ca50_10mm: Rebar) -> None:
        expected_area = 0.7853981633974483  # cm² (pi * 1.0² / 4)
        assert_approx(
            rebar_ca50_10mm.area_cm2,
            expected_area,
            "A 10 mm (1.0 cm) bar should have area pi/4 cm²",
        )


class TestStartEndPosition:
    """Tests for the start/end position derived from center and lengths."""

    def test_start_position(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.center = 100.0
        rebar_ca50_10mm.left_length = 20.0
        expected_start = 80.0  # cm (100 - 20)
        assert rebar_ca50_10mm.start_position == expected_start, (
            "Start position should be center minus left length"
        )

    def test_end_position(self, rebar_ca50_10mm: Rebar) -> None:
        rebar_ca50_10mm.center = 100.0
        rebar_ca50_10mm.right_length = 30.0
        expected_end = 130.0  # cm (100 + 30)
        assert rebar_ca50_10mm.end_position == expected_end, (
            "End position should be center plus right length"
        )
