
from dataclasses import dataclass, field

from src.loading.forces import almost_permanent_combination_els, calculate_cracking_moment
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import SectionPropertiesCalculator as section


@dataclass
class DeformationChecker:
    """
    Excessive deformation verification for linear elements, according to ELS (Service Limit State) criteria, based on ABNT NBR 8681 - Section 7.3.2.

    For slabs (superficial elements), ABNT NBR 6118 - Section 19.3.1, redirects to the linear elements verification
    """
    permanent_load: float  # kN/m
    variable_load: float   # kN/m
    usage: str
    concrete: Concrete
    span: float            # cm
    width: int           # cm
    height: int = field(default=0, init=False)  # cm

    def verify(self, height: int) -> bool:
        """
        Verifies if the deformation of the element is within acceptable limits.

        :return: True if the deformation is acceptable, False otherwise
        :rtype: bool
        """
        # TODO complete implementation and update docstring
        self.height = height
        return self.long_term_deflection <= self.acceptable_deflection 

    @property
    def design_load(self) -> float:
        """
        Calculates the design load for the element, based on the almost permanent combination of loads, according to ABNT NBR 6118 - Section 11.8.3.1 - item a. 
        """
        return almost_permanent_combination_els(self.permanent_load, self.variable_load, self.usage)

    @property
    def cracking_moment(self) -> float:
        """
        Calculates the cracking moment for the element (kN.cm), according to ABNT NBR 6118 - Section 17.3.1.
        """
        tensile_strength = self.concrete.fct_m  # kN/cm²
        moment_of_inertia = section.moment_of_inertia(self.width, self.height)
        distance_to_tension_fiber = 1  # FIXME Placeholder value, should be calculated based on the element's cross-section
        return calculate_cracking_moment(tensile_strength, distance_to_tension_fiber, moment_of_inertia)

    @property
    def service_moment(self) -> float:
        # IMPLEMENT and generate docstring
        return 1  # FIXME Placeholder value, should be calculated based on the element's loading and geometry

    @property
    def is_cracked(self) -> bool:
        """
        Determines if the element is cracked based on the comparison of the service moment and the cracking moment.

        :return: True if the element is cracked, False otherwise
        :rtype: bool
        """
        return self.service_moment > self.cracking_moment

    @property
    def moment_of_inertia(self) -> float:
        """
        Get the equivalent or gross moment of inertia of the cross-section.

        This property calculates the equivalent moment of inertia using Branson's formula to model the transition behavior between Stage I (not cracked) and Stage II (fully cracked) under service loads.

        According to ABNT NBR 6118 - Section: 17.3.2.1.1

        Returns:
            float: The effective equivalent moment of inertia, capped at the gross section moment of inertia (Ic).
        """
        gross_section_moment_of_inertia = section.moment_of_inertia(self.width, self.height)
        if self.is_cracked:
            return gross_section_moment_of_inertia

        cracked_section_moment_of_inertia = section.cracked_section_moment_of_inertia(self.width, self.height)
        moments_ratio = self.cracking_moment / self.service_moment
        equivalent_moment_of_inertia = (moments_ratio**3 * gross_section_moment_of_inertia) + ((1 - moments_ratio**3) * cracked_section_moment_of_inertia)
        return min(equivalent_moment_of_inertia, gross_section_moment_of_inertia)

    @property
    def immediate_deflection(self) -> float:
        # IMPLEMENT and generate docstring
        return 1  # FIXME Placeholder value, should be calculated based on the element's loading

    @property
    def long_term_deflection(self) -> float:
        # IMPLEMENT and generate docstring
        return 1  # FIXME Placeholder value, should be calculated based on the element's loading

    # PAPER get reference on WHY this is the chosen criteria for deflection verification
    # CONFIRM if this is the only criteria I will use
    @property
    def acceptable_deflection(self) -> float:
        """
        Calculate the maximum allowable displacement for visual sensory acceptability.

        According to ABNT NBR 6118:
        - Section: 13.3 (Displacement limits)
        - Table: 13.3 (Limits for displacements)
        - Row: "Sensory acceptability" -> "Visual" (Limit: l/250)

        Returns:
            float: The maximum allowable deflection in the same unit as the span (cm).
        """
        return self.span / 250.0