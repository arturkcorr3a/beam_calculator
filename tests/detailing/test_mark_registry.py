"""Tests for src/detailing/mark_registry.py."""

from dataclasses import replace

from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.mark_registry import (
    MarkRegistry,
    bar_key,
    clamp_key,
    stirrup_key,
)
from src.detailing.span_stirrups import SpanStirrups
from src.properties.steel import Steel
from src.reinforcement.stirrups import StirrupZone
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support

_HOOK = HookGeometry(pin_diameter=5.0, tip_length=8.0)  # standard CA-50 φ10 hook


def _bar(
    start: float = 0,
    end: float = 300,
    is_bottom: bool = True,
    layer_index: int = 0,
    diameter_mm: float = 10,
) -> DetailedBar:
    """Build a run of 2 straight bars"""
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=is_bottom,
        is_tensioned=True,
        layer_index=layer_index,
        y=4.0 if is_bottom else 56.0,
        start=start,
        end=end,
    )


def _clamps(leg_length: float = 51, width: float = 12) -> DetailedClamps:
    """Build one φ12.5 clamp"""
    return DetailedClamps(
        diameter_mm=12.5,
        steel=Steel.CA50,
        quantity=1,
        width=width,
        leg_length=leg_length,
        left=False,
        is_bottom=True,
        position=300,
        source_position=125,
    )


def _stirrups(diameter_mm: float = 6.3) -> SpanStirrups:
    """Build a span's stirrups in one zone"""
    return SpanStirrups(
        start_pillar_id="P1",
        end_pillar_id="P2",
        zones=(StirrupZone(10.0, 490.0, 15.0),),
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
    )


def _beam(width: float = 20.0, height: float = 60.0) -> DetailingBeam:
    """Build an empty detailing beam with the given section (cm) and 2.5 cm cover"""
    return DetailingBeam(
        beam_id="V1",
        width=width,
        height=height,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)),
    )


class TestBarKey:
    """Two bars are identical when they have the same shape and cut length."""

    def test_position_and_face_do_not_matter(self) -> None:
        assert bar_key(_bar(0, 300)) == bar_key(_bar(100, 400, is_bottom=False)), (
            "A 300 cm φ10 bar is the same bar anywhere in the beam"
        )

    def test_role_does_not_matter(self) -> None:
        construction = replace(_bar(), role=BarRole.CONSTRUCTION)
        assert bar_key(_bar()) == bar_key(construction), (
            "A construction bar can be the same physical bar as a main one"
        )

    def test_one_centimeter_is_another_bar(self) -> None:
        assert bar_key(_bar(0, 300)) != bar_key(_bar(0, 301)), "1 cm longer"

    def test_diameter_is_another_bar(self) -> None:
        assert bar_key(_bar()) != bar_key(_bar(diameter_mm=8)), "Another diameter"

    def test_mirrored_hooks_are_the_same_bar(self) -> None:
        left = replace(_bar(), left_hook=_HOOK, left_hook_length=6.0)
        right = replace(_bar(), right_hook=_HOOK, right_hook_length=6.0)
        assert bar_key(left) == bar_key(right), "Turned around, it is the same bar"

    def test_hook_makes_another_bar(self) -> None:
        hooked = replace(_bar(), left_hook=_HOOK, left_hook_length=6.0)
        assert bar_key(hooked) != bar_key(_bar()), "A hook changes the shape"

    def test_bend_diameter_makes_another_bar(self) -> None:
        standard = replace(_bar(), left_hook=_HOOK, left_hook_length=30.0)
        frame_joint = replace(
            standard, left_hook=HookGeometry(pin_diameter=15.0, tip_length=8.0)
        )
        assert bar_key(standard) != bar_key(frame_joint), "Another bend diameter"

    def test_fractional_tips_with_same_cut_are_the_same_bar(self) -> None:
        first = replace(
            _bar(),
            left_hook=HookGeometry(pin_diameter=15.0, tip_length=30.2),
            left_hook_length=37.0,
        )
        second = replace(
            first, left_hook=HookGeometry(pin_diameter=15.0, tip_length=30.4)
        )
        assert bar_key(first) == bar_key(second), (
            "Both are bent the same and cut to 37 cm"
        )


class TestOtherKeys:
    """Clamps and stirrups have identities of their own."""

    def test_clamps(self) -> None:
        assert clamp_key(_clamps()) == clamp_key(_clamps()), "Same clamp"
        assert clamp_key(_clamps()) != clamp_key(_clamps(leg_length=52)), "Longer legs"
        assert clamp_key(_clamps()) != clamp_key(_clamps(width=13)), "Wider U"

    def test_stirrup_outer_dimensions(self) -> None:
        key = stirrup_key(_beam(19.0, 65.0), 6.3, Steel.CA50)
        assert (key.width, key.height) == (14.0, 60.0), "Section minus both covers (cm)"

    def test_stirrups_of_equal_sections_match(self) -> None:
        assert stirrup_key(_beam(), 6.3, Steel.CA50) == stirrup_key(
            _beam(), 6.3, Steel.CA50
        ), "Same section and diameter"
        assert stirrup_key(_beam(), 6.3, Steel.CA50) != stirrup_key(
            _beam(height=70.0), 6.3, Steel.CA50
        ), "Another section"


class TestMarkFor:
    """New keys get the next mark; known keys keep theirs."""

    def test_numbers_new_keys_in_order(self) -> None:
        registry = MarkRegistry()
        assert registry.mark_for(bar_key(_bar(0, 300))) == "N1", "First key"
        assert registry.mark_for(bar_key(_bar(0, 400))) == "N2", "Second key"

    def test_known_key_keeps_its_mark(self) -> None:
        registry = MarkRegistry()
        registry.mark_for(bar_key(_bar(0, 300)))
        registry.mark_for(bar_key(_bar(0, 400)))
        assert registry.mark_for(bar_key(_bar(50, 350))) == "N1", "Same 300 cm bar"

    def test_kinds_never_collide(self) -> None:
        registry = MarkRegistry()
        marks = {
            registry.mark_for(bar_key(_bar())),
            registry.mark_for(clamp_key(_clamps())),
            registry.mark_for(stirrup_key(_beam(), 12.5, Steel.CA50)),
        }
        assert marks == {"N1", "N2", "N3"}, "A bar, a clamp and a stirrup are different"


class TestAssign:
    """Marks are written bottom face first, then clamps, then stirrups."""

    def test_order_within_a_beam(self) -> None:
        beam = _beam()
        top = _bar(0, 100, is_bottom=False)
        second_layer = _bar(0, 200, layer_index=1)
        late = _bar(300, 600)
        early = _bar(0, 400)
        beam.bars = [top, second_layer, late, early]
        beam.clamps = [_clamps()]
        beam.stirrups = [_stirrups()]

        MarkRegistry().assign(beam)

        assert early.mark == "N1", "Bottom face, layer 0, leftmost"
        assert late.mark == "N2", "Bottom face, layer 0, next"
        assert second_layer.mark == "N3", "Bottom face, layer 1"
        assert top.mark == "N4", "Top face"
        assert beam.clamps[0].mark == "N5", "Clamps after the bars"
        assert beam.stirrups[0].mark == "N6", "Stirrups last"

    def test_identical_bars_in_a_beam_share_a_mark(self) -> None:
        beam = _beam()
        beam.bars = [_bar(0, 300), _bar(200, 500, is_bottom=False)]
        MarkRegistry().assign(beam)
        assert [bar.mark for bar in beam.bars] == ["N1", "N1"], "Same 300 cm φ10 bar"

    def test_same_bar_in_two_beams_shares_a_mark(self) -> None:
        registry = MarkRegistry()
        first, second = _beam(), _beam()
        first.bars = [_bar(0, 300)]
        second.bars = [_bar(0, 250), _bar(100, 400)]
        registry.assign(first)
        registry.assign(second)
        assert [bar.mark for bar in second.bars] == ["N2", "N1"], (
            "The 300 cm bar keeps the mark it got in the first beam"
        )

    def test_spans_with_same_stirrups_share_a_mark(self) -> None:
        beam = _beam()
        beam.stirrups = [_stirrups(), _stirrups(), _stirrups(diameter_mm=8)]
        MarkRegistry().assign(beam)
        assert [stirrups.mark for stirrups in beam.stirrups] == ["N1", "N1", "N2"], (
            "Spacing zones do not change the stirrup; the diameter does"
        )
