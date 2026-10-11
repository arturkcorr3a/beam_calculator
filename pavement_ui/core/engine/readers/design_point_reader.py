"""Read a design point (moment extreme) from its governing RebarCalculator."""

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.engine.readers.reinforcement_reader import read_layers
from pavement_ui.core.results.beam_result import DesignPoint, PointKind, SupportMark
from src.calculators.rebar_calculator import RebarCalculator
from src.structural_elements.rectangular_beam import RectangularBeam

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


def read_point(
    calculator: RebarCalculator, supports: tuple[SupportMark, ...]
) -> DesignPoint:
    """Build the design point of one governing calculator

    Args:
        calculator: The point's calculator, after dimensioning.
        supports: Supports along the beam, first to last.
    """
    position_m = m_from_cm(calculator.bending_moment_position)
    span_ends_m = tuple(s.position_m for s in supports[1:])
    span_index = _span_index(position_m, span_ends_m)
    support = _support_at(position_m, supports)
    tensioned = calculator.tensioned_reinforcement
    # same cover and stirrup the engine subtracts for d; read inside the job
    face_offset_cm = RectangularBeam.nominal_covering + (
        calculator.stirrup_diameter or 0.0
    )
    compression = (
        ()
        if calculator.is_singly_reinforced
        else read_layers(calculator.compressed_reinforcement, face_offset_cm)
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
        tension_layers=read_layers(tensioned, face_offset_cm),
        compression_layers=compression,
        moment_shift_cm=tensioned.moment_shift or 0.0,
    )
