from dataclasses import dataclass
from typing import cast

from src.calculators.rebar_calculator import EFFECTIVE_DEPTH_TOLERANCE, RebarCalculator
from src.errors import EffectiveDepthDivergedError, EnginePreconditionError
from src.logger import log_element, log_general, log_iteration
from src.reinforcement.stirrups import Stirrups

type StirrupSignature = tuple[
    float, float, tuple[float, ...]
]  # spacing, diameter, d of each calculator

COORDINATION_LABEL = "Coordinator for span"
MAX_ITERATIONS = 1_000  # stirrup-longitudinal reinforcement passes before giving up


@dataclass(frozen=True)
class StirrupPass:
    """One pass of the stirrup-longitudinal reinforcement iteration

    Attributes:
        signature: Chosen stirrups and resulting effective depths; identifies the state.
        smallest_d: Smallest effective depth the stirrups were dimensioned with (cm).
        spacing: Chosen stirrup spacing (cm).
        diameter: Chosen stirrup diameter (cm).
        required_ratio: A_sw/s the stirrups were chosen for (cm²/cm).
        provided_ratio: A_sw/s of the chosen stirrups (cm²/cm).
    """

    signature: StirrupSignature
    smallest_d: float
    spacing: float
    diameter: float
    required_ratio: float
    provided_ratio: float

    def describe(self) -> str:
        """Describe the stirrups, e.g. ``8.0mm every 20.0 cm``"""
        return f"{self.diameter * 10:.1f}mm every {self.spacing:.1f} cm"


def select_stirrup_pass(
    passes: list[StirrupPass], final_required_ratio: float
) -> tuple[StirrupPass, bool]:
    """Pick the stirrups to keep when the iteration cycles

    A pass is safe when its stirrups cover the A_sw/s required at the effective depth they result in. Pass i's own-d requirement is what pass i + 1 was chosen for; the last pass's is ``final_required_ratio``. The cheapest safe pass is kept; if none is safe, the one with the largest A_sw/s is kept instead.

    Args:
        passes: Consecutive passes of the cycle (non-empty).
        final_required_ratio: A_sw/s required at the last pass's own effective depth (cm²/cm).

    Returns:
        The kept pass, and whether it is safe.
    """
    own_requirements = [following.required_ratio for following in passes[1:]] + [
        final_required_ratio
    ]
    safe = [
        stirrup_pass
        for stirrup_pass, required in zip(passes, own_requirements, strict=True)
        if stirrup_pass.provided_ratio >= required
    ]
    if safe:
        return min(safe, key=lambda stirrup_pass: stirrup_pass.provided_ratio), True
    return max(passes, key=lambda stirrup_pass: stirrup_pass.provided_ratio), False


def coordinate_span(calculators: list[RebarCalculator], stirrups: Stirrups) -> None:
    """Dimension a span's stirrups and longitudinal reinforcements together

    The stirrups depend on the effective depth (d), which in turn depends on the stirrup diameter and on the chosen bars. Each pass dimensions the stirrups with the smallest d among the calculators (the most conservative), then dimensions every calculator's longitudinal reinforcement with the chosen stirrup diameter, moment shift and the span's design shear. Passes repeat until no calculator's d changes by more than EFFECTIVE_DEPTH_TOLERANCE. A repeated state (stirrups and depths) is a cycle; the cheapest stirrups in it that cover the A_sw/s required at their own d are kept.

    Args:
        calculators: Longitudinal reinforcement calculators of the interest points that share the stirrups (one span).
        stirrups: The span's stirrups; chosen in place.

    Raises:
        EnginePreconditionError: If no calculators are given.
        EffectiveDepthDivergedError: If d neither converges nor cycles within MAX_ITERATIONS passes.
    """
    if not calculators:
        raise EnginePreconditionError(
            "At least one rebar calculator is needed to coordinate."
        )

    previous_depths: list[float] | None = None
    passes: list[StirrupPass] = []
    last_seen: dict[StirrupSignature, int] = {}  # signature -> latest pass index
    for iteration in range(1, MAX_ITERATIONS + 1):
        smallest_d = min(calculator.d for calculator in calculators)  # cm
        spacing, stirrup_diameter = stirrups.calculate_and_choose(smallest_d)  # cm
        required_ratio = cast(float, stirrups.required_ratio)  # cm²/cm
        _dimension_longitudinal(calculators, stirrups, stirrup_diameter)

        depths = [calculator.d for calculator in calculators]  # cm
        stirrup_pass = StirrupPass(
            signature=(spacing, stirrup_diameter, tuple(round(d, 6) for d in depths)),
            smallest_d=smallest_d,
            spacing=spacing,
            diameter=stirrup_diameter,
            required_ratio=required_ratio,
            provided_ratio=Stirrups.calculate_ratio(stirrup_diameter, spacing),
        )
        if previous_depths is not None:
            max_delta_d = max(
                abs(depth - previous)
                for depth, previous in zip(depths, previous_depths, strict=True)
            )
            log_iteration(
                f"{iteration}: smallest d={smallest_d:.2f} cm | phi={stirrup_diameter * 10:.1f} mm | max delta d={max_delta_d:.3f} cm",
                COORDINATION_LABEL,
            )
            if max_delta_d <= EFFECTIVE_DEPTH_TOLERANCE:
                log_element(
                    f"phi={stirrup_diameter * 10:.1f} mm | smallest d={min(depths):.2f} cm",
                    COORDINATION_LABEL,
                )
                return
        previous_depths = depths

        previous_index = last_seen.get(stirrup_pass.signature)
        last_seen[stirrup_pass.signature] = len(passes)
        passes.append(stirrup_pass)
        if previous_index is not None:  # this state was already visited
            _resolve_cycle(
                passes[previous_index:-1], required_ratio, calculators, stirrups
            )
            return

    raise EffectiveDepthDivergedError(max_iterations=MAX_ITERATIONS)


def _dimension_longitudinal(
    calculators: list[RebarCalculator], stirrups: Stirrups, stirrup_diameter: float
) -> None:
    """Dimension every calculator's longitudinal reinforcement for the chosen stirrups"""
    moment_shift = stirrups.calculator.calculate_moment_shift()  # cm
    for calculator in calculators:
        calculator.calculate_for(
            stirrup_diameter,
            moment_shift,
            stirrups.calculator.design_shear_force,
        )


def _resolve_cycle(
    cycle: list[StirrupPass],
    final_required_ratio: float,
    calculators: list[RebarCalculator],
    stirrups: Stirrups,
) -> None:
    """Keep the best stirrups of a cycle and dimension the longitudinal reinforcement for them

    Args:
        cycle: The passes of the cycle, in order.
        final_required_ratio: A_sw/s the repeating pass was chosen for, which is what the
            last cycle member requires at its own d (cm²/cm).
        calculators: Longitudinal reinforcement calculators of the span.
        stirrups: The span's stirrups; chosen in place.
    """
    kept, is_safe = select_stirrup_pass(cycle, final_required_ratio)
    # The choice is deterministic, so dimensioning with the same d gives back the same state
    _, stirrup_diameter = stirrups.calculate_and_choose(kept.smallest_d)  # cm
    _dimension_longitudinal(calculators, stirrups, stirrup_diameter)
    log_element(
        f"Cycle between {' <-> '.join(p.describe() for p in cycle)}; keeping {kept.describe()}",
        COORDINATION_LABEL,
    )
    if not is_safe:
        log_general(
            f"WARNING: no stirrups in the cycle cover the A_sw/s required at their own d; keeping the largest, {kept.describe()}"
        )
