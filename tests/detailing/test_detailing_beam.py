"""Tests for src/detailing/detailing_beam.py."""

import pytest

from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailing_beam import DetailingBeam
from src.properties.steel import Steel
from src.structural_elements.support import Support


def _bar(
    start: float, end: float, is_bottom: bool = True, layer_index: int = 0
) -> DetailedBar:
    """Build a 2φ10 run on the given face and layer"""
    return DetailedBar(
        diameter_mm=10,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=is_bottom,
        is_tensioned=True,
        layer_index=layer_index,
        y=4.0 if is_bottom else 56.0,
        start=start,
        end=end,
    )


def _beam(bars: list[DetailedBar]) -> DetailingBeam:
    """Build a 20 x 60 cm detailing beam on pillars from −10 to 510 cm"""
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)),
        bars=bars,
    )


class TestExtent:
    """The beam runs between the end pillars' outer faces."""

    def test_start_and_end(self) -> None:
        beam = _beam([])
        assert (beam.start, beam.end) == (-10.0, 510.0), "Outer faces (cm)"

    def test_needs_two_supports(self) -> None:
        with pytest.raises(ValueError, match="at least 2 supports"):
            DetailingBeam(
                beam_id="V1",
                width=20.0,
                height=60.0,
                nominal_covering=2.5,
                steel=Steel.CA50,
                supports=(Support(0.0, -10.0, 10.0),),
            )


class TestBarsOnFace:
    """bars_on_face filters a face and orders by layer, then left to right."""

    def test_filters_and_orders(self) -> None:
        late = _bar(300.0, 480.0)
        early = _bar(20.0, 200.0)
        second_layer = _bar(0.0, 100.0, layer_index=1)
        top = _bar(0.0, 150.0, is_bottom=False)
        beam = _beam([late, top, second_layer, early])
        assert beam.bars_on_face(is_bottom=True) == [early, late, second_layer], (
            "Bottom bars by layer, then by start"
        )
        assert beam.bars_on_face(is_bottom=False) == [top], "Only the top bar"


class TestBarsAt:
    """bars_at returns the bars of a face covering a position, ends included."""

    def test_covering_bars(self) -> None:
        left = _bar(20.0, 200.0)
        right = _bar(200.0, 480.0)
        beam = _beam([left, right, _bar(0.0, 500.0, is_bottom=False)])
        assert beam.bars_at(100.0, is_bottom=True) == [left], "Only the left bar"
        assert beam.bars_at(200.0, is_bottom=True) == [left, right], (
            "Both bars touch x = 200 cm"
        )
        assert beam.bars_at(490.0, is_bottom=True) == [], "No bottom bar at 490 cm"
