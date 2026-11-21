"""Check the force to anchor at the end supports and add the bars it lacks."""

from collections.abc import Sequence
from dataclasses import dataclass

from src.calculators.support_bars import SpanRange, span_reinforcement
from src.loading.forces import design_effort_elu
from src.logger import log_operation, log_property
from src.reinforcement.reinforcement import Reinforcement
from src.structural_elements.rectangular_beam import RectangularBeam


@dataclass(frozen=True, slots=True)
class OuterSupport:
    """An end support of the beam, with the efforts and section data at it

    Attributes:
        support_index: Index of the support in ``beam.supports``.
        span: The span resting on the support.
        support_moment: Characteristic bending moment on the support (kN.m),
            signed; positive when it tensions the bottom bars.
        design_shear: Design shear force V_Sd at the support (kN).
        effective_depth: Effective depth d of the span's bottom bars (cm).
        stress_block_depth: Rectangular stress block depth y (cm).
        moment_shift: Moment shift a_l of the span's stirrups (cm).
        stirrup_diameter: Diameter of the span's stirrups (cm).
        moment_zeros: Positions along the beam where the bending moment is
            zero (cm).
    """

    support_index: int
    span: SpanRange
    support_moment: float
    design_shear: float
    effective_depth: float
    stress_block_depth: float
    moment_shift: float
    stirrup_diameter: float
    moment_zeros: tuple[float, ...] = ()


def outer_support_force(
    support_moment: float,
    effective_depth: float,
    stress_block_depth: float,
    moment_shift: float,
    design_shear: float,
) -> float:
    """Calculate the tensile force the bars must resist at an end support

    The design moment over the lever arm, counted only when it tensions the bars, plus the shear force times the moment shift over the effective depth. There is no axial force in this work.

    Args:
        support_moment: Characteristic bending moment on the support (kN.m),
            positive when it tensions the bars.
        effective_depth: Effective depth d (cm).
        stress_block_depth: Rectangular stress block depth y (cm); the lever
            arm is d minus half of it.
        moment_shift: Moment shift a_l (cm).
        design_shear: Design shear force V_Sd at the support (kN).

    Returns:
        Force F_sd in kN.

    References:
        ABNT NBR 6118:2026 — Section 18.3.2.4-b
    """
    design_moment = design_effort_elu(support_moment * 100)  # kN.cm
    lever_arm = effective_depth - stress_block_depth / 2  # cm
    shear_force = (moment_shift / effective_depth) * design_shear  # kN
    return max(design_moment / lever_arm, 0.0) + shear_force


def anchor_outer_supports(
    beam: RectangularBeam,
    reinforcements: Sequence[Reinforcement],
    supports: Sequence[OuterSupport],
) -> list[Reinforcement]:
    """Check the bars carried to each end support and size the bars they lack

    The span's positive bars anchored inside the support count towards F_sd / f_yd; being anchored, they already meet Section 18.3.2.4.1. When they fall short, the missing area is sized as a new point on the support's inner face, in a layer after the span's layers. When no bar reaches the support, that point takes the whole area, from the first layer. The new bars are anchored inside the support from its face and run into the span like any interest point's.

    Args:
        beam: Section the beam was dimensioned with.
        reinforcements: The beam's chosen reinforcements, after the span bars
            were carried to the supports (see ``carry_span_bars_to_supports``).
        supports: The beam's end supports.

    Returns:
        The new reinforcements, one per end support that needed bars.

    Raises:
        EnginePreconditionError: Propagated from the new reinforcement if no
            layer is left.
        NoReinforcementLayoutError: Propagated from the new reinforcement if no
            bar layout fits and anchors.

    References:
        ABNT NBR 6118:2026 — Sections 18.3.2.4-b and 18.3.2.4.1
    """
    added: list[Reinforcement] = []
    for support in supports:
        reinforcement = _anchor_outer_support(beam, reinforcements, support)
        if reinforcement is not None:
            added.append(reinforcement)
    return added


def _anchor_outer_support(
    beam: RectangularBeam,
    reinforcements: Sequence[Reinforcement],
    support: OuterSupport,
) -> Reinforcement | None:
    """Check one end support and return the reinforcement sized for its missing area, if any"""
    force = outer_support_force(
        support.support_moment,
        support.effective_depth,
        support.stress_block_depth,
        support.moment_shift,
        support.design_shear,
    )  # kN
    required = force / beam.steel.fyd  # cm²

    base = span_reinforcement(reinforcements, support.span)
    left = support.support_index == support.span.start_support_index
    carried = _carried_area(base, support.support_index, left)  # cm²
    log_property(
        f"End support {support.support_index} (F_sd = M_Sd / z + (a_l / d) V_Sd = {force:.2f} kN, V_Sd = {support.design_shear:.2f} kN): carried A_s = {carried:.3f} cm², required F_sd / f_yd = {required:.3f} cm²"
    )
    if carried >= required:
        log_operation(
            f"End support {support.support_index}: the anchored bars resist F_sd (NBR 6118 - 18.3.2.4-b) and are anchored from the face (18.3.2.4.1)."
        )
        return None

    stacked_on = base if carried > 0 else None
    missing = required - carried  # cm²
    log_operation(
        f"End support {support.support_index}: adding {missing:.3f} cm² of bars "
        + ("in a new layer" if stacked_on is not None else "as a new point")
        + " (NBR 6118 - 18.3.2.4-b)."
    )
    face = beam.supports[support.support_index]
    reinforcement = Reinforcement(
        beam,
        is_bottom_reinforcement=True,
        center_position=face.right if left else face.left,
        id=f"{beam.label} | End support {support.support_index}",
        moment_zeros=support.moment_zeros,
        anchored_support=support.support_index,
        stacked_on=stacked_on,
    )
    reinforcement.moment_shift = support.moment_shift
    reinforcement.stirrup_diameter = support.stirrup_diameter
    reinforcement.effective_depth = support.effective_depth
    reinforcement.stress_block_depth = support.stress_block_depth
    reinforcement.design_shear = support.design_shear
    reinforcement.set_required_area(missing)
    return reinforcement


def _carried_area(
    reinforcement: Reinforcement | None, support_index: int, left: bool
) -> float:
    """Return the area of the reinforcement's layers anchored inside a support (cm²)"""
    if reinforcement is None:
        return 0.0
    return sum(
        layer.area
        for position, layer in enumerate(reinforcement.chosen_bars)
        if layer.bars
        and reinforcement.layer_reaches_support(position, support_index, left)
    )
