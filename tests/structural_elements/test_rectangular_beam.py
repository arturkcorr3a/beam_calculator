"""Unit tests for the RectangularBeam structural element."""

import pytest

from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam


@pytest.fixture
def simply_supported_beam() -> RectangularBeam:
    """Build a real C25/CA50 beam section, 20x60 cm, 500 cm long.

    Exercises ``__init__``, ``_validate_width`` (valid path), and ``area``.
    """
    return RectangularBeam(
        length=500.0,
        width=20.0,
        height=60.0,
        concrete=Concrete.C25,
        steel=Steel.CA50,
        label="B1",
    )


class TestConstruction:
    """Tests for the beam construction and stored geometry/materials."""

    def test_area(self, simply_supported_beam: RectangularBeam) -> None:
        expected_area = 1200.0  # cm² (20 * 60)
        assert simply_supported_beam.area == expected_area, (
            "A 20x60 cm section should have a 1200 cm² area"
        )

    def test_stores_dimensions(self, simply_supported_beam: RectangularBeam) -> None:
        assert simply_supported_beam.width == 20.0, "Width should be stored as given"
        assert simply_supported_beam.height == 60.0, "Height should be stored as given"
        assert simply_supported_beam.length == 500.0, "Length should be stored as given"

    def test_stores_materials(self, simply_supported_beam: RectangularBeam) -> None:
        assert simply_supported_beam.concrete == Concrete.C25, (
            "Concrete class should be stored as given"
        )
        assert simply_supported_beam.steel == Steel.CA50, (
            "Steel grade should be stored as given"
        )


class TestValidateWidth:
    """Tests for the ABNT NBR 6118 minimum beam width enforcement."""

    def test_below_minimum_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 12.0 cm"):
            RectangularBeam(
                length=500.0,
                width=10.0,
                height=60.0,
                concrete=Concrete.C25,
                steel=Steel.CA50,
            )

    def test_at_minimum_constructs(self) -> None:
        beam = RectangularBeam(
            length=500.0,
            width=12.0,
            height=60.0,
            concrete=Concrete.C25,
            steel=Steel.CA50,
        )
        assert beam.width == 12.0, "A 12 cm width sits exactly at the minimum"


class TestNominalCovering:
    """Tests for the metaclass nominal-covering classproperty across exposure classes."""

    @pytest.mark.parametrize(
        ("exposure_class", "pavement_concrete", "expected"),
        [
            (ExposureClass.WEAK, Concrete.C20, 2.5),  # class 1, no discount (fck = 20)
            (ExposureClass.WEAK, Concrete.C25, 2.0),  # class 1, discount (fck > 20)
            (
                ExposureClass.MODERATE,
                Concrete.C25,
                3.0,
            ),  # class 2, no discount (fck = 25)
            (ExposureClass.MODERATE, Concrete.C30, 2.5),  # class 2, discount (fck > 25)
            (
                ExposureClass.SEVERE,
                Concrete.C30,
                4.0,
            ),  # class 3, no discount (fck = 30)
            (ExposureClass.SEVERE, Concrete.C40, 3.5),  # class 3, discount (fck > 30)
            (
                ExposureClass.VERY_SEVERE,
                Concrete.C40,
                5.0,
            ),  # class 4, no discount (fck = 40)
            (
                ExposureClass.VERY_SEVERE,
                Concrete.C50,
                4.5,
            ),  # class 4, discount (fck > 40)
        ],
    )
    def test_covering_by_exposure_class(
        self,
        monkeypatch: pytest.MonkeyPatch,
        exposure_class: ExposureClass,
        pavement_concrete: Concrete,
        expected: float,
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", exposure_class)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", pavement_concrete)
        assert RectangularBeam.nominal_covering == expected, (
            f"Exposure class {exposure_class} with {pavement_concrete} "
            f"should give {expected} cm nominal covering"
        )
