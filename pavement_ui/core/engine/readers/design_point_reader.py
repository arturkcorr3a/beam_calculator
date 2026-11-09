"""Read a design point (moment extreme) from its governing RebarCalculator."""

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.engine.readers.reinforcement_reader import read_layers
from pavement_ui.core.results.beam_design import AnchorageEntry
from pavement_ui.core.results.beam_result import DesignPoint, PointKind, SupportMark
from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.rebar_calculator import RebarCalculator
from src.reinforcement.reinforcement import Reinforcement

_SUPPORT_TOLERANCE_M = 0.01  # a point within 1 cm of a support is on it


def _span_index(position_m: float, span_ends_m: tuple[float, ...]) -> int:
    """Return the number (1…n) of the span containing position_m."""
    for index, end in enumerate(span_ends_m, start=1):
        if position_m <= end:
            return index
    return len(span_ends_m)


def _support_at(
    position_m: float, supports: tuple[SupportMark, ...]
) -> SupportMark | None:
    """Return the support (end or interior) at position_m, if any."""
    for support in supports:
        if abs(support.position_m - position_m) <= _SUPPORT_TOLERANCE_M:
            return support
    return None


def _anchorages(reinforcement: Reinforcement) -> tuple[AnchorageEntry, ...]:
    """Return the chosen layers' anchorage lengths, layers numbered from 1"""
    return tuple(
        AnchorageEntry(
            layer=summary.layer_index + 1,
            left=summary.side == "left",
            lb_cm=summary.basic_length,
            lb_nec_cm=summary.necessary_length,
        )
        for summary in reinforcement.anchorages
    )


def read_point(
    calculator: RebarCalculator,
    supports: tuple[SupportMark, ...],
    analysis: BeamAnalysis,
) -> DesignPoint:
    """Build the design point of one governing calculator

    Args:
        calculator: The point's calculator, after dimensioning.
        supports: Supports along the beam, first to last.
        analysis: The beam's analysis, for the shear at the point.
    """
    position_m = m_from_cm(calculator.bending_moment_position)
    span_ends_m = tuple(s.position_m for s in supports[1:])
    span_index = _span_index(position_m, span_ends_m)
    support = _support_at(position_m, supports)
    tensioned = calculator.tensioned_reinforcement
    compression = (
        ()
        if calculator.is_singly_reinforced
        else read_layers(calculator.compressed_reinforcement)
    )
    return DesignPoint(
        kind=PointKind.SPAN if support is None else PointKind.SUPPORT,
        ref=str(span_index) if support is None else support.label,
        span_index=span_index,
        position_m=position_m,
        mk_knm=calculator.bending_moment,
        d_cm=calculator.d,
        bottom_tensioned=tensioned.is_bottom_reinforcement,
        as_required_cm2=tensioned.required_area or 0.0,
        as_effective_cm2=tensioned.area,
        tension_layers=read_layers(tensioned),
        compression_layers=compression,
        moment_shift_cm=tensioned.moment_shift or 0.0,
        vk_kn=analysis.shear_force(calculator.bending_moment_position),
        y_cm=calculator.actual_y,
        y_max_cm=calculator.max_y,
        anchorages=_anchorages(tensioned),
    )
