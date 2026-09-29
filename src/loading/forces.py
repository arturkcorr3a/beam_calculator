import itertools
from fractions import Fraction
from typing import Any, cast

from sympy import Expr, Interval, Piecewise, Rational, solve, solveset  # type: ignore
from sympy.abc import x as symbol_x  # type: ignore
from sympy.sets.sets import FiniteSet  # type: ignore
from sympy.sets.sets import Interval as SympyInterval

from src.logger import log_property
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as SPC,
)
from src.structural_elements.rectangular_beam import RectangularBeam

LOAD_FACTOR = 1.4  # ABNT NBR 6118 - Section 11.7.1 - Table 11.1 - for both permanent and variable loads
RECTANGULAR_SECTION_SHAPE_FACTOR = 1.5  # ABNT NBR 6118 - Section 17.3.1


def design_effort_elu(bending_moment: float) -> float:
    """Calculate the design effort (ELU) by applying the load factor.

    Args:
        bending_moment: Calculated bending moment in any consistent unit.

    Returns:
        Design bending moment in the same unit as input.
    """
    return bending_moment * LOAD_FACTOR


def max_design_bending_moment(beam: RectangularBeam, d: float, y_max: float) -> float:
    """Calculate the maximum design bending moment for singly reinforced rectangular beam.

    Args:
        beam: Rectangular beam section.
        d: Effective depth of the beam (cm).
        y_max: Maximum depth of the equivalent rectangular stress block (cm).

    Returns:
        Maximum design bending moment (kN.cm).
    """
    uniform_stress = beam.concrete.uniform_stress  # kN/cm²
    return uniform_stress * beam.width * y_max * (d - 0.5 * y_max)


def min_design_bending_moment(beam: RectangularBeam) -> float:
    """Calculate the minimum design bending moment based on the minimum tension rebar area.

    Args:
        beam: Rectangular beam section.

    Returns:
        Minimum design bending moment (kN.cm).
    """
    w_0 = SPC.gross_section_modulus(beam.width, beam.height)
    return 0.8 * w_0 * beam.concrete.fctk_sup  # kN.cm


def get_almost_permanent_combination_reduction_factor(usage: str | None) -> float:
    # IMPLEMENT from ABNT NBR 6118 - Section 11.8.2.4 (Table 11.3) -> redirects to ABNT NBR 8681 - see how can I get it for non-residential nor commercial structures
    if usage is None:
        return 0.3
    return 0.30


def almost_permanent_combination_els(
    permanent_load: float, variable_load: float, usage: str | None = None
) -> float:
    """Calculate the almost permanent load combination for ELS (CQP).

    Assumes a uniform usage category across the structure, yielding a single
    reduction factor (psi_2) for all variable loads.

    Args:
        permanent_load: Permanent load (kN).
        variable_load: Variable load (kN).
        usage: Usage category string used to look up psi_2.

    Returns:
        Almost permanent load combination (kN).

    References:
        ABNT NBR 6118 — Section 11.8.3.2, Table 11.4
    """
    psi_2 = get_almost_permanent_combination_reduction_factor(usage)
    return permanent_load + psi_2 * variable_load


# TODO change the way of ELU and design values: combine the actions previously to the structural analysis; use the following function when performing the structural analysis, and then take the output to calculate
def normal_elu_combination(permanent_load: float, variable_load: float) -> float:
    """Calculate the normal ELU load combination applying load factor γ_f = 1.4.

    Args:
        permanent_load: Permanent load (kN).
        variable_load: Variable load (kN).

    Returns:
        Design load combination (kN).

    References:
        ABNT NBR 6118 — Section 11.8.2.4, Table 11.3
    """
    return LOAD_FACTOR * (permanent_load + variable_load)


def calculate_cracking_moment(
    concrete_tensile_strength: float,
    distance_to_tension_fiber: float,
    moment_of_inertia: float,
) -> float:
    """Calculate the cracking moment (M_r) for a rectangular cross-section.

    Args:
        concrete_tensile_strength: Tensile strength of concrete f_ct (kN/cm²); use
            fct_m for deformation checks or fctk_inf for crack-formation checks.
        distance_to_tension_fiber: Distance from the section centroid to the most
            tensile fiber y_t (cm).
        moment_of_inertia: Gross cross-section moment of inertia I_c (cm⁴).

    Returns:
        Cracking moment M_r (kN.cm).

    References:
        ABNT NBR 6118 — Section 17.3.1
    """
    return (
        RECTANGULAR_SECTION_SHAPE_FACTOR
        * concrete_tensile_strength
        * moment_of_inertia
        / distance_to_tension_fiber
    )


def bending_moment_zeros(
    bending_moment_expression: Expr,
    lower_bound: float,
    upper_bound: float,
    element_label: str = "",
) -> list[float]:
    """Find all x-positions where the bending moment equals zero.

    Args:
        bending_moment_expression: Symbolic M(x) in x (kN.m; x in cm).
        lower_bound: Left boundary of the beam domain (cm).
        upper_bound: Right boundary of the beam domain (cm).

    Returns:
        Sorted list of x-coordinates where M = 0 (cm).
    """
    zeros_raw: object = solveset(
        bending_moment_expression,
        symbol_x,
        domain=Interval(_to_sympy_bound(lower_bound), _to_sympy_bound(upper_bound)),
    )
    finite_zeros = _extract_finite_zeros(zeros_raw, lower_bound, upper_bound)
    log_property(f"Points where bending moment is zero:  {finite_zeros}", element_label)
    return finite_zeros


def bending_moment_extremes_per_segment(
    bending_moment_expression: Expr,
    shear_force_expression: Expr,
    lower_bound: float,
    upper_bound: float,
) -> list[tuple[float, float]]:
    """Find the dominant bending-moment extreme (max or min) in each segment between zeros.

    Args:
        bending_moment_expression: Symbolic M(x) in x (kN.m; x in cm).
        shear_force_expression: Symbolic V(x) in x (kN; x in cm).
        lower_bound: Left boundary of the beam domain (cm).
        upper_bound: Right boundary of the beam domain (cm).

    Returns:
        One `(x, M)` tuple per segment, sorted left to right (x in cm, M in kN.m).
    """
    zeros = bending_moment_zeros(bending_moment_expression, lower_bound, upper_bound)
    boundary_points = sorted({lower_bound, upper_bound} | set(zeros))

    all_breakpoints = _piecewise_breakpoints(
        bending_moment_expression, lower_bound, upper_bound
    )

    extremes: list[tuple[float, float]] = []
    for segment_start, segment_end in itertools.pairwise(boundary_points):
        shear_zeros_raw: object = solveset(
            shear_force_expression,
            symbol_x,
            domain=Interval(
                _to_sympy_bound(segment_start), _to_sympy_bound(segment_end)
            ),
        )
        shear_zeros = _extract_finite_zeros(shear_zeros_raw, segment_start, segment_end)

        interior_breakpoints = [
            bp for bp in all_breakpoints if segment_start < bp < segment_end
        ]

        candidate_positions = sorted(
            set(shear_zeros) | {segment_start, segment_end} | set(interior_breakpoints)
        )

        dominant_position = max(
            candidate_positions,
            key=lambda position: abs(
                float(bending_moment_expression.subs(symbol_x, position))  # type: ignore[attr-defined]
            ),
        )
        dominant_moment = float(
            bending_moment_expression.subs(symbol_x, dominant_position)  # type: ignore[attr-defined]
        )
        extremes.append((dominant_position, dominant_moment))

    return extremes


def positions_for_bending_moment(
    bending_moment_expression: Expr,
    target_moment: float,
    lower_bound: float,
    upper_bound: float,
) -> list[float]:
    """Find all x-positions where the bending moment equals a target value.

    Args:
        bending_moment_expression: Symbolic M(x) in x (kN.m; x in cm).
        target_moment: Target bending moment value (kN.m).
        lower_bound: Left boundary of the beam domain (cm).
        upper_bound: Right boundary of the beam domain (cm).

    Returns:
        Sorted list of x-coordinates where M(x) = target_moment (cm).
        Empty if the target is unreachable or has no real solution.
    """
    solutions: list[Any] = cast(
        list[Any],
        solve(
            bending_moment_expression - target_moment,  # type: ignore
            symbol_x,
        ),
    )
    return sorted(
        float(solution)
        for solution in solutions
        if solution.is_real and lower_bound <= float(solution) <= upper_bound
    )


# Bending-moment analysis utilities ----------------------------------------


def _to_sympy_bound(value: float) -> object:
    """Convert a float domain bound to a sympy exact number.

    Avoids the ``solveset`` Float-precision issue where endpoints with exact
    rational values are missed when the domain is ``Interval(0.0, 600.0)``.

    Args:
        value: Float domain boundary (cm).

    Returns:
        A sympy ``Rational`` (or ``Integer``) equivalent to ``value``.
    """
    fraction = Fraction(value).limit_denominator(10_000)
    return Rational(fraction.numerator, fraction.denominator)


def _extract_finite_zeros(
    solveset_result: object, lower_bound: float, upper_bound: float
) -> list[float]:
    """Extract finite zero-crossings from a ``solveset`` result.

    Handles the two shapes returned for ``Piecewise`` expressions: a plain
    ``FiniteSet`` (iterated directly) and a ``Union`` containing ``FiniteSet``
    or degenerate ``Interval(a, a)`` members. Proper non-degenerate intervals
    are ignored (they indicate M ≡ 0 over a stretch, not an isolated crossing).

    Args:
        solveset_result: Return value of ``sympy.solveset``.
        lower_bound: Left boundary of the beam domain (cm).
        upper_bound: Right boundary of the beam domain (cm).

    Returns:
        Sorted list of x-coordinates where the expression equals zero (cm).
    """
    finite: set[float] = set()

    # Plain FiniteSet — iterate elements directly (no .args sub-structure)
    if isinstance(solveset_result, FiniteSet):
        for value in solveset_result:
            float_value = float(value)  # type: ignore[arg-type]
            if lower_bound <= float_value <= upper_bound:
                finite.add(float_value)
        return sorted(finite)

    # Union or other composite — iterate .args as sub-sets
    args: object = getattr(solveset_result, "args", [solveset_result])
    for arg in args:  # type: ignore[union-attr]
        if isinstance(arg, FiniteSet):
            for value in arg:
                float_value = float(value)  # type: ignore[arg-type]
                if lower_bound <= float_value <= upper_bound:
                    finite.add(float_value)
        elif isinstance(arg, SympyInterval):
            try:
                start_float = float(arg.start)  # type: ignore[arg-type]
                end_float = float(arg.end)  # type: ignore[arg-type]
                if (
                    start_float == end_float
                    and lower_bound <= start_float <= upper_bound
                ):  # degenerate interval: single point
                    finite.add(start_float)
            except (TypeError, ValueError):
                pass

    return sorted(finite)


def _piecewise_breakpoints(
    expression: Expr, lower_bound: float, upper_bound: float
) -> list[float]:
    """Extract structural breakpoints from a sum-of-Piecewise expression.

    Breakpoints are x-coordinates where the shear force can have a jump
    discontinuity (supports, load boundaries).

    Args:
        expression: Symbolic M(x) or V(x) from ``indeterminatebeam``.
        lower_bound: Left boundary of the domain of interest (cm).
        upper_bound: Right boundary of the domain of interest (cm).

    Returns:
        Sorted list of breakpoint x-coordinates within [lower_bound, upper_bound] (cm).
    """
    breakpoints: set[float] = set()
    terms: object = getattr(expression, "args", [expression])
    for term in terms:  # type: ignore[union-attr]
        # Each term may be a coefficient multiplied by a Piecewise; find the
        # inner Piecewise regardless of the product structure.
        inner_piecewise: Piecewise | None = None
        if isinstance(term, Piecewise):
            inner_piecewise = term
        else:
            for sub_arg in getattr(term, "args", []):  # type: ignore[union-attr]
                if isinstance(sub_arg, Piecewise):
                    inner_piecewise = sub_arg
                    break

        if inner_piecewise is not None:
            for _, condition in inner_piecewise.args:  # type: ignore[union-attr]
                if not hasattr(condition, "lhs"):  # type: ignore
                    continue
                # The condition takes the form `(x - c) >= 0` where c is the
                # structural breakpoint. Evaluating the lhs at x=0 yields `-c`,
                # so the breakpoint is `c = -lhs(0)`.
                try:
                    breakpoint_candidate = -float(
                        condition.lhs.subs(symbol_x, 0)  # type: ignore[attr-defined]
                    )
                    if lower_bound <= breakpoint_candidate <= upper_bound:
                        breakpoints.add(breakpoint_candidate)
                except (TypeError, ValueError):
                    pass

    return sorted(breakpoints)
