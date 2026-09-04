from dataclasses import dataclass, field

from src.data.carvalho.table_7_2.data import TABLE_7_2
from src.loading.deformation_checker import DeformationChecker
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)


@dataclass(kw_only=True)
class SlabDeformationChecker(DeformationChecker):
    lx: float  # span length in the x-direction (cm)
    ly: float  # span length in the y-direction (cm)
    width: int = field(default=100, init=False)  # cm
    span: float = field(default=0, init=False)  # cm

    def __post_init__(self):
        self.span = min(
            self.lx, self.ly
        )  # Use the shorter span for deflection calculations

    @property
    def service_moment(self) -> float:
        # IMPLEMENT and generate docstring
        return 1  # FIXME Placeholder value, should be calculated based on the element's loading and geometry

    @property
    def immediate_deflection(self) -> float:
        alpha = self.alpha_for_deflection
        ecs_kn_cm2 = self.concrete.ecs / 10  # MPa to kN/cm²
        elastic_deflection = (
            (self.design_load * self.span) / (ecs_kn_cm2 * self.height**3) * alpha
        )
        return elastic_deflection * (
            section.moment_of_inertia(self.width, self.height)
            / self.equivalent_moment_of_inertia
        )

    @property
    def alpha_for_deflection(self) -> float:
        """
        Get the boundary condition coefficient (alpha) for slab elastic deflection.

        Looks up or interpolates the deflection coefficient from Quadro 7.2 based on the slab's dimensions ratio and support conditions case.

        Based on Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado" - Section 7.3.7.2.1 (Quadro 7.2, p. 332).

        Returns:
            float: Dimensionless deflection coefficient (alpha).
        """
        return TABLE_7_2.get_alpha(self.dimensions_ratio, self.supporting_case)

    @property
    def dimensions_ratio(self) -> float:
        """
        Calculate the ratio of the slab's dimensions (biggest dimension / smallest dimension).

        Based on Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado" - Section 7.3.7.2.1.

        Returns:
            float: Ratio of the slab's dimensions.
        """
        biggest = max(self.lx, self.ly)
        smallest = min(self.lx, self.ly)
        return biggest / smallest

    @property
    def supporting_case(self) -> int:
        # IMPLEMENT and docstring
        return 1  # FIXME Placeholder value, should be determined based on the element's support conditions (Quadro 7.2, p.332 - "Estruturas Usuais de Concreto Armado")
