"""Tests for src/detailing/rounding.py."""

from dataclasses import replace

import pytest

from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.post_processor import _STEPS  # pyright: ignore[reportPrivateUsage]
from src.detailing.rounding import (
    left_end_limit,
    right_end_limit,
    round_bar,
    round_clamps,
    round_detailing,
    round_down,
    round_stirrups,
    round_up,
)
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support

_HOOK = HookGeometry(pin_diameter=8.0, tip_length=12.8)  # standard CA-50 φ16 hook


def _bar(
    start: float,
    end: float,
    diameter_mm: float = 16,
    left_hook: bool = False,
    right_hook: bool = False,
    source_position: float = 125.0,
) -> DetailedBar:
    """Build a bottom run of 2 bars with optional standard hooks (14.74 cm each)"""
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=True,
        is_tensioned=True,
        layer_index=0,
        y=4.43,
        start=start,
        end=end,
        left_hook=_HOOK if left_hook else None,
        right_hook=_HOOK if right_hook else None,
        left_hook_length=14.74 if left_hook else 0.0,
        right_hook_length=14.74 if right_hook else 0.0,
        source_positions=(source_position,),
        good_adherence=True,
        area_ratio=0.93,
    )


def _beam(nominal_covering: float = 2.5) -> DetailingBeam:
    """Build a 20 x 60 cm detailing beam on pillars whose outer faces are at −10 and 510 cm"""
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=nominal_covering,
        steel=Steel.CA50,
        supports=(
            Support(0.0, -10.0, 10.0),
            Support(250.0, 235.0, 265.0),
            Support(500.0, 490.0, 510.0),
        ),
    )


def _stirrups(*zones: StirrupZone) -> SpanStirrups:
    """Build φ6.3 span stirrups with the given zones (cm)"""
    return SpanStirrups(
        start_pillar_id="P1",
        end_pillar_id="P2",
        zones=zones,
        diameter_mm=6.3,
        steel=Steel.CA50,
    )


def _clamps(position: float, left: bool = False) -> DetailedClamps:
    """Build one φ12.5 clamp of a bottom run at x = 125 cm, bent at the given position (cm)"""
    return DetailedClamps(
        diameter_mm=12.5,
        steel=Steel.CA50,
        quantity=1,
        width=12.74,
        leg_length=50.9,
        left=left,
        is_bottom=True,
        position=position,
        source_position=125.0,
    )


class TestRoundUpDown:
    """Whole values within the tolerance are left as they are."""

    def test_round_up(self) -> None:
        assert round_up(234.2) == 235.0, "Fractions round up"
        assert round_up(235.0000001) == 235.0, "Float drift above a whole value stays"

    def test_round_down(self) -> None:
        assert round_down(25.8) == 25.0, "Fractions round down"
        assert round_down(24.9999999) == 25.0, "Float drift below a whole value stays"

    def test_negative_values(self) -> None:
        assert round_down(-7.5) == -8.0, "Down is towards −∞"
        assert round_up(-7.5) == -7.0, "Up is towards +∞"


class TestEndLimits:
    """Bar ends stop at the outer faces minus the end cover, in whole centimeters."""

    def test_straight_ends_use_nominal_cover(self) -> None:
        beam = _beam()
        assert left_end_limit(beam, 16, hooked=False) == -7.0, "−10 + 2.5 → −7 cm"
        assert right_end_limit(beam, 16, hooked=False) == 507.0, "510 − 2.5 → 507 cm"

    def test_hooked_ends_use_three_diameters(self) -> None:
        beam = _beam()
        assert left_end_limit(beam, 16, hooked=True) == -5.0, "−10 + 4.8 → −5 cm"
        assert right_end_limit(beam, 16, hooked=True) == 505.0, "510 − 4.8 → 505 cm"

    def test_hooked_ends_keep_larger_nominal_cover(self) -> None:
        beam = _beam()
        assert right_end_limit(beam, 8, hooked=True) == 507.0, (
            "φ8: 3φ = 2.4 cm < c_nom = 2.5 cm, so 510 − 2.5 → 507 cm"
        )


class TestRoundBar:
    """Ends round outward, except where they would pass the end limit."""

    def test_interior_ends_round_outward(self) -> None:
        bar = round_bar(_beam(), _bar(25.3, 234.6))
        assert (bar.start, bar.end) == (25.0, 235.0), "Start ↓ and end ↑ (cm)"

    def test_whole_ends_left_alone(self) -> None:
        bar = round_bar(_beam(), _bar(25.0000001, 234.9999999))
        assert (bar.start, bar.end) == (25.0, 235.0), "Float drift is not a fraction"

    def test_end_at_cover_limit_rounds_inward(self) -> None:
        bar = round_bar(_beam(), _bar(-7.5, 507.5))
        assert (bar.start, bar.end) == (-7.0, 507.0), (
            "Ends laid out at the outer faces ∓ 2.5 cm cover round inward (cm)"
        )

    def test_hooked_end_uses_hook_cover(self) -> None:
        bar = round_bar(_beam(), _bar(300.0, 505.2, right_hook=True))
        assert bar.end == 505.0, "510 − 3·1.6 = 505.2 rounds inward to 505 cm"

    def test_straight_end_short_of_limit_rounds_outward(self) -> None:
        bar = round_bar(_beam(), _bar(300.0, 505.2))
        assert bar.end == 506.0, "A straight end can reach 507 cm, so 505.2 → 506"

    def test_hooks_round_up(self) -> None:
        bar = round_bar(_beam(), _bar(25.0, 235.0, left_hook=True))
        assert bar.left_hook_length == 15.0, "14.74 cm → 15 cm"
        assert bar.right_hook_length == 0.0, "No hook stays 0"
        assert bar.total_length == 225.0, "210 cm straight + 15 cm hook"

    def test_other_fields_kept(self) -> None:
        source = _bar(25.3, 234.6, left_hook=True)
        bar = round_bar(_beam(), source)
        assert bar is not source, "A rounded copy is returned"
        assert bar == replace(source, start=25.0, end=235.0, left_hook_length=15.0), (
            "Only the ends and hook lengths change"
        )
        assert bar.role == BarRole.MAIN, "The role is kept"


class TestRoundClamps:
    """Legs round up, the width rounds down, and the bend follows the bars."""

    def test_rounds_and_follows_bar_end(self) -> None:
        anchored = round_bar(_beam(), _bar(300.0, 505.2, right_hook=True))
        clamps = round_clamps(_clamps(505.2), anchored)
        assert clamps.leg_length == 51.0, "50.9 cm → 51 cm"
        assert clamps.width == 12.0, "12.74 cm → 12 cm, still inside the stirrup"
        assert clamps.position == 505.0, "The bend follows the rounded bar end (cm)"
        assert clamps.total_length == 114.0, "2 × 51 + 12 cm"

    def test_left_clamps_follow_bar_start(self) -> None:
        anchored = round_bar(_beam(), _bar(-5.2, 200.0, left_hook=True))
        clamps = round_clamps(_clamps(-5.2, left=True), anchored)
        assert clamps.position == anchored.start == -5.0, (
            "Left clamps bend at the rounded start (cm)"
        )


class TestRoundStirrups:
    """Spacings round down; boundaries move towards the sparser zone."""

    def test_spacing_rounds_down_and_faces_kept(self) -> None:
        stirrups = round_stirrups(_stirrups(StirrupZone(10.5, 234.5, 24.438)))
        assert stirrups.zones == (StirrupZone(10.5, 234.5, 24.0),), (
            "24.438 → 24 cm; the zone stays between the pillars' faces"
        )

    def test_boundaries_move_towards_sparser_zone(self) -> None:
        stirrups = round_stirrups(
            _stirrups(
                StirrupZone(10.0, 60.3, 12.0),
                StirrupZone(60.3, 190.6, 24.0),
                StirrupZone(190.6, 235.0, 12.0),
            )
        )
        assert stirrups.zones == (
            StirrupZone(10.0, 61.0, 12.0),
            StirrupZone(61.0, 190.0, 24.0),
            StirrupZone(190.0, 235.0, 12.0),
        ), "The c/12 zones grow into the c/24 zone (cm)"

    def test_zones_with_same_rounded_spacing_merge(self) -> None:
        stirrups = round_stirrups(
            _stirrups(StirrupZone(10.0, 60.3, 24.4), StirrupZone(60.3, 235.0, 24.9))
        )
        assert stirrups.zones == (StirrupZone(10.0, 235.0, 24.0),), (
            "Both spacings round to 24 cm, so the zones merge"
        )

    def test_vanishing_zone_absorbed_by_denser_neighbor(self) -> None:
        stirrups = round_stirrups(
            _stirrups(
                StirrupZone(10.0, 100.2, 12.0),
                StirrupZone(100.2, 100.8, 24.0),
                StirrupZone(100.8, 235.0, 12.0),
            )
        )
        assert stirrups.zones == (StirrupZone(10.0, 235.0, 12.0),), (
            "The 0.6 cm c/24 zone vanishes and the c/12 zones join"
        )

    def test_vanishing_edge_zone_absorbed(self) -> None:
        stirrups = round_stirrups(
            _stirrups(StirrupZone(10.5, 10.8, 24.0), StirrupZone(10.8, 235.0, 12.0))
        )
        assert stirrups.zones == (StirrupZone(10.5, 235.0, 12.0),), (
            "The sparser edge zone ends at 10 cm, before the face, so the c/12 zone takes it"
        )

    def test_spacing_below_minimum_raises(self) -> None:
        with pytest.raises(ValueError, match="below the minimum"):
            round_stirrups(_stirrups(StirrupZone(10.0, 235.0, 4.7)))


class TestRoundDetailing:
    """The step rounds every bar, clamp set and stirrup set of the beam."""

    def test_rounds_everything(self) -> None:
        beam = _beam()
        beam.bars = [_bar(300.0, 505.2, right_hook=True), _bar(25.3, 234.6)]
        beam.clamps = [_clamps(505.2)]
        beam.stirrups = [_stirrups(StirrupZone(10.0, 235.0, 24.438))]

        round_detailing(beam)

        assert [(bar.start, bar.end) for bar in beam.bars] == [
            (300.0, 505.0),
            (25.0, 235.0),
        ], "Every bar should be rounded, in the same order"
        assert beam.clamps[0].position == 505.0, (
            "The clamps should bend at the rounded end of their bars"
        )
        assert beam.stirrups[0].zones[0].spacing == 24.0, (
            "The stirrups should be rounded"
        )

    def test_clamps_without_bar_raise(self) -> None:
        beam = _beam()
        beam.bars = [_bar(25.3, 234.6)]
        beam.clamps = [_clamps(505.2)]
        with pytest.raises(ValueError, match="No bar ends at the clamps' bend"):
            round_detailing(beam)

    def test_registered_as_first_step(self) -> None:
        assert _STEPS[0] is round_detailing, "Rounding should be the first step"
