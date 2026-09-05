"""Dataclass models for Carvalho & Figueiredo Filho (2014) - Chapter 7 - Table 7 (Quadro 7.1)."""

import math
from dataclasses import dataclass

from src.pavement.slab_edge import Edges, SupportCondition


@dataclass(frozen=True)
class MomentCoefficients:
    """Pair of bending moment coefficients (mu_x, mu_y) for a given case."""

    mu_x: float
    mu_y: float


@dataclass(frozen=True)
class SlabMomentEntry:
    """Bending moment coefficient row for a given aspect ratio (ly / lx).

    Each entry stores the aspect ratio and a tuple of 9 MomentCoefficients,
    one per support-configuration case (1 to 9).
    """

    aspect_ratio: float
    cases: tuple[MomentCoefficients, ...]

    def get_mu(self, case: int) -> MomentCoefficients:
        """Return the moment coefficients (mu_x, mu_y) for the specified case (1 to 9)."""
        if case not in range(1, 10):
            raise ValueError(
                f"Invalid case: {case}. Must be an integer between 1 and 9."
            )
        return self.cases[case - 1]

    def get_mu_x(self, case: int) -> float:
        """Return the mu_x coefficient for the specified case (1 to 9)."""
        return self.get_mu(case).mu_x

    def get_mu_y(self, case: int) -> float:
        """Return the mu_y coefficient for the specified case (1 to 9)."""
        return self.get_mu(case).mu_y


@dataclass(frozen=True)
class Table7:
    """Roberto Chust de Carvalho & Jasson Rodrigues de Figueiredo Filho - Chapter 7 - Quadro 7.1.

    Manages the data lookup and interpolation for concrete slab bending moment
    coefficients (mu_x and mu_y).

    This table provides the dimensionless coefficients 'mu_x' and 'mu_y' used to
    calculate the bending moments (Mx and My) of a solid rectangular reinforced
    concrete slab:

        Mx = (mu_x / 100) * p * lx²
        My = (mu_y / 100) * p * lx²

    Where:
    - p: design uniform load
    - lx: shortest span of the slab
    - mu_x, mu_y: coefficients based on aspect ratio lambda (ly / lx) and support case (1 to 9).

    Attributes:
        title: Table title.
        reference: Bibliographic reference.
        description: Human-readable description of the table contents.
        units: Mapping of physical quantity to unit string.
        cases_description: Mapping of case numbers (1-9) to descriptions of boundary conditions.
        entries: Bending moment coefficient entries by aspect ratio.
    """

    title: str
    reference: str
    description: str
    units: dict[str, str]
    cases_description: dict[int, str]
    entries: tuple[SlabMomentEntry, ...]

    def get_mu(self, lambda_val: float, case: int) -> MomentCoefficients:
        """
        Looks up or interpolates the bending moment coefficients (mu_x, mu_y) from the table.

        Parameters:
            lambda_val: Aspect ratio of the slab (ly / lx), must be >= 1.0.
            case: Boundary condition support configuration case, must be between 1 and 9.

        Returns:
            A MomentCoefficients with the interpolated mu_x and mu_y values.

        Raises:
            ValueError: If 'case' is not within [1, 9] or if 'lambda_val' is less than 1.0.
        """
        self._validate_inputs(lambda_val, case)

        # Exact match check (or close to exact match due to floating-point precision)
        for entry in self.entries:
            if math.isclose(lambda_val, entry.aspect_ratio, rel_tol=1e-9):
                return entry.get_mu(case)

        # Handle infinity edge case (or very high values of lambda)
        if lambda_val >= 100.0:
            for entry in self.entries:
                if math.isinf(entry.aspect_ratio):
                    return entry.get_mu(case)

        # Case A: lambda_val is within bounds [1.0, 2.0]
        if lambda_val < 2.0:
            return self._interpolate_linear(lambda_val, case)

        # Case B: lambda_val is between 2.0 and infinity.
        return self._interpolate_asymptotic(lambda_val, case)

    def get_mu_x(self, lambda_val: float, case: int) -> float:
        """Convenience: return only mu_x for the given lambda and case."""
        return self.get_mu(lambda_val, case).mu_x

    def get_mu_y(self, lambda_val: float, case: int) -> float:
        """Convenience: return only mu_y for the given lambda and case."""
        return self.get_mu(lambda_val, case).mu_y

    def _validate_inputs(self, lambda_val: float, case: int) -> None:
        """Helper to validate constraints on input parameters."""
        if case not in range(1, 10):
            raise ValueError(
                f"Invalid case: {case}. Must be an integer between 1 and 9."
            )
        if lambda_val < 1.0:
            raise ValueError(
                f"Invalid aspect ratio (lambda) = {lambda_val:.3f}. "
                "Aspect ratio (ly/lx) must be >= 1.0. Verify your span assignments (ly >= lx)."
            )

    def _interpolate_linear(self, lambda_val: float, case: int) -> MomentCoefficients:
        """Performs standard linear interpolation between adjacent keys below 2.0."""
        discrete_entries = [e for e in self.entries if not math.isinf(e.aspect_ratio)]

        idx = 0
        while (
            idx < len(discrete_entries) - 1
            and discrete_entries[idx + 1].aspect_ratio < lambda_val
        ):
            idx += 1

        entry_lower = discrete_entries[idx]
        entry_upper = discrete_entries[idx + 1]

        mu_lower = entry_lower.get_mu(case)
        mu_upper = entry_upper.get_mu(case)

        t = (lambda_val - entry_lower.aspect_ratio) / (
            entry_upper.aspect_ratio - entry_lower.aspect_ratio
        )
        return MomentCoefficients(
            mu_x=mu_lower.mu_x + t * (mu_upper.mu_x - mu_lower.mu_x),
            mu_y=mu_lower.mu_y + t * (mu_upper.mu_y - mu_lower.mu_y),
        )

    # TODO remove this - if it is lambda>2, return the value for infinity (as it would be for a beam)
    def _interpolate_asymptotic(
        self, lambda_val: float, case: int
    ) -> MomentCoefficients:
        """
        Performs linear interpolation on the reciprocal (1 / lambda) between 2.0 and infinity.
        This provides high physical accuracy matching plate theory asymptotic.
        """
        entry_lower = next(
            e for e in self.entries if math.isclose(e.aspect_ratio, 2.0, rel_tol=1e-9)
        )
        entry_inf = next(e for e in self.entries if math.isinf(e.aspect_ratio))

        mu_lower = entry_lower.get_mu(case)
        mu_inf = entry_inf.get_mu(case)

        lambda_lower = 2.0
        val = 1.0 / lambda_val
        lower = 1.0 / lambda_lower  # 0.5
        inf = 0.0  # 1 / inf

        t = (lower - val) / (lower - inf)
        return MomentCoefficients(
            mu_x=mu_lower.mu_x + t * (mu_inf.mu_x - mu_lower.mu_x),
            mu_y=mu_lower.mu_y + t * (mu_inf.mu_y - mu_lower.mu_y),
        )

    @staticmethod
    def determine_supporting_case(
        support_conditions: dict[Edges, SupportCondition],
        lx: float,
        ly: float,
    ) -> int:
        """Determine the Quadro 7.1 boundary condition case (1-9) from edge support conditions.

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

        raise ValueError(
            f"Could not determine Table 7 case from support conditions: {support_conditions}"
        )
