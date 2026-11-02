import itertools
import math
from dataclasses import dataclass
from typing import cast

import numpy as np
from anastruct.fem.system import SystemElements

from src.analysis.model import BeamSupport, DistributedLoad
from src.config import APP_CONFIG
from src.logger import log_property
from src.properties.section_properties_calculator import SectionPropertiesCalculator
from src.structural_elements.rectangular_beam import RectangularBeam

_CM_PER_M = 100.0
_POSITION_TOLERANCE = 1e-4  # cm — positions closer than this are the same point
_ROOT_TOLERANCE = 1e-9  # m — roots this far outside an element snap to its end


@dataclass(frozen=True)
class _Element:
    """One solved element with a uniform load, in project signs.

    The bending moment over the element is the exact parabola
    M(u) = a·u² + b·u + c, with u the local position (m).

    Attributes:
        start: Global start position (cm).
        end: Global end position (cm).
        moment_start: Bending moment at the start (kN.m, sagging positive).
        moment_end: Bending moment at the end (kN.m, sagging positive).
        load: Uniform load intensity (kN/m, positive downward).
        deflection_start: Deflection at the start (m, upward positive).
        deflection_end: Deflection at the end (m, upward positive).
        slope_start: Rotation at the start (rad, counter-clockwise positive).
        slope_end: Rotation at the end (rad, counter-clockwise positive).
    """

    start: float
    end: float
    moment_start: float
    moment_end: float
    load: float
    deflection_start: float
    deflection_end: float
    slope_start: float
    slope_end: float

    @property
    def length(self) -> float:
        """Element length (m)."""
        return (self.end - self.start) / _CM_PER_M

    @property
    def coefficients(self) -> tuple[float, float, float]:
        """Return (a, b, c) of M(u) = a·u² + b·u + c (kN.m; u in m)."""
        length = self.length
        a = -self.load / 2
        b = (self.moment_end - self.moment_start) / length + self.load * length / 2
        return a, b, self.moment_start

    def local(self, position: float) -> float:
        """Convert a global position (cm) to the local coordinate u (m)."""
        return (position - self.start) / _CM_PER_M

    def moment(self, position: float) -> float:
        """Return the bending moment at a global position (kN.m)."""
        a, b, c = self.coefficients
        u = self.local(position)
        return a * u**2 + b * u + c

    def shear(self, position: float) -> float:
        """Return the shear force dM/dx at a global position (kN)."""
        a, b, _ = self.coefficients
        return 2 * a * self.local(position) + b

    def deflection(self, position: float, bending_stiffness: float) -> float:
        """Return the exact Euler-Bernoulli deflection at a global position (m, upward positive).

        Combines the cubic Hermite interpolation of the end displacements and rotations with the fixed-end particular solution of the uniform load.

        Args:
            bending_stiffness: EI of the beam (kN.m²).
        """
        length = self.length
        u = self.local(position)
        xi = u / length
        h1 = 1 - 3 * xi**2 + 2 * xi**3
        h2 = length * (xi - 2 * xi**2 + xi**3)
        h3 = 3 * xi**2 - 2 * xi**3
        h4 = length * (-(xi**2) + xi**3)
        homogeneous = (
            self.deflection_start * h1
            + self.slope_start * h2
            + self.deflection_end * h3
            + self.slope_end * h4
        )
        particular = self.load * u**2 * (length - u) ** 2 / (24 * bending_stiffness)
        return homogeneous - particular

    def positions_for(self, target_moment: float) -> list[float]:
        """Return the global positions (cm) in this element where M equals a target (kN.m)."""
        a, b, c = self.coefficients
        if a == 0 and b == 0:
            return []  # constant moment: either never or everywhere equal
        length = self.length
        positions: list[float] = []
        for root in cast(list[complex], np.roots([a, b, c - target_moment]).tolist()):
            if abs(root.imag) > _ROOT_TOLERANCE:
                continue
            u = root.real
            if -_ROOT_TOLERANCE <= u <= length + _ROOT_TOLERANCE:
                u = min(max(u, 0.0), length)
                positions.append(self.start + u * _CM_PER_M)
        return positions

    def positions_for_shear(self, target_shear: float) -> list[float]:
        """Return the global positions (cm) in this element where V equals a target (kN)."""
        a, b, _ = self.coefficients
        if a == 0:
            return []  # constant shear: either never or everywhere equal
        u = (target_shear - b) / (2 * a)
        if not -_ROOT_TOLERANCE <= u <= self.length + _ROOT_TOLERANCE:
            return []
        u = min(max(u, 0.0), self.length)
        return [self.start + u * _CM_PER_M]

    def vertex(self) -> float | None:
        """Return the global position (cm) of the parabola's vertex strictly inside the element."""
        a, b, _ = self.coefficients
        if a == 0:
            return None
        u = -b / (2 * a)
        return self.start + u * _CM_PER_M if 0 < u < self.length else None


class AnaStructBeamAnalysis:
    """Solves a beam with anaStruct and exposes it as a BeamAnalysis.

    The beam is split into one element per interval between consecutive supports and load boundaries, so every element carries a single uniform load and its bending moment is an exact parabola. All queries are evaluated from those exact per-element expressions, not from anaStruct's sampled result arrays.

    This is the only module allowed to depend on anaStruct.
    """

    def __init__(
        self,
        section: RectangularBeam,
        supports: list[BeamSupport],
        loads: list[DistributedLoad],
    ) -> None:
        """Build and solve the beam.

        Raises:
            ValueError: If a support or load lies outside the beam, or a support has a negative rotational stiffness.
        """
        self._section = section
        self._validate(supports, loads)

        width, height = section.width, section.height
        inertia = SectionPropertiesCalculator.moment_of_inertia(width, height)  # cm⁴
        area = SectionPropertiesCalculator.rectangular_cross_sectional_area(
            width, height
        )  # cm²
        ecs = APP_CONFIG.pavement_concrete.ecs  # MPa
        self._flexural_rigidity = ecs * inertia * 1e-5  # MPa·cm⁴ → kN·m²
        axial_rigidity = ecs * area * 0.1  # MPa·cm² → kN

        node_positions = self._node_positions(supports, loads)
        system = SystemElements(EI=self._flexural_rigidity, EA=axial_rigidity)
        for start, end in itertools.pairwise(node_positions):
            system.add_element([[start / _CM_PER_M, 0.0], [end / _CM_PER_M, 0.0]])

        self._support_nodes: dict[float, int] = {}
        for support in supports:
            node_id = self._node_id(node_positions, support.position)
            self._add_support(system, node_id, support.rotational_stiffness)
            self._support_nodes[support.position] = node_id

        element_loads = [
            sum(
                load.intensity
                for load in loads
                if load.start <= start + _POSITION_TOLERANCE
                and end <= load.end + _POSITION_TOLERANCE
            )
            for start, end in itertools.pairwise(node_positions)
        ]
        for element_id, intensity in enumerate(element_loads, start=1):
            if intensity != 0:
                system.q_load(q=-intensity, element_id=element_id)

        system.solve()
        self._system = system
        self._elements = self._read_elements(node_positions, element_loads)

    @property
    def length(self) -> float:
        """Total beam length (cm)."""
        return self._section.length

    def bending_moment(self, position: float) -> float:
        """Return the bending moment at a position (kN.m, sagging positive)."""
        return self._element_at(position).moment(position)

    def shear_force(self, position: float) -> float:
        """Return the shear force at a position (kN)."""
        return self._element_at(position).shear(position)

    def deflection(self, position: float) -> float:
        """Return the deflection at a position (cm, downward negative)."""
        element = self._element_at(position)
        return element.deflection(position, self._flexural_rigidity) * _CM_PER_M

    def max_abs_shear(self) -> float:
        """Return the largest absolute shear force along the beam (kN)."""
        return max(
            max(abs(element.shear(element.start)), abs(element.shear(element.end)))
            for element in self._elements
        )

    def reaction(self, position: float) -> float:
        """Return the vertical support reaction at a support position (kN, upward positive).

        Raises:
            ValueError: If there is no support at the position.
        """
        for support_position, node_id in self._support_nodes.items():
            if abs(support_position - position) <= _POSITION_TOLERANCE:
                node = self._system.get_node_results_system(node_id)
                return -float(cast(float, node["Fy"]))
        raise ValueError(f"No support at {position} cm.")

    def moment_zeros(self) -> list[float]:
        """Return the sorted positions where the bending moment is zero (cm)."""
        zeros = self.positions_for_moment(0.0)
        log_property(
            f"Points where bending moment is zero:  {zeros}", self._section.label
        )
        return zeros

    def moment_extremes_per_segment(self) -> list[tuple[float, float]]:
        """Return the dominant bending-moment extreme in each segment between zeros.

        Returns:
            One `(position, moment)` per segment, sorted left to right (position
            in cm, moment in kN.m).
        """
        boundaries = _deduplicate(sorted({0.0, self.length, *self.moment_zeros()}))
        return [
            self.moment_extreme_in_range(segment_start, segment_end)
            for segment_start, segment_end in itertools.pairwise(boundaries)
        ]

    def moment_extreme_in_range(self, start: float, end: float) -> tuple[float, float]:
        """Return the bending moment with the greatest absolute value within a range.

        Each element's moment is a parabola, so the dominant value lies at a range end, an element start, or a parabola vertex.

        Args:
            start: Left end of the range (cm).
            end: Right end of the range (cm); must be >= start.

        Returns:
            `(position, moment)` of the dominant moment (position in cm, moment in kN.m).
        """
        candidates = {element.start for element in self._elements} | {
            vertex
            for element in self._elements
            if (vertex := element.vertex()) is not None
        }
        positions = [start, end] + sorted(c for c in candidates if start < c < end)
        dominant = max(positions, key=lambda x: abs(self.bending_moment(x)))
        return dominant, self.bending_moment(dominant)

    def positions_for_moment(self, target_moment: float) -> list[float]:
        """Return the sorted positions where the bending moment equals a target.

        Args:
            target_moment: Bending moment to locate (kN.m).

        Returns:
            Positions along the beam (cm); empty if the target is never reached.
        """
        positions = sorted(
            position
            for element in self._elements
            for position in element.positions_for(target_moment)
        )
        return _deduplicate(positions)

    def positions_for_shear(self, target_shear: float) -> list[float]:
        """Return the sorted positions where the shear force equals a target.

        Args:
            target_shear: Shear force to locate (kN).

        Returns:
            Positions along the beam (cm); empty if the target is never reached.
            A target skipped by the jump over a support is not reached.
        """
        positions = sorted(
            position
            for element in self._elements
            for position in element.positions_for_shear(target_shear)
        )
        return _deduplicate(positions)

    def _validate(
        self, supports: list[BeamSupport], loads: list[DistributedLoad]
    ) -> None:
        """Reject supports and loads the model cannot represent.

        Raises:
            ValueError: If a support or load lies outside the beam, or a support
                has a negative rotational stiffness.
        """
        length = self._section.length
        for support in supports:
            if not 0 <= support.position <= length:
                raise ValueError(
                    f"Support at {support.position} cm lies outside the beam (0–{length} cm)."
                )
            if support.rotational_stiffness < 0:
                raise ValueError(
                    "Rotational stiffness must be non-negative; got "
                    f"{support.rotational_stiffness} kN.m/rad at {support.position} cm."
                )
        for load in loads:
            if not 0 <= load.start < load.end <= length:
                raise ValueError(
                    f"Load from {load.start} to {load.end} cm lies outside the beam "
                    f"(0–{length} cm) or has no extent."
                )

    def _node_positions(
        self, supports: list[BeamSupport], loads: list[DistributedLoad]
    ) -> list[float]:
        """Return the sorted node positions: beam ends, supports and load boundaries (cm)."""
        raw = {0.0, self._section.length}
        raw |= {support.position for support in supports}
        raw |= {load.start for load in loads} | {load.end for load in loads}
        return _deduplicate(sorted(raw))

    @staticmethod
    def _node_id(node_positions: list[float], position: float) -> int:
        """Return the anaStruct node id (1-based) at a position (cm)."""
        for index, node_position in enumerate(node_positions):
            if abs(node_position - position) <= _POSITION_TOLERANCE:
                return index + 1
        raise ValueError(f"No node at {position} cm.")

    @staticmethod
    def _add_support(
        system: SystemElements, node_id: int, rotational_stiffness: float
    ) -> None:
        """Add a pinned, fixed or elastic-fixed support at a node."""
        if math.isinf(rotational_stiffness):
            system.add_support_fixed(node_id)
            return
        # The hinge is always added explicitly: a rotational spring alone also
        # restrains translation in anaStruct 1.7.0, which is undocumented.
        system.add_support_hinged(node_id)
        if rotational_stiffness > 0:
            system.add_support_spring(node_id, translation=3, k=rotational_stiffness)

    def _read_elements(
        self, node_positions: list[float], element_loads: list[float]
    ) -> list[_Element]:
        """Read the solved end moments and displacements of every element, in project signs."""
        elements: list[_Element] = []
        for index, (start, end) in enumerate(itertools.pairwise(node_positions)):
            results = self._system.get_element_results(index + 1, verbose=True)
            moments = cast(list[float], list(results["M"]))
            start_node = self._system.get_node_results_system(index + 1)
            end_node = self._system.get_node_results_system(index + 2)
            elements.append(
                _Element(
                    start=start,
                    end=end,
                    moment_start=-float(moments[0]),
                    moment_end=-float(moments[-1]),
                    load=element_loads[index],
                    deflection_start=-float(cast(float, start_node["uy"])),
                    deflection_end=-float(cast(float, end_node["uy"])),
                    slope_start=-float(cast(float, start_node["phi_z"])),
                    slope_end=-float(cast(float, end_node["phi_z"])),
                )
            )
        return elements

    def _element_at(self, position: float) -> _Element:
        """Return the element containing a global position (cm).

        Raises:
            ValueError: If the position lies outside the beam.
        """
        for element in self._elements:
            if (
                element.start - _POSITION_TOLERANCE
                <= position
                <= element.end + _POSITION_TOLERANCE
            ):
                return element
        raise ValueError(f"Position {position} cm lies outside the beam.")


def _deduplicate(sorted_positions: list[float]) -> list[float]:
    """Drop positions closer than the tolerance to the previous one (cm)."""
    unique: list[float] = []
    for position in sorted_positions:
        if not unique or position - unique[-1] > _POSITION_TOLERANCE:
            unique.append(position)
    return unique
