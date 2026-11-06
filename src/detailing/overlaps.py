from collections.abc import Iterator
from dataclasses import dataclass, replace

from src.calculators.lap_splice_calculator import MAX_LAP_DIAMETER_MM
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


@dataclass(eq=False)
class _Run:
    """A bar run being resolved, with the ends that already continue into another run"""

    bar: DetailedBar
    left_locked: bool = False
    right_locked: bool = False


def resolve_overlaps(detailing: DetailingBeam) -> None:
    """Resolve the overlaps between main bars designed at different interest points

    On each face and layer, a bar run reaching into the next point's run, end to end, is paired with it: equal diameters first, then the largest. Paired bars of the same diameter merge into one continuous run. Paired bars of different diameters keep only a lap splice between them, centered on the old overlap, when the overlap is longer than the lap (see ``_trim``). A run with more bars than its partner splits, and the extra bars keep their length. A run lying inside another is a parallel bar, not a splice, and is left alone.

    Each lap is recorded in ``detailing.lap_splices``.

    References:
        ABNT NBR 6118:2026 — Section 9.5.2
    """
    runs = [_Run(bar) for bar in detailing.bars]
    skipped: set[tuple[_Run, _Run]] = set()
    while (pair := next(_candidates(runs, skipped), None)) is not None:
        left, right = pair
        if _has_clamps(detailing, left.bar, left=False) or _has_clamps(
            detailing, right.bar, left=True
        ):
            log_operation(_describe("Kept (clamped end)", left.bar, right.bar))
            skipped.add(pair)
            continue
        if left.bar.diameter_mm == right.bar.diameter_mm:
            replacement = _merge(left, right)
        else:
            replacement = _trim(detailing, runs, left, right)
        if replacement is None:
            skipped.add(pair)
            continue
        index = runs.index(left)
        runs = [run for run in runs if run is not left and run is not right]
        runs[index:index] = replacement
    detailing.bars = [run.bar for run in runs]


def _candidates(
    runs: list[_Run], skipped: set[tuple[_Run, _Run]]
) -> Iterator[tuple[_Run, _Run]]:
    """Yield the overlapping pairs of main runs, equal diameters first, then the largest, then left to right

    A pair is a run on the left whose free right end reaches past the free left end of a run on the right, on the same face and layer, designed at other interest points; neither run lies inside the other.
    """
    pairs = [
        (left, right)
        for left in runs
        for right in runs
        if _overlap_end_to_end(left, right) and (left, right) not in skipped
    ]
    pairs.sort(
        key=lambda pair: (
            pair[0].bar.diameter_mm != pair[1].bar.diameter_mm,
            -max(pair[0].bar.diameter_mm, pair[1].bar.diameter_mm),
            pair[0].bar.start,
            pair[1].bar.start,
        )
    )
    yield from pairs


def _overlap_end_to_end(left: _Run, right: _Run) -> bool:
    """Whether the left run's right end reaches into the right run, both free and of other points"""
    a, b = left.bar, right.bar
    return (
        left is not right
        and a.role == BarRole.MAIN
        and b.role == BarRole.MAIN
        and a.is_bottom == b.is_bottom
        and a.layer_index == b.layer_index
        and not set(a.source_positions) & set(b.source_positions)
        and a.start < b.start <= a.end < b.end
        and not left.right_locked
        and not right.left_locked
    )


def _has_clamps(detailing: DetailingBeam, bar: DetailedBar, left: bool) -> bool:
    """Whether clamps anchor one end of a bar run"""
    position = bar.start if left else bar.end
    return any(
        clamps.left == left
        and clamps.is_bottom == bar.is_bottom
        and clamps.source_position in bar.source_positions
        and clamps.position == position
        for clamps in detailing.clamps
    )


def _split(run: _Run, quantity: int) -> tuple[_Run, list[_Run]]:
    """Split a run into one with the given quantity and the rest, which keeps the run's ends"""
    paired = _Run(
        replace(run.bar, quantity=quantity), run.left_locked, run.right_locked
    )
    if run.bar.quantity == quantity:
        return paired, []
    rest = _Run(
        replace(run.bar, quantity=run.bar.quantity - quantity),
        run.left_locked,
        run.right_locked,
    )
    return paired, [rest]


def _merge(left: _Run, right: _Run) -> list[_Run]:
    """Join paired bars of the same diameter into one run from the left start to the right end

    The merged run keeps the outer hooks and the sources of both points. It is tensioned if either was, sits in a good bond zone only if both did, and keeps the larger area ratio.
    """
    quantity = min(left.bar.quantity, right.bar.quantity)
    left_paired, left_rest = _split(left, quantity)
    right_paired, right_rest = _split(right, quantity)
    a, b = left_paired.bar, right_paired.bar
    merged = replace(
        a,
        end=b.end,
        right_hook=b.right_hook,
        right_hook_length=b.right_hook_length,
        is_tensioned=a.is_tensioned or b.is_tensioned,
        good_adherence=a.good_adherence and b.good_adherence,
        area_ratio=max(a.area_ratio, b.area_ratio),
        source_positions=tuple(sorted(a.source_positions + b.source_positions)),
    )
    log_operation(_describe(f"Merged {quantity} bar(s)", a, b))
    return [
        _Run(merged, left_paired.left_locked, right_paired.right_locked),
        *left_rest,
        *right_rest,
    ]


def _trim(
    detailing: DetailingBeam, runs: list[_Run], left: _Run, right: _Run
) -> list[_Run] | None:
    """Cut paired bars of different diameters back to a lap splice, centered on their overlap

    The lap is sized with the smaller diameter (Section 9.5.2.1), for tension unless both runs are compressed, and rounded up. α_0t comes from the share of the face's bars spliced in that section, counting the laps already made there (Table 9.4). The trimmed ends lose their hooks.

    Returns:
        The runs replacing the pair, or None when they are kept as they are: a bar above 32 mm (no lap splices, Section 9.5.2), more than half of the tensioned bars spliced in a section with more than one layer (Table 9.3), or an overlap no longer than the lap.

    References:
        ABNT NBR 6118:2026 — Sections 9.5.2, 9.5.2.1, 9.5.2.2 and 9.5.2.3, Tables 9.3 and 9.4
    """
    a, b = left.bar, right.bar
    if max(a.diameter_mm, b.diameter_mm) > MAX_LAP_DIAMETER_MM:
        log_operation(_describe("Kept (bar above 32 mm)", a, b))
        return None

    quantity = min(a.quantity, b.quantity)
    center = (b.start + a.end) / 2  # cm
    share, layers = section_share(
        (run.bar for run in runs),
        detailing.lap_splices,
        is_bottom=a.is_bottom,
        center=center,
        reach=splice_length(a, b, share=1.0) / 2,  # cm, the longest lap (α_0t = 2.0)
        quantity=quantity,
        paired_quantity=quantity,
    )
    if exceeds_spliced_share(share, layers, a.is_tensioned or b.is_tensioned):
        log_operation(
            _describe(
                f"Kept ({share:.0%} spliced in a section with {layers} layers)",
                a,
                b,
            )
        )
        return None

    lap = round_up(splice_length(a, b, share))  # cm
    if b.start + lap >= a.end:
        log_operation(_describe(f"Kept (overlap within the {lap:g} cm lap)", a, b))
        return None

    lap_start = round_down(center - lap / 2)  # cm
    lap_end = lap_start + lap  # cm
    left_paired, left_rest = _split(left, quantity)
    right_paired, right_rest = _split(right, quantity)
    trimmed_left = replace(
        left_paired.bar, end=lap_end, right_hook=None, right_hook_length=0.0
    )
    trimmed_right = replace(
        right_paired.bar, start=lap_start, left_hook=None, left_hook_length=0.0
    )
    detailing.lap_splices.append(
        LapSplice(
            is_bottom=a.is_bottom,
            layer_index=a.layer_index,
            start=lap_start,
            end=lap_end,
            quantity=quantity,
            diameter_mm=min(a.diameter_mm, b.diameter_mm),
        )
    )
    log_operation(
        _describe(
            f"Trimmed {quantity} bar(s) to a {lap:g} cm lap [{lap_start:g}–{lap_end:g}] (α_0t share {share:.0%})",
            a,
            b,
        )
    )
    return [
        _Run(trimmed_left, left_paired.left_locked, right_locked=True),
        *left_rest,
        _Run(trimmed_right, left_locked=True, right_locked=right_paired.right_locked),
        *right_rest,
    ]


def _describe(action: str, a: DetailedBar, b: DetailedBar) -> str:
    """Describe an overlap decision for the log"""
    face = "bottom" if a.is_bottom else "top"
    return (
        f"{action}: {face} layer {a.layer_index}, {a.quantity}φ{a.diameter_mm:g} [{a.start:g}–{a.end:g}]"
        f" with {b.quantity}φ{b.diameter_mm:g} [{b.start:g}–{b.end:g}] cm"
    )
