from dataclasses import dataclass
from typing import cast

from src.checkers.deformation_checker import DeformationChecker
from src.loading.forces import almost_permanent_combination_els
from src.logger import log_operation
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.structural_elements.rectangular_beam import RectangularBeam


@dataclass(kw_only=True)
class BeamDeformationChecker(DeformationChecker):
    structural_beam: RectangularBeam
    position: float  # cm — position along the beam length of the interest point

    @property
    def service_moment(self) -> float:
        """The service moment (kN.cm) at the interest point under service loads.

        References:
            ABNT NBR 6118:2014 — Section 17.3.1
        """
        moment_kn_m = cast(
            float,
            self.structural_beam.get_bending_moment(self.position),  # type: ignore
        )  # kN.m
        service_moment = abs(moment_kn_m) * 100.0  # kN.m -> kN.cm
        log_operation(f"Service bending moment: {service_moment:.2f} kN.cm")
        return service_moment

    @property
    def design_load(self) -> float:
        load_kn_m = almost_permanent_combination_els(
            self.permanent_load, self.variable_load
        )
        design_load = load_kn_m / 100  # Convert kN/m to kN/cm
        log_operation(f"Design load for ELS: {design_load:.2f} kN/cm")
        return design_load

    # ASK if this fix is applicable
    @property
    def immediate_deflection(self) -> float:
        """Immediate deflection (cm) at the interest point under service loads, scaled by the Branson stiffness ratio (I_gross / I_eq).

        References:
            ABNT NBR 6118:2014 — Section 17.3.2.1.1
        """
        elastic_deflection = abs(
            cast(float, self.structural_beam.get_deflection(self.position))  # type: ignore , cm
        )
        gross_moment_of_inertia = section.moment_of_inertia(self.width, self.height)
        immediate_deflection = elastic_deflection * (
            gross_moment_of_inertia / self.equivalent_moment_of_inertia
        )
        log_operation(f"Immediate deflection: {immediate_deflection:.2f} cm")
        return immediate_deflection
