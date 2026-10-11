"""Sample bending moment and shear force diagrams from an engine analysis."""

from collections.abc import Callable, Sequence

from pavement_ui.core.engine.keys import m_from_cm
from pavement_ui.core.results.beam_result import DiagramSeries
from src.analysis.beam_analysis import BeamAnalysis

_SAMPLES = 200
_SUPPORT_OFFSET_CM = 0.01  # each side of a support, to capture shear jumps


def _positions_cm(length_cm: float, supports_cm: Sequence[float]) -> list[float]:
    """Evenly spaced positions, plus both sides of every interior support."""
    positions = {length_cm * i / _SAMPLES for i in range(_SAMPLES + 1)}
    for support in supports_cm:
        if 0.0 < support < length_cm:
            positions.update(
                (support - _SUPPORT_OFFSET_CM, support + _SUPPORT_OFFSET_CM)
            )
            positions.discard(support)
    return sorted(positions)


def _series(
    positions_cm: list[float],
    supports_cm: Sequence[float],
    force: Callable[[float], float],
) -> DiagramSeries:
    """Evaluate force; points beside a support are recorded at the support itself."""
    xs: list[float] = []
    values: list[float] = []
    for x in positions_cm:
        snapped = next(
            (s for s in supports_cm if abs(x - s) <= _SUPPORT_OFFSET_CM * 1.5), x
        )
        xs.append(m_from_cm(snapped))
        values.append(force(x))
    return DiagramSeries(tuple(xs), tuple(values))


def sample(
    analysis: BeamAnalysis, supports_cm: Sequence[float]
) -> tuple[DiagramSeries, DiagramSeries]:
    """Sample the moment (kN·m, sagging positive) and shear (kN) diagrams

    Args:
        analysis: The beam's structural analysis (positions in cm).
        supports_cm: Support positions along the beam (cm); at interior
            supports the shear is sampled on both sides under the same x.

    Returns:
        The moment and shear series, with positions in m.
    """
    positions = _positions_cm(analysis.length, supports_cm)
    moment = _series(positions, supports_cm, analysis.bending_moment)
    shear = _series(positions, supports_cm, analysis.shear_force)
    return moment, shear
