"""Unit tests for the RectangularBeam structural element."""

import pytest

from src.config import APP_CONFIG
from src.config_options import ExposureClass
from src.errors import BeamTooNarrowError, EnginePreconditionError, InputError
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support
from tests.helpers import assert_approx


@pytest.fixture
def simply_supported_beam() -> RectangularBeam:
    """Build a real CA50 beam section, 20x60 cm, 500 cm long.

    Exercises ``__init__``, ``_validate_width`` (valid path), and ``area``.
    """
    return RectangularBeam(
        length=500.0,
        width=20.0,
        height=60.0,
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

    def test_stores_steel(self, simply_supported_beam: RectangularBeam) -> None:
        assert simply_supported_beam.steel == Steel.CA50, (
            "Steel grade should be stored as given"
        )


class TestValidateWidth:
    """Tests for the ABNT NBR 6118 minimum beam width enforcement."""

    def test_below_minimum_raises(self) -> None:
        with pytest.raises(BeamTooNarrowError, match="at least 12.0 cm"):
            RectangularBeam(
                length=500.0,
                width=10.0,
                height=60.0,
                steel=Steel.CA50,
            )

    def test_at_minimum_constructs(self) -> None:
        beam = RectangularBeam(
            length=500.0,
            width=12.0,
            height=60.0,
            steel=Steel.CA50,
        )
        assert beam.width == 12.0, "A 12 cm width sits exactly at the minimum"


@pytest.fixture
def three_support_beam() -> RectangularBeam:
    """Build a 600 cm beam on three 20 cm wide supports at 0, 300 and 600 cm."""
    return RectangularBeam(
        length=600.0,
        width=20.0,
        height=60.0,
        steel=Steel.CA50,
        supports=[
            Support(center=0.0, left=-10.0, right=10.0),
            Support(center=300.0, left=290.0, right=310.0),
            Support(center=600.0, left=590.0, right=610.0),
        ],
    )


class TestSupports:
    """Tests for the beam's support list and its validation."""

    def test_default_point_supports_at_ends(
        self, simply_supported_beam: RectangularBeam
    ) -> None:
        assert simply_supported_beam.supports == [
            Support(0.0, 0.0, 0.0),
            Support(500.0, 500.0, 500.0),
        ], "Without supports, the beam should get zero-width supports at both ends"

    def test_stores_given_supports(self, three_support_beam: RectangularBeam) -> None:
        centers = [support.center for support in three_support_beam.supports]
        assert centers == [0.0, 300.0, 600.0], "Supports should be stored as given"

    def test_overlapping_supports_raise(self) -> None:
        with pytest.raises(InputError, match="without overlapping"):
            RectangularBeam(
                length=500.0,
                width=20.0,
                height=60.0,
                steel=Steel.CA50,
                supports=[
                    Support(center=0.0, left=-10.0, right=10.0),
                    Support(center=15.0, left=5.0, right=25.0),
                ],
            )

    def test_unordered_supports_raise(self) -> None:
        with pytest.raises(InputError, match="without overlapping"):
            RectangularBeam(
                length=500.0,
                width=20.0,
                height=60.0,
                steel=Steel.CA50,
                supports=[
                    Support(center=500.0, left=490.0, right=510.0),
                    Support(center=0.0, left=-10.0, right=10.0),
                ],
            )


class TestGetSupportFace:
    """Tests for the nearest support face lookup."""

    def test_mid_span_to_the_left(self, three_support_beam: RectangularBeam) -> None:
        face = three_support_beam.get_support_face(150.0, left=True)
        assert_approx(face, 10.0, "First support's right face is left of 150 cm")

    def test_mid_span_to_the_right(self, three_support_beam: RectangularBeam) -> None:
        face = three_support_beam.get_support_face(150.0, left=False)
        assert_approx(face, 290.0, "Interior support's left face is right of 150 cm")

    def test_end_support_center_to_the_right(
        self, three_support_beam: RectangularBeam
    ) -> None:
        face = three_support_beam.get_support_face(0.0, left=False)
        assert_approx(face, 10.0, "From the end support center, its inner face")

    def test_inside_interior_support(self, three_support_beam: RectangularBeam) -> None:
        left_face = three_support_beam.get_support_face(300.0, left=True)
        right_face = three_support_beam.get_support_face(300.0, left=False)
        assert_approx(left_face, 290.0, "Inside a support, its own left face")
        assert_approx(right_face, 310.0, "Inside a support, its own right face")

    def test_exactly_on_a_face(self, three_support_beam: RectangularBeam) -> None:
        left_face = three_support_beam.get_support_face(310.0, left=True)
        right_face = three_support_beam.get_support_face(310.0, left=False)
        assert_approx(left_face, 310.0, "A face on the position counts to the left")
        assert_approx(right_face, 310.0, "A face on the position counts to the right")

    def test_no_face_to_the_left_raises(
        self, three_support_beam: RectangularBeam
    ) -> None:
        with pytest.raises(
            EnginePreconditionError, match="No support face to the left"
        ):
            three_support_beam.get_support_face(-20.0, left=True)

    def test_no_face_to_the_right_raises(
        self, three_support_beam: RectangularBeam
    ) -> None:
        with pytest.raises(
            EnginePreconditionError, match="No support face to the right"
        ):
            three_support_beam.get_support_face(620.0, left=False)


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
        # Small aggregate (1.0 cm floor), so Table 7.2 governs
        monkeypatch.setattr(APP_CONFIG, "max_aggregate_size", 0.95)
        monkeypatch.setattr(APP_CONFIG, "exposure_class", exposure_class)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", pavement_concrete)
        assert RectangularBeam.nominal_covering == expected, (
            f"Exposure class {exposure_class} with {pavement_concrete} "
            f"should give {expected} cm nominal covering"
        )

    @pytest.mark.parametrize(
        ("exposure_class", "pavement_concrete", "max_aggregate_size", "expected"),
        [
            # class 1, C25: table 2.0 cm, 2.5 cm aggregate needs 2.5 cm
            (ExposureClass.WEAK, Concrete.C25, 2.5, 2.5),
            # class 2, C30: table 2.5 cm, 3.8 cm aggregate needs 3.5 cm
            (ExposureClass.MODERATE, Concrete.C30, 3.8, 3.5),
            # class 3, C30: table 4.0 cm beats the 3.5 cm from a 3.8 cm aggregate
            (ExposureClass.SEVERE, Concrete.C30, 3.8, 4.0),
        ],
    )
    def test_covering_raised_by_aggregate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        exposure_class: ExposureClass,
        pavement_concrete: Concrete,
        max_aggregate_size: float,
        expected: float,
    ) -> None:
        monkeypatch.setattr(APP_CONFIG, "max_aggregate_size", max_aggregate_size)
        monkeypatch.setattr(APP_CONFIG, "exposure_class", exposure_class)
        monkeypatch.setattr(APP_CONFIG, "pavement_concrete", pavement_concrete)
        assert RectangularBeam.nominal_covering == expected, (
            f"Exposure class {exposure_class} with {pavement_concrete} and a "
            f"{max_aggregate_size} cm aggregate should give {expected} cm nominal covering"
        )
