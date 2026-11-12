from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import count
from typing import cast

from src.analysis.beam_analysis import BeamAnalysis
from src.calculators.beam_calculator import BeamCalculator
from src.calculators.rebar_calculator import RebarCalculator
from src.config import APP_CONFIG
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.post_processor import detail_beam
from src.loading.forces import almost_permanent_combination_els
from src.loading.linear_loads import LinearLoads
from src.loading.load_component import LoadComponent, LoadKind
from src.logger import log_element, log_general, log_operation, logger_label
from src.pavement_elements.beam_span import Span
from src.pavement_elements.geometry_utils import (
    TOLERANCE,
    Alignment,
    Axis,
    between,
    get_pillar_perpendicular_range,
    ranges_overlap,
    round_up_to_multiple_of_5,
    x_coord,
    y_coord,
)
from src.pavement_elements.pillar import Pillar
from src.reinforcement.clamps import Clamps
from src.reinforcement.reinforcement import Reinforcement
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rebar import Rebar
from src.structural_elements.rectangular_beam import RectangularBeam
from src.text_table import format_table

# PAPER find reference for this value, I think they are not in NBR 6118, but should be in the classical literature - I know it's between 12 and 15
BEAM_HEIGHT_ESTIMATION_FACTOR = 12  # for pre-dimensioning

_MIN_BEAM_WIDTH_CM = 12.0  # cm — ABNT NBR 6118 §13.2.2

_MAX_PRE_SIZE_ITERATIONS = 10  # guard for the height ↔ effective span fixed point


@dataclass
class WallDefinition:
    structural: bool
    masonry_type: str
    nominal_thickness: float
    coating_thickness: int

    def get_parameters_for_load(self) -> tuple[bool, str, float, int]:
        """Returns the parameters needed for calculating the wall load."""
        return (
            self.structural,
            self.masonry_type,
            self.nominal_thickness,
            self.coating_thickness,
        )


@logger_label("{id}")
@dataclass(repr=False)
class ContinuousBeam:
    """A structural beam spanning multiple pillars along a single axis (X or Y).

    Resolves its own axis, centerline, and width-wise pillar support from pillar_ids and reference_pillar_id via resolve_and_validate(), and exposes the resulting spans between consecutive pillars.
    """

    pillar_ids: list[str]
    reference_pillar_id: str
    width: float
    alignment: Alignment
    wall: WallDefinition

    id: str = field(default="", kw_only=True)  # empty: generated from the counter
    axis: Axis | None = field(default=None, init=False)
    centerline: float | None = field(default=None, init=False)
    spans: list[Span] = field(default_factory=list[Span], init=False)
    height: float = field(default=0.0, init=False)  # cm
    reinforcement: list[Reinforcement] = field(
        default_factory=list[Reinforcement], init=False
    )
    analysis: BeamAnalysis | None = field(
        default=None, init=False
    )  # structural analysis of the last dimensioning
    rebar_calculators: list[RebarCalculator] = field(
        default_factory=list[RebarCalculator], init=False
    )  # governing calculator of each interest point, left to right
    detailing: DetailingBeam | None = field(
        default=None, init=False
    )  # bars as built, post-processed from the last dimensioning

    _counter = count(1)  # Class-level counter for auto-generating IDs

    @classmethod
    def reset_id_counter(cls) -> None:
        """Restart auto-generated ids at 1 (V1)"""
        cls._counter = count(1)

    def __repr__(self) -> str:
        """Identity only: the analysis, calculators and detailing of a dimensioned
        beam would make the full dataclass repr huge"""
        return f"ContinuousBeam(id={self.id!r}, pillar_ids={self.pillar_ids!r})"

    def __post_init__(self):
        if not self.id:
            self.id = f"V{next(self._counter)}"
        self.height = (
            self.width
        )  # Start with a square section, just so it is not zero until it is calculated
        self._validate_reference_pillar()
        self._validate_pillar_count()
        self._validate_width()

    def _validate_pillar_count(self) -> None:
        if len(self.pillar_ids) < 2:
            raise ValueError(f"Beam '{self.id}' must have at least 2 pillars.")

    def _validate_reference_pillar(self) -> None:
        """Ensures the reference pillar is included in the beam's pillar_ids."""
        if self.reference_pillar_id not in self.pillar_ids:
            raise ValueError(
                "Reference pillar ID must be included in the beam's pillar_ids."
            )

    def _validate_width(self) -> None:
        """Enforce ABNT NBR 6118 minimum beam width requirement.

        Raises:
            ValueError: If width is below 12 cm.

        References:
            ABNT NBR 6118:2014 — Section 13.2.2
        """
        if self.width < _MIN_BEAM_WIDTH_CM:
            raise ValueError(
                f"Beam '{self.id}' width must be at least {_MIN_BEAM_WIDTH_CM} cm. "
                f"Got {self.width} cm."
            )

    def clear_resolved(self) -> None:
        """Clears resolved attributes to force re-calculation. To be called after changes to the pavement"""
        self.axis = None
        self.centerline = None
        self.spans = []
        self.analysis = None
        self.rebar_calculators = []
        self.detailing = None

    # PAPER find reference for this method
    def pre_size(self, pillar_registry: dict[str, Pillar]) -> float:
        """Pre-dimension the beam height from its longest effective span

        The effective span depends on the height itself (0.3 h cap), so the
        height is iterated from the current value until it no longer changes.

        Returns:
            The chosen height (cm).

        References:
            ABNT NBR 6118:2014 — Section 14.6.2.4
        """
        height = self.height
        for _ in range(_MAX_PRE_SIZE_ITERATIONS):
            max_length = max(
                span.get_effective_length(pillar_registry, height)
                for span in self.spans
            )
            new_height = round_up_to_multiple_of_5(
                max_length / BEAM_HEIGHT_ESTIMATION_FACTOR
            )
            if new_height == height:
                break
            height = new_height

        self.height = height
        log_element(f"Chosen height = {self.height} cm")
        return self.height

    def dimension(self, pillar_registry: dict[str, Pillar]) -> None:
        """Runs structural dimensioning: builds the model, calculates reinforcement, and exports the report.

        Raises:
            ValueError: If the dimensioning fails; the message is prefixed with
                the beam id, since the calculators' messages do not name it.
        """
        log_general("Start calculation process...")
        self.detailing = None
        try:
            BeamCalculator(self, pillar_registry).run()
        except ValueError as error:
            raise ValueError(f"Beam '{self.id}': {error}") from error
        log_element(f"dimensioned {self.width:.0f} x {self.height:.0f} cm")

    def detail(self) -> DetailingBeam:
        """Post-process the dimensioned beam's bars into its detailing (see ``detail_beam``)

        The design objects (reinforcement, stirrups) are left as they are.

        Returns:
            The new detailing, also kept in ``detailing``.

        Raises:
            ValueError: If the beam has not been dimensioned or a post-processing step fails; the message is prefixed with the beam id.
        """
        try:
            self.detailing = detail_beam(self)
        except ValueError as error:
            raise ValueError(f"Beam '{self.id}': {error}") from error
        log_element(f"detailed with {len(self.detailing.bars)} bar run(s)")
        return self.detailing

    def report(self, pillar_registry: dict[str, Pillar]) -> str:
        """Describe the beam's final state after dimensioning

        Lists the section and materials, the supporting pillars, each span's geometry, loads and stirrups, and the longitudinal reinforcement of every interest point (with its hooks and anchorage clamps), grouped by span. Positions along the beam (x) accumulate the spans' effective lengths from the first theoretical support; layer heights (y) are measured from the bottom edge.

        Returns:
            Multi-line plain-text report.

        Raises:
            ValueError: If the beam has no spans or its stirrups were not set (not dimensioned).
        """
        if not self.spans or not all(hasattr(span, "stirrups") for span in self.spans):
            raise ValueError(
                f"Beam '{self.id}' has not been dimensioned. Can't report its state."
            )

        span_ranges = self._span_ranges(pillar_registry)
        title = f" Beam {self.id} — final state"
        rule = "═" * max(72, len(title) + 1)
        lines = [rule, title, rule, "", "Section & materials"]
        lines += self._report_section(span_ranges[-1][2])
        lines += ["", "Pillars"]
        lines += self._report_pillars(pillar_registry)
        lines += ["", "Spans"]
        lines += self._report_spans(pillar_registry, span_ranges)
        for span, start, end in span_ranges:
            lines += ["", f"Longitudinal reinforcement — span {self._span_name(span)}"]
            lines += self._report_reinforcement(start, end)
        return "\n".join(lines)

    def _report_section(self, length: float) -> list[str]:
        """Describe the section, materials and axis; length is the total effective length (cm)."""
        axis = cast(Axis, self.axis)
        coordinate = "y" if axis == Axis.X else "x"
        items = [
            ("b_w x h", f"{self.width:g} x {self.height:g} cm"),
            ("Concrete", APP_CONFIG.pavement_concrete.name),
            ("Steel", APP_CONFIG.pavement_steel.name),
            ("Nominal cover", f"{RectangularBeam.nominal_covering:.1f} cm"),
            (
                "Axis",
                f"{axis.name} (centerline {coordinate} = {self.centerline:.1f} cm)",
            ),
            ("Length (l_ef)", f"{length:.1f} cm"),
            ("Layer y", "from bottom edge"),
        ]
        width = max(len(key) for key, _ in items)
        return [f"  {key:<{width}}    {value}" for key, value in items]

    def _report_pillars(self, pillar_registry: dict[str, Pillar]) -> list[str]:
        """Tabulate the position and cross-section of each supporting pillar."""
        rows: list[list[str]] = []
        for pillar_id in self.pillar_ids:
            pillar = pillar_registry[pillar_id]
            rows.append(
                [
                    pillar.id,
                    f"({pillar.x:.1f}, {pillar.y:.1f})",
                    f"{pillar.width:g} x {pillar.depth:g}",
                ]
            )
        return format_table(["Pillar", "Position (cm)", "Section (cm)"], rows, "  ")

    def _report_spans(
        self,
        pillar_registry: dict[str, Pillar],
        span_ranges: list[tuple[Span, float, float]],
    ) -> list[str]:
        """Tabulate each span's range, lengths, loads and stirrups."""
        rows: list[list[str]] = []
        for span, start, end in span_ranges:
            stirrups = span.stirrups
            stirrups_description = self._describe_stirrups(stirrups)
            required_ratio = (
                "—"
                if stirrups.required_ratio is None
                else f"{stirrups.required_ratio:.4f}"
            )
            rows.append(
                [
                    self._span_name(span),
                    f"{start:.1f} – {end:.1f}",
                    f"{span.get_length(pillar_registry):.1f}",
                    f"{end - start:.1f}",
                    f"{span.permanent_load:.2f}",
                    f"{span.variable_load:.2f}",
                    f"{span.permanent_load + span.variable_load:.2f}",
                    stirrups_description,
                    required_ratio,
                ]
            )
        headers = [
            "Span",
            "x range (cm)",
            "l (cm)",
            "l_ef (cm)",
            "g (kN/m)",
            "q (kN/m)",
            "g+q (kN/m)",
            "Stirrups",
            "A_sw/s req (cm²/cm)",
        ]
        return format_table(headers, rows, "  ")

    @staticmethod
    def _describe_stirrups(stirrups: Stirrups) -> str:
        """Describe a span's stirrups, e.g. "φ8 c/13.0", listing each zone's spacing and x range (cm) when they are scaled."""
        if stirrups.diameter is None or stirrups.spacing is None:
            return "—"
        diameter = f"φ{stirrups.diameter * 10:g}"  # mm
        if len(stirrups.zones) <= 1:
            return f"{diameter} c/{stirrups.spacing:.1f}"  # cm
        zones = " | ".join(
            f"c/{zone.spacing:.1f} [{zone.start:.1f}–{zone.end:.1f}]"
            for zone in stirrups.zones
        )  # cm
        return f"{diameter} {zones}"

    def _report_reinforcement(self, start: float, end: float) -> list[str]:
        """Describe the longitudinal reinforcement centered within [start, end] (cm), left to right."""
        reinforcements = sorted(
            (r for r in self.reinforcement if start <= r.center_position <= end),
            key=lambda r: r.center_position,
        )
        if not reinforcements:
            return ["  none"]

        lines: list[str] = []
        for reinforcement in reinforcements:
            lines += self._describe_reinforcement(reinforcement)
        return lines

    def _describe_reinforcement(self, reinforcement: Reinforcement) -> list[str]:
        """Describe one face's reinforcement at an interest point: a summary line and its layer table."""
        face = "bottom" if reinforcement.is_bottom_reinforcement else "top"
        required_area = (
            "—"
            if reinforcement.required_area is None
            else f"{reinforcement.required_area:.2f} cm²"
        )
        moment_shift = (
            "—"
            if reinforcement.moment_shift is None
            else f"{reinforcement.moment_shift:.1f} cm"
        )
        summary = (
            f"  x = {reinforcement.center_position:.2f} cm · {face}"
            f" · As,req {required_area}"
            f" · As,prov {reinforcement.area:.2f} cm²"
            f" · a_l {moment_shift}"
        )

        center = reinforcement.center_position  # cm
        rows: list[list[str]] = []
        for layer in reinforcement.chosen_bars:
            if not layer.bars:
                continue
            bar = layer.bars[0]  # all bars of a layer share lengths and hooks
            rows.append(
                [
                    str(layer.layer_index),
                    f"{layer.y_centroid_position:.2f}",
                    self._describe_bars(layer.bars),
                    f"{center - bar.left_length:.1f}",
                    f"{center + bar.right_length:.1f}",
                    self._describe_hook(bar.left_hook_enabled, bar.left_hook_length),
                    self._describe_hook(bar.right_hook_enabled, bar.right_hook_length),
                    self._describe_clamps(layer.left_clamps),
                    self._describe_clamps(layer.right_clamps),
                ]
            )
        headers = [
            "Layer",
            "y (cm)",
            "Bars",
            "From (cm)",
            "To (cm)",
            "Hook L (cm)",
            "Hook R (cm)",
            "Clamps L",
            "Clamps R",
        ]
        return [summary, *format_table(headers, rows, "    ")]

    def _span_ranges(
        self, pillar_registry: dict[str, Pillar]
    ) -> list[tuple[Span, float, float]]:
        """Returns each span with its start and end positions along the beam (cm), left to right."""
        ranges: list[tuple[Span, float, float]] = []
        start = 0.0
        for span in self.spans:
            end = start + span.get_effective_length(pillar_registry)
            ranges.append((span, start, end))
            start = end
        return ranges

    @staticmethod
    def _span_name(span: Span) -> str:
        return f"{span.start_pillar_id}–{span.end_pillar_id}"

    @staticmethod
    def _describe_bars(bars: list[Rebar]) -> str:
        """Summarize bars by diameter, largest first (e.g. '2φ16 + 1φ12.5')."""
        counter = Counter(bar.diameter_mm for bar in bars)
        return " + ".join(
            f"{count}φ{diameter:g}"
            for diameter, count in sorted(counter.items(), reverse=True)
        )

    @staticmethod
    def _describe_hook(enabled: bool, length: float) -> str:
        """Summarize a side's hook as its length (cm), or 'no' if there is none."""
        return f"{length:.1f}" if enabled else "no"

    @staticmethod
    def _describe_clamps(clamps: Clamps | None) -> str:
        """Summarize a side's anchorage clamps (e.g. '1φ12.5 l=74.3'), or '—' if none."""
        if clamps is None:
            return "—"
        return f"{clamps.quantity}φ{clamps.diameter:g} l={clamps.length:.1f}"

    def resolve_and_validate(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Resolves the beam's axis, centerline, and validates that all pillars support the entire beam width and no pillars are skipped.
        """
        self._validate_pillars_exist(pillar_registry)
        self._determine_axis(pillar_registry)
        self._validate_alignment()
        self._determine_centerline(pillar_registry)
        self._validate_all_pillars_support_the_whole_beam_width(pillar_registry)
        self._validate_no_skipped_pillars(pillar_registry)
        self._build_resolved_spans()

        log_element(
            f"Longitudinal axis: {self.axis.name} ; centerline: {self.centerline:.1f} cm; {len(self.spans)} span(s)"  # type:ignore
        )

    def contains_pillar(self, pillar_id: str) -> bool:
        """Checks if the beam contains a specific pillar ID."""
        return pillar_id in self.pillar_ids

    def get_spans_between(self, start_pillar_id: str, end_pillar_id: str) -> list[Span]:
        """Returns all the spans between two pillars."""
        spans: list[Span] = []

        if (
            start_pillar_id not in self.pillar_ids
            or end_pillar_id not in self.pillar_ids
        ):
            raise ValueError(
                f"Both pillars must be part of the beam's pillar_ids. Given: '{start_pillar_id}', '{end_pillar_id}'"
            )

        start_index = self.pillar_ids.index(start_pillar_id)
        end_index = self.pillar_ids.index(end_pillar_id)

        if start_index > end_index:
            start_index, end_index = end_index, start_index

        sublist = self.pillar_ids[start_index : end_index + 1]

        for i in range(len(sublist) - 1):
            pillar_a = sublist[i]
            pillar_b = sublist[i + 1]
            for span in self.spans:
                if span.contains_pillar(pillar_a) and span.contains_pillar(pillar_b):
                    spans.append(span)
                    break

        return spans

    def load_spans(self) -> None:
        """Loads all spans based on the loads applied to their supported slabs."""
        area_m2 = self.width / 100 * self.height / 100
        own_weight = LinearLoads.get_concrete_element_own_weight(area_m2)  # kN/m
        wall_height = APP_CONFIG.ceiling_height
        wall_weight = LinearLoads.get_wall_load(
            *self.wall.get_parameters_for_load(), wall_height
        )  # kN/m
        log_operation(
            f"Loads: self-weight {own_weight:.2f} kN/m, wall {wall_weight:.2f} kN/m"
        )
        for span in self.spans:
            span.add_component(LoadComponent(LoadKind.OWN_WEIGHT, None, own_weight))
            span.add_component(LoadComponent(LoadKind.WALL, None, wall_weight))

    def get_most_loaded_span_for_els(self) -> Span:
        """Returns the span with the highest total load (permanent + variable)."""
        if not self.spans:
            raise ValueError(f"Beam '{self.id}' has no spans to evaluate.")
        most_loaded_span_for_els = max(
            self.spans,
            key=lambda span: almost_permanent_combination_els(
                span.permanent_load, span.variable_load, span.psi_2
            ),
        )
        log_operation(
            f"Most loaded span for ELS: {most_loaded_span_for_els.start_pillar_id} to {most_loaded_span_for_els.end_pillar_id} with total load {almost_permanent_combination_els(most_loaded_span_for_els.permanent_load, most_loaded_span_for_els.variable_load, most_loaded_span_for_els.psi_2):.2f} kN/m"
        )
        return most_loaded_span_for_els

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_pillars_exist(self, pillar_registry: dict[str, Pillar]) -> None:
        """Ensures all pillar_ids exist in the provided pillar_registry."""
        for pillar_id in self.pillar_ids:
            if pillar_id not in pillar_registry:
                raise ValueError(
                    f"Beam '{self.id}': pillar '{pillar_id}' does not exist in the registry."
                )

    def _determine_axis(self, pillar_registry: dict[str, Pillar]) -> Axis:
        """
        Determines the axis of the beam based on the spread of its pillars and sorts the pillar IDs accordingly.
        """
        pillars = [pillar_registry[id] for id in self.pillar_ids]

        x_coords = [pillar.x for pillar in pillars]
        y_coords = [pillar.y for pillar in pillars]
        x_spread = max(x_coords) - min(x_coords)
        y_spread = max(y_coords) - min(y_coords)

        if x_spread >= y_spread:
            axis = Axis.X
            self.pillar_ids = [
                pillar.id for pillar in sorted(pillars, key=lambda pillar: pillar.x)
            ]
        else:
            axis = Axis.Y
            self.pillar_ids = [
                pillar.id for pillar in sorted(pillars, key=lambda pillar: pillar.y)
            ]

        self.axis = axis
        return axis

    def _validate_alignment(self) -> None:
        """Validates that the beam's alignment is compatible with its axis."""
        if self.axis is None:
            raise ValueError(
                f"Beam '{self.id}' has no axis set. Can't validate alignment."
            )
        self.alignment.validate(self.axis)

    def _determine_centerline(self, pillar_registry: dict[str, Pillar]) -> float:
        """
        Calculates the centerline coordinate (cm) of the beam based on its axis, alignment and reference pillar.
        """
        reference_pillar = pillar_registry[self.reference_pillar_id]
        if self.axis == Axis.X:
            pillar_reach = reference_pillar.get_y_range()
            match self.alignment:
                case Alignment.TOP:
                    centerline = pillar_reach[1] - self.width / 2
                case Alignment.BOTTOM:
                    centerline = pillar_reach[0] + self.width / 2
                case Alignment.CENTER:
                    centerline = reference_pillar.y
                case _:
                    raise ValueError(
                        f"Invalid alignment for beam '{self.id}'. Alignment: '{self.alignment.value}'"
                    )
        elif self.axis == Axis.Y:
            pillar_reach = reference_pillar.get_x_range()
            match self.alignment:
                case Alignment.LEFT:
                    centerline = pillar_reach[0] + self.width / 2
                case Alignment.RIGHT:
                    centerline = pillar_reach[1] - self.width / 2
                case Alignment.CENTER:
                    centerline = reference_pillar.x
                case _:
                    raise ValueError(
                        f"Invalid alignment for beam '{self.id}'. Alignment: '{self.alignment.value}'"
                    )
        else:
            raise ValueError(
                f"Beam '{self.id}' has no axis set. Can't calculate centerline."
            )
        self.centerline = centerline
        return centerline

    def _validate_all_pillars_support_the_whole_beam_width(
        self, pillar_registry: dict[str, Pillar]
    ) -> None:
        """
        Validates that each pillar's perpendicular cross-section fully contains the beam's width band.
        """
        if self.axis is None or self.centerline is None:
            raise ValueError(
                f"Beam '{self.id}' has no axis or centerline set. Can't validate pillar support."
            )

        beam_low, beam_high = self._get_range()

        for pillar_id in self.pillar_ids:
            pillar = pillar_registry[pillar_id]
            pillar_low, pillar_high = get_pillar_perpendicular_range(pillar, self.axis)
            if pillar_low > beam_low + TOLERANCE or pillar_high < beam_high - TOLERANCE:
                raise ValueError(
                    f"Beam '{self.id}': pillar '{pillar.id}' cross-section "
                    f"[{pillar_low:.4f}, {pillar_high:.4f}] cm does not fully cover the beam "
                    f"width band [{beam_low:.4f}, {beam_high:.4f}] cm "
                )

    def _get_range(self) -> tuple[float, float]:
        """Returns the coordinates range of the beam perpendicular to its axis (min, max)."""
        if self.centerline is None:
            raise ValueError(
                f"Beam '{self.id}' has no centerline set. Can't calculate range."
            )
        beam_low = self.centerline - self.width / 2
        beam_high = self.centerline + self.width / 2
        return (beam_low, beam_high)

    def _validate_no_skipped_pillars(self, pillar_registry: dict[str, Pillar]) -> None:
        """
        Ensures no pillar on the same axis line is omitted from pillar_ids.
        """
        if self.axis is None:
            raise ValueError(
                f"Beam '{self.id}' has no axis set. Can't validate skipped pillars."
            )

        anchors = [pillar_registry[pillar_id] for pillar_id in self.pillar_ids]
        pillars_on_same_line = self._pillars_touching_beam(
            pillar_registry, axis=self.axis
        )

        if self.axis == Axis.X:
            pillars_on_same_line.sort(key=x_coord)
            coord_key = x_coord
            start_coord = anchors[0].x
            end_coord = anchors[-1].x
        else:
            pillars_on_same_line.sort(key=y_coord)
            coord_key = y_coord
            start_coord = anchors[0].y
            end_coord = anchors[-1].y

        beam_pillar_ids = set(self.pillar_ids)
        skipped = [
            pillar
            for pillar in pillars_on_same_line
            if pillar.id not in beam_pillar_ids
            and between(coord_key(pillar), start_coord, end_coord)
        ]

        if skipped:
            skipped_pillar_ids = ", ".join(f"'{pillar.id}'" for pillar in skipped)
            raise ValueError(
                f"Beam '{self.id}' skips pillar(s) {skipped_pillar_ids} that lie on the same  axis line between its endpoints."
            )

    def _pillars_touching_beam(
        self, pillar_registry: dict[str, Pillar], axis: Axis
    ) -> list[Pillar]:
        """
        Finds every pillar whose position or cross-section footprint intersects the beam.
        """
        beam_range = self._get_range()
        return [
            pillar
            for pillar in pillar_registry.values()
            if ranges_overlap(get_pillar_perpendicular_range(pillar, axis), beam_range)
        ]

    def _build_resolved_spans(self) -> None:
        """Builds resolved_spans from the sorted pillar_ids."""
        self.spans = [
            Span(
                beam=self,
                start_pillar_id=self.pillar_ids[i],
                end_pillar_id=self.pillar_ids[i + 1],
            )
            for i in range(len(self.pillar_ids) - 1)
        ]
