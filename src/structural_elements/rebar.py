from dataclasses import dataclass, field
from math import pi

from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel

HOOK_STRAIGHT_LENGTH_RATIO = 8  # NBR 6118 - Section 9.4.2.3-c (90° hook)


@dataclass(unsafe_hash=True)
class Rebar:
    """Represents a steel reinforcement bar."""

    diameter_mm: float
    steel: Steel
    center: float = field(
        default=0.0, init=False, compare=False
    )  # Center position of the rebar along the beam's length
    left_length: float = field(default=0.0, init=False, compare=False)
    right_length: float = field(default=0.0, init=False, compare=False)
    left_hook_enabled: bool = field(default=False, init=False, compare=False)
    right_hook_enabled: bool = field(default=False, init=False, compare=False)

    def __post_init__(self):
        if not self.steel.is_size_available(self.diameter_mm):
            raise ValueError(
                f"Diameter {self.diameter_mm} mm is not available for the specified steel type."
            )

    def effective_covering(self, nominal_covering: float) -> float:
        """Minimum cover this bar requires per NBR 6118 §7.4.7.5: max(nominal, diameter)."""
        return max(self.diameter_mm / 10, nominal_covering)

    @property
    def area_cm2(self) -> float:
        """Calculates the cross-sectional area of the rebar in cm²."""
        diameter_cm = self.diameter_mm / 10.0
        return section.circular_cross_sectional_area(diameter_cm)

    @property
    def hook_length(self) -> float:
        """Return the extra cut length of one 90° hook (cm)

        The straight length already reaches the outer face of the hook's leg, so the hook adds the quarter arc and the 8φ tip, minus the D/2 + φ the straight length covers past the curve start: π(D + φ)/4 + 8φ - (D/2 + φ).

        Raises:
            ValueError: Propagated from the bending pin if the norm gives none for the bar.

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.3
        """
        diameter_cm = self.diameter_mm / 10  # cm
        pin_diameter = self.steel.bend_pin_diameter(self.diameter_mm)  # cm
        arc = pi * (pin_diameter + diameter_cm) / 4  # cm
        straight_tip = HOOK_STRAIGHT_LENGTH_RATIO * diameter_cm  # cm
        overlap = pin_diameter / 2 + diameter_cm  # cm
        return arc + straight_tip - overlap

    @property
    def hook_height(self) -> float:
        """Return the height of one 90° hook, from the bar's axis to the tip of its leg (cm)

        D/2 + φ/2 + 8φ.

        Raises:
            ValueError: Propagated from the bending pin if the norm gives none for the bar.

        References:
            ABNT NBR 6118:2026 — Section 9.4.2.3
        """
        diameter_cm = self.diameter_mm / 10  # cm
        pin_diameter = self.steel.bend_pin_diameter(self.diameter_mm)  # cm
        return (
            pin_diameter / 2
            + diameter_cm / 2
            + HOOK_STRAIGHT_LENGTH_RATIO * diameter_cm
        )

    @property
    def left_hook_length(self) -> float:
        """Return the left hook length (cm), zero when the hook is disabled"""
        return self.hook_length if self.left_hook_enabled else 0.0

    @property
    def right_hook_length(self) -> float:
        """Return the right hook length (cm), zero when the hook is disabled"""
        return self.hook_length if self.right_hook_enabled else 0.0

    @property
    def total_length(self) -> float:
        """Return the bar's cut length (cm): straight lengths plus enabled hooks"""
        return (
            self.left_length
            + self.right_length
            + self.left_hook_length
            + self.right_hook_length
        )

    @property
    def start_position(self) -> float:
        """Calculates the start position of the rebar based on its center and necessary left length."""
        return self.center - self.left_length

    @property
    def end_position(self) -> float:
        """Calculates the end position of the rebar based on its center and necessary right length."""
        return self.center + self.right_length
