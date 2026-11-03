"""Tests for src/detailing/construction_bars.py.

The beam is 20 x 60 cm (c_nom = 2.5 cm) on three 20 cm pillars, with outer faces at −10 and 510 cm and the middle pillar from 240 to 260 cm. Spans P1–P2 and P2–P3 have φ6.3 stirrups from 10 to 240 and from 260 to 490 cm. In C30, the φ6.3 construction lap is 20 cm on both faces (20 cm governs).
"""

from dataclasses import replace

import pytest

from src.config import APP_CONFIG
from src.detailing.construction_bars import add_construction_bars
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.overlaps import resolve_overlaps
from src.detailing.post_processor import _STEPS  # pyright: ignore[reportPrivateUsage]
from src.detailing.span_stirrups import SpanStirrups
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.support import Support
from tests.helpers import assert_approx


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


def _bar(
    start: float,
    end: float,
    source: float,
    is_bottom: bool,
    quantity: int = 2,
    layer_index: int = 0,
) -> DetailedBar:
    """Build a main run of φ10 bars designed at one point"""
    return DetailedBar(
        diameter_mm=10,
        steel=Steel.CA50,
        quantity=quantity,
        is_bottom=is_bottom,
        is_tensioned=True,
        layer_index=layer_index,
        y=3.6 if is_bottom else 56.4,
        start=start,
        end=end,
        source_positions=(source,),
    )


def _stirrups(
    start_id: str, end_id: str, start: float, end: float, diameter_mm: float
) -> SpanStirrups:
    """Build one span's stirrups in a single zone at 15 cm"""
    return SpanStirrups(
        start_pillar_id=start_id,
        end_pillar_id=end_id,
        zones=(StirrupZone(start, end, 15.0),),
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
    )


def _beam(*bars: DetailedBar, second_span_diameter: float = 6.3) -> DetailingBeam:
    """Build the two-span detailing beam with the given bars"""
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(
            Support(0.0, -10.0, 10.0),
            Support(250.0, 240.0, 260.0),
            Support(500.0, 490.0, 510.0),
        ),
        bars=list(bars),
        stirrups=[
            _stirrups("P1", "P2", 10.0, 240.0, 6.3),
            _stirrups("P2", "P3", 260.0, 490.0, second_span_diameter),
        ],
    )


def _full_face(is_bottom: bool) -> DetailedBar:
    """Build a run covering a whole face"""
    return _bar(-7, 507, 250, is_bottom)


def _construction(beam: DetailingBeam, is_bottom: bool) -> list[tuple[float, float]]:
    """Return the extents of the construction runs on one face, left to right (cm)"""
    return [
        (bar.start, bar.end)
        for bar in beam.bars_on_face(is_bottom)
        if bar.role == BarRole.CONSTRUCTION
    ]


class TestTopGaps:
    """Porta-estribos fill the top between negative-moment groups."""

    def test_gaps_between_negative_groups(self) -> None:
        beam = _beam(
            _bar(-7, 100, 0, is_bottom=False),
            _bar(200, 300, 250, is_bottom=False),
            _bar(400, 507, 500, is_bottom=False),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(80, 220), (280, 420)], (
            "Each gap gets bars lapped 20 cm into the groups on both sides (cm)"
        )
        assert _construction(beam, is_bottom=True) == [], "The bottom is covered"

    def test_construction_bar_fields(self) -> None:
        beam = _beam(
            _bar(-7, 100, 0, is_bottom=False),
            _bar(200, 507, 500, is_bottom=False),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        bar = next(b for b in beam.bars if b.role == BarRole.CONSTRUCTION)
        assert (bar.quantity, bar.diameter_mm) == (2, 6.3), "2φ6.3, the stirrup φ"
        assert_approx(
            bar.y, 60 - (2.5 + 0.63 + 0.315), "Inside the top stirrup corner (cm)"
        )
        assert not bar.is_tensioned, "Construction bars carry no calculated force"
        assert bar.left_hook is None and bar.right_hook is None, "No hooks"
        assert bar.source_positions == (), "Not designed at an interest point"
        assert not bar.good_adherence, "56.6 cm in a 60 cm beam is in the poor zone"


class TestBottomGaps:
    """Construction bars fill the bottom where the span bars stop short of each other."""

    def test_gap_across_interior_pillar(self) -> None:
        beam = _beam(
            _bar(3, 230, 125, is_bottom=True),
            _bar(270, 497, 375, is_bottom=True),
            _full_face(is_bottom=False),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=True) == [(210, 290)], (
            "One bar across the middle pillar, lapped into both span groups (cm)"
        )
        bar = next(b for b in beam.bars if b.role == BarRole.CONSTRUCTION)
        assert_approx(
            bar.y, 2.5 + 0.63 + 0.315, "Inside the bottom stirrup corner (cm)"
        )
        assert bar.good_adherence, "The bottom corner is in the good zone"

    def test_gap_inside_pillar_needs_no_bar(self) -> None:
        beam = _beam(
            _bar(3, 245, 125, is_bottom=True),
            _bar(255, 497, 375, is_bottom=True),
            _full_face(is_bottom=False),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=True) == [], (
            "A gap inside the pillar, where there are no stirrups, gets no bar"
        )

    def test_larger_stirrup_diameter_across_pillar(self) -> None:
        beam = _beam(
            _bar(3, 230, 125, is_bottom=True),
            _bar(270, 497, 375, is_bottom=True),
            _full_face(is_bottom=False),
            second_span_diameter=8.0,
        )
        add_construction_bars(beam)
        bar = next(b for b in beam.bars if b.role == BarRole.CONSTRUCTION)
        assert bar.diameter_mm == 8.0, "A gap across both spans takes the larger φ_t"


class TestBeamEnds:
    """A gap that reaches a beam end runs to the end limit, without a hook."""

    def test_gaps_reaching_both_ends(self) -> None:
        beam = _beam(_bar(200, 300, 250, is_bottom=False), _full_face(is_bottom=True))
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(-7, 220), (280, 507)], (
            "Bars run to the outer faces minus 2.5 cm cover, rounded inward (cm)"
        )

    def test_face_without_bars(self) -> None:
        beam = _beam(_full_face(is_bottom=True))
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(-7, 507)], (
            "A face with no bars gets one construction run end to end (cm)"
        )


class TestCoverage:
    """A point is covered with at least two layer-0 bars."""

    def test_no_gap_no_bar(self) -> None:
        beam = _beam(_full_face(is_bottom=True), _full_face(is_bottom=False))
        add_construction_bars(beam)
        assert len(beam.bars) == 2, "Fully covered faces get nothing"

    def test_one_bar_is_a_gap(self) -> None:
        beam = _beam(
            _bar(-7, 507, 250, is_bottom=False, quantity=1),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(-7, 507)], (
            "A single bar does not fill both corners"
        )

    def test_single_bars_of_two_points_add_up(self) -> None:
        beam = _beam(
            _bar(-7, 300, 0, is_bottom=False, quantity=1),
            _bar(200, 507, 500, is_bottom=False, quantity=1),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(-7, 220), (280, 507)], (
            "Two single bars cover 200–300 cm together (cm)"
        )

    def test_second_layer_does_not_count(self) -> None:
        beam = _beam(
            _bar(-7, 507, 250, is_bottom=False, layer_index=1),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(-7, 507)], (
            "Layer-1 bars do not sit in the stirrup corners"
        )


class TestShortCoveredStretch:
    """Gaps whose bars would overlap get a single construction run."""

    def test_gaps_merge_over_short_stretch(self) -> None:
        beam = _beam(
            _bar(-7, 100, 0, is_bottom=False),
            _bar(130, 160, 150, is_bottom=False),
            _bar(400, 507, 500, is_bottom=False),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(80, 420)], (
            "The 30 cm stretch is shorter than two 20 cm laps, so one run fills both gaps"
        )

    def test_gaps_kept_apart_over_long_stretch(self) -> None:
        beam = _beam(
            _bar(-7, 100, 0, is_bottom=False),
            _bar(130, 180, 150, is_bottom=False),
            _bar(400, 507, 500, is_bottom=False),
            _full_face(is_bottom=True),
        )
        add_construction_bars(beam)
        assert _construction(beam, is_bottom=False) == [(80, 150), (160, 420)], (
            "A 50 cm stretch is longer than two laps, so each gap gets its run"
        )


class TestStepOrder:
    """Construction bars are added after the overlaps are resolved."""

    def test_runs_after_overlaps(self) -> None:
        index = _STEPS.index(add_construction_bars)
        assert _STEPS[index - 1] is resolve_overlaps, "Overlaps, then construction bars"

    def test_overlaps_ignore_construction_bars(self) -> None:
        beam = _beam(_bar(200, 300, 250, is_bottom=False), _full_face(is_bottom=True))
        add_construction_bars(beam)
        before = list(beam.bars)
        resolve_overlaps(beam)
        assert beam.bars == before, (
            "Construction runs never merge or trim with main runs"
        )

    def test_main_bars_untouched(self) -> None:
        main = _bar(200, 300, 250, is_bottom=False)
        beam = _beam(main, _full_face(is_bottom=True))
        add_construction_bars(beam)
        assert beam.bars[0] == replace(main), "The main runs keep their extents"
        assert beam.lap_splices == [], "Construction laps are not recorded as splices"
