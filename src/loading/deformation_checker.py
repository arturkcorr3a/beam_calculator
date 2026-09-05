from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.loading.forces import (
    almost_permanent_combination_els,
    calculate_cracking_moment,
)
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel


@dataclass(kw_only=True)
class DeformationChecker(ABC):
    """
    Excessive deformation verification for linear elements, according to ELS (Service Limit State) criteria, based on ABNT NBR 8681 - Section 7.3.2.

    For slabs (superficial elements), ABNT NBR 6118 - Section 19.3.1, redirects to the linear elements verification
    """

    permanent_load: float  # kN/m
    variable_load: float  # kN/m
    usage: str
    concrete: Concrete
    span: float  # cm
    width: int  # cm
    effective_depth_discount: float  # cm
    compressed_reinforcement_area: float  # cm²
    effective_depth_compressed: float  # cm²
    _tensioned_reinforcement_area: float  # cm²
    height: int = field(default=0, init=False)  # cm
    effective_depth: float = field(init=False)  # cm

    def verify(self, height: int) -> bool:
        """
        Verifies if the deformation of the element is within acceptable limits.

        :return: True if the deformation is acceptable, False otherwise
        :rtype: bool
        """
        self.height = height
        self.effective_depth = self.height - self.effective_depth_discount
        return self.long_term_deflection <= self.acceptable_deflection

    @property
    def design_load(self) -> float:
        """
        Calculates the design load for the element (kN/cm²), based on the almost permanent combination of loads, according to ABNT NBR 6118 - Section 11.8.3.1 - item a.
        """
        load_kn_m2 = almost_permanent_combination_els(
            self.permanent_load, self.variable_load, self.usage
        )
        return load_kn_m2 / 10_000  # Convert kN/m² to kN/cm²

    @property
    def cracking_moment(self) -> float:
        """
        Calculates the cracking moment for the element (kN.cm), according to ABNT NBR 6118 - Section 17.3.1.
        """
        tensile_strength = self.concrete.fct_m  # kN/cm²
        moment_of_inertia = section.moment_of_inertia(self.width, self.height)
        distance_to_tension_fiber = self.height / 2.0
        return calculate_cracking_moment(
            tensile_strength, distance_to_tension_fiber, moment_of_inertia
        )

    @property
    @abstractmethod
    def service_moment(self) -> float:
        """The service moment (kN.cm) is the bending moment that the element experiences under service loads."""

    @property
    def is_cracked(self) -> bool:
        """
        Determines if the element is cracked based on the comparison of the service moment and the cracking moment.

        :return: True if the element is cracked, False otherwise
        :rtype: bool
        """
        return self.service_moment > self.cracking_moment

    @property
    def equivalent_moment_of_inertia(self) -> float:
        """
        Get the equivalent or gross moment of inertia of the cross-section.

        This property calculates the equivalent moment of inertia using Branson's formula to model the transition behavior between Stage I (not cracked) and Stage II (fully cracked) under service loads.

        According to ABNT NBR 6118 - Section: 17.3.2.1.1

        Returns:
            float: The effective equivalent moment of inertia, capped at the gross section moment of inertia (Ic).
        """
        gross_section_moment_of_inertia = section.moment_of_inertia(
            self.width, self.height
        )
        if not self.is_cracked:
            return gross_section_moment_of_inertia

        # FIXME after resolving the following TODO, use Steel.elastic_modulus directly instead of any_steel
        any_steel = Steel.CA25  # TODO make the elastic module for the steel a static property, as it is the same for all types
        modular_ratio = any_steel.elastic_modulus / self.concrete.ecs

        cracked_section_moment_of_inertia = section.cracked_section_moment_of_inertia(
            self.width,
            self.effective_depth,
            self.tensioned_reinforcement_area,
            modular_ratio,
            self.compressed_reinforcement_area,
            self.effective_depth_compressed,
        )
        moments_ratio = self.cracking_moment / self.service_moment
        equivalent_moment_of_inertia = (
            moments_ratio**3 * gross_section_moment_of_inertia
        ) + ((1 - moments_ratio**3) * cracked_section_moment_of_inertia)
        return min(equivalent_moment_of_inertia, gross_section_moment_of_inertia)

    @property
    @abstractmethod
    def immediate_deflection(self) -> float:
        """
        Calculate the immediate elastic deflection of the structural element.

        Unifies the elastic deflection models for both beams and slabs using
        the boundary condition factor (alpha).

        References:
        -----------
        Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado":
        - Beams (Chapter 4): Section 4.8.2.3, Eq. 4.26 (p. 199)
        - Slabs (Chapter 7): Section 7.3.7.2.1, Eq. 7.16 (p. 331)

        Returns:
            float: Immediate elastic deflection.
        """

    @property
    @abstractmethod
    def alpha_for_deflection(self) -> float:
        """
        Get the boundary condition coefficient (alpha) for deflection calculations.

        References:
        -----------
        Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado":
        - Beams (Chapter 4): Returns the load/support factor 'alpha_c' (Section 4.8.2.3).
        - Slabs (Chapter 7): Returns the plate boundary coefficient 'alpha' from Quadro 7.2 based on aspect ratio (Section 7.3.7.2.1).

        Returns:
            float: The dimensionless coefficient dictated by the element's support conditions, geometry, and loading shape.
        """

    @property
    def long_term_deflection(self) -> float:
        """
        Calculate the total long-term deflection (t = ∞) including concrete creep effects.

        Computes the creep multiplier (fluency factor, alpha_f) based on the compression  reinforcement ratio (rho) to find the total consolidated displacement.

        Based on ABNT NBR 6118 - Section: 17.3.2.1.2 (Long-term additional deflection)

        Returns:
            float: Total long-term deflection (immediate + creep-deferred displacement).
        """
        time_coefficient = 2  # per ABNT NBR 6118 - Section 17.3.2.1.2, time coefficient for long term deflection (from t=0 to t=∞)
        rho = self.compressed_reinforcement_area / (self.width * self.effective_depth)
        fluency_factor = time_coefficient / (1 + 50 * rho)
        return (1 + fluency_factor) * self.immediate_deflection

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

    @property
    def tensioned_reinforcement_area(self):
        return self._tensioned_reinforcement_area