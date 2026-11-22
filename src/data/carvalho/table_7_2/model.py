"""Dataclass models for Carvalho & Figueiredo Filho (2014) - Chapter 7 - Table 7.2 (Quadro 7.2)."""

import math
from dataclasses import dataclass

from src.data.carvalho.utils import find_bracket_and_fraction
from src.errors import EnginePreconditionError
from src.logger import log_property, logger_label
from src.pavement_elements.slab_edge import Edges, SupportCondition


@logger_label("Carvalho - Table 7.2")
@dataclass(frozen=True)
class SlabDeflectionEntry:
    """Deflection coefficient (alpha) row for a given aspect ratio (ly / lx)."""

    aspect_ratio: float
    cases: tuple[float, ...]

    def get_alpha(self, case: int) -> float:
        """Return the alpha coefficient for the specified boundary case (1 to 9)."""
        if case not in range(1, 10):
            raise EnginePreconditionError(
                f"Invalid case: {case}. Must be an integer between 1 and 9."
            )
        result = self.cases[case - 1]
        log_property(f"α(case={case}) = {result:.6f}")
        return result


@logger_label("Carvalho - Table 7.2")
@dataclass(frozen=True)
class Table72:
    """Roberto Chust de Carvalho & Jasson Rodrigues de Figueiredo Filho - Chapter 7 - Quadro 7.2.

    Manages the data lookup and interpolation for concrete slab elastic deflection
    coefficients (alpha).

    This table provides the dimensionless coefficient 'alpha' used to calculate
    the elastic deflection (f) of a solid rectangular reinforced concrete slab:

        f = (p * lx^4) / (E_cs * h^3) * (alpha / 100)

    Where:
    - p: design uniform load
    - lx: shortest span of the slab
    - E_cs: concrete secant modulus of elasticity
    - h: slab thickness/height
    - alpha: coefficient based on aspect ratio lambda (ly / lx) and support Case (1 to 9).

    Attributes:
        title: Table title.
        reference: Bibliographic reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        cases_description: Mapping of case numbers (1-9) to descriptions of boundary conditions.
        entries: Deflection coefficient entries by aspect ratio.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    cases_description: dict[int, str]
    entries: tuple[SlabDeflectionEntry, ...]

    def get_alpha(self, lambda_val: float, case: int) -> float:
        """Look up or interpolate the deflection coefficient (alpha) from the table.

        Args:
            lambda_val: Aspect ratio of the slab (ly / lx), must be >= 1.0.
            case: Boundary condition support configuration case (1–9).

        Returns:
            Dimensionless deflection coefficient alpha.

        Raises:
            EnginePreconditionError: If case is not in [1, 9] or lambda_val < 1.0.
        """
        self._validate_inputs(lambda_val, case)

        # Exact match check (or close to exact match due to floating-point precision)
        for entry in self.entries:
            if math.isclose(lambda_val, entry.aspect_ratio, rel_tol=1e-9):
                result = entry.get_alpha(case)
                log_property(f"α(λ={lambda_val:.4f}, case={case}) = {result:.6f}")
                return result

        # No exact match — interpolate within [1.0, 2.0) or use infinity entry
        if lambda_val < 2.0:
            result = self._interpolate_linear(lambda_val, case)
        else:
            # lambda_val >= 2.0 (or >= 100): behaves as a beam, use the infinity entry.
            result = next(
                e for e in self.entries if math.isinf(e.aspect_ratio)
            ).get_alpha(case)

        log_property(f"α(λ={lambda_val:.4f}, case={case}) = {result:.6f}")
        return result

    def _validate_inputs(self, lambda_val: float, case: int) -> None:
        """Helper to validate constraints on input parameters."""
        if case not in range(1, 10):
            raise EnginePreconditionError(
                f"Invalid case: {case}. Must be an integer between 1 and 9."
            )
        if lambda_val < 1.0:
            raise EnginePreconditionError(
                f"Invalid aspect ratio (lambda) = {lambda_val:.3f}. "
                "Aspect ratio (ly/lx) must be >= 1.0. Verify your span assignments (ly >= lx)."
            )

    def _interpolate_linear(self, lambda_val: float, case: int) -> float:
        """Performs standard linear interpolation between adjacent keys below 2.0."""
        discrete_entries = [e for e in self.entries if not math.isinf(e.aspect_ratio)]
        entry_lower, entry_upper, t = find_bracket_and_fraction(
            discrete_entries, lambda_val
        )
        alpha_lower = entry_lower.get_alpha(case)
        alpha_upper = entry_upper.get_alpha(case)
        return alpha_lower + t * (alpha_upper - alpha_lower)

    @staticmethod
    def determine_supporting_case(
        support_conditions: dict[Edges, SupportCondition],
        lx: float,
        ly: float,
    ) -> int:
        """Determine the Quadro 7.2 boundary condition case (1-9) from edge support conditions.

        Args:
            support_conditions: Mapping of each edge to its support condition
                ("pinned" or "fixed").
            lx: Span length in the x-direction (cm).
            ly: Span length in the y-direction (cm).

        Returns:
            Case number (1 - 9).
        """
        fixed_edges = {
            edge for edge, cond in support_conditions.items() if cond == "fixed"
        }
        num_fixed = len(fixed_edges)

        # Classify edges as long or short based on slab dimensions.
        # TOP/BOTTOM have physical length ~ lx; LEFT/RIGHT have physical length ~ ly.
        if ly >= lx:
            long_edges = {Edges.LEFT, Edges.RIGHT}
            short_edges = {Edges.TOP, Edges.BOTTOM}
        else:
            long_edges = {Edges.TOP, Edges.BOTTOM}
            short_edges = {Edges.LEFT, Edges.RIGHT}

        # Case 1: all four borders simply supported
        if num_fixed == 0:
            return 1

        # Cases 2–3: exactly one border fixed
        if num_fixed == 1:
            (fixed_edge,) = fixed_edges
            if fixed_edge in short_edges:
                return 2  # one short border fixed
            return 3  # one long border fixed

        # Cases 4–6: exactly two borders fixed
        if num_fixed == 2:
            if fixed_edges == short_edges:
                return 5  # two opposite short borders fixed
            if fixed_edges == long_edges:
                return 6  # two opposite long borders fixed
            return 4  # two adjacent fixed borders (one long + one short)

        # Cases 7–8: exactly three borders fixed (one pinned)
        if num_fixed == 3:
            pinned_edges = {
                edge
                for edge, support_condition in support_conditions.items()
                if support_condition == "pinned"
            }
            (pinned_edge,) = pinned_edges
            if pinned_edge in long_edges:
                return 7  # single pinned border is a long border
            return 8  # single pinned border is a short border

        # Case 9: all four borders fixed
        if num_fixed == 4:
            return 9

        raise EnginePreconditionError(
            f"Could not determine Table 7.2 case from support conditions: {support_conditions}"
        )
