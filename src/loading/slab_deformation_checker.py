from dataclasses import dataclass, field
from typing import override

from src.config import APP_CONFIG
from src.data.carvalho.table_7.data import SLAB_MOMENT_COEFFICIENTS_TABLE
from src.data.carvalho.table_7_2.data import TABLE_7_2
from src.data.carvalho.table_7_2.model import Table72
from src.elements.rectangular_beam import RectangularBeam
from src.loading.deformation_checker import DeformationChecker
from src.loading.forces import min_design_bending_moment
from src.pavement.slab_edge import Edges, SupportCondition
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.properties.steel import Steel
from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups


def _default_effective_depth_discount() -> float:
    """Get the default effective depth discount (cm) for slabs, based on ABNT NBR 6118 - Section 7.4."""
    covering = APP_CONFIG.nominal_covering
    rebar_discount_10_mm = 1
    return covering + 1.5 * rebar_discount_10_mm


@dataclass(kw_only=True)
class SlabDeformationChecker(DeformationChecker):
    lx: float  # span length in the x-direction (cm)
    ly: float  # span length in the y-direction (cm)
    support_conditions: dict[Edges, SupportCondition]

    width: int = field(default=100, init=False)  # cm
    span: float = field(init=False)  # cm

    compressed_reinforcement_area: float = field(default=0, init=False)  # cm²
    effective_depth_compressed: float = field(default=0, init=False)  # cm²

    effective_depth_discount: float = field(
        default_factory=_default_effective_depth_discount, init=False
    )  # cm
    _tensioned_reinforcement_area: float = field(init=False)  # cm²

    def __post_init__(self):
        self.span = min(
            self.lx, self.ly
        )  # Use the shorter span for deflection calculations

    @property
    def service_moment(self) -> float:
        return (
            (self.coefficient_for_service_moment / 100.0)
            * self.design_load
            * self.span**2
        ) * self.width  # kN.cm

    @property
    def immediate_deflection(self) -> float:
        alpha = self.alpha_for_deflection
        ecs_kn_cm2 = self.concrete.ecs / 10  # MPa to kN/cm²
        elastic_deflection = (
            (self.design_load * self.span**4)
            / (ecs_kn_cm2 * self.height**3)
            * (alpha / 100)
        )
        return elastic_deflection * (
            section.moment_of_inertia(self.width, self.height)
            / self.equivalent_moment_of_inertia
        )

    @property
    def coefficient_for_service_moment(self) -> float:
        """Get the coefficient for calculating the service moment based on the slab's support conditions and dimensions.

        Reference: Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado" - Tables 7.3, 7.4 and 7.5

        Returns:
            float: Coefficient for service moment calculation.
        """
        coefficients = SLAB_MOMENT_COEFFICIENTS_TABLE.get_mu(
            self.dimensions_ratio, self.supporting_case
        )
        return max(
            coefficients.mu_x, coefficients.mu_y
        )  # Use the maximum value to get the max moment

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
        """Determine the Quadro 7.2 boundary condition case (1-9) for this slab, using the slab's
        edge support conditions and dimensions.

        Based on Carvalho & Figueiredo Filho, "Estruturas Usuais de Concreto Armado" -
        Quadro 7.2 (p. 332).

        Returns:
            int: Case number (1-9).
        """
        return Table72.determine_supporting_case(
            self.support_conditions, self.lx, self.ly
        )

    # REVIEW this is working
    @property
    @override
    def tensioned_reinforcement_area(self):
        dummy_beam = RectangularBeam.__new__(RectangularBeam)
        dummy_beam.length = self.span
        dummy_beam.width = self.width
        dummy_beam.height = self.height
        dummy_beam.concrete = self.concrete
        dummy_beam.steel = Steel[APP_CONFIG.steel]
        md_min = min_design_bending_moment(dummy_beam)  # kN.cm

        dummy_stirrup_calculator = StirrupCalculator(dummy_beam, 0)
        dummy_stirrups = Stirrups(dummy_beam, dummy_stirrup_calculator)
        calculator = RebarCalculator(dummy_beam, 0, dummy_stirrups)

        calculator.design_bending_moment = md_min
        calculator.d = self.effective_depth  # cm
        calculated_min = calculator.as1  # cm^2
        absolute_min = 0.15 / 100 * dummy_beam.width * dummy_beam.height
        return max(calculated_min, absolute_min)
