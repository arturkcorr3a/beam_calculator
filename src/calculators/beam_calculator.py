from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, cast

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.outer_support_bars import OuterSupport, anchor_outer_supports
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.calculators.support_bars import (
    SpanRange,
    carry_span_bars_to_supports,
    span_reinforcement,
)
from src.checkers.beam_deformation_checker import BeamDeformationChecker
from src.config import APP_CONFIG
from src.loading.forces import design_effort_elu
from src.logger import log_operation, logger_label
from src.pavement_elements.beam_span import Span
from src.pavement_elements.geometry_utils import Axis
from src.reinforcement.reinforcement import END_SUPPORT_TOLERANCE, Reinforcement
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam
from src.structural_elements.support import Support

if TYPE_CHECKING:
    from src.pavement_elements.continuous_beam import ContinuousBeam
    from src.pavement_elements.pillar import Pillar

SHEAR_SAMPLE_OFFSET = 0.1  # cm, inside the span, away from the support discontinuity
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
        """Dimensions the beam span by span: builds the structural model, computes forces, then coordinates each span's stirrups with the longitudinal reinforcement of its interest points and distributes the stirrups in zones along the span.

        The hogging moments at the supports are rounded for the support width (see ``_round_support_moments``); the moments used for the anchorage checks are not.

        Each interior support is dimensioned by both adjacent spans; only the governing result (see ``_keep_governing_support_results``) is stored and checked for deformation. Once chosen, each span's bottom bars are extended into its supports where needed (see ``carry_span_bars_to_supports``), and then the end supports get the bars they lack to anchor the compression strut (see ``anchor_outer_supports``).
        """
        supports = self._build_supports()
        loads = self._build_loads()
        structural_beam = self._build_structural_beam()
        analysis = analyse_beam(structural_beam, supports, loads)

        interest_points = self._round_support_moments(
            self._interest_points(analysis), analysis, structural_beam
        )
        moment_zeros = tuple(analysis.moment_zeros())  # cm
        self._build_stirrups(structural_beam, analysis)

        results: list[tuple[float, RebarCalculator]] = []
        span_calculators: list[list[RebarCalculator]] = []
        span_support_moments: list[tuple[float, ...]] = []
        for span_index, (span, start, end) in enumerate(self._span_ranges()):
            support_moments = self._support_moments(
                analysis, structural_beam, span_index
            )  # kN.m
            span_support_moments.append(support_moments)
            points = [
                (position, moment)
                for position, moment in interest_points
                if start <= position <= end
            ]
            if not points:
                points = self._round_support_moments(
                    [self._span_extreme(analysis, start, end)],
                    analysis,
                    structural_beam,
                )
                log_operation(
                    f"No interest point in span {start:.2f}-{end:.2f} cm; using its greatest moment"
                )

            calculators: list[RebarCalculator] = []
            for position, moment in points:
                log_operation(f"Interest point: {moment:.2f} kN.m at {position:.2f} cm")
                calculators.append(
                    self._build_rebar_calculator(
                        structural_beam,
                        moment,
                        position,
                        moment_zeros,
                        support_moments,
                        analysis.positions_for_moment,
                    )
                )
            coordinate_span(calculators, span.stirrups)
            span_calculators.append(calculators)
            span.stirrups.distribute(analysis, start, end)
            results.extend(
                (position, calculator)
                for (position, _), calculator in zip(points, calculators, strict=True)
            )

        self._beam.analysis = analysis
        self._beam.reinforcement = []
        self._beam.rebar_calculators = []
        for position, calculator in self._keep_governing_support_results(results):
            self._store_reinforcement(calculator)
            self._beam.rebar_calculators.append(calculator)
            self._verify_deformation(structural_beam, analysis, calculator, position)
        carry_span_bars_to_supports(self._beam.reinforcement, self._support_spans())
        self._beam.reinforcement += anchor_outer_supports(
            structural_beam,
            self._beam.reinforcement,
            self._outer_supports(
                structural_beam,
                analysis,
                span_calculators,
                moment_zeros,
                span_support_moments,
            ),
        )

    def _outer_supports(
        self,
        structural_beam: RectangularBeam,
        analysis: BeamAnalysis,
        span_calculators: list[list[RebarCalculator]],
        moment_zeros: tuple[float, ...],
        support_moments: list[tuple[float, ...]],
    ) -> list[OuterSupport]:
        """Collect the efforts and section data at the beam's end supports

        V_Sd is the design shear just inside the span (SHEAR_SAMPLE_OFFSET from the support). The section data come from the span's positive bars or, without them, from the span's point with the smallest d (the one its stirrups were sized for).

        Args:
            span_calculators: Each span's coordinated calculators, left to right.
            moment_zeros: Positions along the beam where the moment is zero (cm).
            support_moments: Each span's characteristic moment on each support (kN.m), left to right (see ``_support_moments``).
        """
        spans = self._support_spans()
        candidates = [(spans[0], 0, 1.0), (spans[-1], len(spans), -1.0)]
        outer: list[OuterSupport] = []
        for span, support_index, direction in candidates:
            support = structural_beam.supports[support_index]
            if not support.is_extremity(structural_beam.length):
                continue
            if any(o.support_index == support_index for o in outer):
                continue
            source = self._section_source(span, span_calculators[spans.index(span)])
            shear = analysis.shear_force(
                support.center + direction * SHEAR_SAMPLE_OFFSET
            )  # kN
            outer.append(
                OuterSupport(
                    support_index=support_index,
                    span=span,
                    support_moment=support_moments[spans.index(span)][support_index],
                    design_shear=design_effort_elu(abs(shear)),
                    effective_depth=cast(float, source.effective_depth),
                    stress_block_depth=cast(float, source.stress_block_depth),
                    moment_shift=cast(float, source.moment_shift),
                    stirrup_diameter=cast(float, source.stirrup_diameter),
                    moment_zeros=moment_zeros,
                )
            )
        return outer

    def _support_moments(
        self,
        analysis: BeamAnalysis,
        structural_beam: RectangularBeam,
        span_index: int,
    ) -> tuple[float, ...]:
        """Reads the characteristic moment on each support, as seen by one span (kN.m).

        A support with a rotational spring has a moment jump, so the span reads the side facing it: its start support from the right and its end support from the left. The other supports are read from the left.

        Args:
            span_index: Index of the span; it rests on supports ``span_index`` and ``span_index + 1``.
        """
        return tuple(
            analysis.bending_moment(support.center, from_right=index == span_index)
            for index, support in enumerate(structural_beam.supports)
        )

    def _section_source(
        self, span: SpanRange, calculators: list[RebarCalculator]
    ) -> Reinforcement:
        """Return the reinforcement whose d, y, a_l and stirrup diameter describe the span at its end support

        The span's positive bars, if stored; otherwise the tensioned bars of the span's point with the smallest d.
        """
        positive = span_reinforcement(self._beam.reinforcement, span)
        if positive is not None:
            return positive
        smallest = min(calculators, key=lambda calculator: calculator.d)
        return smallest.tensioned_reinforcement

    def _support_spans(self) -> list[SpanRange]:
        """Returns each span's extent with the indices of its supports, left to right; span i rests on supports i and i + 1."""
        return [
            SpanRange(start, end, index, index + 1)
            for index, (_, start, end) in enumerate(self._span_ranges())
        ]

    def _interest_points(self, analysis: BeamAnalysis) -> list[tuple[float, float]]:
        """Finds the dominant bending-moment extreme per segment along the beam.

        Extremes on an interior support are split into one point on each side of it (see ``_split_support_points``), so both adjacent spans dimension them.

        Returns:
            `(position, moment)` pairs (position in cm, moment in kN.m), sorted left to right.
        """
        return self._split_support_points(
            analysis.moment_extremes_per_segment(), analysis
        )

    def _round_support_moments(
        self,
        points: list[tuple[float, float]],
        analysis: BeamAnalysis,
        structural_beam: RectangularBeam,
    ) -> list[tuple[float, float]]:
        """Rounds the hogging moment of the points on a support, as allowed by NBR 6118:2026 item 14.6.3 (Figure 14.6).

        The support has a width, not a single point, so the peak of the moment diagram over it is reduced by ``ΔM = R·t/8``, with R the support reaction and t the support width along the beam. The reduced moment never changes sign. Positive moments and points away from the supports are kept as they are.

        Args:
            points: `(position, moment)` pairs (position in cm, moment in kN.m, sagging positive).
            analysis: Solved beam, read for the support reactions.
            structural_beam: Beam whose supports give the pillar widths.
        """
        rounded: list[tuple[float, float]] = []
        for position, moment in points:
            support = next(
                (
                    support
                    for support in structural_beam.supports
                    if abs(position - support.center)
                    <= SUPPORT_SPLIT_OFFSET + END_SUPPORT_TOLERANCE
                ),
                None,
            )
            if support is None or moment >= 0:
                rounded.append((position, moment))
                continue
            reaction = analysis.reaction(support.center)  # kN
            width = support.right - support.left  # cm
            reduction = reaction * width / 8 / 100  # kN.m
            reduced = min(moment + reduction, 0.0)  # kN.m
            log_operation(
                f"Support at {support.center:.2f} cm: moment rounded from {moment:.2f} to {reduced:.2f} kN.m (R = {reaction:.2f} kN, t = {width:.2f} cm)"
            )
            rounded.append((position, reduced))
        return rounded

    def _span_extreme(
        self, analysis: BeamAnalysis, start: float, end: float
    ) -> tuple[float, float]:
        """Finds the bending moment with the greatest absolute value inside a span.

        The search stops SUPPORT_SPLIT_OFFSET short of each span end, so a maximum on a support lands inside this span, like the points of ``_split_support_points``.

        Args:
            start: Span start along the beam (cm).
            end: Span end along the beam (cm).

        Returns:
            `(position, moment)` pair (position in cm, moment in kN.m).
        """
        return analysis.moment_extreme_in_range(
            start + SUPPORT_SPLIT_OFFSET, end - SUPPORT_SPLIT_OFFSET
        )

    def _split_support_points(
        self, points: list[tuple[float, float]], analysis: BeamAnalysis
    ) -> list[tuple[float, float]]:
        """Splits every point on an interior support into two, SUPPORT_SPLIT_OFFSET to its left and right.

        Each takes the support's moment on its own side (they differ where a rotational spring makes the moment jump). Points at the beam ends and elsewhere are kept as they are.

        Args:
            points: `(position, moment)` pairs (position in cm, moment in kN.m).
            analysis: Solved beam, read for the moment on each side of the support.
        """
        interior_supports = self._get_interior_supports()  # cm
        split_points: list[tuple[float, float]] = []
        for position, moment in points:
            support = next(
                (
                    support
                    for support in interior_supports
                    if abs(position - support) <= END_SUPPORT_TOLERANCE
                ),
                None,
            )
            if support is not None:
                split_points.append(
                    (position - SUPPORT_SPLIT_OFFSET, analysis.bending_moment(support))
                )
                split_points.append(
                    (
                        position + SUPPORT_SPLIT_OFFSET,
                        analysis.bending_moment(support, from_right=True),
                    )
                )
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
            span.characteristic_shear_force = max_shear_force
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
        # FIXME dont consider effective length caps on inner pillars
        axis = cast(Axis, self._beam.axis)
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
                ].calculate_stiffness_for_beam_supporting(axis),
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
        steel = APP_CONFIG.pavement_steel
        return RectangularBeam(
            length,
            self._beam.width,
            self._beam.height,
            steel,
            self.label,
            supports=self._build_support_geometry(),
        )

    def _build_support_geometry(self) -> list[Support]:
        """Builds the extent of each pillar along the beam, ordered left to right.

        Centers sit on the theoretical supports (cumulative effective lengths, cm); faces sit half the pillar's parallel extent to each side.
        """
        axis = cast(Axis, self._beam.axis)
        centers = [0.0] + [end for _, _, end in self._span_ranges()]
        supports: list[Support] = []
        for center, pillar_id in zip(centers, self._support_pillar_ids(), strict=True):
            half_width = (
                self._pillar_registry[pillar_id].get_parallel_extent(axis) / 2
            )  # cm
            supports.append(Support(center, center - half_width, center + half_width))
        return supports

    def _build_rebar_calculator(
        self,
        structural_beam: RectangularBeam,
        bending_moment: float,
        bending_moment_position: float,
        moment_zeros: tuple[float, ...],
        support_moments: tuple[float, ...],
        moment_positions: Callable[[float], Sequence[float]],
    ) -> RebarCalculator:
        """Builds the longitudinal reinforcement calculator for a single interest point (dimensioned later by ``coordinate_span``).

        Args:
            bending_moment: Characteristic bending moment at the point (kN.m); its
                sign selects the tensioned face.
            bending_moment_position: Position of the point along the beam (cm).
            moment_zeros: Positions along the beam where the bending moment is
                zero (cm), used for the bars' anchorage.
            support_moments: Characteristic bending moment on each support
                (kN.m), left to right, used for the support anchorage checks.
            moment_positions: Returns the positions along the beam (cm) where the
                characteristic bending moment equals a given value (kN.m), used
                to stagger the tensioned bars by layer.
        """
        return RebarCalculator(
            beam=structural_beam,
            bending_moment=bending_moment,
            bending_moment_position=bending_moment_position,
            id=self.label,
            moment_zeros=moment_zeros,
            support_moments=support_moments,
            moment_positions=moment_positions,
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
            permanent_load=span.permanent_load,
            variable_load=span.variable_load,
            psi_2=span.psi_2,
            id=self.label,
        )
        is_deformation_ok = checker.verify(structural_beam.height)
        if is_deformation_ok:
            log_operation("Deformation is within acceptable limits.")
            return

        log_message = f"Deformation exceeds acceptable limits at {position:.2f} cm. Immediate deflection: {checker.immediate_deflection:.2f} cm, Long-term deflection: {checker.long_term_deflection:.2f} cm, Acceptable deflection: {checker.acceptable_deflection:.2f} cm."
        log_operation(log_message)
        raise ValueError(log_message)
