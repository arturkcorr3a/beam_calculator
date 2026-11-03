"""Tests for src/detailing/overlaps.py.

Every case uses CA-50 in C30 and bars in a good bond zone with A_s,calc/A_s,ef = 1, so l_b = 33.357φ and a lap with every bar spliced (α_0t = 2.0) is 66.7φ.
"""

from dataclasses import replace

import pytest

from src.config import APP_CONFIG
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.lap_splice import LapSplice
from src.detailing.overlaps import resolve_overlaps
from src.detailing.post_processor import _STEPS  # pyright: ignore[reportPrivateUsage]
from src.detailing.rounding import round_detailing
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support

_HOOK = HookGeometry(pin_diameter=5.0, tip_length=8.0)  # standard CA-50 φ10 hook


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


def _bar(
    start: float,
    end: float,
    source: float,
    diameter_mm: float = 10,
    quantity: int = 2,
    is_bottom: bool = True,
    layer_index: int = 0,
) -> DetailedBar:
    """Build a main run of tensioned bars in a good bond zone, designed at one point"""
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        quantity=quantity,
        is_bottom=is_bottom,
        is_tensioned=True,
        layer_index=layer_index,
        y=4.0 if is_bottom else 56.0,
        start=start,
        end=end,
        source_positions=(source,),
        good_adherence=True,
        area_ratio=1.0,
    )


def _beam(*bars: DetailedBar) -> DetailingBeam:
    """Build a 20 x 60 cm detailing beam on pillars from −10 to 510 cm with the given bars"""
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(Support(0.0, -10.0, 10.0), Support(500.0, 490.0, 510.0)),
        bars=list(bars),
    )


def _extents(beam: DetailingBeam) -> list[tuple[int, float, float, float]]:
    """Return each run as (quantity, diameter, start, end), in order"""
    return [(bar.quantity, bar.diameter_mm, bar.start, bar.end) for bar in beam.bars]


class TestMerge:
    """Paired bars of the same diameter become one continuous run."""

    def test_same_diameter_merges(self) -> None:
        left = replace(_bar(20, 300, 100), left_hook=_HOOK, left_hook_length=6.0)
        right = replace(_bar(250, 480, 400), right_hook=_HOOK, right_hook_length=6.0)
        beam = _beam(left, right)
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 10, 20, 480)], "One 2φ10 run from 20 to 480 cm"
        merged = beam.bars[0]
        assert merged.left_hook == _HOOK and merged.right_hook == _HOOK, (
            "The outer hooks should be kept"
        )
        assert merged.source_positions == (100, 400), "Both points are the sources"
        assert beam.lap_splices == [], "A merge needs no lap"

    def test_touching_ends_merge(self) -> None:
        beam = _beam(_bar(20, 250, 100), _bar(250, 480, 400))
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 10, 20, 480)], "Runs that touch also merge"

    def test_partial_merge_keeps_extra_bars(self) -> None:
        beam = _beam(_bar(20, 300, 100, quantity=3), _bar(250, 480, 400))
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 10, 20, 480), (1, 10, 20, 300)], (
            "Two bars merge; the third keeps its length"
        )

    def test_merged_flags(self) -> None:
        left = replace(_bar(20, 300, 100), is_tensioned=False, area_ratio=0.8)
        right = replace(_bar(250, 480, 400), good_adherence=False, area_ratio=0.9)
        beam = _beam(left, right)
        resolve_overlaps(beam)
        merged = beam.bars[0]
        assert merged.is_tensioned, "Tensioned if either run was"
        assert not merged.good_adherence, "Good bond zone only if both were"
        assert merged.area_ratio == 0.9, "The larger area ratio is kept"

    def test_chain_merges_three_points(self) -> None:
        beam = _beam(_bar(20, 200, 100), _bar(150, 350, 250), _bar(300, 480, 400))
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 10, 20, 480)], "Three runs become one"
        assert beam.bars[0].source_positions == (100, 250, 400), "All three sources"

    def test_same_diameters_pair_first(self) -> None:
        beam = _beam(
            _bar(20, 300, 100, diameter_mm=16, quantity=1),
            _bar(20, 300, 100, diameter_mm=10, quantity=1),
            _bar(250, 480, 400, diameter_mm=10, quantity=1),
            _bar(250, 480, 400, diameter_mm=16, quantity=1),
        )
        resolve_overlaps(beam)
        assert sorted(_extents(beam)) == [(1, 10, 20, 480), (1, 16, 20, 480)], (
            "φ16 merges with φ16 and φ10 with φ10, instead of a φ16–φ10 lap"
        )


class TestTrim:
    """Paired bars of different diameters keep only a lap splice."""

    def test_different_diameters_trim_to_lap(self) -> None:
        left = replace(
            _bar(20, 400, 100, diameter_mm=12.5),
            right_hook=_HOOK,
            right_hook_length=6.0,
        )
        beam = _beam(left, _bar(200, 480, 400))
        resolve_overlaps(beam)
        # φ10 lap, all bars spliced: 66.71 → 67 cm, centered on 300 → [266, 333]
        assert _extents(beam) == [(2, 12.5, 20, 333), (2, 10, 266, 480)], (
            "Both runs should stop at the lap's ends (cm)"
        )
        assert beam.bars[0].right_hook is None, "The trimmed end loses its hook"
        assert beam.bars[0].right_hook_length == 0.0, "No hook, no extra length"
        assert beam.lap_splices == [
            LapSplice(
                is_bottom=True,
                layer_index=0,
                start=266,
                end=333,
                quantity=2,
                diameter_mm=10,
            )
        ], "The lap should be recorded with the smaller diameter"

    def test_overlap_within_lap_is_kept(self) -> None:
        beam = _beam(_bar(20, 300, 100, diameter_mm=12.5), _bar(250, 480, 400))
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 12.5, 20, 300), (2, 10, 250, 480)], (
            "A 50 cm overlap is shorter than the 67 cm lap, so both runs stay"
        )
        assert beam.lap_splices == [], "No lap is made"

    def test_partial_pairing(self) -> None:
        beam = _beam(
            _bar(20, 400, 100, diameter_mm=16, quantity=3),
            _bar(200, 480, 400, diameter_mm=12.5),
        )
        resolve_overlaps(beam)
        # 3 bars at the section after pairing, 2 spliced → α_0t = 2.0
        # φ12.5 lap: 83.39 → 84 cm, centered on 300 → [258, 342]
        assert _extents(beam) == [
            (2, 16, 20, 342),
            (1, 16, 20, 400),
            (2, 12.5, 258, 480),
        ], "Two φ16 lap with the φ12.5; the third φ16 keeps its length (cm)"
        assert len(beam.lap_splices) == 1, "Only one lap: lapped ends do not pair again"

    def test_share_counts_parallel_bars(self) -> None:
        beam = _beam(
            _bar(20, 400, 100, diameter_mm=12.5),
            _bar(200, 480, 400),
            _bar(0, 500, 250, quantity=4),
        )
        resolve_overlaps(beam)
        # 6 bars at the section, 2 spliced → 33 % → α_0t = 1.6 → 53.37 → 54 cm
        assert beam.lap_splices[0].length == 54, "α_0t = 1.6 for a third spliced"

    def test_share_counts_laps_in_same_section(self) -> None:
        beam = _beam(
            _bar(20, 400, 100, diameter_mm=12.5),
            _bar(200, 480, 400),
            _bar(0, 500, 250, quantity=4),
        )
        beam.lap_splices.append(
            LapSplice(
                is_bottom=True,
                layer_index=0,
                start=280,
                end=320,
                quantity=2,
                diameter_mm=10,
            )
        )
        resolve_overlaps(beam)
        # 4 of 6 bars spliced in the section → α_0t = 2.0 → 67 cm
        assert beam.lap_splices[-1].length == 67, (
            "A lap already in the section raises the share spliced"
        )

    def test_compressed_bars_use_compression_lap(self) -> None:
        left = replace(_bar(20, 400, 100, diameter_mm=12.5), is_tensioned=False)
        right = replace(_bar(200, 480, 400), is_tensioned=False)
        beam = _beam(left, right)
        resolve_overlaps(beam)
        # φ10 l_0c = l_b = 33.36 → 34 cm, centered on 300 → [283, 317]
        assert beam.lap_splices[0].start == 283, "Compression lap of 34 cm"
        assert beam.lap_splices[0].length == 34, "Compression lap of 34 cm"


class TestKept:
    """Pairs that cannot be spliced keep the bars as designed."""

    def test_more_than_half_spliced_with_two_layers(self) -> None:
        beam = _beam(
            _bar(20, 400, 100, diameter_mm=12.5),
            _bar(200, 480, 400),
            _bar(100, 350, 100, quantity=1, layer_index=1),
        )
        resolve_overlaps(beam)
        # 3 bars at the section, 2 spliced (67 %) with two layers → Table 9.3
        assert _extents(beam)[:2] == [(2, 12.5, 20, 400), (2, 10, 200, 480)], (
            "Both runs keep their length"
        )
        assert beam.lap_splices == [], "No lap is made"

    def test_bars_above_32_mm(self) -> None:
        beam = _beam(
            _bar(20, 400, 100, diameter_mm=40), _bar(200, 480, 400, diameter_mm=32)
        )
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 40, 20, 400), (2, 32, 200, 480)], (
            "Bars above 32 mm cannot be lap spliced"
        )

    def test_clamped_end(self) -> None:
        beam = _beam(_bar(20, 300, 100), _bar(250, 480, 400))
        beam.clamps = [
            DetailedClamps(
                diameter_mm=12.5,
                steel=Steel.CA50,
                quantity=1,
                width=12,
                leg_length=51,
                left=False,
                is_bottom=True,
                position=300,
                source_position=100,
            )
        ]
        resolve_overlaps(beam)
        assert _extents(beam) == [(2, 10, 20, 300), (2, 10, 250, 480)], (
            "An end with clamps is not merged away"
        )


class TestNoPair:
    """Runs that do not meet end to end, on the same face and layer, never pair."""

    def test_other_face(self) -> None:
        beam = _beam(_bar(20, 300, 100), _bar(250, 480, 400, is_bottom=False))
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "Bottom and top runs do not interact"

    def test_other_layer(self) -> None:
        beam = _beam(_bar(20, 300, 100), _bar(250, 480, 400, layer_index=1))
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "Runs of different layers do not interact"

    def test_same_source(self) -> None:
        beam = _beam(_bar(20, 300, 100), _bar(250, 480, 100))
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "Runs of the same point do not pair"

    def test_run_inside_another(self) -> None:
        beam = _beam(_bar(20, 480, 100), _bar(200, 300, 400))
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "A run inside another is a parallel bar"

    def test_gap_between_runs(self) -> None:
        beam = _beam(_bar(20, 200, 100), _bar(250, 480, 400))
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "Runs with a gap do not pair"

    def test_construction_bars_ignored(self) -> None:
        construction = replace(
            _bar(250, 480, 400), role=BarRole.CONSTRUCTION, source_positions=()
        )
        beam = _beam(_bar(20, 300, 100), construction)
        resolve_overlaps(beam)
        assert len(beam.bars) == 2, "Only main bars pair"


class TestStepOrder:
    """Overlaps resolve right after the rounding, on whole centimeters."""

    def test_runs_after_rounding(self) -> None:
        assert _STEPS[:2] == (round_detailing, resolve_overlaps), (
            "Rounding, then overlaps"
        )
