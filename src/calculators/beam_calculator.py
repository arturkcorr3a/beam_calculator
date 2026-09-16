from __future__ import annotations

from typing import TYPE_CHECKING, cast

from indeterminatebeam import UDLV, Support  # type: ignore

from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.logger import log_operation, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam
    from src.pavement_elements.pillar import Pillar


@logger_label("{label}")
class BeamCalculator:
    """Bridges a ContinuousBeam (pavement domain) to RectangularBeam (structural analysis), running the full dimensioning pipeline."""

    def __init__(
        self, beam: ContinuousBeam, pillar_registry: dict[str, Pillar]
    ) -> None:
        self._beam = beam
        self._pillar_registry = pillar_registry

    @property
    def label(self) -> str:
        return self._beam.id

    def run(self) -> None:
        """Dimensions the beam: builds the structural model, computes forces, and calculates reinforcement."""
        supports = self._build_supports()
        loads = self._build_loads()
        structural_beam = self._build_structural_beam(supports, loads)
        max_bending_moment_and_position, max_shear_force = self._get_max_forces(
            structural_beam
        )
        max_bending_moment, max_bending_moment_position = (
            max_bending_moment_and_position
        )
        calculator = self._calculate(
            structural_beam=structural_beam,
            max_bending_moment=max_bending_moment,
            max_bending_moment_position=max_bending_moment_position,
            max_shear_force=max_shear_force,
        )
        self._verify_deformation(structural_beam, calculator)

    # FIXME considering all supports as pinned -> fix to include pillar coherence and rigidity
    def _build_supports(self) -> list[Support]:
        # TODO docstring after function is complete (FIXME above is resolved)
        pinned = (1, 1, 0)
        support_position = 0
        first_support = Support(support_position, pinned)
        supports = [first_support]
        for span in self._beam.spans:
            support_position += span.get_length(self._pillar_registry)
            next_support = Support(support_position, pinned)  # pyright: ignore[reportArgumentType]
            supports.append(next_support)
        return supports

    def _build_loads(self) -> list[UDLV]:
        """Builds a list of distributed vertical loads for each span, combining permanent and variable loads."""
        loads: list[UDLV] = []
        start_position = 0
        for span in self._beam.spans:
            end_position = start_position + span.get_length(self._pillar_registry)
            total_load = (
                span.permanent_load + span.variable_load
            )  # kN/m, permanent + variable as it is ELU
            load = UDLV(-total_load, (start_position, end_position))  # pyright: ignore[reportArgumentType] # negative for downward load
            loads.append(load)
            start_position = end_position
        return loads

    def _build_structural_beam(
        self,
        supports: list[Support],
        loads: list[UDLV],
    ) -> RectangularBeam:
        """Builds a RectangularBeam instance for structural analysis and dimensioning."""
        length = sum(
            span.get_length(self._pillar_registry) for span in self._beam.spans
        )
        concrete = Concrete[APP_CONFIG.pavement_concrete]
        steel = Steel[APP_CONFIG.pavement_steel]
        return RectangularBeam(
            length,
            self._beam.width,
            self._beam.height,
            concrete,
            steel,
            supports,
            loads,  # pyright: ignore[reportArgumentType]
        )

    def _get_max_forces(
        self, structural_beam: RectangularBeam
    ) -> tuple[tuple[float, float], float]:
        """Calculates the design bending moment and shear force for the given structural beam.

        Returns:
            A tuple containing the max bending moment (kN.m) and max shear force (kN).
        """
        max_bending_moment_and_position = structural_beam.get_max_bending_moment()

        max_shear_force = cast(float, structural_beam.get_shear_force(return_max=True))  # pyright: ignore[reportUnknownMemberType] # kN
        log_operation(
            f"max moment {max_bending_moment_and_position[0]:.2f} kN.m at {max_bending_moment_and_position[1]:.2f} cm and max shear {max_shear_force:.2f} kN"
        )
        return max_bending_moment_and_position, max_shear_force

    def _calculate(
        self,
        structural_beam: RectangularBeam,
        max_bending_moment: float,
        max_bending_moment_position: float,
        max_shear_force: float,
    ) -> RebarCalculator:
        design_shear_force = design_effort_elu(max_shear_force)  # kN
        stirrup_calculator = StirrupCalculator(structural_beam, design_shear_force)
        stirrups = Stirrups(structural_beam, stirrup_calculator)

        calculator = RebarCalculator(
            structural_beam, max_bending_moment, stirrups, max_bending_moment_position, self._beam.id
        )
        calculator.calculate()
        return calculator

    def _verify_deformation(
        self, structural_beam: RectangularBeam, rebar_calculator: RebarCalculator
    ) -> None:
        # ASK if this is ok (getting the most loaded span) or if I should make it by span, with each span with its own checker
        most_loaded_span = self._beam.get_most_loaded_span_for_els()

        effective_depth_discount = structural_beam.height - rebar_calculator.d
        checker = BeamDeformationChecker(
            structural_beam=structural_beam,
            tensioned_reinforcement_area=rebar_calculator.tensioned_reinforcement.area,
            compressed_reinforcement_area=rebar_calculator.compressed_reinforcement.area,
            effective_depth_compressed=rebar_calculator.d_compressed,
            effective_depth_discount=effective_depth_discount,
            span=structural_beam.length,
            width=structural_beam.width,
            concrete=structural_beam.concrete,
            permanent_load=most_loaded_span.permanent_load,
            variable_load=most_loaded_span.variable_load,
        )
        is_deformation_ok = checker.verify(structural_beam.height)
        if is_deformation_ok:
            log_operation("Deformation is within acceptable limits.")
            return

        log_operation("Deformation exceeds acceptable limits.")
        raise ValueError(
            f"Deformation exceeds acceptable limits. Immediate deflection: {checker.immediate_deflection:.2f} cm, Long-term deflection: {checker.long_term_deflection:.2f} cm, Acceptable deflection: {checker.acceptable_deflection:.2f} cm."
        )
