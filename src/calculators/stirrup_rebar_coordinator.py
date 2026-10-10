from src.calculators.rebar_calculator import EFFECTIVE_DEPTH_TOLERANCE, RebarCalculator
from src.logger import log_element, log_iteration
from src.reinforcement.stirrups import Stirrups

MAX_ITERATIONS = 1_000  # stirrup-longitudinal reinforcement passes before giving up


def coordinate_span(calculators: list[RebarCalculator], stirrups: Stirrups) -> None:
    """Dimension a span's stirrups and longitudinal reinforcements together

    The stirrups depend on the effective depth (d), which in turn depends on the stirrup diameter and on the chosen bars. Each pass dimensions the stirrups with the smallest d among the calculators (the most conservative), then dimensions every calculator's longitudinal reinforcement with the chosen stirrup diameter and moment shift. Passes repeat until no calculator's d changes by more than EFFECTIVE_DEPTH_TOLERANCE.

    Args:
        calculators: Longitudinal reinforcement calculators of the interest points that share the stirrups (one span).
        stirrups: The span's stirrups; chosen in place.

    Raises:
        ValueError: If no calculators are given, or if d does not converge within MAX_ITERATIONS passes.
    """
    if not calculators:
        raise ValueError("At least one rebar calculator is needed to coordinate.")

    coordination_label = "Coordinator for span"

    previous_depths: list[float] | None = None
    for iteration in range(1, MAX_ITERATIONS + 1):
        smallest_d = min(calculator.d for calculator in calculators)  # cm
        _, stirrup_diameter = stirrups.calculate_and_choose(smallest_d)  # cm
        moment_shift = stirrups.calculator.calculate_moment_shift()  # cm

        for calculator in calculators:
            calculator.calculate_for(stirrup_diameter, moment_shift)

        depths = [calculator.d for calculator in calculators]  # cm
        if previous_depths is not None:
            max_delta_d = max(
                abs(depth - previous)
                for depth, previous in zip(depths, previous_depths, strict=True)
            )
            log_iteration(
                f"{iteration}: smallest d={smallest_d:.2f} cm | phi={stirrup_diameter * 10:.1f} mm | max delta d={max_delta_d:.3f} cm",
                coordination_label,
            )
            if max_delta_d <= EFFECTIVE_DEPTH_TOLERANCE:
                log_element(
                    f"phi={stirrup_diameter * 10:.1f} mm | smallest d={min(depths):.2f} cm",
                    coordination_label,
                )
                return
        previous_depths = depths

    raise ValueError(
        f"Effective depth (d) did not converge within {MAX_ITERATIONS} stirrup-longitudinal reinforcement passes."
    )
