"""Unit tests for the SkinReinforcement selector (NBR 6118:2026 - Section 17.3.5.2.3)."""

import types
from collections.abc import Sequence
from typing import cast

import pytest

from src.calculators.rebar_calculator import RebarCalculator
from src.errors import SkinReinforcementNoRoomError
from src.properties.steel import Steel
from src.reinforcement.skin_reinforcement import SkinReinforcement
from src.structural_elements.rectangular_beam import RectangularBeam
from tests.helpers import assert_approx

_LAYER_EXTENT = 5.1  # cm, cover 2.5 + stirrup 1.0 + one φ16 layer
_CORNER_EXTENT = 4.5  # cm, cover 2.5 + stirrup 1.0 + a φ10 construction bar


def _beam(width: float, height: float, steel: Steel = Steel.CA50) -> RectangularBeam:
    """Build a beam double; the skin reinforcement only reads its steel and section"""
    return cast(
        RectangularBeam,
        types.SimpleNamespace(steel=steel, width=width, height=height),
    )


def _calculator(
    d: float, tensioned_extent: float, compressed_extent: float, is_bottom: bool
) -> types.SimpleNamespace:
    """Build a dimensioned RebarCalculator double from the extents of its bars (cm)"""
    return types.SimpleNamespace(
        d=d,
        tensioned_reinforcement=types.SimpleNamespace(
            face_extent=lambda: tensioned_extent,
            is_bottom_reinforcement=is_bottom,
        ),
        compressed_reinforcement=types.SimpleNamespace(
            face_extent=lambda: compressed_extent
        ),
    )


@pytest.fixture
def skin() -> SkinReinforcement:
    """Skin reinforcement of a 20x70 CA-50 beam: 1.4 cm² per face"""
    return SkinReinforcement(_beam(20.0, 70.0), id="SK")


class TestIsRequired:
    """Beams up to 60 cm high may omit the skin reinforcement."""

    def test_not_required_at_60(self) -> None:
        assert not SkinReinforcement.is_required(60.0), "h = 60 cm may omit it"

    def test_required_above_60(self) -> None:
        assert SkinReinforcement.is_required(61.0), "h = 61 cm needs it"


class TestSteel:
    """Only CA-50 and CA-60 bars may be used."""

    def test_ca60_is_accepted(self) -> None:
        skin = SkinReinforcement(_beam(20.0, 70.0, Steel.CA60))
        assert skin.steel == Steel.CA60, "CA-60 is allowed"

    def test_ca25_raises(self) -> None:
        with pytest.raises(
            ValueError, match=r"h = 70 cm > 60 cm .* project steel is CA-25\."
        ):
            SkinReinforcement(_beam(20.0, 70.0, Steel.CA25))


class TestRequiredArea:
    """0.10 % of the web area per face, capped at 5 cm²/m of web height."""

    def test_ratio_of_web_area(self, skin: SkinReinforcement) -> None:
        """0.001 x 20 x 70 = 1.4 cm²"""
        assert_approx(skin.required_area, 1.4, "Area per face (cm²)")

    def test_capped_per_meter_of_height(self) -> None:
        """0.001 x 120 x 70 = 8.4 cm² is capped at 5 x 0.70 = 3.5 cm²"""
        skin = SkinReinforcement(_beam(120.0, 70.0))
        assert_approx(skin.required_area, 3.5, "Capped area per face (cm²)")


class TestMaxSpacing:
    """The least of 20 cm, d/3 and 15φ."""

    def test_fixed_limit_governs(self) -> None:
        """d/3 = 30, 15φ16 = 24: 20 cm governs"""
        assert_approx(SkinReinforcement.max_spacing(90.0, 16), 20.0, "s_max (cm)")

    def test_depth_governs(self) -> None:
        """d/3 = 15 cm governs"""
        assert_approx(SkinReinforcement.max_spacing(45.0, 16), 15.0, "s_max (cm)")

    def test_diameter_governs(self) -> None:
        """15φ8 = 12 cm governs"""
        assert_approx(SkinReinforcement.max_spacing(90.0, 8), 12.0, "s_max (cm)")


class TestChooseFor:
    """Bars per face fill the web between the bottom and top bars."""

    def test_band_spans_the_whole_web(self, skin: SkinReinforcement) -> None:
        """Band 5.1-65.5 cm (60.4 cm): 5φ6.3 cover the area, but 15φ = 9.45 cm needs 6, still the least area"""
        layout = skin.choose_for(
            effective_depth=65.0,
            bottom_extent=_LAYER_EXTENT,
            top_extent=_CORNER_EXTENT,
        )
        assert_approx(layout.band_start, _LAYER_EXTENT, "band start (cm)")
        assert_approx(layout.band_end, 70.0 - _CORNER_EXTENT, "band end (cm)")
        assert layout.diameter_mm == 6.3, "φ6.3 gives the least area"
        assert layout.bars_per_face == 6, "the spacing limit adds a bar"
        assert layout.spacing == 9, "60.4 / 7 = 8.6 rounds to 9 cm, within 15φ"

    def test_bars_are_centered_in_the_band(self, skin: SkinReinforcement) -> None:
        """6φ6.3 c/9 in the 60.4 cm band leave (60.4 - 45) / 2 = 7.7 cm at each edge"""
        layout = skin.choose_for(
            effective_depth=65.0,
            bottom_extent=_LAYER_EXTENT,
            top_extent=_CORNER_EXTENT,
        )
        assert_approx(layout.edge_gap, 7.7, "gap at each band edge (cm)")
        expected = [12.8 + 9.0 * row for row in range(6)]  # cm
        for actual, height in zip(layout.heights, expected, strict=True):
            assert_approx(actual, height, "row height from the bottom face (cm)")

    def test_wide_edge_gaps_add_a_bar(self, skin: SkinReinforcement) -> None:
        """Band 55 cm: 5φ6.3 would need s ≥ (55 - 2 x 9.45) / 4 = 9.03 > 9 cm, so 6φ6.3 c/8 (7.5 cm edges)"""
        layout = skin.choose_for(
            effective_depth=65.0, bottom_extent=5.0, top_extent=10.0
        )
        assert layout.diameter_mm == 6.3, "φ6.3 gives the least area"
        assert layout.bars_per_face == 6, "no whole spacing fits five bars"
        assert layout.spacing == 8, "55 / 7 = 7.9 rounds to 8 cm"
        assert_approx(layout.edge_gap, 7.5, "edge gap within 15φ (cm)")

    def test_least_area_wins(self, skin: SkinReinforcement) -> None:
        """Band 20-40 cm: 3φ8 (1.51 cm²) beats 5φ6.3, 2φ10 and 2φ12.5"""
        layout = skin.choose_for(
            effective_depth=65.0, bottom_extent=20.0, top_extent=30.0
        )
        assert layout.diameter_mm == 8, "φ8 gives the least area"
        assert layout.bars_per_face == 3, "three bars cover 1.4 cm²"
        assert_approx(layout.spacing, 5.0, "spacing over the band (cm)")
        assert_approx(
            layout.area_per_face, 3 * 0.502655, "3φ8 per face (cm²)", abs_tol=1e-4
        )

    def test_band_too_narrow_for_whole_spacing_raises(
        self, skin: SkinReinforcement
    ) -> None:
        """A 2 cm band cannot hold the bars at a spacing of at least 1 cm"""
        with pytest.raises(
            SkinReinforcementNoRoomError, match="whole-centimeter spacing"
        ) as raised:
            skin.choose_for(effective_depth=65.0, bottom_extent=34.0, top_extent=34.0)
        assert_approx(raised.value.band_height, 2.0, "band left between the bars (cm)")
        assert raised.value.bars_per_face is not None, (
            "the error should keep the bars that did not fit"
        )

    def test_no_band_raises(self, skin: SkinReinforcement) -> None:
        """Bars 40 cm from the bottom and 35 cm from the top overlap in a 70 cm web"""
        with pytest.raises(
            SkinReinforcementNoRoomError, match="No room for skin reinforcement"
        ) as raised:
            skin.choose_for(effective_depth=65.0, bottom_extent=40.0, top_extent=35.0)
        assert_approx(raised.value.band_height, -5.0, "the bars overlap by 5 cm (cm)")
        assert raised.value.bars_per_face is None, "no bars were tried"


class TestChoose:
    """Each point's band runs between its bottom and top bars; the span keeps the most bars."""

    def test_top_tensioned_point_uses_compressed_bars_at_bottom(
        self, skin: SkinReinforcement
    ) -> None:
        """Tensioned bars on top (20 cm), compressed at the bottom (30 cm): band 30-50 cm"""
        calculators = cast(
            Sequence[RebarCalculator],
            [_calculator(65.0, 20.0, 30.0, is_bottom=False)],
        )
        layout = skin.choose(calculators)
        assert_approx(layout.band_start, 30.0, "band starts on the bottom bars (cm)")
        assert_approx(layout.band_end, 50.0, "band ends on the top bars (cm)")

    def test_keeps_most_bars(self, skin: SkinReinforcement) -> None:
        """The full-web band gives 6φ6.3; the 20 cm band gives 3φ8"""
        calculators = cast(
            Sequence[RebarCalculator],
            [
                _calculator(65.0, 20.0, 30.0, is_bottom=False),
                _calculator(65.0, _LAYER_EXTENT, _CORNER_EXTENT, is_bottom=True),
            ],
        )
        layout = skin.choose(calculators)
        assert layout.bars_per_face == 6, "the wider band needs more bars"
        assert layout.diameter_mm == 6.3, "φ6.3 is the wider band's choice"
        assert skin.layout is layout, "the choice is stored"

    def test_no_points_raises(self, skin: SkinReinforcement) -> None:
        with pytest.raises(ValueError, match="at least one interest point"):
            skin.choose([])
