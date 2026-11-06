from dataclasses import replace
from math import ceil

from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.lap_splice_calculator import (
    MAX_LAP_DIAMETER_MM,
    construction_lap_length,
)
from src.detailing.detailed_bar import BarRole, DetailedBar
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.lap_splice import (
    LapSplice,
    exceeds_spliced_share,
    section_share,
    splice_length,
)
from src.detailing.rounding import round_down, round_up
from src.logger import log_operation

MAX_BAR_LENGTH = 1200.0  # cm, commercial bar length, hooks included
_TENSION_TOLERANCE = 1e-9  # kN.m, tensions closer than this are a tie


def split_long_bars(detailing: DetailingBeam) -> None:
    """Split every bar run longer than a commercial bar into lap-spliced pieces

    A run whose cut length, hooks included, passes 12 m is cut into the fewest pieces that fit (see ``_split``). Main runs are split first, bottom face first, by layer and left to right, so the laps they make count in the share of the later ones. Laps of main runs are recorded in ``lap_splices``; laps of construction runs are not, as in ``add_construction_bars``.

    Raises:
        ValueError: If a long run has bars above 32 mm, the beam has no analysis, or no splice position meets Table 9.3.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2
    """
    bars = list(detailing.bars)
    order = sorted(
        bars,
        key=lambda bar: (
            bar.role != BarRole.MAIN,
            not bar.is_bottom,
            bar.layer_index,
            bar.start,
        ),
    )
    for bar in order:
        if bar.total_length <= MAX_BAR_LENGTH:
            continue
        index = next(i for i, other in enumerate(bars) if other is bar)
        _split(detailing, bars, index)
    detailing.bars = bars


def _split(detailing: DetailingBeam, bars: list[DetailedBar], index: int) -> None:
    """Cut the bar run at ``bars[index]`` into the fewest pieces of at most 12 m, from left to right

    The number of pieces is the smallest that fits the run with the longest lap (α_0t = 2.0) between pieces. Each lap starts at a whole centimeter, inside the window that keeps the current piece within 12 m and leaves room for the rest in the remaining pieces. Within the window, the lap goes where the bars' face is least tensioned at the lap's center (the rightmost on a tie), skipping positions that splice too many bars in one section (Table 9.3). The first piece keeps the left hook and the last one the right hook.

    The run is replaced by its pieces in ``bars`` as the laps are placed, so each lap counts the ones before it.

    Raises:
        ValueError: If the bars are above 32 mm, the beam has no analysis, the lap does not fit in a commercial bar, or no position in a window meets Table 9.3.

    References:
        ABNT NBR 6118:2026 — Sections 9.5.2, 9.5.2.1 and 9.5.2.2, Tables 9.3 and 9.4
    """
    bar = bars[index]
    if bar.diameter_mm > MAX_LAP_DIAMETER_MM:
        raise ValueError(
            f"A {bar.total_length:g} cm φ{bar.diameter_mm:g} run needs a splice, but bars above {MAX_LAP_DIAMETER_MM:g} mm cannot be lap spliced."
        )
    analysis = detailing.analysis
    if analysis is None:
        raise ValueError("The beam has no analysis to place the splices of long bars.")
    longest = round_up(_lap_length(bar, share=1.0))  # cm
    if longest >= MAX_BAR_LENGTH:
        raise ValueError(
            f"A {longest:g} cm lap of φ{bar.diameter_mm:g} bars does not fit in a {MAX_BAR_LENGTH:g} cm bar."
        )
    count = ceil((bar.total_length - longest) / (MAX_BAR_LENGTH - longest))

    pieces: list[DetailedBar] = []
    rest = bar
    for remaining in range(count - 1, 0, -1):
        low = max(
            rest.start + 1,
            rest.end
            + rest.right_hook_length
            - remaining * MAX_BAR_LENGTH
            + (remaining - 1) * longest,
        )
        high = min(
            rest.start + MAX_BAR_LENGTH - longest - rest.left_hook_length,
            rest.end - longest,
        )
        lap_start, lap = _splice_position(
            detailing, analysis, bars, rest, round_up(low), round_down(high), longest
        )
        piece = replace(
            rest, end=lap_start + lap, right_hook=None, right_hook_length=0.0
        )
        rest = replace(rest, start=lap_start, left_hook=None, left_hook_length=0.0)
        pieces.append(piece)
        bars[index : index + 1] = [piece, rest]
        index += 1
        if bar.role == BarRole.MAIN:
            detailing.lap_splices.append(
                LapSplice(
                    is_bottom=bar.is_bottom,
                    layer_index=bar.layer_index,
                    start=lap_start,
                    end=lap_start + lap,
                    quantity=bar.quantity,
                    diameter_mm=bar.diameter_mm,
                )
            )
    pieces.append(rest)
    face = "bottom" if bar.is_bottom else "top"
    log_operation(
        f"Split {face} layer {bar.layer_index} {bar.quantity}φ{bar.diameter_mm:g} [{bar.start:g}–{bar.end:g}] ({bar.total_length:g} cm) into "
        + ", ".join(f"[{p.start:g}–{p.end:g}]" for p in pieces)
    )


def _splice_position(
    detailing: DetailingBeam,
    analysis: BeamAnalysis,
    bars: list[DetailedBar],
    bar: DetailedBar,
    low: float,
    high: float,
    longest: float,
) -> tuple[float, float]:
    """Pick the start of a lap in [low, high] (cm) where the bars are least tensioned

    Returns:
        The lap's start and length (cm).

    Raises:
        ValueError: If every position in the window splices too many bars in one section (Table 9.3).
    """
    best: tuple[float, float, float] | None = None  # (tension, start, length)
    position = low
    while position <= high:
        center = position + longest / 2  # cm
        share, layers = section_share(
            bars,
            detailing.lap_splices,
            is_bottom=bar.is_bottom,
            center=center,
            reach=longest / 2,
            quantity=bar.quantity,
        )
        is_main = bar.role == BarRole.MAIN
        if not (is_main and exceeds_spliced_share(share, layers, bar.is_tensioned)):
            tension = _tension(analysis, bar.is_bottom, center)
            if best is None or tension <= best[0] + _TENSION_TOLERANCE:
                best = (tension, position, round_up(_lap_length(bar, share)))
        position += 1
    if best is None:
        raise ValueError(
            f"No splice position for {bar.quantity}φ{bar.diameter_mm:g} between {low:g} and {high:g} cm keeps the bars spliced in one section within Table 9.3."
        )
    return best[1], best[2]


def _lap_length(bar: DetailedBar, share: float) -> float:
    """Return the lap between two pieces of a bar run (cm): the construction lap for construction bars"""
    if bar.role == BarRole.CONSTRUCTION:
        return construction_lap_length(bar.diameter_mm, bar.steel, bar.good_adherence)
    return splice_length(bar, bar, share)


def _tension(analysis: BeamAnalysis, is_bottom: bool, position: float) -> float:
    """Return the bending moment tensioning a face at a position (kN.m), zero when it compresses it

    Positions past the beam's theoretical ends read the moment at the nearest end.
    """
    moment = analysis.bending_moment(min(max(position, 0.0), analysis.length))  # kN.m
    return max(moment, 0.0) if is_bottom else max(-moment, 0.0)
