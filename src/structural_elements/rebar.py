from dataclasses import dataclass, field

from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel


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
    def start_position(self) -> float:
        """Calculates the start position of the rebar based on its center and necessary left length."""
        return self.center - self.left_length

    @property
    def end_position(self) -> float:
        """Calculates the end position of the rebar based on its center and necessary right length."""
        return self.center + self.right_length
