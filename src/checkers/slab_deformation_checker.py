from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import override

from src.calculators.rebar_calculator import RebarCalculator
from src.checkers.deformation_check_result import DeformationCheckResult
from src.checkers.deformation_checker import DeformationChecker
from src.config import APP_CONFIG
from src.data.carvalho.table_7.data import SLAB_MOMENT_COEFFICIENTS_TABLE
from src.data.carvalho.table_7_2.data import TABLE_7_2
from src.data.carvalho.table_7_2.model import Table72
from src.loading.combination_factors import almost_permanent_reduction_factor
from src.loading.forces import (
    almost_permanent_combination_els,
    min_design_bending_moment,
)
from src.loading.superficial_loads import SuperficialLoads
from src.logger import log_operation
from src.pavement_elements.slab_edge import Edges, SupportCondition
from src.properties.section_properties_calculator import (
    SectionPropertiesCalculator as section,
)
from src.structural_elements.rectangular_beam import RectangularBeam

ASSUMED_SLAB_BAR_DIAMETER = 1.0  # cm


def _default_effective_depth_discount() -> float:
    """Get the default effective depth discount (cm) for slabs, considering the inner layer of an orthogonal reinforcement.

    Returns:
        Distance from the tensioned face to the inner layer's centroid (cm).

    References:
        ABNT NBR 6118:2026 — Section 7.4 (nominal cover)
    """
    from src.pavement_elements.slab import Slab

    covering = Slab.nominal_covering
    return covering + 1.5 * ASSUMED_SLAB_BAR_DIAMETER


@dataclass(kw_only=True)
class SlabDeformationChecker(DeformationChecker):
    lx: float  # span length in the x-direction (cm)
    ly: float  # span length in the y-direction (cm)
    usage: str
    support_conditions: dict[Edges, SupportCondition]

    width: float = field(default=100.0, init=False)  # cm
    span: float = field(init=False)  # cm

    compressed_reinforcement_area: float = field(default=0, init=False)  # cm²
    effective_depth_compressed: float = field(default=0, init=False)  # cm

    effective_depth_discount: float = field(
        default_factory=_default_effective_depth_discount, init=False
    )  # cm
    tensioned_reinforcement_area: float = field(init=False)  # cm²

    def __post_init__(self):
        self.span = min(
            self.lx, self.ly
        )  # Use the shorter span for deflection calculations

    @override
    def verify(self, height: float) -> bool:
        with self.own_weight_for_current_height(height):
            return super().verify(height)

    @override
    def result(self) -> DeformationCheckResult:
        """Snapshot the verification at the last verified height, with the slab's own weight

        Returns:
            The verification's values; ``permanent_load`` includes the own weight.

        Raises:
            ValueError: If ``verify`` has not been called yet.
        """
        with self.own_weight_for_current_height(self.height):
            return super().result()

    @contextmanager
    def own_weight_for_current_height(self, height: float):
        """Adjust the permanent load to account for the self-weight of the slab."""
        self.permanent_load += SuperficialLoads.get_concrete_element_own_weight(
            height / 100.0
        )
        try:
            yield
        finally:
            # Reset the permanent load after the context
            self.permanent_load -= SuperficialLoads.get_concrete_element_own_weight(
                height / 100.0
            )

    @property
    def service_moment(self) -> float:
        service_moment = (
            (self.coefficient_for_service_moment / 100.0)
            * self.design_load
            * self.span**2
        ) * self.width  # kN.cm
        log_operation(f"Service moment = {service_moment:.2f} kN.cm")
        return service_moment

    @property
    def design_load(self) -> float:
        load_kn_m2 = almost_permanent_combination_els(
            self.permanent_load,
            self.variable_load,
            almost_permanent_reduction_factor(self.usage),
        )
        design_load = load_kn_m2 / 10_000  # Convert kN/m² to kN/cm²
        log_operation(f"Design load = {design_load:.4f} kN/cm²")
        return design_load

    @property
    def immediate_deflection(self) -> float:
        """
        Calculate the immediate elastic deflection of the structural element.

        Unifies the elastic deflection models for both beams and slabs using
        the boundary condition factor (alpha).

        Reference:
            Carvalho & Figueiredo Filho (2014) — Section 7.3.7.2.1, Eq. 7.16 (p. 331)

        Returns:
            float: Immediate elastic deflection.
        """
        alpha = self.alpha_for_deflection
        ecs_kn_cm2 = self.concrete.ecs / 10  # MPa to kN/cm²
        elastic_deflection = (
            (self.design_load * self.span**4)
            / (ecs_kn_cm2 * self.height**3)
            * (alpha / 100)
        )
        immediate_deflection = elastic_deflection * (
            section.moment_of_inertia(self.width, self.height)
            / self.equivalent_moment_of_inertia
        )
        log_operation(f"Immediate deflection = {immediate_deflection:.2f} cm")
        return immediate_deflection

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

    @property
    @override
    def _tensioned_reinforcement_area(self):
        dummy_beam = RectangularBeam(
            self.span,
            self.width,
            self.height,
            self.concrete,
            APP_CONFIG.pavement_steel,
        )
        md_min = min_design_bending_moment(dummy_beam)  # kN.cm

        calculator = RebarCalculator(
            beam=dummy_beam,
            bending_moment=self.service_moment,
            bending_moment_position=0,
            d=self.effective_depth,
            d_compressed=self.effective_depth_compressed,
            id="Dummy for min tension rebar area calculation",
        )

        calculator.design_bending_moment = md_min
        calculator.d = self.effective_depth  # cm
        calculated_min = calculator.as1  # cm^2
        absolute_min = 0.15 / 100 * dummy_beam.width * dummy_beam.height
        return max(calculated_min, absolute_min)
