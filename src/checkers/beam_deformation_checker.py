from dataclasses import dataclass
from typing import cast

from src.checkers.deformation_checker import DeformationChecker
from src.loading.forces import almost_permanent_combination_els
from src.logger import log_operation
from src.structural_elements.rectangular_beam import RectangularBeam


@dataclass(kw_only=True)
class BeamDeformationChecker(DeformationChecker):
    structural_beam: RectangularBeam

    @property
    def service_moment(self) -> float:
        service_moment = cast(
            float, self.structural_beam.get_bending_moment(return_absmax=True)
        )  # type: ignore , kN.m
        log_operation(f"Service bending moment: {service_moment:.2f} kN.m")
        return service_moment

    @property
    def design_load(self) -> float:
        load_kn_m = almost_permanent_combination_els(
            self.permanent_load, self.variable_load
        )
        design_load = load_kn_m / 100  # Convert kN/m to kN/cm
        log_operation(f"Design load for ELS: {design_load:.2f} kN/cm")
        return design_load

    @property
    def immediate_deflection(self) -> float:
        """
        The immediate deflection (cm) is the deflection of the beam under service loads, calculated using the structural analysis of the beam via lib indeterminatebeam.
        """
        immediate_deflection = cast(
            float, self.structural_beam.get_deflection(return_absmax=True)
        )  # type: ignore , cm
        log_operation(f"Immediate deflection: {immediate_deflection:.2f} cm")
        return immediate_deflection

    # FIXME this queries structural_beam.get_deflection(return_absmax=True) from indeterminatebeam, which assumes an uncracked gross section Unlike SlabDeformationChecker, it never applies (Branson's equation).
