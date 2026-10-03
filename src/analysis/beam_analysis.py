from typing import Protocol


class BeamAnalysis(Protocol):
    """Results of a solved beam, independent of the structural solver.

    Positions are measured from the beam start (cm). Bending moments follow the
    sagging-positive convention.
    """

    @property
    def length(self) -> float:
        """Total beam length (cm)."""
        ...

    def bending_moment(self, position: float) -> float:
        """Return the bending moment at a position (kN.m)."""
        ...

    def shear_force(self, position: float) -> float:
        """Return the shear force at a position (kN)."""
        ...

    def deflection(self, position: float) -> float:
        """Return the deflection at a position (cm, downward negative)."""
        ...

    # TODO I will need it by span
    def max_shear_force(self) -> float:
        """Return the largest signed shear force along the beam (kN)."""
        ...

    def reaction(self, position: float) -> float:
        """Return the vertical support reaction at a support position (kN)."""
        ...

    def moment_zeros(self) -> list[float]:
        """Return the sorted positions where the bending moment is zero (cm)."""
        ...

    def moment_extremes_per_segment(self) -> list[tuple[float, float]]:
        """Return the dominant bending-moment extreme in each segment between zeros.

        Returns:
            One `(position, moment)` per segment, sorted left to right (position in cm, moment in kN.m).
        """
        ...

    def positions_for_moment(self, target_moment: float) -> list[float]:
        """Return the sorted positions where the bending moment equals a target.

        Args:
            target_moment: Bending moment to locate (kN.m).

        Returns:
            Positions along the beam (cm); empty if the target is never reached.
        """
        ...
