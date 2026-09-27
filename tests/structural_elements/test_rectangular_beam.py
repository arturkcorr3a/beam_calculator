"""Unit tests for the RectangularBeam structural element."""

import pytest
from indeterminatebeam import Support  # type: ignore
from indeterminatebeam.loading import UDLV  # type: ignore

from src.config import APP_CONFIG
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx


@pytest.fixture
def simply_supported_beam() -> RectangularBeam:
    """Build a real C25/CA50 beam, 20x60 cm, 500 cm long, pinned both ends.

    A uniform vertical load of -1 kN/cm spans the full length. Construction runs
    the full indeterminatebeam analysis, so this fixture exercises ``__init__``,
    ``update_units_local``, ``_validate_width`` (valid path), ``area``, and
    ``get_max_bending_moment``.
    """
    return RectangularBeam(
        length=500.0,
        width=20.0,
        height=60.0,
        concrete=Concrete.C25,
        steel=Steel.CA50,
        supports=[Support(0.0, (1, 1, 0)), Support(500.0, (1, 1, 0))], # pyright: ignore[reportArgumentType]
        loads=[UDLV(-1.0, (0.0, 500.0))], # pyright: ignore[reportArgumentType]
        label="B1",
    )


class TestConstruction:
    """Tests for the beam construction and stored geometry/materials."""

    def test_area(self, simply_supported_beam: RectangularBeam) -> None:
        expected_area = 1200.0  # cm² (20 * 60)
        assert simply_supported_beam.area == expected_area, (
            "A 20x60 cm section should have a 1200 cm² area"
        )

    def test_stores_dimensions(
        self, simply_supported_beam: RectangularBeam
    ) -> None:
        assert simply_supported_beam.width == 20.0, "Width should be stored as given"
        assert simply_supported_beam.height == 60.0, (
            "Height should be stored as given"
        )
        assert simply_supported_beam.length == 500.0, (
            "Length should be stored as given"
        )

    def test_stores_materials(
        self, simply_supported_beam: RectangularBeam
    ) -> None:
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
                supports=[Support(0.0, (1, 1, 0)), Support(500.0, (1, 1, 0))], # pyright: ignore[reportArgumentType]
                loads=[UDLV(-1.0, (0.0, 500.0))], # pyright: ignore[reportArgumentType]
            )

    def test_at_minimum_constructs(self) -> None:
        beam = RectangularBeam(
            length=500.0,
            width=12.0,
            height=60.0,
            concrete=Concrete.C25,
            steel=Steel.CA50,
            supports=[Support(0.0, (1, 1, 0)), Support(500.0, (1, 1, 0))], # pyright: ignore[reportArgumentType]
            loads=[UDLV(-1.0, (0.0, 500.0))], # pyright: ignore[reportArgumentType]
        )
        assert beam.width == 12.0, "A 12 cm width sits exactly at the minimum"


class TestGetMaxBendingMoment:
    """Tests for the largest-magnitude bending moment and its position."""

    def test_simply_supported_udl(
        self, simply_supported_beam: RectangularBeam
    ) -> None:
        moment, position = simply_supported_beam.get_max_bending_moment()
        expected_moment = 3.125  # kN.m (w*L²/8 for the analysed unit load)
        expected_position = 250.0  # cm (midspan)
        assert_approx(
            moment,
            expected_moment,
            "Max moment of a simply supported UDL beam should be at midspan",
        )
        assert_approx(
            position,
            expected_position,
            "The max moment should occur at midspan (250 cm)",
        )


class TestNominalCovering:
    """Tests for the metaclass nominal-covering classproperty across exposure classes."""

    @pytest.mark.parametrize(
        ("exposure_class", "pavement_concrete", "expected"),
        [
            (1, "C20", 2.5),  # class 1, no discount (fck = 20)
            (1, "C25", 2.0),  # class 1, discount (fck > 20)
            (2, "C25", 3.0),  # class 2, no discount (fck = 25)
            (2, "C30", 2.5),  # class 2, discount (fck > 25)
            (3, "C30", 4.0),  # class 3, no discount (fck = 30)
            (3, "C40", 3.5),  # class 3, discount (fck > 30)
            (4, "C40", 5.0),  # class 4, no discount (fck = 40)
            (4, "C50", 4.5),  # class 4, discount (fck > 40)
        ],
    )
    def test_covering_by_exposure_class(
        self,
        monkeypatch: pytest.MonkeyPatch,
        exposure_class: int,
        pavement_concrete: str,
        expected: float,
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", exposure_class)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", pavement_concrete)
        assert RectangularBeam.nominal_covering == expected, (
            f"Exposure class {exposure_class} with {pavement_concrete} "
            f"should give {expected} cm nominal covering"
        )

    def test_invalid_exposure_class_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "exposure_class", 5)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", "C30")
        with pytest.raises(ValueError, match="Invalid exposure class"):
            _ = RectangularBeam.nominal_covering
