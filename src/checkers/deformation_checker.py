from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.loading.forces import (
    calculate_cracking_moment,
)
from src.logger import log_operation, log_property, logger_label
from src.properties.concrete import Concrete
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel


@logger_label("Deformation Checker for {id}")
@dataclass(kw_only=True)
class DeformationChecker(ABC):
    """
    Excessive deformation verification for linear elements, according to ELS (Service Limit State) criteria, based on ABNT NBR 8681 - Section 7.3.2.

    For slabs (superficial elements), ABNT NBR 6118 - Section 19.3.1, redirects to the linear elements verification
    """

    permanent_load: float  # kN/m
    variable_load: float  # kN/m
    concrete: Concrete
    span: float  # cm
    width: float  # cm
    effective_depth_discount: float  # cm
    compressed_reinforcement_area: float  # cm²
    effective_depth_compressed: float  # cm²
    tensioned_reinforcement_area: float  # cm²
    height: float = field(default=0, init=False)  # cm
    effective_depth: float = field(init=False)  # cm
    id: str = field(default="")  # Optional identifier for logging purposes

    def verify(self, height: float) -> bool:
        """Verify whether the deformation of the element is within acceptable limits.

        Args:
            height: Cross-section height to evaluate (cm).

        Returns:
            True if the long-term deflection is within the acceptable limit.
        """
        self.height = height
        self.effective_depth = self.height - self.effective_depth_discount
        result = self.long_term_deflection <= self.acceptable_deflection
        log_operation(
            f"Acceptable deflection = {self.acceptable_deflection:.2f} cm; "
            f"Result = {'PASS' if result else 'FAIL'}"
        )
        return result

    @property
    @abstractmethod
    def design_load(self) -> float:
        """
        Calculates the design load for the element (kN/cm² or kN/cm), based on the almost permanent combination of loads, according to ABNT NBR 6118 - Section 11.8.3.1 - item a.
        """

    @property
    def cracking_moment(self) -> float:
        """
        Calculates the cracking moment for the element (kN.cm), according to ABNT NBR 6118 - Section 17.3.1.
        """
        tensile_strength = self.concrete.fct_m  # kN/cm²
        moment_of_inertia = section.moment_of_inertia(self.width, self.height)
        distance_to_tension_fiber = self.height / 2.0
        cracking_moment = calculate_cracking_moment(
            tensile_strength, distance_to_tension_fiber, moment_of_inertia
        )
        log_operation(f"Cracking moment = {cracking_moment:.2f} kN.cm")
        return cracking_moment

    @property
    @abstractmethod
    def service_moment(self) -> float:
        """The service moment (kN.cm) is the bending moment that the element experiences under service loads."""

    @property
    def is_cracked(self) -> bool:
        """Determine whether the element is cracked by comparing the service moment to the cracking moment."""
        return self.service_moment > self.cracking_moment

    @property
    def equivalent_moment_of_inertia(self) -> float:
        """
        Get the equivalent or gross moment of inertia of the cross-section.

        This property calculates the equivalent moment of inertia using Branson's formula to model the transition behavior between Stage I (not cracked) and Stage II (fully cracked) under service loads.

        According to ABNT NBR 6118 - Section: 17.3.2.1.1

        Returns:
            Effective equivalent moment of inertia, capped at the gross section I_c (cm⁴).
        """
        gross_section_moment_of_inertia = section.moment_of_inertia(
            self.width, self.height
        )
        if not self.is_cracked:
            log_operation(
                f"Element is not cracked; using gross section moment of inertia = {gross_section_moment_of_inertia:.2f} cm⁴"
            )
            return gross_section_moment_of_inertia

        modular_ratio = Steel.elastic_modulus / self.concrete.ecs

        cracked_section_moment_of_inertia = section.cracked_section_moment_of_inertia(
            self.width,
            self.effective_depth,
            self._tensioned_reinforcement_area,
            modular_ratio,
            self.compressed_reinforcement_area,
            self.effective_depth_compressed,
        )
        moments_ratio = self.cracking_moment / self.service_moment
        equivalent_moment_of_inertia = (
            moments_ratio**3 * gross_section_moment_of_inertia
        ) + ((1 - moments_ratio**3) * cracked_section_moment_of_inertia)

        equivalent_moment_of_inertia = min(
            equivalent_moment_of_inertia, gross_section_moment_of_inertia
        )
        log_operation(
            f"Element is cracked; using equivalent moment of inertia = {equivalent_moment_of_inertia:.2f} cm⁴"
        )
        return equivalent_moment_of_inertia

    @property
    @abstractmethod
    def immediate_deflection(self) -> float:
        pass

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
        log_property(f"Fluency factor = {fluency_factor:.2f}")

        long_term_deflection = (1 + fluency_factor) * self.immediate_deflection
        log_operation(f"Long-term deflection = {long_term_deflection:.2f} cm")
        return long_term_deflection

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
    def _tensioned_reinforcement_area(self):
        return self.tensioned_reinforcement_area