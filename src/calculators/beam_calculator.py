from __future__ import annotations

from typing import TYPE_CHECKING, cast

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.logger import log_operation, logger_label
from src.pavement_elements.beam_span import Span
from src.pavement_elements.geometry_utils import Axis
from src.reinforcement.reinforcement import END_SUPPORT_TOLERANCE
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam
    from src.pavement_elements.pillar import Pillar

SUPPORT_SPLIT_OFFSET = (
    0.01  # cm, shift of an interior-support point into each adjacent span
)


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
        """Dimensions the beam span by span: builds the structural model, computes forces, then coordinates each span's stirrups with the longitudinal reinforcement of its interest points.

        Each interior support is dimensioned by both adjacent spans; only the governing result (see ``_keep_governing_support_results``) is stored and checked for deformation.
        """
        supports = self._build_supports()
        loads = self._build_loads()
        structural_beam = self._build_structural_beam()
        analysis = analyse_beam(structural_beam, supports, loads)

        interest_points = self._interest_points(analysis)
        self._build_stirrups(structural_beam, analysis)

        results: list[tuple[float, RebarCalculator]] = []
        for span, start, end in self._span_ranges():
            points = [
                (position, moment)
                for position, moment in interest_points
                if start <= position <= end
            ]
            if not points:
                # TODO dimension the minimum reinforcement (stirrups and longitudinal) for spans without interest points
                log_operation(
                    f"No interest point in span {start:.2f}-{end:.2f} cm; stirrups not dimensioned"
                )
                continue

            calculators: list[RebarCalculator] = []
            for position, moment in points:
                log_operation(f"Interest point: {moment:.2f} kN.m at {position:.2f} cm")
                calculators.append(
                    self._build_rebar_calculator(structural_beam, moment, position)
                )
            coordinate_span(calculators, span.stirrups)
            results.extend(
                (position, calculator)
                for (position, _), calculator in zip(points, calculators, strict=True)
            )

        self._beam.reinforcement = []
        for position, calculator in self._keep_governing_support_results(results):
            self._store_reinforcement(calculator)
            self._verify_deformation(structural_beam, analysis, calculator, position)

    def _interest_points(self, analysis: BeamAnalysis) -> list[tuple[float, float]]:
        """Finds the dominant bending-moment extreme per segment along the beam.

        Extremes on an interior support are split into one point on each side of it (see ``_split_support_points``), so both adjacent spans dimension them.

        Returns:
            `(position, moment)` pairs (position in cm, moment in kN.m), sorted left to right.
        """
        return self._split_support_points(analysis.moment_extremes_per_segment())

    def _split_support_points(
        self, points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        """Splits every point on an interior support into two, SUPPORT_SPLIT_OFFSET to its left and right.

        Both keep the support's moment. Points at the beam ends and elsewhere are kept as they are.

        Args:
            points: `(position, moment)` pairs (position in cm, moment in kN.m).
        """
        interior_supports = self._get_interior_supports()  # cm
        split_points: list[tuple[float, float]] = []
        for position, moment in points:
            if any(
                abs(position - support) <= END_SUPPORT_TOLERANCE
                for support in interior_supports
            ):
                split_points.append((position - SUPPORT_SPLIT_OFFSET, moment))
                split_points.append((position + SUPPORT_SPLIT_OFFSET, moment))
            else:
                split_points.append((position, moment))
        return split_points

    def _keep_governing_support_results(
        self, results: list[tuple[float, RebarCalculator]]
    ) -> list[tuple[float, RebarCalculator]]:
        """Keeps, at each interior support, only the side with the greatest total chosen steel area (tensioned + compressed).

        Each interior support is dimensioned twice, once per adjacent span (see ``_split_support_points``). On a tie, the left side is kept. Other results are kept as they are, in order.

        Args:
            results: `(position, calculator)` pairs of the coordinated interest points (position in cm).
        """
        discarded: set[int] = set()
        for support in self._get_interior_supports():
            sides = [
                index
                for index, (position, _) in enumerate(results)
                if abs(position - support)
                <= SUPPORT_SPLIT_OFFSET + END_SUPPORT_TOLERANCE
            ]  # get the indices of the points on both sides of the support

            if len(sides) < 2:
                continue

            areas = {index: results[index][1].total_area for index in sides}  # cm²
            governing = max(sides, key=areas.__getitem__)  # first max → left on a tie
            discarded.update(index for index in sides if index != governing)

            areas_desc = " | ".join(
                f"{results[index][0]:.2f} cm: {areas[index]:.3f} cm²" for index in sides
            )
            log_operation(
                f"Support at {support:.2f} cm: kept {results[governing][0]:.2f} cm ({areas_desc})"
            )

        remaining = [
            result for index, result in enumerate(results) if index not in discarded
        ]
        return remaining

    def _get_interior_supports(self) -> list[float]:
        """Returns the positions of the supports between spans along the beam (cm), left to right."""
        return [end for _, _, end in self._span_ranges()[:-1]]

    def _span_ranges(self) -> list[tuple[Span, float, float]]:
        """Returns each span with its start and end positions along the beam (cm), left to right."""
        ranges: list[tuple[Span, float, float]] = []
        start = 0.0
        for span in self._beam.spans:
            end = start + span.get_effective_length(self._pillar_registry)
            ranges.append((span, start, end))
            start = end
        return ranges

    def _build_stirrups(
        self, structural_beam: RectangularBeam, analysis: BeamAnalysis
    ) -> None:
        """Builds the beam's stirrups, one per span (and sets it), dimensioned for the ELU design value of the maximum shear force on that span."""
        position = 0.0
        for span in self._beam.spans:
            shear_force_start = analysis.shear_force(
                position + 0.1
            )  # kN, 1 mm inside the span to avoid support discontinuity
            position += span.get_effective_length(self._pillar_registry)
            shear_force_end = analysis.shear_force(
                position - 0.1
            )  # kN, 1 mm inside the span to avoid support discontinuity

            max_shear_force = max(abs(shear_force_start), abs(shear_force_end))  # kN
            design_shear_force = design_effort_elu(max_shear_force)  # kN
            stirrup_calculator = StirrupCalculator(
                structural_beam, design_shear_force, self.label
            )

            span.set_stirrups(Stirrups(structural_beam, stirrup_calculator, self.label))

    def _build_supports(self) -> list[BeamSupport]:
        """Builds an elastic-fixed support on each pillar along the beam.

        Each support restrains horizontal and vertical translation, and its rotation is restrained by the pillar's rotational stiffness (see ``Pillar.calculate_stiffness``). Positions accumulate the spans' effective lengths (cm).

        Returns:
            One support per span boundary, ordered left to right.
        """
        axis = cast(Axis, self._beam.axis)
        concrete = APP_CONFIG.pavement_concrete
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
        concrete = APP_CONFIG.pavement_concrete
        steel = APP_CONFIG.pavement_steel
        return RectangularBeam(
            length,
            self._beam.width,
            self._beam.height,
            concrete,
            steel,
            self.label,
        )

    def _build_rebar_calculator(
        self,
        structural_beam: RectangularBeam,
        bending_moment: float,
        bending_moment_position: float,
    ) -> RebarCalculator:
        """Builds the longitudinal reinforcement calculator for a single interest point (dimensioned later by ``coordinate_span``).

        Args:
            bending_moment: Characteristic bending moment at the point (kN.m); its
                sign selects the tensioned face.
            bending_moment_position: Position of the point along the beam (cm).
        """
        return RebarCalculator(
            beam=structural_beam,
            bending_moment=bending_moment,
            bending_moment_position=bending_moment_position,
            id=self.label,
        )

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
