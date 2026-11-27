from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

from src.config import APP_CONFIG
from src.errors import PillarTooSmallError
from src.logger import log_operation
from src.pavement_elements.geometry_utils import Axis
from src.properties.section_properties_calculator import SectionPropertiesCalculator

MIN_DIMENSION_CM = 14.0  # cm — ABNT NBR 6118 §13.2.3
MIN_AREA_CM2 = 360.0  # cm² — ABNT NBR 6118 §13.2.3

# PAPER get reference for this (https://wwwp.feb.unesp.br/pbastos/concreto2/Vigas.pdf)
HALF_PILLAR_COEFFICIENT = 3  # 3EI/L — half-pillar with its far end pinned at mid-height
# ABNT NBR 6118:2026 §14.6.6.1-b — interior support rigid when b_int > e/4
RIGID_SUPPORT_HEIGHT_DIVISOR = 4


@dataclass
class Pillar:
    """
    Represents a structural pillar, acting as a node in the pavement grid.

    Attributes:
        id: Unique identifier (e.g. "P1"); generated from a counter when not given
        x: Physical x-coordinate (cm)
        y: Physical y-coordinate (cm)
        width: Cross-section width (cm)
        depth: Cross-section depth (cm)
        pinned: Whether the beams rest on it without rotational restraint (simple support)
    """

    x: float
    y: float
    width: float
    depth: float
    id: str = field(default="", kw_only=True)  # empty: generated from the counter
    pinned: bool = field(default=False, kw_only=True)

    _counter = count(1)  # Class-level counter for auto-generating IDs

    @classmethod
    def reset_id_counter(cls) -> None:
        """Restart auto-generated ids at 1 (P1)"""
        cls._counter = count(1)

    def __post_init__(self):
        if not self.id:
            self.id = f"P{next(self._counter)}"
        self._validate_dimensions()

    def get_x_range(self) -> tuple[float, float]:
        """Returns the x-coordinate range of the pillar based on its width."""
        half = self.width / 2
        return (self.x - half, self.x + half)

    def get_y_range(self) -> tuple[float, float]:
        """Returns the y-coordinate range of the pillar based on its depth."""
        half = self.depth / 2
        return (self.y - half, self.y + half)

    def get_parallel_extent(self, axis: Axis) -> float:
        """Return the cross-section extent (cm) along a beam axis.

        For an X-beam this is the width (x extent); for a Y-beam, the depth (y extent).
        """
        return self.width if axis == Axis.X else self.depth

    def get_perpendicular_extent(self, axis: Axis) -> float:
        """Return the cross-section extent (cm) perpendicular to a beam axis.

        For an X-beam this is the depth (y extent); for a Y-beam, the width (x extent).
        """
        return self.depth if axis == Axis.X else self.width

    def calculate_stiffness_for_beam_supporting(self, axis: Axis) -> float:
        """Return the rotational stiffness this pillar gives a beam along an axis.

        Args:
            axis: Axis of the beam the pillar supports.

        Returns:
            Rotational stiffness (kN.m/rad).
        """
        # PAPER — reference for the half-pillar rotational stiffness 3·E·I/(l/2)
        inertia = SectionPropertiesCalculator.moment_of_inertia(
            self.get_perpendicular_extent(axis), self.get_parallel_extent(axis)
        )  # cm⁴
        half_height = APP_CONFIG.ceiling_height / 2  # m
        half_stiffness = (
            HALF_PILLAR_COEFFICIENT
            * APP_CONFIG.pavement_concrete.ecs
            * 1e3
            * inertia
            * 1e-8
            / half_height
        )  # MPa→kN/m², cm⁴→m⁴ ⇒ kN·m/rad
        stiffness = 2 * half_stiffness
        log_operation(
            f"Pillar {self.id} rotational stiffness for {axis.value} beam: "
            f"Ic = {inertia:.0f} cm⁴, k = {stiffness:.1f} kN.m/rad"
        )
        return stiffness

    def is_rigid_inner_support(self, axis: Axis) -> bool:
        """Return whether this pillar, as an interior support, fixes the beam rigidly.

        The support is rigid when its width along the beam, b_int, exceeds a quarter of the pillar's equivalent height e. Then the hogging moment cannot be smaller than the fixed-end moment. e is the distance between the mid-heights of the beams at the top and at the base of the lance; with equal beams on every floor it equals the ceiling height.

        Args:
            axis: Axis of the beam the pillar supports.

        References:
            ABNT NBR 6118:2026 — Section 14.6.6.1-b
        """
        width = self.get_parallel_extent(axis)  # cm, b_int
        limit = APP_CONFIG.ceiling_height * 100 / RIGID_SUPPORT_HEIGHT_DIVISOR  # cm
        is_rigid = width > limit
        log_operation(
            f"Pillar {self.id} as an interior support of a {axis.value} beam: "
            f"b_int = {width:.1f} cm, e/4 = {limit:.1f} cm → "
            f"{'rigid' if is_rigid else 'elastic'}"
        )
        return is_rigid

    def _validate_dimensions(self) -> None:
        """Enforce ABNT NBR 6118 minimum pillar cross-section requirements.

        Raises:
            PillarTooSmallError: If either dimension is below 14 cm, or if the
                gross cross-sectional area is below 360 cm².

        References:
            ABNT NBR 6118:2014 — Section 13.2.3
        """
        if self.width < MIN_DIMENSION_CM or self.depth < MIN_DIMENSION_CM:
            raise PillarTooSmallError(
                f"Pillar dimensions must be at least {MIN_DIMENSION_CM} cm. "
                f"Got {self.width}×{self.depth} cm.",
                pillar_id=self.id,
                width=self.width,
                depth=self.depth,
            )
        if self.width * self.depth < MIN_AREA_CM2:
            raise PillarTooSmallError(
                f"Pillar gross area must be at least {MIN_AREA_CM2} cm². "
                f"Got {self.width * self.depth:.1f} cm².",
                pillar_id=self.id,
                width=self.width,
                depth=self.depth,
            )
