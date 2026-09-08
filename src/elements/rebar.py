from dataclasses import dataclass

from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel


@dataclass(frozen=True)
class Rebar:
    """Represents a steel reinforcement bar."""
    diameter_mm: float
    steel: Steel

    def __post_init__(self):
        if not self.steel.is_size_available(self.diameter_mm):
            raise ValueError(f"Diameter {self.diameter_mm} mm is not available for the specified steel type.")

    def effective_covering(self, nominal_covering: float) -> float:
        """Minimum cover this bar requires per NBR 6118 §7.4.7.5: max(nominal, diameter)."""
        return max(self.diameter_mm / 10, nominal_covering)

    @property
    def area_cm2(self) -> float:
        """Calculates the cross-sectional area of the rebar in cm²."""
        diameter_cm = self.diameter_mm / 10.0
        return section.circular_cross_sectional_area(diameter_cm)