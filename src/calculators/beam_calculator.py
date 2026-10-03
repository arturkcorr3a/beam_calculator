from __future__ import annotations

from typing import TYPE_CHECKING, cast

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.logger import log_operation, logger_label
from src.pavement_elements.beam_span import Span
from src.pavement_elements.geometry_utils import Axis
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
        """Dimensions the beam: builds the structural model, computes forces, and calculates reinforcement at every interest point."""
        supports = self._build_supports()
        loads = self._build_loads()
        structural_beam = self._build_structural_beam()
        analysis = analyse_beam(structural_beam, supports, loads)

        interest_points = self._interest_points(analysis)
        stirrups = self._build_stirrups(structural_beam, analysis)

        self._beam.reinforcement = []
        for position, moment in interest_points:
            log_operation(f"Interest point: {moment:.2f} kN.m at {position:.2f} cm")
            calculator = self._calculate(
                structural_beam=structural_beam,
                stirrups=stirrups,
                bending_moment=moment,
                bending_moment_position=position,
            )
            self._store_reinforcement(calculator)
            self._verify_deformation(structural_beam, analysis, calculator, position)

    def _interest_points(self, analysis: BeamAnalysis) -> list[tuple[float, float]]:
        """Finds the dominant bending-moment extreme per segment along the beam.

        Returns:
            One `(position, moment)` per segment between bending-moment zeros
            (position in cm, moment in kN.m), sorted left to right.
        """
        return analysis.moment_extremes_per_segment()

    def _build_stirrups(
        self, structural_beam: RectangularBeam, analysis: BeamAnalysis
    ) -> Stirrups:
        """Builds the beam's stirrups, dimensioned for the ELU design value of the maximum shear force."""
        max_shear_force = analysis.max_abs_shear()  # kN
        design_shear_force = design_effort_elu(max_shear_force)  # kN
        stirrup_calculator = StirrupCalculator(
            structural_beam, design_shear_force, self.label
        )
        return Stirrups(structural_beam, stirrup_calculator, self.label)

    def _build_supports(self) -> list[BeamSupport]:
        """Builds an elastic-fixed support on each pillar along the beam.

        Each support restrains horizontal and vertical translation, and its rotation is restrained by the pillar's rotational stiffness (see ``Pillar.calculate_stiffness``). Positions accumulate the spans' effective lengths (cm).

        Returns:
            One support per span boundary, ordered left to right.
        """
        axis = cast(Axis, self._beam.axis)
        concrete = Concrete[APP_CONFIG.pavement_concrete]
        positions = [0.0]
        for span in self._beam.spans:
            positions.append(
                positions[-1] + span.get_effective_length(self._pillar_registry)
            )
        return [
            BeamSupport(
                position,
                self._pillar_registry[
                    pillar_id
                ].calculate_stiffness_for_beam_supporting(axis, concrete),
            )
            for position, pillar_id in zip(
                positions, self._support_pillar_ids(), strict=True
            )
        ]

    def _support_pillar_ids(self) -> list[str]:
        """Returns the id of the pillar under each support, ordered left to right."""
        spans = self._beam.spans
        return [spans[0].start_pillar_id] + [span.end_pillar_id for span in spans]

    def _build_loads(self) -> list[DistributedLoad]:
        """Builds a list of distributed vertical loads for each span, combining permanent and variable loads."""
        loads: list[DistributedLoad] = []
        start_position = 0.0
        for i, span in enumerate(self._beam.spans):
            end_position = start_position + span.get_effective_length(
                self._pillar_registry
            )
            total_load = (
                span.permanent_load + span.variable_load
            )  # kN/m, permanent + variable as it is ELU
            load = DistributedLoad(start_position, end_position, total_load)
            log_operation(
                f"Span {i}: permanent {span.permanent_load:.2f} kN/m, variable {span.variable_load:.2f} kN/m, total {total_load:.2f} kN/m"
            )
            loads.append(load)
            start_position = end_position
        return loads

    def _build_structural_beam(self) -> RectangularBeam:
        """Builds the RectangularBeam section used for dimensioning."""
        length = sum(
            span.get_effective_length(self._pillar_registry)
            for span in self._beam.spans
        )
        concrete = Concrete[APP_CONFIG.pavement_concrete]
        steel = Steel[APP_CONFIG.pavement_steel]
        return RectangularBeam(
            length,
            self._beam.width,
            self._beam.height,
            concrete,
            steel,
            self.label,
        )

    def _calculate(
        self,
        structural_beam: RectangularBeam,
        stirrups: Stirrups,
        bending_moment: float,
        bending_moment_position: float,
    ) -> RebarCalculator:
        """Dimensions the longitudinal reinforcement for a single interest point.

        Args:
            bending_moment: Characteristic bending moment at the point (kN.m); its
                sign selects the tensioned face.
            bending_moment_position: Position of the point along the beam (cm).
        """
        calculator = RebarCalculator(
            beam=structural_beam,
            bending_moment=bending_moment,
            stirrups=stirrups,
            bending_moment_position=bending_moment_position,
            id=self.label,
        )
        calculator.calculate()
        return calculator

    def _store_reinforcement(self, calculator: RebarCalculator) -> None:
        """Appends the point's tensioned reinforcement (and compressed, if doubly reinforced) to the beam."""
        self._beam.reinforcement.append(calculator.tensioned_reinforcement)
        if not calculator.is_singly_reinforced:
            self._beam.reinforcement.append(calculator.compressed_reinforcement)

    def _span_at(self, position: float) -> Span:
        """Returns the span containing the given position along the beam (cm)."""
        start_position = 0.0
        for span in self._beam.spans:
            end_position = start_position + span.get_effective_length(
                self._pillar_registry
            )
            if position <= end_position:
                return span
            start_position = end_position
        return self._beam.spans[-1]

    def _verify_deformation(
        self,
        structural_beam: RectangularBeam,
        analysis: BeamAnalysis,
        rebar_calculator: RebarCalculator,
        position: float,
    ) -> None:
        """Verifies the ELS deflection limit at a single interest point using its own span's loads.

        Raises:
            ValueError: If the long-term deflection at the point exceeds the limit.
        """
        span = self._span_at(position)

        effective_depth_discount = structural_beam.height - rebar_calculator.d
        checker = BeamDeformationChecker(
            analysis=analysis,
            position=position,
            tensioned_reinforcement_area=rebar_calculator.tensioned_reinforcement.area,
            compressed_reinforcement_area=rebar_calculator.compressed_reinforcement.area,
            effective_depth_compressed=rebar_calculator.d_compressed,
            effective_depth_discount=effective_depth_discount,
            span=span.get_effective_length(self._pillar_registry),
            width=structural_beam.width,
            concrete=structural_beam.concrete,
            permanent_load=span.permanent_load,
            variable_load=span.variable_load,
            id=self.label,
        )
        is_deformation_ok = checker.verify(structural_beam.height)
        if is_deformation_ok:
            log_operation("Deformation is within acceptable limits.")
            return

        log_message = f"Deformation exceeds acceptable limits at {position:.2f} cm. Immediate deflection: {checker.immediate_deflection:.2f} cm, Long-term deflection: {checker.long_term_deflection:.2f} cm, Acceptable deflection: {checker.acceptable_deflection:.2f} cm."
        log_operation(log_message)
        raise ValueError(log_message)
