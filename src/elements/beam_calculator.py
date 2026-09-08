from __future__ import annotations

from typing import TYPE_CHECKING, cast

from indeterminatebeam import DistributedLoadV, Support  # type: ignore

from src.config import APP_CONFIG
from src.elements.rectangular_beam import RectangularBeam
from src.loading.forces import design_effort_elu
from src.logger import log_operation, logger_label
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.rebar_calculator import RebarCalculator
from src.reinforcement.stirrup_calculator import StirrupCalculator
from src.reinforcement.stirrups import Stirrups

if TYPE_CHECKING:
    from src.pavement.continuous_beam import ContinuousBeam
    from src.pavement.pillar import Pillar


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
        max_bending_moment, max_shear_force = self._get_max_forces(structural_beam)
        self._calculate(structural_beam, max_bending_moment, max_shear_force)

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

    def _build_loads(self) -> list[DistributedLoadV]:
        """Builds a list of distributed vertical loads for each span, combining permanent and variable loads."""
        loads: list[DistributedLoadV] = []
        start_position = 0
        for span in self._beam.spans:
            end_position = start_position + span.get_length(self._pillar_registry)
            total_load = (
                span.permanent_load + span.variable_load
            )  # kN/m, permanent + variable as it is ELU
            load = DistributedLoadV(-total_load, (start_position, end_position))  # pyright: ignore[reportArgumentType] # negative for downward load
            loads.append(load)
            start_position = end_position
        return loads

    def _build_structural_beam(
        self,
        supports: list[Support],
        loads: list[DistributedLoadV],
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

    def _get_max_forces(self, structural_beam: RectangularBeam) -> tuple[float, float]:
        """Calculates the design bending moment and shear force for the given structural beam.

        Returns:
            A tuple containing the max bending moment (kN.m) and max shear force (kN).
        """
        max_bending_moment = cast(
            float,
            structural_beam.get_bending_moment(return_max=True),  # pyright: ignore[reportUnknownMemberType]
        )  # kN.m
        max_shear_force = cast(float, structural_beam.get_shear_force(return_max=True))  # pyright: ignore[reportUnknownMemberType] # kN
        log_operation(f"max moment {max_bending_moment:.2f} kN.m, max shear {max_shear_force:.2f} kN")
        return max_bending_moment, max_shear_force

    def _calculate(
        self,
        structural_beam: RectangularBeam,
        max_bending_moment: float,
        max_shear_force: float,
    ) -> None:
        design_shear_force = design_effort_elu(max_shear_force)  # kN
        stirrup_calculator = StirrupCalculator(structural_beam, design_shear_force)
        stirrups = Stirrups(structural_beam, stirrup_calculator)

        calculator = RebarCalculator(structural_beam, max_bending_moment, stirrups)
        calculator.calculate()
