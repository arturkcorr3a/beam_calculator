from dataclasses import dataclass

from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)


@dataclass(frozen=True, kw_only=True)
class Clamps:
    """Store the U-shaped clamps that complete the anchorage at a beam extremity

    Attributes:
        diameter: Clamp bar diameter φ in mm.
        quantity: Number of clamps. Each clamp has two legs crossing the section.
        width: Clamp width in cm, equal to the stirrup width.
        length: Total clamp length l_c in cm.
    """

    diameter: float
    quantity: int
    width: float
    length: float

    @property
    def area(self) -> float:
        """Return the steel area crossing the section, counting both legs of every clamp (cm²)"""
        return (
            2
            * self.quantity
            * section.circular_cross_sectional_area(self.diameter / 10)
        )
