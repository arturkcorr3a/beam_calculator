from dataclasses import dataclass
from itertools import pairwise

from src.calculators.lap_splice_calculator import construction_lap_length
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.rounding import left_end_limit, right_end_limit, round_up
from src.logger import log_operation
from src.reinforcement.layer import Layer

CORNER_BARS = 2  # one bar in each corner of a two-leg stirrup
_MM_PER_CM = 10.0


@dataclass(frozen=True)
class _Gap:
    """A stretch of one face without bars in the stirrup corners

    Attributes:
        start: Gap start; the beam's start when no bar comes before it (cm).
        end: Gap end; the beam's end when no bar comes after it (cm).
        diameter_mm: Largest stirrup diameter φ_t along the gap (mm).
    """

    start: float
    end: float
    diameter_mm: float


def add_construction_bars(detailing: DetailingBeam) -> None:
    """Add construction bars where stirrups have no longitudinal bar in their corners

    On each face, a point is covered where the layer-0 bars add up to at least two. Every uncovered stretch that reaches a stretch with stirrups gets two construction bars with the diameter of the stirrups there (the largest, when it crosses a pillar). They lap into the bars on each side by the construction lap, or run to the beam's end limit, without hooks, where no bar follows. Gaps whose bars would overlap, because the covered stretch between them is shorter than two laps, get one bar.

    The laps are not recorded in ``lap_splices``: the main bars carry on past them, so no main bar is spliced.

    References:
        ABNT NBR 6118:2026 — Sections 9.3.1 and 9.5.2.3
    """
    added: list[DetailedBar] = []
    for is_bottom in (True, False):
        gaps = _gaps(detailing, is_bottom)
        for cluster in _clusters(detailing, gaps, is_bottom):
            added.append(_construction_bar(detailing, cluster, is_bottom))
    detailing.bars += added
    for bar in added:
        face = "bottom" if bar.is_bottom else "top"
        log_operation(
            f"Construction bars: {face} {bar.quantity}φ{bar.diameter_mm:g} [{bar.start:g}–{bar.end:g}] cm"
        )


def _covered(detailing: DetailingBeam, is_bottom: bool) -> list[tuple[float, float]]:
    """Return the stretches of a face with at least two layer-0 bars, merged, left to right (cm)"""
    bars = [
        bar
        for bar in detailing.bars_on_face(is_bottom)
        if bar.layer_index == 0 and bar.end > bar.start
    ]
    points = sorted(
        {
            detailing.start,
            detailing.end,
            *(x for bar in bars for x in (bar.start, bar.end)),
        }
    )
    covered: list[tuple[float, float]] = []
    for start, end in pairwise(points):
        middle = (start + end) / 2  # cm
        count = sum(bar.quantity for bar in bars if bar.start <= middle <= bar.end)
        if count < CORNER_BARS:
            continue
        if covered and covered[-1][1] == start:
            covered[-1] = (covered[-1][0], end)
        else:
            covered.append((start, end))
    return covered


def _gaps(detailing: DetailingBeam, is_bottom: bool) -> list[_Gap]:
    """Return the uncovered stretches of a face that reach a stretch with stirrups, left to right"""
    covered = _covered(detailing, is_bottom)
    bounds = [
        detailing.start,
        *(x for stretch in covered for x in stretch),
        detailing.end,
    ]
    gaps: list[_Gap] = []
    for start, end in zip(bounds[::2], bounds[1::2], strict=True):
        diameters = [
            stirrups.diameter_mm
            for stirrups in detailing.stirrups
            if min(end, stirrups.end) > max(start, stirrups.start)
        ]
        if end > start and diameters:
            gaps.append(_Gap(start, end, max(diameters)))
    return gaps


def _clusters(
    detailing: DetailingBeam, gaps: list[_Gap], is_bottom: bool
) -> list[list[_Gap]]:
    """Group neighboring gaps whose construction bars would overlap"""
    clusters: list[list[_Gap]] = []
    for gap in gaps:
        if clusters:
            last = clusters[-1]
            lap = _lap_length(
                detailing, max(g.diameter_mm for g in [*last, gap]), is_bottom
            )
            if gap.start - last[-1].end <= 2 * lap:
                last.append(gap)
                continue
        clusters.append([gap])
    return clusters


def _construction_bar(
    detailing: DetailingBeam, cluster: list[_Gap], is_bottom: bool
) -> DetailedBar:
    """Build the two construction bars that fill a group of gaps, lapped into the bars around it"""
    diameter_mm = max(gap.diameter_mm for gap in cluster)
    lap = _lap_length(detailing, diameter_mm, is_bottom)  # cm
    first, last = cluster[0], cluster[-1]
    start = (
        left_end_limit(detailing, diameter_mm, hooked=False)
        if first.start <= detailing.start
        else max(
            first.start - lap, left_end_limit(detailing, diameter_mm, hooked=False)
        )
    )
    end = (
        right_end_limit(detailing, diameter_mm, hooked=False)
        if last.end >= detailing.end
        else min(last.end + lap, right_end_limit(detailing, diameter_mm, hooked=False))
    )
    y = _bar_height(detailing, diameter_mm, is_bottom)  # cm
    return DetailedBar(
        diameter_mm=diameter_mm,
        steel=detailing.steel,
        quantity=CORNER_BARS,
        is_bottom=is_bottom,
        is_tensioned=False,
        layer_index=0,
        y=y,
        start=start,
        end=end,
        role=BarRole.CONSTRUCTION,
        good_adherence=Layer.is_good_adherence_position(y, detailing.height),
    )


def _bar_height(detailing: DetailingBeam, diameter_mm: float, is_bottom: bool) -> float:
    """Return the height of a construction bar's axis from the bottom face (cm)

    The bar touches the stirrup's inner face: nominal cover, plus the stirrup and half the bar. The stirrup diameter is taken equal to the bar's.
    """
    offset = detailing.nominal_covering + 1.5 * diameter_mm / _MM_PER_CM  # cm
    return offset if is_bottom else detailing.height - offset


def _lap_length(detailing: DetailingBeam, diameter_mm: float, is_bottom: bool) -> float:
    """Return the construction lap of a bar, rounded up to whole centimeters (cm)"""
    y = _bar_height(detailing, diameter_mm, is_bottom)  # cm
    good_adherence = Layer.is_good_adherence_position(y, detailing.height)
    return round_up(
        construction_lap_length(diameter_mm, detailing.steel, good_adherence)
    )
