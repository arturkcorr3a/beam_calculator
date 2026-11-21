"""Tests for src/detailing/splitting.py.

Every case uses CA-50 in C30 and bars in a good bond zone with A_s,calc/A_s,ef = 1. A φ10 tension lap is 66.71 → 67 cm with every bar spliced (α_0t = 2.0) and 60.04 → 61 cm with half (α_0t = 1.8). The beam runs between pillars with outer faces at −10 cm and 10 cm past the bars' far end.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import cast

import pytest

from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.lap_splice_calculator import construction_lap_length
from src.config import APP_CONFIG
from src.detailing.construction_bars import add_construction_bars
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.lap_splice import LapSplice
from src.detailing.post_processor import _STEPS  # pyright: ignore[reportPrivateUsage]
from src.detailing.rounding import round_up
from src.detailing.splitting import MAX_BAR_LENGTH, split_long_bars
from src.logger import suppress_logging
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pavement import Pavement
from src.pavement_elements.pillar import Pillar
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rebar import HookGeometry
from src.structural_elements.support import Support

_HOOK = HookGeometry(pin_diameter=5.0, tip_length=8.0)  # standard CA-50 φ10 hook


@pytest.fixture(autouse=True)
def pinned_concrete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the project concrete to C30 for every test in this module"""
    monkeypatch.setattr(APP_CONFIG, "pavement_concrete", Concrete.C30)


@dataclass
class _Analysis:
    """Structural analysis stub with a given bending moment diagram (kN.m)"""

    length: float
    moment: Callable[[float], float]

    def bending_moment(self, position: float) -> float:
        return self.moment(position)


def _no_moment(position: float) -> float:
    """Return a moment of zero everywhere, so every position ties"""
    return 0.0


def _bar(
    end: float,
    is_bottom: bool = True,
    layer_index: int = 0,
    diameter_mm: float = 10,
) -> DetailedBar:
    """Build a main run of 2 tensioned bars from 0 to the given end (cm)"""
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        quantity=2,
        is_bottom=is_bottom,
        is_tensioned=True,
        layer_index=layer_index,
        y=4.0 if is_bottom else 56.0,
        start=0,
        end=end,
        source_positions=(end / 2,),
    )


def _beam(
    *bars: DetailedBar,
    moment: Callable[[float], float] = _no_moment,
    with_analysis: bool = True,
) -> DetailingBeam:
    """Build a 20 x 60 cm detailing beam long enough for the bars, with a moment diagram"""
    length = max(bar.end for bar in bars)  # cm
    return DetailingBeam(
        beam_id="V1",
        width=20.0,
        height=60.0,
        nominal_covering=2.5,
        steel=Steel.CA50,
        supports=(
            Support(0.0, -10.0, 10.0),
            Support(length, length - 10, length + 10),
        ),
        bars=list(bars),
        analysis=cast(BeamAnalysis, _Analysis(length, moment))
        if with_analysis
        else None,
    )


def _extents(beam: DetailingBeam) -> list[tuple[float, float]]:
    """Return each run's extent, in order (cm)"""
    return [(bar.start, bar.end) for bar in beam.bars]


def _laps(beam: DetailingBeam) -> list[tuple[float, float]]:
    """Return each recorded lap's extent, in order (cm)"""
    return [(lap.start, lap.end) for lap in beam.lap_splices]


class TestPieces:
    """Long runs become the fewest pieces of at most 12 m, lapped together."""

    def test_short_run_kept(self) -> None:
        beam = _beam(_bar(1200))
        split_long_bars(beam)
        assert _extents(beam) == [(0, 1200)], "A 1200 cm run fits a commercial bar"
        assert beam.lap_splices == [], "No lap is needed"

    def test_two_pieces(self) -> None:
        beam = _beam(_bar(1300))
        split_long_bars(beam)
        # window for the lap start: 1300 − 1200 = 100 to 1200 − 67 = 1133; ties → rightmost
        assert _extents(beam) == [(0, 1200), (1133, 1300)], (
            "Two pieces lapped 67 cm, the first one 1200 cm long"
        )
        assert _laps(beam) == [(1133, 1200)], "The lap should be recorded"
        lap = beam.lap_splices[0]
        assert (lap.quantity, lap.diameter_mm, lap.is_bottom) == (2, 10, True), (
            "The lap splices the run's 2 φ10 bars"
        )

    def test_three_pieces(self) -> None:
        beam = _beam(_bar(2600))
        split_long_bars(beam)
        assert _extents(beam) == [(0, 1200), (1133, 2333), (2266, 2600)], (
            "2600 cm needs three pieces with two 67 cm laps"
        )
        assert all(bar.total_length <= MAX_BAR_LENGTH for bar in beam.bars), (
            "Every piece fits a commercial bar"
        )

    def test_hooks_stay_on_outer_pieces(self) -> None:
        hooked = replace(
            _bar(1300),
            left_hook=_HOOK,
            right_hook=_HOOK,
            left_hook_length=15.0,
            right_hook_length=15.0,
        )
        beam = _beam(hooked)
        split_long_bars(beam)
        first, last = beam.bars
        assert (first.start, first.end) == (0, 1185), (
            "The left hook's 15 cm leaves 1185 cm of straight bar"
        )
        assert first.total_length == 1200, "1185 + 15 cm"
        assert first.left_hook == _HOOK and first.right_hook is None, (
            "The first piece keeps only the left hook"
        )
        assert last.right_hook == _HOOK and last.left_hook is None, (
            "The last piece keeps only the right hook"
        )


class TestSplicePosition:
    """The lap goes where its face is least tensioned."""

    def test_bottom_lap_at_lowest_positive_moment(self) -> None:
        beam = _beam(_bar(1300), moment=lambda x: x)
        split_long_bars(beam)
        assert _laps(beam) == [(100, 167)], (
            "With M growing to the right, the bottom lap goes as far left as it can"
        )
        assert _extents(beam) == [(0, 167), (100, 1300)], "The second piece is 1200 cm"

    def test_top_lap_reads_negative_moment(self) -> None:
        beam = _beam(_bar(1300, is_bottom=False), moment=lambda x: -x)
        split_long_bars(beam)
        assert _laps(beam) == [(100, 167)], (
            "With −M growing to the right, the top lap goes as far left as it can"
        )

    def test_compressed_face_ties(self) -> None:
        beam = _beam(_bar(1300, is_bottom=False), moment=lambda x: x)
        split_long_bars(beam)
        assert _laps(beam) == [(1133, 1200)], (
            "A positive moment does not tension the top: every position ties"
        )


class TestTable93:
    """Splices of tensioned bars in two layers stay below half per section."""

    def test_layers_staggered(self) -> None:
        beam = _beam(_bar(1300), _bar(1300, layer_index=1))
        split_long_bars(beam)
        # layer 0: 2 of 4 bars spliced → α_0t = 1.8 → 61 cm, at the right end of the window
        # layer 1: closer than 0.2 × 67 cm to that lap would splice 4 of 4 → moves left
        assert _laps(beam) == [(1133, 1194), (1052, 1113)], (
            "The second layer's lap is staggered out of the first one's section"
        )
        gap = beam.lap_splices[0].start - beam.lap_splices[1].end
        assert gap >= 0.2 * 61, "The laps are not in the same section (Section 9.5.2.1)"

    def test_no_valid_position_raises(self) -> None:
        beam = _beam(_bar(1300), _bar(1300, layer_index=1))
        beam.lap_splices.append(
            LapSplice(
                is_bottom=True,
                layer_index=1,
                start=0,
                end=1300,
                quantity=2,
                diameter_mm=10,
            )
        )
        with pytest.raises(ValueError, match="Table 9.3"):
            split_long_bars(beam)


class TestOtherRuns:
    """Construction and compressed runs use their own laps; some runs cannot be split."""

    def test_construction_run(self) -> None:
        construction = replace(
            _bar(1300),
            role=BarRole.CONSTRUCTION,
            is_tensioned=False,
            diameter_mm=6.3,
            source_positions=(),
        )
        beam = _beam(construction)
        split_long_bars(beam)
        assert _extents(beam) == [(0, 1200), (1180, 1300)], (
            "The φ6.3 construction lap is 20 cm"
        )
        assert beam.lap_splices == [], "Construction laps are not recorded"

    def test_compressed_run(self) -> None:
        beam = _beam(replace(_bar(1300), is_tensioned=False))
        split_long_bars(beam)
        assert _laps(beam) == [(1166, 1200)], "φ10 l_0c = 33.36 → 34 cm"

    def test_bars_above_32_mm_raise(self) -> None:
        beam = _beam(_bar(1300, diameter_mm=40))
        with pytest.raises(ValueError, match="cannot be lap spliced"):
            split_long_bars(beam)

    def test_missing_analysis_raises(self) -> None:
        beam = _beam(_bar(1300), with_analysis=False)
        with pytest.raises(ValueError, match="no analysis"):
            split_long_bars(beam)

    def test_missing_analysis_fine_without_long_runs(self) -> None:
        beam = _beam(_bar(1200), with_analysis=False)
        split_long_bars(beam)
        assert _extents(beam) == [(0, 1200)], "No split, no analysis needed"


class TestStepOrder:
    """Long runs are split last, after the construction bars."""

    def test_runs_after_construction_bars(self) -> None:
        index = _STEPS.index(split_long_bars)
        assert _STEPS[index - 1] is add_construction_bars, (
            "Construction bars, then splitting"
        )


@pytest.fixture(scope="module")
def long_span_pavement() -> Pavement:
    """Resolve one 14 m beam on two 20 x 20 cm pillars, loaded by its own weight and a wall.

    Module-scoped, with logging suppressed: the resolve is slow and the test only reads it.
    """
    pavement = Pavement()
    pillars = [
        Pillar(x=0, y=0, width=20, depth=20),
        Pillar(x=1400, y=0, width=20, depth=20),
    ]
    for pillar in pillars:
        pavement.add_pillar(pillar)
    wall = WallDefinition(False, "hollow concrete block", 14, 1)
    pavement.add_beam(
        ContinuousBeam(
            [p.id for p in pillars], pillars[0].id, 20, Alignment.CENTER, wall
        )
    )
    with suppress_logging():
        pavement.resolve()
    return pavement


class TestRealBeam:
    """A real 14 m beam gets its bottom bars spliced within 12 m."""

    def test_every_bar_fits_and_laps_are_recorded(
        self, long_span_pavement: Pavement
    ) -> None:
        detailing = next(iter(long_span_pavement.beams.values())).detailing
        assert detailing is not None, "The beam should be detailed"
        assert all(bar.total_length <= MAX_BAR_LENGTH for bar in detailing.bars), (
            "No bar should pass 12 m"
        )
        assert detailing.lap_splices, "The long bottom bars should be spliced"
        for lap in detailing.lap_splices:
            lapped = [
                bar
                for bar in detailing.bars
                if bar.is_bottom == lap.is_bottom
                and bar.diameter_mm == lap.diameter_mm
                and (bar.end == lap.end or bar.start == lap.start)
            ]
            assert len(lapped) == 2, "Each lap joins the two pieces of one run"


def _skin(
    start: float = 10.0,
    end: float = 235.0,
    diameter_mm: float = 8,
    mark: str | None = None,
) -> DetailedSkinBars:
    """Build the skin bars of span P1–P2: two rows, at 15 and 25 cm"""
    return DetailedSkinBars(
        start_pillar_id="P1",
        end_pillar_id="P2",
        diameter_mm=diameter_mm,
        steel=Steel.CA50,
        heights=(15.0, 25.0),
        start=start,
        end=end,
        mark=mark,
    )


class TestSplitSkin:
    """Skin bars longer than 12 m become equal pieces with the construction lap."""

    def test_short_skin_kept(self) -> None:
        beam = _beam(_bar(1200))
        beam.skin_bars = [_skin(0.0, 1200.0)]
        split_long_bars(beam)
        assert [(s.start, s.end) for s in beam.skin_bars] == [(0.0, 1200.0)], (
            "a 1200 cm skin bar fits a commercial bar"
        )

    def test_long_skin_split_with_construction_lap(self) -> None:
        """Rows at 15 and 25 cm of a 60 cm beam lie in the good bond zone"""
        beam = _beam(_bar(1200))
        beam.skin_bars = [_skin(0.0, 1300.0)]
        split_long_bars(beam)
        lap = round_up(construction_lap_length(8, Steel.CA50, True))  # cm
        pieces = beam.skin_bars
        assert len(pieces) == 2, "two pieces fit 1300 cm"
        assert pieces[0].start == 0.0, "the first piece starts at the run's start"
        assert pieces[-1].end == 1300.0, "the last piece ends at the run's end"
        assert pieces[0].end - pieces[1].start == lap, "pieces overlap by the lap"
        assert all(piece.total_length <= MAX_BAR_LENGTH for piece in pieces), (
            "every piece fits a commercial bar"
        )
        assert beam.lap_splices == [], "skin laps are not recorded"
