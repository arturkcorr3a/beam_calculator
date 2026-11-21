"""An isolated continuous beam on pillars, built outside a pavement."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate

from src.detailing.detailing_beam import DetailingBeam
from src.detailing.mark_registry import MarkRegistry
from src.errors import InputError
from src.loading.linear_loads import LinearLoads
from src.loading.load_component import LoadComponent, LoadKind
from src.logger import log_general, log_operation
from src.pavement_elements.beam_span import Span
from src.pavement_elements.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement_elements.geometry_utils import Alignment
from src.pavement_elements.pillar import Pillar

_CM2_PER_M2 = 10_000.0


@dataclass(frozen=True, slots=True)
class IsolatedPillar:
    """Cross-section of a pillar under the beam

    Attributes:
        width: Extent along the beam axis (cm).
        depth: Extent perpendicular to the beam axis (cm); must cover the beam width.
    """

    width: float
    depth: float


@dataclass(frozen=True, slots=True)
class OwnWeightLoad:
    """The beam's own weight, from its section

    Attributes:
        span_index: Zero-based span the load acts on; None for every span.
    """

    span_index: int | None = None


@dataclass(frozen=True, slots=True)
class WallLoad:
    """A masonry wall standing on the beam

    Attributes:
        wall: Masonry type, thickness and coating (ABNT NBR 6120:2019 Table 2).
        height: Wall height (m).
        span_index: Zero-based span the load acts on; None for every span.
    """

    wall: WallDefinition
    height: float
    span_index: int | None = None


@dataclass(frozen=True, slots=True)
class CustomLoad:
    """A uniform load given by the user

    Attributes:
        label: Name shown in the reports.
        value: Load intensity (kN/m), positive downward.
        variable: Whether the load is variable; otherwise permanent.
        psi_2: Quasi-permanent reduction factor, in [0, 1]; used only when variable.
        span_index: Zero-based span the load acts on; None for every span.
    """

    label: str
    value: float
    variable: bool = False
    psi_2: float = 0.0
    span_index: int | None = None


type IsolatedLoad = OwnWeightLoad | WallLoad | CustomLoad


def build_isolated_beam(
    span_lengths: Sequence[float],
    width: float,
    height: float,
    pillars: Sequence[IsolatedPillar],
    loads: Sequence[IsolatedLoad],
    beam_id: str = "V1",
) -> tuple[ContinuousBeam, dict[str, Pillar]]:
    """Build a loaded continuous beam on pillars, ready to be dimensioned

    The pillars ("P1", "P2", …) are laid along the x axis at the cumulative span
    lengths, and the beam is centered on them. The section is the one given (no
    pre-sizing). Each load is added to the span it names, or to every span.
    The caller dimensions it (``ContinuousBeam.dimension``) and then details
    it with ``detail_isolated_beam``.

    Args:
        span_lengths: Distance between consecutive pillar axes (cm), > 0.
        width: Beam width b (cm).
        height: Beam height h (cm), > 0.
        pillars: One pillar per support, left to right (spans + 1).

    Returns:
        The beam and its pillar registry.

    Raises:
        InputError: If the inputs are inconsistent (pillar count, lengths,
            height, span index, ψ2), or propagated from the beam and pillar
            validations (minimum dimensions, pillar depth not covering the
            beam, no clear span).
    """
    _validate(span_lengths, height, pillars, loads)
    log_general(f"Isolated beam {beam_id}: {len(span_lengths)} span(s)")
    positions = [0.0, *accumulate(span_lengths)]  # cm
    registry = {
        f"P{index}": Pillar(x, 0.0, pillar.width, pillar.depth, id=f"P{index}")
        for index, (x, pillar) in enumerate(zip(positions, pillars, strict=True), 1)
    }
    ids = list(registry)
    beam = ContinuousBeam(ids, ids[0], width, Alignment.CENTER, None, id=beam_id)
    beam.height = height
    beam.resolve_and_validate(registry)
    for load in loads:
        _apply(beam, load)
    return beam, registry


def detail_isolated_beam(beam: ContinuousBeam) -> DetailingBeam:
    """Detail a dimensioned isolated beam and mark its bars from N1

    Marks are what the bar schedule and the quantities count, as in a pavement
    with this beam alone.

    Raises:
        BeamCalculatorError: Propagated from ``ContinuousBeam.detail``.
    """
    detailing = beam.detail()
    MarkRegistry().assign(detailing)
    return detailing


def _validate(
    span_lengths: Sequence[float],
    height: float,
    pillars: Sequence[IsolatedPillar],
    loads: Sequence[IsolatedLoad],
) -> None:
    """Raise InputError on inputs the beam and pillar classes do not check."""
    if not span_lengths:
        raise InputError("The beam must have at least one span.")
    if len(pillars) != len(span_lengths) + 1:
        raise InputError(
            f"A beam with {len(span_lengths)} span(s) needs {len(span_lengths) + 1} "
            f"pillars. Got {len(pillars)}."
        )
    if any(length <= 0 for length in span_lengths):
        raise InputError(f"Span lengths must be positive. Got {list(span_lengths)} cm.")
    if height <= 0:
        raise InputError(f"Beam height must be positive. Got {height} cm.")
    for load in loads:
        index = load.span_index
        if index is not None and not 0 <= index < len(span_lengths):
            raise InputError(
                f"Load on span {index + 1}, but the beam has {len(span_lengths)} span(s)."
            )
        if isinstance(load, CustomLoad) and not 0.0 <= load.psi_2 <= 1.0:
            raise InputError(f"psi_2 must be between 0 and 1. Got {load.psi_2}.")


def _spans(beam: ContinuousBeam, span_index: int | None) -> list[Span]:
    return beam.spans if span_index is None else [beam.spans[span_index]]


def _apply(beam: ContinuousBeam, load: IsolatedLoad) -> None:
    """Add one load's component to each span it acts on."""
    psi_2: float | None = None
    match load:
        case OwnWeightLoad():
            value = LinearLoads.get_concrete_element_own_weight(
                beam.width * beam.height / _CM2_PER_M2
            )  # kN/m
            component = LoadComponent(LoadKind.OWN_WEIGHT, None, value)
        case WallLoad():
            value = LinearLoads.get_wall_load(
                *load.wall.get_parameters_for_load(), load.height
            )  # kN/m
            component = LoadComponent(LoadKind.WALL, None, value)
        case CustomLoad(variable=True):
            component = LoadComponent(LoadKind.CUSTOM, load.label, 0.0, load.value)
            psi_2 = load.psi_2
        case CustomLoad():
            component = LoadComponent(LoadKind.CUSTOM, load.label, load.value)
    where = "all spans" if load.span_index is None else f"span {load.span_index + 1}"
    log_operation(
        f"Load {component.kind.value} {component.source_id or ''}: "
        f"g {component.permanent:.2f}, q {component.variable:.2f} kN/m on {where}"
    )
    for span in _spans(beam, load.span_index):
        span.add_component(component, psi_2)
