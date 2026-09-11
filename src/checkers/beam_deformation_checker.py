from dataclasses import dataclass
from typing import cast

from src.checkers.deformation_checker import DeformationChecker
from src.loading.forces import almost_permanent_combination_els
from src.structural_elements.rectangular_beam import RectangularBeam


@dataclass(kw_only=True)
class BeamDeformationChecker(DeformationChecker):
    structural_beam: RectangularBeam

    @property
    def service_moment(self) -> float:
        return cast(float, self.structural_beam.get_bending_moment(return_absmax=True))  # type: ignore , kN.m

    @property
    def design_load(self) -> float:
        load_kn_m = almost_permanent_combination_els(
            self.permanent_load, self.variable_load
        )
        return load_kn_m / 100  # Convert kN/m to kN/cm

    @property
    def immediate_deflection(self) -> float:
        """
        The immediate deflection (cm) is the deflection of the beam under service loads, calculated using the structural analysis of the beam via lib indeterminatebeam.
        """
        return cast(float, self.structural_beam.get_deflection(return_absmax=True))  # type: ignore , cm
