import itertools
import math
from fractions import Fraction
from typing import Any, cast

from indeterminatebeam import UDLV, Beam, Support  # type: ignore
from sympy import Expr, Interval, Piecewise, Rational, solve, solveset  # type: ignore
from sympy.abc import x as symbol_x  # type: ignore
from sympy.sets.sets import FiniteSet  # type: ignore
from sympy.sets.sets import Interval as SympyInterval

from src.analysis.model import BeamSupport, DistributedLoad
from src.logger import log_property
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.structural_elements.rectangular_beam import RectangularBeam

UNITS = {
    "length": "cm",
    "force": "kN",
    "moment": "kN.m",
    "distributed": "kN/m",
    "stiffness": "kN/m",
    "A": "cm2",
    "G": "MPa",
    "E": "MPa",
    "I": "cm4",
    "deflection": "cm",
}

PINNED = (1, 1, 0)
FIXED = (1, 1, 1)


class IndeterminateBeamAnalysis:
    """Solves a beam with ``indeterminatebeam`` and exposes it as a BeamAnalysis.

    This is the only module allowed to depend on ``indeterminatebeam`` and sympy.
    """

    def __init__(
        self,
        section: RectangularBeam,
        supports: list[BeamSupport],
        loads: list[DistributedLoad],
    ) -> None:
        """Build and analyse the beam.

        Raises:
            NotImplementedError: If a support has a finite, nonzero rotational
                stiffness — ``indeterminatebeam`` cannot model rotational springs.
        """
        self._section = section
        width, height = section.width, section.height
        beam = Beam(  # pyright: ignore[reportUnknownVariableType]
            section.length,
            section.concrete.g_c,
            round(section.concrete.ecs),
            SectionPropertiesCalculator.moment_of_inertia(width, height),
            SectionPropertiesCalculator.rectangular_cross_sectional_area(width, height),
        )
        for key, unit in UNITS.items():
            beam.update_units(key, unit)  # pyright: ignore[reportUnknownMemberType]
        beam.add_loads(*[_to_udlv(load) for load in loads])  # pyright: ignore[reportUnknownMemberType]
        beam.add_supports(*[_to_support(support) for support in supports])  # pyright: ignore[reportUnknownMemberType]
        beam.analyse()  # pyright: ignore[reportUnknownMemberType]
        self._beam: Any = beam

    @property
    def length(self) -> float:
        """Total beam length (cm)."""
        return self._section.length

    def bending_moment(self, position: float) -> float:
        """Return the bending moment at a position (kN.m, sagging positive)."""
        return float(self._beam.get_bending_moment(position))

    def shear_force(self, position: float) -> float:
        """Return the shear force at a position (kN)."""
        return float(self._beam.get_shear_force(position))

    def deflection(self, position: float) -> float:
        """Return the deflection at a position (cm, downward negative)."""
        return float(self._beam.get_deflection(position))

    def max_abs_shear(self) -> float:
        """Return the largest absolute shear force along the beam (kN)."""
        return abs(float(self._beam.get_shear_force(return_absmax=True)))

    def reaction(self, position: float) -> float:
        """Return the vertical support reaction at a support position (kN)."""
        return float(self._beam.get_reaction(position, "y"))

    def moment_zeros(self) -> list[float]:
        """Return the sorted positions where the bending moment is zero (cm)."""
        return bending_moment_zeros(
            self._bending_moment_expression, 0.0, self.length, self._section.label
        )

    def moment_extremes_per_segment(self) -> list[tuple[float, float]]:
        """Return the dominant bending-moment extreme in each segment between zeros.

        Returns:
            One `(position, moment)` per segment, sorted left to right (position
            in cm, moment in kN.m).
        """
        return bending_moment_extremes_per_segment(
            self._bending_moment_expression,
            self._shear_force_expression,
            0.0,
            self.length,
        )

    def moment_extreme_in_range(self, start: float, end: float) -> tuple[float, float]:
        """Return the bending moment with the greatest absolute value within a range.

        Args:
            start: Left end of the range (cm).
            end: Right end of the range (cm); must be >= start.

        Returns:
            `(position, moment)` of the dominant moment (position in cm, moment in kN.m).
        """
        return bending_moment_extreme_in_range(
            self._bending_moment_expression, self._shear_force_expression, start, end
        )

    def positions_for_moment(self, target_moment: float) -> list[float]:
        """Return the sorted positions where the bending moment equals a target.

        Args:
            target_moment: Bending moment to locate (kN.m).

        Returns:
            Positions along the beam (cm); empty if the target is never reached.
        """
        return positions_for_bending_moment(
            self._bending_moment_expression, target_moment, 0.0, self.length
        )

    @property
    def _bending_moment_expression(self) -> Expr:
        """Symbolic M(x) in x (kN.m; x in cm)."""
        return cast(Expr, self._beam._bending_moments)

    @property
    def _shear_force_expression(self) -> Expr:
        """Symbolic V(x) in x (kN; x in cm)."""
        return cast(Expr, self._beam._shear_forces)


def _to_support(support: BeamSupport) -> Any:
    """Convert a BeamSupport into an ``indeterminatebeam.Support``.

    Raises:
        NotImplementedError: If the rotational stiffness is finite and nonzero.
    """
    if support.rotational_stiffness == 0.0:
        fixity = PINNED
    elif math.isinf(support.rotational_stiffness):
        fixity = FIXED
    else:
        raise NotImplementedError(
            "indeterminatebeam cannot model rotational springs; got a rotational "
            f"stiffness of {support.rotational_stiffness} kN.m/rad at "
            f"{support.position} cm."
        )
    return Support(support.position, fixity)  # pyright: ignore[reportArgumentType]


def _to_udlv(load: DistributedLoad) -> Any:
    """Convert a DistributedLoad into an ``indeterminatebeam`` UDLV (negative is downward)."""
    return UDLV(-load.intensity, (load.start, load.end))  # pyright: ignore[reportArgumentType]


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

    return [
        _dominant_bending_moment(
            bending_moment_expression,
            shear_force_expression,
            segment_start,
            segment_end,
            all_breakpoints,
        )
        for segment_start, segment_end in itertools.pairwise(boundary_points)
    ]


def bending_moment_extreme_in_range(
    bending_moment_expression: Expr,
    shear_force_expression: Expr,
    start: float,
    end: float,
) -> tuple[float, float]:
    """Find the bending moment with the greatest absolute value within a range.

    Args:
        bending_moment_expression: Symbolic M(x) in x (kN.m; x in cm).
        shear_force_expression: Symbolic V(x) in x (kN; x in cm).
        start: Left end of the range (cm).
        end: Right end of the range (cm); must be >= start.

    Returns:
        `(x, M)` of the dominant moment (x in cm, M in kN.m).
    """
    breakpoints = _piecewise_breakpoints(bending_moment_expression, start, end)
    return _dominant_bending_moment(
        bending_moment_expression, shear_force_expression, start, end, breakpoints
    )


def _dominant_bending_moment(
    bending_moment_expression: Expr,
    shear_force_expression: Expr,
    start: float,
    end: float,
    breakpoints: list[float],
) -> tuple[float, float]:
    """Pick the greatest absolute bending moment among the range ends, shear zeros and interior breakpoints.

    Args:
        bending_moment_expression: Symbolic M(x) in x (kN.m; x in cm).
        shear_force_expression: Symbolic V(x) in x (kN; x in cm).
        start: Left end of the range (cm).
        end: Right end of the range (cm).
        breakpoints: Piecewise breakpoints of M(x) (cm); only those strictly inside the range are used.

    Returns:
        `(x, M)` of the dominant moment (x in cm, M in kN.m).
    """
    shear_zeros_raw: object = solveset(
        shear_force_expression,
        symbol_x,
        domain=Interval(_to_sympy_bound(start), _to_sympy_bound(end)),
    )
    shear_zeros = _extract_finite_zeros(shear_zeros_raw, start, end)

    interior_breakpoints = [bp for bp in breakpoints if start < bp < end]

    candidate_positions = sorted(
        set(shear_zeros) | {start, end} | set(interior_breakpoints)
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
    return dominant_position, dominant_moment


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
