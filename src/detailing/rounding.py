from dataclasses import replace
from itertools import pairwise
from math import ceil, floor

from src.calculators.stirrup_calculator import MIN_SPACING
from src.detailing.detailed_bar import DetailedBar
from src.detailing.detailed_clamps import DetailedClamps
from src.detailing.detailed_skin_bars import DetailedSkinBars
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.span_stirrups import SpanStirrups
from src.logger import log_operation
from src.reinforcement.stirrups import StirrupZone

ROUNDING_TOLERANCE = 1e-6  # cm, absorbs float drift on values that are already whole
HOOK_END_COVER_RATIO = (
    3  # cover of a hooked end, in bar diameters - NBR 6118 - Section 9.4.2.5
)
_MM_PER_CM = 10.0


def round_up(value: float) -> float:
    """Round a length up to whole centimeters, leaving whole values (within the tolerance) as they are

    Args:
        value: Length or position (cm).
    """
    return float(ceil(value - ROUNDING_TOLERANCE))


def round_down(value: float) -> float:
    """Round a length down to whole centimeters, leaving whole values (within the tolerance) as they are

    Args:
        value: Length or position (cm).
    """
    return float(floor(value + ROUNDING_TOLERANCE))


def end_cover(beam: DetailingBeam, diameter_mm: float, hooked: bool) -> float:
    """Return the cover a bar end needs at the beam's outer faces (cm)

    A straight end needs the nominal cover; a hooked end needs at least three bar diameters.

    References:
        ABNT NBR 6118:2026 — Section 9.4.2.5
    """
    if not hooked:
        return beam.nominal_covering
    return max(beam.nominal_covering, HOOK_END_COVER_RATIO * diameter_mm / _MM_PER_CM)


def left_end_limit(beam: DetailingBeam, diameter_mm: float, hooked: bool) -> float:
    """Return the leftmost whole-centimeter position a bar end can reach: the first pillar's outer face plus the end cover (cm)"""
    return round_up(beam.start + end_cover(beam, diameter_mm, hooked))


def right_end_limit(beam: DetailingBeam, diameter_mm: float, hooked: bool) -> float:
    """Return the rightmost whole-centimeter position a bar end can reach: the last pillar's outer face minus the end cover (cm)"""
    return round_down(beam.end - end_cover(beam, diameter_mm, hooked))


def round_detailing(detailing: DetailingBeam) -> None:
    """Round every length of a detailing beam to whole centimeters

    Bars, clamps, stirrups and skin bars are replaced by rounded copies (see ``round_bar``, ``round_clamps``, ``round_stirrups`` and ``round_skin_bars``). Each clamp set's bend follows the rounded end of the bars it anchors.

    Raises:
        ValueError: If a clamp set has no bar ending at its bend, or a stirrup spacing rounds below the minimum.
    """
    anchored = [_anchored_bar(clamps, detailing.bars) for clamps in detailing.clamps]
    rounded_bars = {id(bar): round_bar(detailing, bar) for bar in detailing.bars}
    detailing.clamps = [
        round_clamps(clamps, rounded_bars[id(bar)])
        for clamps, bar in zip(detailing.clamps, anchored, strict=True)
    ]
    detailing.bars = [rounded_bars[id(bar)] for bar in detailing.bars]
    detailing.stirrups = [round_stirrups(stirrups) for stirrups in detailing.stirrups]
    detailing.skin_bars = [round_skin_bars(skin) for skin in detailing.skin_bars]
    log_operation(
        f"Rounded to whole centimeters: {len(detailing.bars)} bar run(s), {len(detailing.clamps)} clamp set(s), {len(detailing.stirrups)} stirrup set(s), {len(detailing.skin_bars)} skin bar set(s)"
    )


def round_bar(beam: DetailingBeam, bar: DetailedBar) -> DetailedBar:
    """Return a copy of a bar run with whole-centimeter ends and hooks

    Each end rounds outward, so the anchorage only grows, but never past the beam's outer faces minus the end cover (``left_end_limit``, ``right_end_limit``). An end laid out against that limit therefore rounds inward, keeping the cover. Hook lengths round up.
    """
    start = max(
        round_down(bar.start),
        left_end_limit(beam, bar.diameter_mm, bar.left_hook is not None),
    )
    end = min(
        round_up(bar.end),
        right_end_limit(beam, bar.diameter_mm, bar.right_hook is not None),
    )
    return replace(
        bar,
        start=start,
        end=end,
        left_hook_length=round_up(bar.left_hook_length),
        right_hook_length=round_up(bar.right_hook_length),
    )


def round_skin_bars(skin: DetailedSkinBars) -> DetailedSkinBars:
    """Return a copy of a span's skin bars with whole-centimeter ends

    Each end rounds inward, so the bars never enter the pillars.
    """
    return replace(skin, start=round_up(skin.start), end=round_down(skin.end))


def round_clamps(clamps: DetailedClamps, anchored_bar: DetailedBar) -> DetailedClamps:
    """Return a copy of a clamp set with whole-centimeter legs and width, bent at the anchored bars' rounded end

    The legs round up; the width rounds down, so the U still fits inside the stirrup.

    Args:
        anchored_bar: The rounded bar run whose end the clamps anchor.
    """
    position = anchored_bar.start if clamps.left else anchored_bar.end
    return replace(
        clamps,
        position=position,
        leg_length=round_up(clamps.leg_length),
        width=round_down(clamps.width),
    )


def _anchored_bar(clamps: DetailedClamps, bars: list[DetailedBar]) -> DetailedBar:
    """Find a bar run of the clamps' source point and face whose end sits at the clamps' bend

    Raises:
        ValueError: If no bar run ends at the bend.
    """
    for bar in bars:
        bar_end = bar.start if clamps.left else bar.end
        if (
            clamps.source_position in bar.source_positions
            and bar.is_bottom == clamps.is_bottom
            and abs(bar_end - clamps.position) <= ROUNDING_TOLERANCE
        ):
            return bar
    raise ValueError(
        f"No bar ends at the clamps' bend at {clamps.position:.2f} cm (source {clamps.source_position:.2f} cm)."
    )


def round_stirrups(stirrups: SpanStirrups) -> SpanStirrups:
    """Return a copy of a span's stirrups with whole-centimeter dimensions, spacings and zone boundaries

    The outer dimensions round down, so the stirrup keeps the cover, and the cut length rounds up. Spacings round down. Each boundary between zones moves towards the sparser zone, so the denser stirrups only spread. Neighbors left with the same spacing merge, and a zone squeezed to nothing is absorbed by its denser neighbor. The outer limits stay on the pillars' faces.

    Raises:
        ValueError: If a spacing rounds below the minimum spacing.

    References:
        ABNT NBR 6118:2026 — Section 18.3.3.2
    """
    zones = [
        StirrupZone(zone.start, zone.end, round_down(zone.spacing))
        for zone in stirrups.zones
    ]
    for zone in zones:
        if zone.spacing < MIN_SPACING:
            raise ValueError(
                f"Stirrup spacing rounds down to {zone.spacing:g} cm, below the minimum of {MIN_SPACING:g} cm."
            )
    return replace(
        stirrups,
        zones=_round_boundaries(_merge_equal(zones)),
        outer_width=round_down(stirrups.outer_width),
        outer_height=round_down(stirrups.outer_height),
        cut_length=round_up(stirrups.cut_length),
    )


def _round_boundaries(zones: list[StirrupZone]) -> tuple[StirrupZone, ...]:
    """Round the boundaries between zones towards the sparser side, absorbing zones that vanish"""
    while True:
        inner = [
            round_up(left.end) if left.spacing < right.spacing else round_down(left.end)
            for left, right in pairwise(zones)
        ]
        bounds = [zones[0].start, *inner, zones[-1].end]
        rounded = [
            StirrupZone(start, end, zone.spacing)
            for zone, (start, end) in zip(zones, pairwise(bounds), strict=True)
        ]
        vanished = next(
            (index for index, zone in enumerate(rounded) if zone.end <= zone.start),
            None,
        )
        if vanished is None:
            return tuple(rounded)
        zones = _absorb(zones, vanished)


def _absorb(zones: list[StirrupZone], index: int) -> list[StirrupZone]:
    """Give a zone's stretch to its denser neighbor, merging neighbors left with the same spacing"""
    neighbors = [i for i in (index - 1, index + 1) if 0 <= i < len(zones)]
    receiver = min(neighbors, key=lambda i: zones[i].spacing)
    zone, other = zones[index], zones[receiver]
    zones = list(zones)
    zones[receiver] = StirrupZone(
        min(zone.start, other.start), max(zone.end, other.end), other.spacing
    )
    del zones[index]
    return _merge_equal(zones)


def _merge_equal(zones: list[StirrupZone]) -> list[StirrupZone]:
    """Merge neighboring zones that have the same spacing"""
    merged: list[StirrupZone] = []
    for zone in zones:
        if merged and merged[-1].spacing == zone.spacing:
            merged[-1] = StirrupZone(merged[-1].start, zone.end, zone.spacing)
        else:
            merged.append(zone)
    return merged
